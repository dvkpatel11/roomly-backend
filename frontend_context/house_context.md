# House Page - Backend Context

## Overview

Resource tracking (groceries, supplies), guest management, house rules, and settings.

## Related Files:

## app/routers/guests.py

```python
from app.services.guest_service import GuestService
from fastapi import APIRouter, Depends, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from ..database import get_db
from ..services.approval_service import ApprovalService
from ..schemas.guest import GuestCreate
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    validate_pagination,
)
from ..models.user import User
from ..utils.constants import AppConstants, GuestPolicy

router = APIRouter(tags=["guests"])


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def register_guest(
    guest_data: GuestCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Register a new guest (requires household approval)"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    guest = approval_service.create_guest_request(
        guest_data=guest_data,
        household_id=household_id,
        hosted_by=current_user.id,
    )

    return RouterResponse.created(
        data={"guest": guest}, message="Guest registration submitted for approval"
    )


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_guests(
    upcoming_only: bool = Query(True, description="Show only upcoming guests"),
    include_pending: bool = Query(True, description="Include pending approvals"),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    guest_service = GuestService(db)
    guests = guest_service.get_household_guests(
        user_household[1], upcoming_only, include_pending, limit, offset
    )
    return RouterResponse.success(data=guests)


@router.get("/pending", response_model=Dict[str, Any])
@handle_service_errors
async def get_pending_guest_approvals(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guests pending approval"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    pending_guests = approval_service.get_pending_guest_approvals(
        household_id=household_id
    )

    return RouterResponse.success(
        data={
            "pending_guests": pending_guests,
            "count": len(pending_guests),
        }
    )


@router.get("/{guest_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_details(
    guest_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get detailed guest information"""
    current_user, household_id = user_household

    # TODO: Add get_guest_details method to ApprovalService
    # For now, return placeholder
    guest_details = {
        "guest_id": guest_id,
        "household_id": household_id,
        "message": "Guest details not yet implemented",
    }

    return RouterResponse.success(data={"guest": guest_details})


@router.put("/{guest_id}/approve", response_model=Dict[str, Any])
@handle_service_errors
async def approve_guest(
    guest_id: int,
    approval_data: Dict[str, str] = Body(None, example={"reason": "Looks good to me!"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Approve a guest request"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    result = approval_service.approve_guest(
        guest_id=guest_id, approver_id=current_user.id
    )

    return RouterResponse.success(
        data=result, message=result.get("message", "Guest approval processed")
    )


@router.put("/{guest_id}/deny", response_model=Dict[str, Any])
@handle_service_errors
async def deny_guest(
    guest_id: int,
    denial_data: Dict[str, str] = Body(
        ..., example={"reason": "Conflicts with existing plans"}
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Deny a guest request"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    reason = denial_data.get("reason", "")

    result = approval_service.deny_guest(
        guest_id=guest_id, denier_id=current_user.id, reason=reason
    )

    return RouterResponse.success(
        data=result, message=result.get("message", "Guest request denied")
    )


@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def cancel_guest_request(
    guest_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Cancel a guest request (host only)"""
    current_user, household_id = user_household

    # TODO: Add cancel_guest_request method to ApprovalService
    # This should verify the current user is the host
    pass


@router.get("/policies", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_policies(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household guest policies"""
    current_user, household_id = user_household

    # TODO: Get from household settings instead of defaults
    policies = {
        "max_overnight_guests": GuestPolicy.DEFAULT_MAX_OVERNIGHT_GUESTS,
        "max_consecutive_nights": GuestPolicy.DEFAULT_MAX_CONSECUTIVE_NIGHTS,
        "approval_required": GuestPolicy.DEFAULT_APPROVAL_REQUIRED,
        "quiet_hours_start": GuestPolicy.DEFAULT_QUIET_HOURS_START,
        "quiet_hours_end": GuestPolicy.DEFAULT_QUIET_HOURS_END,
    }

    return RouterResponse.success(data={"guest_policies": policies})


@router.put("/policies", response_model=Dict[str, Any])
@handle_service_errors
async def update_guest_policies(
    policies_data: Dict[str, Any] = Body(
        ...,
        example={
            "max_overnight_guests": 3,
            "max_consecutive_nights": 5,
            "approval_required": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Update household guest policies (admin only)"""
    current_user, household_id = user_household

    # TODO: Integrate with household service to update settings
    # For now, return success message

    return RouterResponse.updated(
        data={"updated_policies": policies_data},
        message="Guest policies updated successfully",
    )


@router.get("/calendar", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_calendar(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guest calendar showing upcoming stays"""
    current_user, household_id = user_household

    # TODO: Add get_guest_calendar method to ApprovalService
    calendar_data = {
        "start_date": start_date,
        "end_date": end_date,
        "guest_stays": [],
        "conflicts": [],
    }

    return RouterResponse.success(data={"guest_calendar": calendar_data})


@router.get("/statistics", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_statistics(
    months_back: int = Query(6, ge=1, le=24, description="Months of data to analyze"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guest statistics for household"""
    current_user, household_id = user_household

    # TODO: Add get_guest_statistics method to ApprovalService
    statistics = {
        "household_id": household_id,
        "period_months": months_back,
        "total_guest_requests": 0,
        "approved_guests": 0,
        "denied_guests": 0,
        "overnight_stays": 0,
        "average_stay_duration": 0,
        "most_active_host": None,
        "approval_rate": 0,
    }

    return RouterResponse.success(data={"guest_statistics": statistics})


@router.get("/config/relationship-types", response_model=Dict[str, Any])
async def get_relationship_types():
    """Get available guest relationship types"""
    relationship_types = [
        {"value": "friend", "label": "Friend"},
        {"value": "family", "label": "Family"},
        {"value": "partner", "label": "Partner"},
        {"value": "colleague", "label": "Colleague"},
        {"value": "acquaintance", "label": "Acquaintance"},
        {"value": "other", "label": "Other"},
    ]

    return RouterResponse.success(data={"relationship_types": relationship_types})
```

