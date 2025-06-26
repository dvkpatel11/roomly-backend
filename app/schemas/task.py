from pydantic import BaseModel, computed_field, validator, Field
from typing import List, Optional
from datetime import datetime
from .common import SuccessResponse, PaginatedResponse
from app.models.enums import TaskStatus
from app.models.enums import Priority, RecurrencePattern


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    priority: Priority = Priority.NORMAL
    estimated_duration: Optional[int] = Field(
        None, gt=0, description="Duration in minutes"
    )


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
    priority: Optional[Priority] = None
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None
    estimated_duration: Optional[int] = Field(None, gt=0)


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

    # COMPUTED FIELD
    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if not self.due_date or self.completed:
            return False
        return datetime.utcnow() > self.due_date

    @computed_field
    @property
    def days_until_due(self) -> Optional[int]:
        """Days until due date (negative if overdue)"""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.utcnow()
        return delta.days

    class Config:
        from_attributes = True


TaskListResponse = PaginatedResponse[TaskResponse]
TaskDetailResponse = SuccessResponse[TaskResponse]


class TaskLeaderboard(BaseModel):
    user_id: int
    user_name: str
    tasks_completed: int
    completion_rate: float
    current_streak: int


class TaskStatistics(BaseModel):
    household_id: int
    period_months: int
    total_members: int
    total_completed_tasks: int
    average_completion_rate: float
    overdue_tasks_count: int
    leaderboard_preview: List[dict]
    most_productive_member: Optional[dict]


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., description="New task status")


class TaskReassignment(BaseModel):
    new_assignee_id: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=200)
