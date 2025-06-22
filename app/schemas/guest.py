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
    special_requests: Optional[str] = None


class GuestCreate(GuestBase):
    pass


class GuestResponse(GuestBase):
    id: int
    household_id: int
    hosted_by: int
    is_approved: bool
    approved_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
