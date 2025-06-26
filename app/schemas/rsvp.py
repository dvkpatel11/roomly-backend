from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from ..models.enums import RSVPStatus
from .common import SuccessResponse, PaginatedResponse


class RSVPBase(BaseModel):
    status: RSVPStatus
    guest_count: int = Field(1, ge=1, le=10, description="Number of people attending")
    special_requests: Optional[str] = Field(None, max_length=300)
    response_notes: Optional[str] = Field(None, max_length=500)


class RSVPCreate(RSVPBase):
    event_id: int


class RSVPUpdate(BaseModel):
    status: Optional[RSVPStatus] = None
    guest_count: Optional[int] = Field(None, ge=1, le=10)
    special_requests: Optional[str] = Field(None, max_length=300)
    response_notes: Optional[str] = Field(None, max_length=500)


class RSVPResponse(RSVPBase):
    id: int
    event_id: int
    event_title: str
    user_id: int
    user_name: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


RSVPDetailResponse = SuccessResponse[RSVPResponse]
RSVPListResponse = PaginatedResponse[RSVPResponse]
