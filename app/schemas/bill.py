from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class BillBase(BaseModel):
    name: str
    amount: float
    category: str
    due_day: int
    split_method: str
    notes: Optional[str] = None


class BillCreate(BillBase):
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
    is_active: Optional[bool] = None

    @validator("due_day")
    def validate_due_day(cls, v):
        if v is not None and not 1 <= v <= 31:
            raise ValueError("Due day must be between 1 and 31")
        return v

    @validator("amount")
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive")
        return v


class BillResponse(BillBase):
    id: int
    household_id: int
    created_by: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


__all__ = ["BillBase", "BillCreate", "BillUpdate", "BillResponse"]
