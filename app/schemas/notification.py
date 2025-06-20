from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    BILL_DUE = "bill_due"
    TASK_OVERDUE = "task_overdue"
    TASK_ASSIGNED = "task_assigned"
    EVENT_REMINDER = "event_reminder"
    GUEST_REQUEST = "guest_request"
    EXPENSE_ADDED = "expense_added"
    PAYMENT_RECEIVED = "payment_received"
    ANNOUNCEMENT = "announcement"
    POLL_CREATED = "poll_created"
    SYSTEM = "system"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=500)
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    action_url: Optional[str] = None


class NotificationCreate(NotificationBase):
    user_id: int
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    household_id: int
    is_read: bool
    sent_in_app: bool
    sent_email: bool
    sent_push: bool
    related_entity_type: Optional[str]
    related_entity_id: Optional[int]
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationPreferences(BaseModel):
    bill_reminders_email: bool = True
    bill_reminders_push: bool = True
    task_reminders_email: bool = True
    task_reminders_push: bool = True
    event_reminders_email: bool = True
    event_reminders_push: bool = True
    announcements_email: bool = True
    announcements_push: bool = False
    guest_requests_email: bool = True
    guest_requests_push: bool = True
    expense_updates_email: bool = False
    expense_updates_push: bool = True


class NotificationPreferencesUpdate(BaseModel):
    bill_reminders_email: Optional[bool] = None
    bill_reminders_push: Optional[bool] = None
    task_reminders_email: Optional[bool] = None
    task_reminders_push: Optional[bool] = None
    event_reminders_email: Optional[bool] = None
    event_reminders_push: Optional[bool] = None
    announcements_email: Optional[bool] = None
    announcements_push: Optional[bool] = None
    guest_requests_email: Optional[bool] = None
    guest_requests_push: Optional[bool] = None
    expense_updates_email: Optional[bool] = None
    expense_updates_push: Optional[bool] = None


class NotificationSummary(BaseModel):
    unread_count: int
    high_priority_count: int
    recent_notifications: List[NotificationResponse]
