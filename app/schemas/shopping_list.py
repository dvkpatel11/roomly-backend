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
