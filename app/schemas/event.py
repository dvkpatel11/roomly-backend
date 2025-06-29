from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
from .common import SuccessResponse, PaginatedResponse
from .enums import EventStatus, EventType


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    event_type: EventType
    location: Optional[str] = Field(None, max_length=200)
    max_attendees: Optional[int] = Field(None, gt=0)
    is_public: bool = True
    requires_approval: bool = False


class EventCreate(EventBase):
    start_date: datetime
    end_date: Optional[datetime] = None

    @validator("end_date")
    def end_after_start(cls, v, values):
        if v and "start_date" in values and v <= values["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    event_type: Optional[EventType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    max_attendees: Optional[int] = Field(None, gt=0)
    is_public: Optional[bool] = None
    requires_approval: Optional[bool] = None
    status: Optional[EventStatus] = None


class EventResponse(EventBase):
    id: int
    household_id: int
    created_by: int
    creator_name: str
    start_date: datetime
    end_date: Optional[datetime]
    status: EventStatus
    attendee_count: int
    user_rsvp_status: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class EventSummary(BaseModel):
    id: int
    title: str
    event_type: EventType
    start_date: datetime
    attendee_count: int
    user_rsvp_status: Optional[str]


EventListResponse = PaginatedResponse[EventResponse]
EventDetailResponse = SuccessResponse[EventResponse]
