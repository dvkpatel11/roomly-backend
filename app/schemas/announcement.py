from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class AnnouncementCategory(str, Enum):
    GENERAL = "general"
    MAINTENANCE = "maintenance"
    EVENT = "event"
    RULE = "rule"
    URGENT = "urgent"
    FINANCIAL = "financial"

class AnnouncementPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    category: AnnouncementCategory
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    is_pinned: bool = False
    expires_at: Optional[datetime] = None

class AnnouncementCreate(AnnouncementBase):
    @validator('expires_at')
    def expires_in_future(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Expiration date must be in the future')
        return v

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[AnnouncementCategory] = None
    priority: Optional[AnnouncementPriority] = None
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
    priority: AnnouncementPriority
    is_pinned: bool
    created_at: datetime
    author_name: str
