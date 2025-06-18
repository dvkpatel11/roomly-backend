from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
from enum import Enum

from app.models.enums import TaskStatus


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class RecurrencePattern(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration: Optional[int] = Field(
        None, gt=0, description="Duration in minutes"
    )
    points: int = Field(10, ge=1, le=100, description="Points for completion")


class TaskCreate(TaskBase):
    assigned_to: int
    due_date: Optional[datetime] = None
    recurring: bool = False
    recurrence_pattern: Optional[RecurrencePattern] = None

    @validator("recurrence_pattern")
    def validate_recurrence(cls, v, values):
        if values.get("recurring") and not v:
            raise ValueError("Recurrence pattern required for recurring tasks")
        if not values.get("recurring") and v:
            raise ValueError("Recurrence pattern only valid for recurring tasks")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: Optional[TaskPriority] = None
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None
    estimated_duration: Optional[int] = Field(None, gt=0)
    points: Optional[int] = Field(None, ge=1, le=100)


class TaskComplete(BaseModel):
    completion_notes: Optional[str] = Field(None, max_length=300)
    photo_proof_url: Optional[str] = None
    actual_duration: Optional[int] = Field(
        None, gt=0, description="Actual duration in minutes"
    )


class TaskResponse(TaskBase):
    id: int
    household_id: int
    assigned_to: int
    assigned_user_name: str
    created_by: int
    status: TaskStatus
    completed: bool
    completed_at: Optional[datetime]
    due_date: Optional[datetime]
    recurring: bool
    recurrence_pattern: Optional[RecurrencePattern]
    completion_notes: Optional[str]
    photo_proof_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TaskLeaderboard(BaseModel):
    user_id: int
    user_name: str
    total_points: int
    tasks_completed: int
    completion_rate: float
    current_streak: int
