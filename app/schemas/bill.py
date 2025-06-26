from pydantic import BaseModel, validator, Field
from typing import Any, Dict, Optional
from datetime import datetime
from .enums import ExpenseCategory, SplitMethod
from ..utils.validation import ValidationHelpers
from .common import SuccessResponse, PaginatedResponse


class BillBase(BaseModel):
    name: str
    amount: float
    category: ExpenseCategory
    due_day: int
    split_method: SplitMethod
    notes: Optional[str] = None


class BillCreate(BillBase):
    split_details: Optional[Dict[str, Any]] = None

    @validator("due_day")
    def validate_due_day(cls, v):
        if not 1 <= v <= 31:
            raise ValueError("Due day must be between 1 and 31")
        return v


class BillUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    due_day: Optional[int] = None
    split_method: Optional[str] = None
    notes: Optional[str] = None
    split_details: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @validator("due_day")
    def validate_due_day(cls, v):
        if v is not None and not 1 <= v <= 31:
            raise ValueError("Due day must be between 1 and 31")
        return v

    @validator("amount")
    def validate_amount(cls, v):
        return ValidationHelpers.validate_amount(v) if v is not None else v


class BillResponse(BillBase):
    id: int
    household_id: int
    created_by: int
    is_active: bool
    split_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BillPaymentRecord(BaseModel):
    amount_paid: float = Field(..., gt=0, description="Amount being paid")
    payment_method: Optional[str] = Field(
        None, max_length=50, description="How payment was made"
    )
    notes: Optional[str] = Field(None, max_length=200, description="Payment notes")
    for_month: str = Field(
        ..., description="Month this payment is for (YYYY-MM format)"
    )


# Wrapped response types
BillListResponse = PaginatedResponse[BillResponse]
BillDetailResponse = SuccessResponse[BillResponse]
