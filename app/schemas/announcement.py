from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
from ..models.enums import AnnouncementType as AnnouncementCategory, Priority


class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    category: AnnouncementCategory
    priority: str = Priority.NORMAL.value
    is_pinned: bool = False
    expires_at: Optional[datetime] = None


class AnnouncementCreate(AnnouncementBase):
    @validator("expires_at")
    def expires_in_future(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError("Expiration date must be in the future")
        return v


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[AnnouncementCategory] = None
    priority: Optional[Priority] = None
    is_pinned: Optional[bool] = None
    expires_at: Optional[datetime] = None


class AnnouncementResponse(AnnouncementBase):
    id: int
    household_id: int
    created_by: int
    author_name: str
    is_expired: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AnnouncementSummary(BaseModel):
    id: int
    title: str
    category: AnnouncementCategory
    priority: Priority
    is_pinned: bool
    created_at: datetime
    author_name: str
