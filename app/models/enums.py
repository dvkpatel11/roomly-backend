from enum import Enum


class HouseholdRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class EventStatus(str, Enum):
    PENDING = "pending_approval"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
