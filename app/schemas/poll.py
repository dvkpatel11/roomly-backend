from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime
from .common import SuccessResponse, PaginatedResponse

class PollBase(BaseModel):
    question: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    options: List[str] = Field(..., min_items=2, max_items=10)
    is_multiple_choice: bool = False
    is_anonymous: bool = False
    closes_at: Optional[datetime] = None


class PollCreate(PollBase):
    @validator("options")
    def validate_options(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("Poll options must be unique")
        for option in v:
            if not option.strip():
                raise ValueError("Poll options cannot be empty")
        return [option.strip() for option in v]

    @validator("closes_at")
    def closes_in_future(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError("Close date must be in the future")
        return v


class PollUpdate(BaseModel):
    question: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    closes_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class PollVoteCreate(BaseModel):
    selected_options: List[int] = Field(..., min_items=1)

    @validator("selected_options")
    def validate_selections(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("Cannot select the same option multiple times")
        return v


class PollResponse(PollBase):
    id: int
    household_id: int
    created_by: int
    creator_name: str
    is_active: bool
    total_votes: int
    user_has_voted: bool
    user_votes: Optional[List[int]]
    created_at: datetime

    class Config:
        from_attributes = True

PollListResponse = PaginatedResponse[PollResponse] 
PollDetailResponse = SuccessResponse[PollResponse]