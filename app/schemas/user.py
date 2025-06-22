from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: str
    name: str
    phone: Optional[str] = None  # Added missing field
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None  # Added missing field
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    supabase_id: Optional[str] = None  # Added missing field
    created_at: datetime
    updated_at: Optional[datetime] = None  # Added missing field

    class Config:
        from_attributes = True
