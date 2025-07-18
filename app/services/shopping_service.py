from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.shopping_list import ShoppingList, ShoppingItem
from ..models.user import User
from ..models.household_membership import HouseholdMembership
from ..schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingItemCreate,
)
from .expense_service import ExpenseService


class ShoppingService:
    def __init__(self, db: Session):
        self.db = db
        self.expense_service = ExpenseService(db)

    def create_shopping_list(
        self, list_data: ShoppingListCreate, household_id: int, created_by: int
    ) -> ShoppingList:
        """Create a new shopping list"""

        shopping_list = ShoppingList(
            name=list_data.name,
            description=list_data.description,
            store_name=list_data.store_name,
            planned_date=list_data.planned_date,
            household_id=household_id,
            created_by=created_by,
            assigned_shopper=list_data.assigned_shopper
            or self._get_next_shopper(household_id),
            is_active=True,
        )

        self.db.add(shopping_list)
        self.db.commit()
        self.db.refresh(shopping_list)

        return shopping_list

    def add_item_to_list(
        self, item_data: ShoppingItemCreate, requested_by: int
    ) -> ShoppingItem:
        """Add item to shopping list"""

        # Check for duplicates
        existing_item = (
            self.db.query(ShoppingItem)
            .filter(
                and_(
                    ShoppingItem.shopping_list_id == item_data.shopping_list_id,
                    ShoppingItem.name.ilike(f"%{item_data.name}%"),
                    ShoppingItem.is_purchased == False,
                )
            )
            .first()
        )

        if existing_item:
            # Update quantity instead of creating duplicate
            existing_item.notes = (
                f"{existing_item.notes or ''} | Additional request by {requested_by}"
            )
            self.db.commit()
            return existing_item

        item = ShoppingItem(
            name=item_data.name,
            quantity=item_data.quantity,
            category=item_data.category.value,
            estimated_cost=item_data.estimated_cost,
            notes=item_data.notes,
            is_urgent=item_data.is_urgent,
            shopping_list_id=item_data.shopping_list_id,
            requested_by=requested_by,
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        # Update list estimated total
        self._update_list_estimated_cost(item_data.shopping_list_id)

        return item

    def mark_item_purchased(
        self, item_id: int, actual_cost: Optional[float] = None
    ) -> ShoppingItem:
        """Mark item as purchased"""

        item = self.db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()
        if not item:
            raise ValueError("Item not found")

        if item.is_purchased:
            raise ValueError("Item already marked as purchased")

        item.is_purchased = True
        item.purchased_at = datetime.utcnow()

        if actual_cost is not None:
            item.actual_cost = actual_cost

        self.db.commit()
        self.db.refresh(item)

        # Check if all items are purchased
        self._check_list_completion(item.shopping_list_id)

        return item

    def complete_shopping_trip(self, list_id: int, shopper_id: int) -> Dict[str, Any]:
        """Complete shopping trip and create expense"""

        shopping_list = (
            self.db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
        )
        if not shopping_list:
            raise ValueError("Shopping list not found")

        if shopping_list.completed_at:
            raise ValueError("Shopping trip already completed")

        # Get all items
        items = (
            self.db.query(ShoppingItem)
            .filter(ShoppingItem.shopping_list_id == list_id)
            .all()
        )

        total_actual_cost = sum(
            item.actual_cost or item.estimated_cost or 0
            for item in items
            if item.is_purchased
        )

        # Mark list as completed
        shopping_list.completed_at = datetime.utcnow()
        shopping_list.is_active = False

        self.db.commit()

        # Create expense for the shopping trip
        if total_actual_cost > 0:
            expense_description = f"Groceries - {shopping_list.name}"
            if shopping_list.store_name:
                expense_description += f" at {shopping_list.store_name}"

            # Create expense using expense service
            expense = self.expense_service.create_expense_with_split(
                expense_data=type(
                    "obj",
                    (object,),
                    {
                        "description": expense_description,
                        "amount": total_actual_cost,
                        "category": "groceries",
                        "split_method": "equal_split",
                        "receipt_url": None,
                        "notes": f"Auto-generated from shopping list: {shopping_list.name}",
                    },
                )(),
                household_id=shopping_list.household_id,
                created_by=shopper_id,
            )

            return {
                "success": True,
                "message": "Shopping trip completed and expense created",
                "total_cost": total_actual_cost,
                "expense_id": expense.id,
                "items_purchased": len([item for item in items if item.is_purchased]),
            }
        else:
            return {
                "success": True,
                "message": "Shopping trip completed (no expenses recorded)",
                "total_cost": 0,
                "items_purchased": len([item for item in items if item.is_purchased]),
            }

    def get_active_shopping_lists(self, household_id: int) -> List[Dict[str, Any]]:
        """Get active shopping lists for household"""

        lists = (
            self.db.query(ShoppingList)
            .filter(
                and_(
                    ShoppingList.household_id == household_id,
                    ShoppingList.is_active == True,
                )
            )
            .order_by(desc(ShoppingList.created_at))
            .all()
        )

        result = []
        for shopping_list in lists:
            # Get item counts
            total_items = (
                self.db.query(ShoppingItem)
                .filter(ShoppingItem.shopping_list_id == shopping_list.id)
                .count()
            )

            purchased_items = (
                self.db.query(ShoppingItem)
                .filter(
                    and_(
                        ShoppingItem.shopping_list_id == shopping_list.id,
                        ShoppingItem.is_purchased == True,
                    )
                )
                .count()
            )

            # Get shopper info
            shopper = None
            if shopping_list.assigned_shopper:
                shopper = (
                    self.db.query(User)
                    .filter(User.id == shopping_list.assigned_shopper)
                    .first()
                )

            result.append(
                {
                    "id": shopping_list.id,
                    "name": shopping_list.name,
                    "store_name": shopping_list.store_name,
                    "planned_date": shopping_list.planned_date,
                    "total_items": total_items,
                    "purchased_items": purchased_items,
                    "progress_percentage": (
                        (purchased_items / total_items * 100) if total_items > 0 else 0
                    ),
                    "assigned_shopper": shopper.name if shopper else None,
                    "estimated_total": shopping_list.total_estimated_cost,
                    "created_at": shopping_list.created_at,
                }
            )

        return result

    def get_shopping_list_details(self, list_id: int) -> Dict[str, Any]:
        """Get detailed shopping list with all items"""

        shopping_list = (
            self.db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
        )
        if not shopping_list:
            raise ValueError("Shopping list not found")

        items = (
            self.db.query(ShoppingItem)
            .filter(ShoppingItem.shopping_list_id == list_id)
            .order_by(ShoppingItem.category, ShoppingItem.name)
            .all()
        )

        # Group items by category
        items_by_category = {}
        total_estimated = 0
        total_actual = 0

        for item in items:
            if item.category not in items_by_category:
                items_by_category[item.category] = []

            requester = self.db.query(User).filter(User.id == item.requested_by).first()

            item_data = {
                "id": item.id,
                "name": item.name,
                "quantity": item.quantity,
                "estimated_cost": item.estimated_cost,
                "actual_cost": item.actual_cost,
                "is_purchased": item.is_purchased,
                "is_urgent": item.is_urgent,
                "requested_by": requester.name if requester else "Unknown",
                "notes": item.notes,
                "purchased_at": item.purchased_at,
            }

            items_by_category[item.category].append(item_data)

            if item.estimated_cost:
                total_estimated += item.estimated_cost
            if item.actual_cost:
                total_actual += item.actual_cost

        # Get shopper and creator info
        shopper = None
        creator = None

        if shopping_list.assigned_shopper:
            shopper = (
                self.db.query(User)
                .filter(User.id == shopping_list.assigned_shopper)
                .first()
            )

        if shopping_list.created_by:
            creator = (
                self.db.query(User).filter(User.id == shopping_list.created_by).first()
            )

        return {
            "id": shopping_list.id,
            "name": shopping_list.name,
            "description": shopping_list.description,
            "store_name": shopping_list.store_name,
            "planned_date": shopping_list.planned_date,
            "is_active": shopping_list.is_active,
            "created_by": creator.name if creator else "Unknown",
            "assigned_shopper": shopper.name if shopper else None,
            "total_estimated_cost": total_estimated,
            "total_actual_cost": total_actual,
            "items_by_category": items_by_category,
            "total_items": len(items),
            "purchased_items": len([item for item in items if item.is_purchased]),
            "created_at": shopping_list.created_at,
            "completed_at": shopping_list.completed_at,
        }

    def _get_next_shopper(self, household_id: int) -> int:
        """FIXED: Get next person in rotation for shopping assignment using HouseholdMembership"""

        # Get all household members using proper relationship
        members = (
            self.db.query(User)
            .join(HouseholdMembership, User.id == HouseholdMembership.user_id)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                    User.is_active == True,
                )
            )
            .order_by(User.id)
            .all()
        )

        if not members:
            raise ValueError("No household members found")

        # Get last assigned shopper
        last_list = (
            self.db.query(ShoppingList)
            .filter(ShoppingList.household_id == household_id)
            .order_by(desc(ShoppingList.created_at))
            .first()
        )

        if not last_list or not last_list.assigned_shopper:
            return members[0].id

        # Find next in rotation
        current_index = 0
        for i, member in enumerate(members):
            if member.id == last_list.assigned_shopper:
                current_index = i
                break

        next_index = (current_index + 1) % len(members)
        return members[next_index].id

    def _update_list_estimated_cost(self, list_id: int):
        """Update total estimated cost for shopping list"""

        total = (
            self.db.query(ShoppingItem)
            .filter(ShoppingItem.shopping_list_id == list_id)
            .with_entities(func.sum(ShoppingItem.estimated_cost))
            .scalar()
            or 0
        )

        shopping_list = (
            self.db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
        )
        if shopping_list:
            shopping_list.total_estimated_cost = total
            self.db.commit()

    def _check_list_completion(self, list_id: int):
        """Check if all items are purchased and auto-complete if needed"""

        remaining_items = (
            self.db.query(ShoppingItem)
            .filter(
                and_(
                    ShoppingItem.shopping_list_id == list_id,
                    ShoppingItem.is_purchased == False,
                )
            )
            .count()
        )

        if remaining_items == 0:
            shopping_list = (
                self.db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
            )
            if shopping_list and not shopping_list.completed_at:
                shopping_list.completed_at = datetime.utcnow()
                shopping_list.is_active = False
                self.db.commit()

    def reassign_shopper(self, list_id: int, new_shopper_id: int) -> bool:
        """Reassign shopper for shopping list"""

        shopping_list = (
            self.db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
        )
        if not shopping_list:
            return False

        shopping_list.assigned_shopper = new_shopper_id
        self.db.commit()

        return True

    def get_shopping_statistics(
        self, household_id: int, months_back: int = 3
    ) -> Dict[str, Any]:
        """Get shopping statistics for household"""

        since_date = datetime.utcnow() - timedelta(days=months_back * 30)

        # Get completed shopping lists
        completed_lists = (
            self.db.query(ShoppingList)
            .filter(
                and_(
                    ShoppingList.household_id == household_id,
                    ShoppingList.completed_at >= since_date,
                )
            )
            .all()
        )

        total_spent = sum(
            shopping_list.total_actual_cost or 0 for shopping_list in completed_lists
        )

        # Get most active shopper
        shopper_stats = {}
        for shopping_list in completed_lists:
            shopper_id = shopping_list.assigned_shopper
            if shopper_id:
                if shopper_id not in shopper_stats:
                    shopper_stats[shopper_id] = 0
                shopper_stats[shopper_id] += 1

        most_active_shopper = None
        if shopper_stats:
            most_active_id = max(shopper_stats, key=shopper_stats.get)
            most_active_user = (
                self.db.query(User).filter(User.id == most_active_id).first()
            )
            most_active_shopper = most_active_user.name if most_active_user else None

        return {
            "total_shopping_trips": len(completed_lists),
            "total_amount_spent": total_spent,
            "average_per_trip": (
                total_spent / len(completed_lists) if completed_lists else 0
            ),
            "most_active_shopper": most_active_shopper,
            "shopping_frequency_per_month": (
                len(completed_lists) / months_back if months_back > 0 else 0
            ),
        }

    def update_shopping_list(
        self, list_id: int, list_updates: Dict[str, Any]
    ) -> ShoppingList:
        """Update shopping list metadata"""

        shopping_list = (
            self.db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
        )

        if not shopping_list:
            raise ValueError("Shopping list not found")

        if shopping_list.completed_at:
            raise ValueError("Cannot update completed shopping list")

        try:
            # Update allowed fields
            allowed_fields = {
                "name",
                "description",
                "store_name",
                "planned_date",
                "assigned_shopper",
                "total_estimated_cost",
            }

            for field, value in list_updates.items():
                if field in allowed_fields and value is not None:
                    setattr(shopping_list, field, value)

            shopping_list.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(shopping_list)

            return shopping_list

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to update shopping list: {str(e)}")

    def delete_shopping_list(self, list_id: int, deleted_by: int) -> bool:
        """Delete or deactivate a shopping list"""

        shopping_list = (
            self.db.query(ShoppingList).filter(ShoppingList.id == list_id).first()
        )

        if not shopping_list:
            return False

        # Check if user has permission (creator or assigned shopper)
        if (
            shopping_list.created_by != deleted_by
            and shopping_list.assigned_shopper != deleted_by
        ):
            raise PermissionError(
                "Only creator or assigned shopper can delete this list"
            )

        try:
            # Check if list has items
            items_count = (
                self.db.query(ShoppingItem)
                .filter(ShoppingItem.shopping_list_id == list_id)
                .count()
            )

            if items_count > 0:
                # Deactivate instead of delete to preserve history
                shopping_list.is_active = False
                shopping_list.updated_at = datetime.utcnow()

                # Add deletion note
                if shopping_list.description:
                    shopping_list.description += (
                        f" (Deleted by user on {datetime.utcnow().date()})"
                    )
                else:
                    shopping_list.description = (
                        f"Deleted by user on {datetime.utcnow().date()}"
                    )
            else:
                # Actually delete if no items
                self.db.delete(shopping_list)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to delete shopping list: {str(e)}")

    def remove_shopping_item(self, item_id: int, removed_by: int) -> bool:
        """Remove an item from shopping list"""

        item = self.db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()

        if not item:
            return False

        # Get shopping list to check permissions
        shopping_list = (
            self.db.query(ShoppingList)
            .filter(ShoppingList.id == item.shopping_list_id)
            .first()
        )

        if not shopping_list:
            return False

        # Check permissions (creator, assigned shopper, or item requester)
        allowed_users = {
            shopping_list.created_by,
            shopping_list.assigned_shopper,
            item.requested_by,
        }
        if removed_by not in allowed_users:
            raise PermissionError("Not authorized to remove this item")

        if item.is_purchased:
            raise ValueError("Cannot remove purchased items")

        try:
            self.db.delete(item)

            # Update list estimated cost
            self._update_list_estimated_cost(item.shopping_list_id)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to remove item: {str(e)}")

    def get_all_shopping_lists(
        self, household_id: int, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """Get all shopping lists (both active and completed) with pagination"""

        query = (
            self.db.query(ShoppingList)
            .filter(ShoppingList.household_id == household_id)
            .order_by(desc(ShoppingList.created_at))
        )

        # Get total count
        total_count = query.count()

        # Get lists with pagination
        lists = query.offset(offset).limit(limit).all()

        result = []
        for shopping_list in lists:
            # Get item counts
            total_items = (
                self.db.query(ShoppingItem)
                .filter(ShoppingItem.shopping_list_id == shopping_list.id)
                .count()
            )

            purchased_items = (
                self.db.query(ShoppingItem)
                .filter(
                    and_(
                        ShoppingItem.shopping_list_id == shopping_list.id,
                        ShoppingItem.is_purchased == True,
                    )
                )
                .count()
            )

            # Get creator and shopper info
            creator = None
            if shopping_list.created_by:
                creator = (
                    self.db.query(User)
                    .filter(User.id == shopping_list.created_by)
                    .first()
                )

            shopper = None
            if shopping_list.assigned_shopper:
                shopper = (
                    self.db.query(User)
                    .filter(User.id == shopping_list.assigned_shopper)
                    .first()
                )

            result.append(
                {
                    "id": shopping_list.id,
                    "name": shopping_list.name,
                    "description": shopping_list.description,
                    "store_name": shopping_list.store_name,
                    "planned_date": shopping_list.planned_date,
                    "is_active": shopping_list.is_active,
                    "total_items": total_items,
                    "purchased_items": purchased_items,
                    "progress_percentage": (
                        (purchased_items / total_items * 100) if total_items > 0 else 0
                    ),
                    "created_by": shopping_list.created_by,
                    "creator_name": creator.name if creator else "Unknown",
                    "assigned_shopper": shopping_list.assigned_shopper,
                    "shopper_name": shopper.name if shopper else None,
                    "total_estimated_cost": shopping_list.total_estimated_cost,
                    "total_actual_cost": shopping_list.total_actual_cost,
                    "created_at": shopping_list.created_at,
                    "completed_at": shopping_list.completed_at,
                    "updated_at": shopping_list.updated_at,
                    "status": (
                        "completed"
                        if shopping_list.completed_at
                        else "active" if shopping_list.is_active else "cancelled"
                    ),
                }
            )

        return {
            "shopping_lists": result,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
            "active_count": len([l for l in result if l["is_active"]]),
            "completed_count": len([l for l in result if l["completed_at"]]),
            "cancelled_count": len(
                [l for l in result if not l["is_active"] and not l["completed_at"]]
            ),
        }

    def update_shopping_item(
        self, item_id: int, item_updates: Dict[str, Any], updated_by: int
    ) -> ShoppingItem:
        """Update shopping item details"""

        item = self.db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()

        if not item:
            raise ValueError("Shopping item not found")

        # Get shopping list to check permissions and status
        shopping_list = (
            self.db.query(ShoppingList)
            .filter(ShoppingList.id == item.shopping_list_id)
            .first()
        )

        if not shopping_list:
            raise ValueError("Shopping list not found")

        if shopping_list.completed_at:
            raise ValueError("Cannot update items in completed shopping list")

        # Check permissions (creator, assigned shopper, or item requester)
        allowed_users = {
            shopping_list.created_by,
            shopping_list.assigned_shopper,
            item.requested_by,
        }
        if updated_by not in allowed_users:
            raise PermissionError("Not authorized to update this item")

        try:
            # Update allowed fields
            allowed_fields = {
                "name",
                "quantity",
                "category",
                "estimated_cost",
                "notes",
                "is_urgent",
            }

            for field, value in item_updates.items():
                if field in allowed_fields and value is not None:
                    setattr(item, field, value)

            item.updated_at = datetime.utcnow()
            self.db.commit()

            # Update list estimated cost if cost was changed
            if "estimated_cost" in item_updates:
                self._update_list_estimated_cost(item.shopping_list_id)

            self.db.refresh(item)
            return item

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to update item: {str(e)}")
