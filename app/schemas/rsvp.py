from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class RSVPStatus(str, Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"

class RSVPBase(BaseModel):
    status: RSVPStatus
    guest_count: int = Field(1, ge=1, le=10, description="Number of people attending")
    dietary_restrictions: Optional[str] = Field(None, max_length=300)
    special_requests: Optional[str] = Field(None, max_length=300)
    response_notes: Optional[str] = Field(None, max_length=500)

class RSVPCreate(RSVPBase):
    event_id: int

class RSVPUpdate(BaseModel):
    status: Optional[RSVPStatus] = None
    guest_count: Optional[int] = Field(None, ge=1, le=10)
    dietary_restrictions: Optional[str] = Field(None, max_length=300)
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

class EventRSVPSummary(BaseModel):
    event_id: int
    event_title: str
    total_responses: int
    yes_count: int
    no_count: int
    maybe_count: int
    total_guests: int
    responses: List[RSVPResponse]

class UserRSVPSummary(BaseModel):
    user_id: int
    upcoming_events: List[RSVPResponse]
    past_events_count: int