## app/routers/shopping.py

```python
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
    validate_pagination,
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

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    if active_only:
        lists = shopping_service.get_active_shopping_lists(household_id=household_id)
    else:
        # TODO: Add get_all_shopping_lists method to ShoppingService
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
```

## app/routers/households.py

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..services.household_service import HouseholdService
from ..schemas.household import (
    HouseholdCreate,
    HouseholdUpdate,
    HouseholdInvitation,
)
from ..dependencies.permissions import (
    require_household_member,
    require_household_admin,
)
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
)
from ..models.user import User
from ..models.enums import HouseholdRole
from .auth import get_current_user

router = APIRouter(tags=["households"])


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def create_household(
    household_data: HouseholdCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new household with current user as admin"""
    household_service = HouseholdService(db)

    household = household_service.create_household(
        household_data=household_data, creator_id=current_user.id
    )

    return RouterResponse.created(
        data={"household": household}, message="Household created successfully"
    )


@router.get("/me", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_household(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get current user's household information"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    details = household_service.get_household_details(household_id)

    return RouterResponse.success(data={"household": details})


@router.get("/{household_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_details(
    household_id: int,
    user_household: tuple[User, int] = Depends(require_household_member),
    db: Session = Depends(get_db),
):
    household_service = HouseholdService(db)

    if not household_service.check_member_permissions(current_user.id, household_id):
        raise HTTPException(403, "Access denied")

    household_service = HouseholdService(db)
    details = household_service.get_household_details(household_id)
    return RouterResponse.success(data={"household": details})


@router.put("/me", response_model=Dict[str, Any])
@handle_service_errors
async def update_my_household(
    household_update: HouseholdUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Update current user's household settings (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    household = household_service.update_household_settings(
        household_id=household_id,
        settings_update=household_update,
        updated_by=current_user.id,
    )

    return RouterResponse.updated(
        data={"household": household}, message="Household updated successfully"
    )


@router.get("/me/members", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_household_members(
    include_stats: bool = Query(False, description="Include member statistics"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household members with optional statistics"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    members = household_service.get_household_members(household_id)

    return RouterResponse.success(
        data={
            "members": members,
            "total_count": len(members),
            "admin_count": len([m for m in members if m["role"] == "admin"]),
            "active_count": len([m for m in members if m["is_active"]]),
        }
    )


@router.post("/me/members", response_model=Dict[str, Any])
@handle_service_errors
async def add_member_to_my_household(
    member_data: Dict[str, Any] = Body(..., example={"user_id": 2, "role": "member"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Add user to household (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    user_id = member_data.get("user_id")
    role = member_data.get("role", "member")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required"
        )

    # Validate role
    if role not in [r.value for r in HouseholdRole]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in HouseholdRole]}",
        )

    result = household_service.add_member_to_household(
        household_id=household_id,
        user_id=user_id,
        role=role,
        added_by=current_user.id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add member"
        )

    return RouterResponse.success(
        message=f"Member added successfully with role: {role}"
    )


@router.delete("/me/members/{user_id}", response_model=Dict[str, Any])
@handle_service_errors
async def remove_member_from_my_household(
    user_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Remove member from household (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    result = household_service.remove_member_from_household(
        household_id=household_id,
        user_id=user_id,
        removed_by=current_user.id,
    )

    return RouterResponse.success(data=result, message="Member removal completed")


@router.put("/me/members/{user_id}/role", response_model=Dict[str, Any])
@handle_service_errors
async def update_member_role(
    user_id: int,
    role_data: Dict[str, str] = Body(..., example={"role": "admin"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Update member role (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    new_role = role_data.get("role")
    if not new_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="role is required"
        )

    # Validate role
    if new_role not in [r.value for r in HouseholdRole]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in HouseholdRole]}",
        )

    success = household_service.update_member_role(
        household_id=household_id,
        user_id=user_id,
        new_role=new_role,
        updated_by=current_user.id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update member role",
        )

    return RouterResponse.updated(message=f"Member role updated to {new_role}")


@router.get("/me/health-score", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_household_health_score(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household health score"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    health_score = household_service.calculate_household_health_score(household_id)

    return RouterResponse.success(data={"health_score": health_score})


@router.get("/me/statistics", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_household_statistics(
    months_back: int = Query(6, ge=1, le=24, description="Months of data to analyze"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive household statistics"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    stats = household_service.get_household_statistics(household_id)

    return RouterResponse.success(
        data={
            "statistics": stats,
            "period_months": months_back,
            "household_id": household_id,
        }
    )


@router.post("/me/invite", response_model=Dict[str, Any])
@handle_service_errors
async def invite_member_to_household(
    invitation: HouseholdInvitation,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Send invitation to join household (admin only)"""
    current_user, household_id = user_household

    # TODO: Integrate with email service to send actual invitation
    # For now, return success message

    return RouterResponse.success(
        data={
            "invitation": {
                "email": invitation.email,
                "role": invitation.role,
                "invited_by": current_user.name,
                "household_id": household_id,
            }
        },
        message=f"Invitation sent to {invitation.email}",
    )


@router.post("/join", response_model=Dict[str, Any])
@handle_service_errors
async def join_household_by_invitation(
    join_data: Dict[str, Any] = Body(
        ..., example={"invitation_code": "abc123", "household_id": 1}
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Join household using invitation code"""
    household_service = HouseholdService(db)

    invitation_code = join_data.get("invitation_code")
    household_id = join_data.get("household_id")

    if not invitation_code or not household_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invitation_code and household_id are required",
        )

    # TODO: Validate invitation code
    # For now, just add user as member

    success = household_service.add_member_to_household(
        household_id=household_id,
        user_id=current_user.id,
        role="member",
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to join household"
        )

    return RouterResponse.success(message="Successfully joined household")


@router.post("/me/leave", response_model=Dict[str, Any])
@handle_service_errors
async def leave_my_household(
    confirm: bool = Body(False, description="Confirmation flag"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Leave current household"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must confirm leaving by setting confirm=true",
        )

    result = household_service.remove_member_from_household(
        household_id=household_id,
        user_id=current_user.id,
        removed_by=current_user.id,  # Self-removal
    )

    return RouterResponse.success(data=result, message="Successfully left household")


@router.post("/me/transfer-ownership", response_model=Dict[str, Any])
@handle_service_errors
async def transfer_household_ownership(
    transfer_data: Dict[str, int] = Body(..., example={"new_admin_id": 2}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Transfer household ownership to another member (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    new_admin_id = transfer_data.get("new_admin_id")
    if not new_admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="new_admin_id is required"
        )

    success = household_service.transfer_household_ownership(
        household_id=household_id,
        current_admin_id=current_user.id,
        new_admin_id=new_admin_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to transfer ownership",
        )

    return RouterResponse.success(
        message="Household ownership transferred successfully"
    )


@router.get("/config/roles", response_model=Dict[str, Any])
async def get_household_roles():
    """Get available household roles"""
    roles = [
        {"value": role.value, "label": role.value.title()} for role in HouseholdRole
    ]

    return RouterResponse.success(data={"roles": roles})


@router.get("/me/summary", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get quick household summary for dashboard"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    # Get basic household info
    details = household_service.get_household_details(household_id)
    health_score = household_service.calculate_household_health_score(household_id)

    summary = {
        "household": {
            "id": details["id"],
            "name": details["name"],
            "member_count": details["member_count"],
            "user_role": next(
                (m["role"] for m in details["members"] if m["id"] == current_user.id),
                "member",
            ),
        },
        "health_score": health_score["overall_score"],
        "quick_stats": {
            "active_members": details["member_count"],
            "health_score": health_score["overall_score"],
            "improvement_suggestions": health_score["improvement_suggestions"][
                :2
            ],  # Top 2
        },
    }

    return RouterResponse.success(data=summary)
```

## app/schemas/guest.py

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class GuestBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    relationship_to_host: str
    check_in: datetime
    check_out: Optional[datetime] = None
    is_overnight: bool = False
    notes: Optional[str] = None

class GuestCreate(GuestBase):
    pass

class GuestResponse(GuestBase):
    id: int
    household_id: int
    hosted_by: int
    is_approved: bool
    approved_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
```

## app/schemas/guest_approval.py

```python
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class GuestApprovalCreate(BaseModel):
    guest_id: int
    approved: bool
    reason: Optional[str] = Field(None, max_length=500)


class GuestApprovalResponse(BaseModel):
    id: int
    guest_id: int
    user_id: int
    user_name: str
    approved: bool
    reason: Optional[str]
    created_at: datetime
```

## app/schemas/shopping_list.py

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ShoppingItemCategory(str, Enum):
    PRODUCE = "produce"
    DAIRY = "dairy"
    MEAT = "meat"
    PANTRY = "pantry"
    FROZEN = "frozen"
    BEVERAGES = "beverages"
    SNACKS = "snacks"
    HOUSEHOLD = "household"
    PERSONAL_CARE = "personal_care"
    OTHER = "other"

class ShoppingListBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    store_name: Optional[str] = Field(None, max_length=100)
    planned_date: Optional[datetime] = None

class ShoppingListCreate(ShoppingListBase):
    assigned_shopper: Optional[int] = None

class ShoppingListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    store_name: Optional[str] = Field(None, max_length=100)
    planned_date: Optional[datetime] = None
    assigned_shopper: Optional[int] = None
    is_active: Optional[bool] = None

class ShoppingItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    quantity: str = Field("1", min_length=1, max_length=50)
    category: ShoppingItemCategory = ShoppingItemCategory.OTHER
    estimated_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=200)
    is_urgent: bool = False

class ShoppingItemCreate(ShoppingItemBase):
    shopping_list_id: int

class ShoppingItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    quantity: Optional[str] = Field(None, min_length=1, max_length=50)
    category: Optional[ShoppingItemCategory] = None
    estimated_cost: Optional[float] = Field(None, ge=0)
    actual_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=200)
    is_urgent: Optional[bool] = None
    is_purchased: Optional[bool] = None

class ShoppingItemResponse(ShoppingItemBase):
    id: int
    shopping_list_id: int
    requested_by: int
    requester_name: str
    actual_cost: Optional[float]
    is_purchased: bool
    purchased_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class ShoppingListResponse(ShoppingListBase):
    id: int
    household_id: int
    created_by: int
    creator_name: str
    assigned_shopper: Optional[int]
    shopper_name: Optional[str]
    is_active: bool
    total_estimated_cost: Optional[float]
    total_actual_cost: Optional[float]
    items_count: int
    purchased_items_count: int
    created_at: datetime
    completed_at: Optional[datetime]
    items: List[ShoppingItemResponse]

    class Config:
        from_attributes = True

class ShoppingListSummary(BaseModel):
    id: int
    name: str
    items_count: int
    purchased_items_count: int
    total_estimated_cost: Optional[float]
    assigned_shopper: Optional[str]
    planned_date: Optional[datetime]
    is_active: bool
```

## app/schemas/household.py

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class HouseholdBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=300)
    house_rules: Optional[str] = Field(None, max_length=2000)


class HouseholdCreate(HouseholdBase):
    pass


class HouseholdUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=300)
    house_rules: Optional[str] = Field(None, max_length=2000)


class HouseholdMember(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    joined_at: datetime
    role: str = "member"  # admin, member


class HouseholdSettings(BaseModel):
    guest_policy: Dict[str, Any] = {
        "max_overnight_guests": 2,
        "max_consecutive_nights": 3,
        "approval_required": True,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
    }
    notification_settings: Dict[str, Any] = {
        "bill_reminder_days": 3,
        "task_overdue_hours": 24,
        "event_reminder_hours": 24,
    }
    task_settings: Dict[str, Any] = {
        "rotation_enabled": True,
        "point_system_enabled": True,
        "photo_proof_required": False,
    }


class HouseholdResponse(HouseholdBase):
    id: int
    created_at: datetime
    member_count: int
    admin_count: int
    members: List[HouseholdMember]
    settings: HouseholdSettings

    class Config:
        from_attributes = True


class HouseholdStats(BaseModel):
    total_expenses: float
    total_bills: float
    active_tasks: int
    completed_tasks: int
    upcoming_events: int
    active_members: int
    household_health_score: int


class HouseholdInvitation(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    role: str = "member"
    personal_message: Optional[str] = Field(None, max_length=300)


class HouseholdSummary(BaseModel):
    id: int
    name: str
    member_count: int
    address: Optional[str]
    user_role: str
    joined_at: datetime


```

## app/models/guest.py

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    relationship_to_host = Column(String)  # friend, family, partner, etc.

    # Visit details
    check_in = Column(DateTime, nullable=False)
    check_out = Column(DateTime)
    is_overnight = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)

    # Additional info
    notes = Column(Text)
    special_requests = Column(Text)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    hosted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="guests")
    host = relationship("User", back_populates="hosted_guests", foreign_keys=[hosted_by])
    approver = relationship("User", back_populates="approved_guests", foreign_keys=[approved_by])
```

## app/models/guest_approval.py

```python
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class GuestApproval(Base):
    __tablename__ = "guest_approvals"

    id = Column(Integer, primary_key=True)
    guest_id = Column(Integer, ForeignKey("guests.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved = Column(Boolean, nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    guest = relationship("Guest")
    user = relationship("User")
```

## app/models/shopping_list.py

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Grocery List")
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Shopping trip details
    store_name = Column(String)
    planned_date = Column(DateTime)
    total_estimated_cost = Column(Float)
    total_actual_cost = Column(Float)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_shopper = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="shopping_lists")
    creator = relationship("User", back_populates="created_shopping_lists", foreign_keys=[created_by])
    shopper = relationship("User", back_populates="assigned_shopping_lists", foreign_keys=[assigned_shopper])
    items = relationship("ShoppingItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    quantity = Column(String, default="1")  # "2 lbs", "1 gallon", "3 items"
    category = Column(String)  # produce, dairy, meat, etc.
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    notes = Column(Text)

    # Status
    is_purchased = Column(Boolean, default=False)
    is_urgent = Column(Boolean, default=False)

    # Foreign Keys
    shopping_list_id = Column(Integer, ForeignKey("shopping_lists.id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    purchased_at = Column(DateTime)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    shopping_list = relationship("ShoppingList", back_populates="items")
    requester = relationship("User", back_populates="requested_shopping_items", foreign_keys=[requested_by])
```

## app/models/household_membership.py

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from ..database import Base
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import relationship


class HouseholdMembership(Base):
    __tablename__ = "household_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    role = Column(String, default="member")  # admin, member
    joined_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Unique constraint
    user = relationship("User", back_populates="household_memberships")
    household = relationship("Household", back_populates="memberships")

    __table_args__ = (
        Index("idx_unique_household_member", "user_id", "household_id", unique=True),
        UniqueConstraint("user_id", "household_id", name="uq_user_household"),
    )
```
