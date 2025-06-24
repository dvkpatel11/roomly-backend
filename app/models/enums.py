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


class TaskRecurrence(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ShoppingCategory(str, Enum):
    PRODUCE = "produce"
    DAIRY = "dairy"
    MEAT = "meat"
    BAKERY = "bakery"
    BEVERAGES = "beverages"
    SNACKS = "snacks"
    HOUSEHOLD = "household"
    PERSONAL_CARE = "personal_care"
    OTHER = "other"


class AnnouncementType(str, Enum):
    GENERAL = "general"
    EVENT = "event"
    TASK = "task"
    BILL = "bill"
    POLL = "poll"
    SYSTEM = "system"
    MAINTENANCE = "maintenance"
    RULE = "rule"


class BillType(str, Enum):
    RENT = "rent"
    UTILITIES = "utilities"
    INTERNET = "internet"
    GROCERIES = "groceries"
    OTHER = "other"


class EventType(str, Enum):
    MEETING = "meeting"
    PARTY = "party"
    STUDY_SESSION = "study_session"
    GAME_NIGHT = "game_night"
    MOVIE_NIGHT = "movie_night"
    DINNER = "dinner"
    OTHER = "other"
    CLEANING = "cleaning"


class GuestRelationship(str, Enum):
    FAMILY = "family"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    OTHER = "other"
