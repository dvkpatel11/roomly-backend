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
