from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from ..database import get_db
from ..services.shopping_service import ShoppingService
from ..schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingListUpdate,
    ShoppingItemCreate,
    ShoppingItemUpdate,
)
from ..dependencies.permissions import require_household_member
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
)
from ..models.user import User
from ..utils.constants import AppConstants

router = APIRouter(tags=["shopping"])


@router.post(
    "/lists", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED
)
@handle_service_errors
async def create_shopping_list(
    list_data: ShoppingListCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new shopping list"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    shopping_list = shopping_service.create_shopping_list(
        list_data=list_data,
        household_id=household_id,
        created_by=current_user.id,
    )

    return RouterResponse.created(
        data={"shopping_list": shopping_list},
        message="Shopping list created successfully",
    )


@router.get("/lists", response_model=Dict[str, Any])
@handle_service_errors
async def get_shopping_lists(
    active_only: bool = Query(True, description="Show only active shopping lists"),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household shopping lists with pagination"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)
    
    if active_only:
        lists = shopping_service.get_active_shopping_lists(household_id=household_id)
    else:
        lists = shopping_service.get_active_shopping_lists(household_id=household_id)

    return RouterResponse.success(
        data={
            "shopping_lists": lists,
            "total_count": len(lists),
            "active_only": active_only,
        }
    )


@router.get("/lists/{list_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_shopping_list_details(
    list_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get detailed shopping list with all items"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    details = shopping_service.get_shopping_list_details(list_id)

    return RouterResponse.success(data={"shopping_list": details})


@router.put("/lists/{list_id}", response_model=Dict[str, Any])
@handle_service_errors
async def update_shopping_list(
    list_id: int,
    list_updates: ShoppingListUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update shopping list details"""
    current_user, household_id = user_household

    # TODO: Add update_shopping_list method to ShoppingService
    return RouterResponse.updated(
        data={"list_id": list_id, "updates": list_updates.dict(exclude_unset=True)},
        message="Shopping list updated successfully",
    )


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def delete_shopping_list(
    list_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Delete a shopping list"""
    current_user, household_id = user_household

    # TODO: Add delete_shopping_list method to ShoppingService
    pass


@router.post(
    "/lists/{list_id}/items",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
@handle_service_errors
async def add_shopping_item(
    list_id: int,
    item_data: ShoppingItemCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Add item to shopping list"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    # Set the shopping list ID
    item_data.shopping_list_id = list_id

    item = shopping_service.add_item_to_list(
        item_data=item_data, requested_by=current_user.id
    )

    return RouterResponse.created(
        data={"shopping_item": item}, message="Item added to shopping list"
    )


@router.put("/lists/{list_id}/items/{item_id}", response_model=Dict[str, Any])
@handle_service_errors
async def update_shopping_item(
    list_id: int,
    item_id: int,
    item_updates: ShoppingItemUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update shopping item details"""
    current_user, household_id = user_household

    # TODO: Add update_shopping_item method to ShoppingService
    return RouterResponse.updated(
        data={"item_id": item_id, "updates": item_updates.dict(exclude_unset=True)},
        message="Shopping item updated successfully",
    )


@router.put("/lists/{list_id}/items/{item_id}/purchased", response_model=Dict[str, Any])
@handle_service_errors
async def mark_item_purchased(
    list_id: int,
    item_id: int,
    purchase_data: Dict[str, float] = Body(None, example={"actual_cost": 12.99}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Mark item as purchased"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    actual_cost = None
    if purchase_data:
        actual_cost = purchase_data.get("actual_cost")

    item = shopping_service.mark_item_purchased(
        item_id=item_id, actual_cost=actual_cost
    )

    return RouterResponse.updated(
        data={"shopping_item": item}, message="Item marked as purchased"
    )


@router.delete(
    "/lists/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
@handle_service_errors
async def remove_shopping_item(
    list_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Remove item from shopping list"""
    current_user, household_id = user_household

    # TODO: Add remove_shopping_item method to ShoppingService
    pass


@router.put("/lists/{list_id}/complete", response_model=Dict[str, Any])
@handle_service_errors
async def complete_shopping_trip(
    list_id: int,
    completion_data: Dict[str, Any] = Body(
        None, example={"create_expense": True, "notes": "Weekly grocery run completed"}
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Complete shopping trip and optionally create expense"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    result = shopping_service.complete_shopping_trip(
        list_id=list_id, shopper_id=current_user.id
    )

    return RouterResponse.success(
        data=result, message="Shopping trip completed successfully"
    )


@router.put("/lists/{list_id}/reassign", response_model=Dict[str, Any])
@handle_service_errors
async def reassign_shopper(
    list_id: int,
    assignment_data: Dict[str, int] = Body(..., example={"new_shopper_id": 2}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Reassign shopper for shopping list"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    new_shopper_id = assignment_data.get("new_shopper_id")
    if not new_shopper_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="new_shopper_id is required"
        )

    success = shopping_service.reassign_shopper(
        list_id=list_id, new_shopper_id=new_shopper_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shopping list not found"
        )

    return RouterResponse.updated(message="Shopper reassigned successfully")


@router.get("/lists/{list_id}/items", response_model=Dict[str, Any])
@handle_service_errors
async def get_shopping_list_items(
    list_id: int,
    category: Optional[str] = Query(None, description="Filter by item category"),
    purchased_only: bool = Query(False, description="Show only purchased items"),
    unpurchased_only: bool = Query(False, description="Show only unpurchased items"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get items from a shopping list with filtering"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    # Get full list details and extract items
    details = shopping_service.get_shopping_list_details(list_id)
    items_by_category = details.get("items_by_category", {})

    # Flatten items and apply filters
    all_items = []
    for cat_items in items_by_category.values():
        all_items.extend(cat_items)

    # Apply filters
    filtered_items = all_items

    if category:
        filtered_items = [
            item for item in filtered_items if item.get("category") == category
        ]

    if purchased_only:
        filtered_items = [item for item in filtered_items if item.get("is_purchased")]
    elif unpurchased_only:
        filtered_items = [
            item for item in filtered_items if not item.get("is_purchased")
        ]

    return RouterResponse.success(
        data={
            "items": filtered_items,
            "total_count": len(filtered_items),
            "list_id": list_id,
            "filters": {
                "category": category,
                "purchased_only": purchased_only,
                "unpurchased_only": unpurchased_only,
            },
        }
    )


@router.get("/statistics", response_model=Dict[str, Any])
@handle_service_errors
async def get_shopping_statistics(
    months_back: int = Query(3, ge=1, le=12, description="Months of data to analyze"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get shopping statistics for household"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    stats = shopping_service.get_shopping_statistics(
        household_id=household_id, months_back=months_back
    )

    return RouterResponse.success(
        data={
            "shopping_statistics": stats,
            "period_months": months_back,
        }
    )


@router.get("/me/assignments", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_shopping_assignments(
    active_only: bool = Query(True, description="Show only active assignments"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get shopping lists assigned to current user"""
    current_user, household_id = user_household
    shopping_service = ShoppingService(db)

    # Get all active lists and filter by assignment
    lists = shopping_service.get_active_shopping_lists(household_id=household_id)

    # Filter for current user assignments
    my_assignments = [
        shopping_list
        for shopping_list in lists
        if shopping_list.get("assigned_shopper") == current_user.name
    ]

    return RouterResponse.success(
        data={
            "assigned_lists": my_assignments,
            "total_assignments": len(my_assignments),
            "active_only": active_only,
        }
    )


@router.get("/config/categories", response_model=Dict[str, Any])
async def get_shopping_categories():
    """Get available shopping item categories"""
    categories = [
        {"value": "produce", "label": "Produce"},
        {"value": "dairy", "label": "Dairy"},
        {"value": "meat", "label": "Meat & Seafood"},
        {"value": "bakery", "label": "Bakery"},
        {"value": "pantry", "label": "Pantry"},
        {"value": "frozen", "label": "Frozen"},
        {"value": "beverages", "label": "Beverages"},
        {"value": "snacks", "label": "Snacks"},
        {"value": "household", "label": "Household Items"},
        {"value": "personal_care", "label": "Personal Care"},
        {"value": "other", "label": "Other"},
    ]

    return RouterResponse.success(data={"categories": categories})


@router.get("/templates", response_model=Dict[str, Any])
@handle_service_errors
async def get_shopping_list_templates(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get shopping list templates for quick list creation"""
    current_user, household_id = user_household

    # TODO: Add get_shopping_templates method to ShoppingService
    templates = [
        {
            "name": "Weekly Groceries",
            "items": [
                {"name": "Milk", "category": "dairy"},
                {"name": "Bread", "category": "bakery"},
                {"name": "Eggs", "category": "dairy"},
                {"name": "Bananas", "category": "produce"},
            ],
        },
        {
            "name": "Party Supplies",
            "items": [
                {"name": "Chips", "category": "snacks"},
                {"name": "Soda", "category": "beverages"},
                {"name": "Ice", "category": "frozen"},
            ],
        },
    ]

    return RouterResponse.success(data={"templates": templates})
