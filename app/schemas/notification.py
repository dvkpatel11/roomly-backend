from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .enums import NotificationType, Priority as NotificationPriority
from .common import SuccessResponse, PaginatedResponse


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=500)
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    action_url: Optional[str] = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    household_id: int
    is_read: bool
    sent_in_app: bool
    sent_push: bool
    related_entity_type: Optional[str]
    related_entity_id: Optional[int]
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationPreferences(BaseModel):
    # Task notifications
    task_reminders: bool = True
    task_assignments: bool = True

    # Bill notifications
    bill_reminders: bool = True
    bill_payments: bool = True

    # Event notifications
    event_reminders: bool = True
    new_events: bool = True

    # Household notifications
    announcements: bool = True
    guest_requests: bool = True

    # Financial notifications
    expense_updates: bool = True
    payment_received: bool = True

    # Community notifications
    polls_created: bool = False
    system_updates: bool = True


class NotificationPreferencesUpdate(BaseModel):
    task_reminders: Optional[bool] = None
    task_assignments: Optional[bool] = None
    bill_reminders: Optional[bool] = None
    bill_payments: Optional[bool] = None
    event_reminders: Optional[bool] = None
    new_events: Optional[bool] = None
    announcements: Optional[bool] = None
    guest_requests: Optional[bool] = None
    expense_updates: Optional[bool] = None
    payment_received: Optional[bool] = None
    polls_created: Optional[bool] = None
    system_updates: Optional[bool] = None


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


NotificationListResponse = PaginatedResponse[NotificationResponse]
NotificationDetailResponse = SuccessResponse[NotificationResponse]
NotificationPreferencesResponse = SuccessResponse[NotificationPreferences]
NotificationSummaryResponse = SuccessResponse[NotificationSummary]
