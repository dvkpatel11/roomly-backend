from pydantic import BaseModel, Field
from typing import Optional, TypeVar
from datetime import datetime
from .common import SuccessResponse, PaginatedResponse

T = TypeVar("T")


class GenericApprovalCreate(BaseModel):
    """Generic approval creation schema - works for events, guests, etc."""

    entity_id: int = Field(..., description="ID of the entity being approved")
    approved: bool = Field(..., description="Whether to approve or reject")
    reason: Optional[str] = Field(
        None, max_length=500, description="Reason for decision"
    )


class GenericApprovalResponse(BaseModel):
    """Generic approval response schema"""

    id: int
    entity_id: int
    entity_type: str  # "event", "guest", etc.
    user_id: int
    user_name: str
    approved: bool
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class EventApprovalCreate(GenericApprovalCreate):
    """Event-specific approval (inherits from generic)"""

    pass


class EventApprovalResponse(GenericApprovalResponse):
    """Event-specific approval response"""

    entity_type: str = "event"


class GuestApprovalCreate(GenericApprovalCreate):
    """Guest-specific approval (inherits from generic)"""

    pass


class GuestApprovalResponse(GenericApprovalResponse):
    """Guest-specific approval response"""

    entity_type: str = "guest"


EventApprovalDetailResponse = SuccessResponse[EventApprovalResponse]
EventApprovalListResponse = PaginatedResponse[EventApprovalResponse]
GuestApprovalDetailResponse = SuccessResponse[GuestApprovalResponse]
GuestApprovalListResponse = PaginatedResponse[GuestApprovalResponse]
