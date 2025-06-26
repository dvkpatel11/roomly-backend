from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class FinancialSummary(BaseModel):
    total_owed: float
    total_owed_to_you: float
    monthly_spending: float
    pending_payments: int
    upcoming_bills: List[Dict[str, Any]]
    recent_expenses: List[Dict[str, Any]]
    largest_expense_this_month: Optional[Dict[str, Any]]


class TaskSummary(BaseModel):
    overdue_tasks: int
    tasks_due_today: int
    tasks_due_this_week: int
    completed_this_week: int
    your_task_score: int
    your_rank: int
    upcoming_tasks: List[Dict[str, Any]]
    completion_rate: float


class EventSummary(BaseModel):
    upcoming_events: List[Dict[str, Any]]
    events_this_week: int
    events_you_created: int
    pending_rsvps: List[Dict[str, Any]]


class GuestSummary(BaseModel):
    guests_this_week: int
    pending_approvals: List[Dict[str, Any]]
    your_guests_this_month: int


class CommunicationSummary(BaseModel):
    unread_announcements: int
    active_polls: List[Dict[str, Any]]
    recent_announcements: List[Dict[str, Any]]


class NotificationSummary(BaseModel):
    unread_count: int
    high_priority_count: int
    recent_notifications: List[Dict[str, Any]]


class QuickAction(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    url: str
    priority: int


class ActivityFeedItem(BaseModel):
    id: int
    type: str  # expense, task, event, announcement, etc.
    title: str
    description: str
    user_name: str
    timestamp: datetime
    icon: str
    url: Optional[str]


class HouseholdHealthScore(BaseModel):
    overall_score: int
    financial_health: int
    task_completion: int
    communication_activity: int
    member_satisfaction: int
    improvement_suggestions: List[str]
