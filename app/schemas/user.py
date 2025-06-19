from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: str
    name: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    household_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class UserScheduleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    start_time: datetime
    end_time: datetime
    schedule_type: str
    is_shared_with_household: bool = False
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    location: Optional[str] = None
    is_at_home: bool = False


class UserScheduleResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    schedule_type: str
    is_shared_with_household: bool
    is_recurring: bool
    recurrence_pattern: Optional[str]
    location: Optional[str]
    is_at_home: bool
    created_at: datetime
