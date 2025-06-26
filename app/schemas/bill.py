from pydantic import BaseModel, validator, Field, computed_field
from typing import Any, Dict, Optional
from datetime import datetime, date
from ..models.enums import ExpenseCategory, SplitMethod
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

    # COMPUTED FIELDS
    @computed_field
    @property
    def days_until_due(self) -> int:
        """Days until next due date"""
        today = date.today()
        current_month_due = date(today.year, today.month, min(self.due_day, 28))

        if current_month_due >= today:
            delta = current_month_due - today
            return delta.days
        else:
            # Next month
            if today.month == 12:
                next_due = date(today.year + 1, 1, min(self.due_day, 28))
            else:
                next_due = date(today.year, today.month + 1, min(self.due_day, 28))
            delta = next_due - today
            return delta.days

    @computed_field
    @property
    def is_due_soon(self) -> bool:
        """Check if bill is due within 3 days"""
        return self.days_until_due <= 3

    @computed_field
    @property
    def next_due_date(self) -> date:
        """Calculate next due date"""
        today = date.today()
        current_month_due = date(today.year, today.month, min(self.due_day, 28))

        if current_month_due >= today:
            return current_month_due
        else:
            # Next month
            if today.month == 12:
                return date(today.year + 1, 1, min(self.due_day, 28))
            else:
                return date(today.year, today.month + 1, min(self.due_day, 28))

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
