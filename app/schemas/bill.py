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
    @validator('due_day')
    def validate_due_day(cls, v):
        if not 1 <= v <= 31:
            raise ValueError('Due day must be between 1 and 31')
        return v

class BillResponse(BillBase):
    id: int
    household_id: int
    created_by: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
