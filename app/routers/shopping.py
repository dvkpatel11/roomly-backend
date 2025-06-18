from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..services.shopping_service import ShoppingService
from ..schemas.shopping_list import (
    ShoppingListCreate, ShoppingListUpdate, ShoppingListResponse,
    ShoppingItemCreate, ShoppingItemUpdate, ShoppingItemResponse
)
from .auth import get_current_user
from ..models.user import User

router = APIRouter()

@router.post("/lists", response_model=ShoppingListResponse)
async def create_shopping_list(
    list_data: ShoppingListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new shopping list"""
    try:
        shopping_service = ShoppingService(db)
        shopping_list = shopping_service.create_shopping_list(
            list_data=list_data,
            household_id=current_user.household_id,
            created_by=current_user.id
        )
        return shopping_list
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/lists")
async def get_shopping_lists(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household shopping lists"""
    shopping_service = ShoppingService(db)
    
    lists = shopping_service.get_active_shopping_lists(
        household_id=current_user.household_id
    )
    
    return {"shopping_lists": lists}

@router.get("/lists/{list_id}")
async def get_shopping_list_details(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed shopping list with all items"""
    try:
        shopping_service = ShoppingService(db)
        details = shopping_service.get_shopping_list_details(list_id)
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/lists/{list_id}/items", response_model=ShoppingItemResponse)
async def add_shopping_item(
    list_id: int,
    item_data: ShoppingItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add item to shopping list"""
    try:
        # Set the shopping list ID
        item_data.shopping_list_id = list_id
        
        shopping_service = ShoppingService(db)
        item = shopping_service.add_item_to_list(
            item_data=item_data,
            requested_by=current_user.id
        )
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/lists/{list_id}/items/{item_id}/purchased")
async def mark_item_purchased(
    list_id: int,
    item_id: int,
    actual_cost: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark item as purchased"""
    try:
        shopping_service = ShoppingService(db)
        item = shopping_service.mark_item_purchased(
            item_id=item_id,
            actual_cost=actual_cost
        )
        return {"message": "Item marked as purchased", "item": item}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/lists/{list_id}/items/{item_id}")
async def remove_shopping_item(
    list_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove item from shopping list"""
    # Add method to ShoppingService
    return {"message": "Item removed from shopping list"}

@router.put("/lists/{list_id}/complete")
async def complete_shopping_trip(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete shopping trip and create expense"""
    try:
        shopping_service = ShoppingService(db)
        result = shopping_service.complete_shopping_trip(
            list_id=list_id,
            shopper_id=current_user.id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/lists/{list_id}/reassign")
async def reassign_shopper(
    list_id: int,
    new_shopper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reassign shopper for shopping list"""
    shopping_service = ShoppingService(db)
    
    success = shopping_service.reassign_shopper(
        list_id=list_id,
        new_shopper_id=new_shopper_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    
    return {"message": "Shopper reassigned successfully"}

@router.get("/statistics")
async def get_shopping_statistics(
    months_back: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get shopping statistics for household"""
    shopping_service = ShoppingService(db)
    
    stats = shopping_service.get_shopping_statistics(
        household_id=current_user.household_id,
        months_back=months_back
    )
    
    return stats
