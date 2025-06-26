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


class RecurrencePattern(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
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
    PANTRY = "pantry"
    FROZEN = "frozen"
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


class SplitMethod(str, Enum):
    EQUAL = "equal_split"
    BY_USAGE = "by_usage"
    SPECIFIC = "specific_amounts"
    PERCENTAGE = "percentage"


class ExpenseCategory(str, Enum):
    GROCERIES = "groceries"
    UTILITIES = "utilities"
    RENT = "rent"
    CLEANING = "cleaning"
    ENTERTAINMENT = "entertainment"
    MAINTENANCE = "maintenance"
    INTERNET = "internet"
    TRANSPORTATION = "transportation"
    OTHER = "other"


class RSVPStatus(str, Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class NotificationType(Enum):
    BILL_DUE = "bill_due"
    BILL_OVERDUE = "bill_overdue"
    TASK_ASSIGNED = "task_assigned"
    TASK_OVERDUE = "task_overdue"
    TASK_COMPLETED = "task_completed"
    EVENT_REMINDER = "event_reminder"
    EVENT_CANCELLED = "event_cancelled"
    GUEST_REQUEST = "guest_request"
    GUEST_APPROVED = "guest_approved"
    GUEST_DENIED = "guest_denied"
    EXPENSE_ADDED = "expense_added"
    PAYMENT_RECEIVED = "payment_received"
    ANNOUNCEMENT = "announcement"
    POLL_CREATED = "poll_created"
    MEMBER_JOINED = "member_joined"
    SYSTEM = "system"
