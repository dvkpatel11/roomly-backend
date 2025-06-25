from pydantic import BaseModel, validator, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from ..models.enums import ExpenseCategory, SplitMethod


class ExpenseBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0, description="Amount must be positive")
    category: ExpenseCategory
    split_method: SplitMethod
    receipt_url: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)


class ExpenseCreate(ExpenseBase):
    @validator("description")
    def description_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()


class ExpenseUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[ExpenseCategory] = None
    split_method: Optional[SplitMethod] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)


class ExpenseResponse(ExpenseBase):
    id: int
    household_id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime]
    split_details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ExpenseSplit(BaseModel):
    user_id: int
    user_name: str
    amount_owed: float
    is_paid: bool = False
    payment_date: Optional[datetime] = None


class ExpenseSplitCalculation(BaseModel):
    expense_id: int
    total_amount: float
    split_method: SplitMethod
    splits: list[ExpenseSplit]
    calculation_details: Dict[str, Any]
