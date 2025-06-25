from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from ..models.enums import NotificationType, Priority as NotificationPriority


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


class NotificationListResponse(BaseModel):
    """Response model for notification list endpoint"""

    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int
    limit: int
    offset: int
    has_more: bool


class NotificationPreferences(BaseModel):
    """FIXED: Aligned with model structure"""

    # Bill reminders
    bill_reminders_email: bool = True
    bill_reminders_push: bool = True
    bill_reminders_in_app: bool = True

    # Task reminders
    task_reminders_email: bool = True
    task_reminders_push: bool = True
    task_reminders_in_app: bool = True

    # Event reminders
    event_reminders_email: bool = True
    event_reminders_push: bool = True
    event_reminders_in_app: bool = True

    # Announcements
    announcements_email: bool = True
    announcements_push: bool = False
    announcements_in_app: bool = True

    # Guest requests
    guest_requests_email: bool = True
    guest_requests_push: bool = True
    guest_requests_in_app: bool = True

    # Expense updates
    expense_updates_email: bool = False
    expense_updates_push: bool = True
    expense_updates_in_app: bool = True

    # Payment notifications
    payment_received_email: bool = False
    payment_received_push: bool = True
    payment_received_in_app: bool = True

    # Poll notifications
    poll_created_email: bool = False
    poll_created_push: bool = True
    poll_created_in_app: bool = True

    # System updates
    system_updates_email: bool = True
    system_updates_push: bool = False
    system_updates_in_app: bool = True


class NotificationPreferencesUpdate(BaseModel):
    """Partial update schema - all fields optional"""

    # Bill reminders
    bill_reminders_email: Optional[bool] = None
    bill_reminders_push: Optional[bool] = None
    bill_reminders_in_app: Optional[bool] = None

    # Task reminders
    task_reminders_email: Optional[bool] = None
    task_reminders_push: Optional[bool] = None
    task_reminders_in_app: Optional[bool] = None

    # Event reminders
    event_reminders_email: Optional[bool] = None
    event_reminders_push: Optional[bool] = None
    event_reminders_in_app: Optional[bool] = None

    # Announcements
    announcements_email: Optional[bool] = None
    announcements_push: Optional[bool] = None
    announcements_in_app: Optional[bool] = None

    # Guest requests
    guest_requests_email: Optional[bool] = None
    guest_requests_push: Optional[bool] = None
    guest_requests_in_app: Optional[bool] = None

    # Expense updates
    expense_updates_email: Optional[bool] = None
    expense_updates_push: Optional[bool] = None
    expense_updates_in_app: Optional[bool] = None

    # Payment notifications
    payment_received_email: Optional[bool] = None
    payment_received_push: Optional[bool] = None
    payment_received_in_app: Optional[bool] = None

    # Poll notifications
    poll_created_email: Optional[bool] = None
    poll_created_push: Optional[bool] = None
    poll_created_in_app: Optional[bool] = None

    # System updates
    system_updates_email: Optional[bool] = None
    system_updates_push: Optional[bool] = None
    system_updates_in_app: Optional[bool] = None


class NotificationSummary(BaseModel):
    unread_count: int
    high_priority_count: int
    recent_notifications: List[NotificationResponse]


class NotificationFilters(BaseModel):
    """Filter parameters for notification queries"""

    unread_only: bool = Field(False, description="Show only unread notifications")
    priority: Optional[str] = Field(None, description="Filter by priority level")
    notification_type: Optional[str] = Field(
        None, description="Filter by notification type"
    )
