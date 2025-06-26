from enum import Enum


class ResponseMessages:
    """Standard API response messages"""

    # Success messages
    SUCCESS = "Success"
    CREATED = "Created successfully"
    UPDATED = "Updated successfully"
    DELETED = "Deleted successfully"


# Application Constants
class AppConstants:
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # File Upload (when implemented)
    MAX_FILE_SIZE_MB = 10
    ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ALLOWED_DOCUMENT_EXTENSIONS = [".pdf", ".doc", ".docx", ".txt"]

    # Validation Limits
    MAX_HOUSEHOLD_MEMBERS = 10
    MAX_EXPENSE_AMOUNT = 10000.00
    MAX_TASK_POINTS = 100
    MIN_TASK_POINTS = 1
    MAX_GUEST_DAYS = 30
    MAX_SHOPPING_ITEMS = 100

    # Notification Settings
    DEFAULT_BILL_REMINDER_DAYS = 3
    DEFAULT_TASK_OVERDUE_HOURS = 24
    DEFAULT_EVENT_REMINDER_HOURS = 24
    MAX_NOTIFICATION_RETRIES = 3

    # Task System
    MONTHLY_POINT_RESET_DAY = 1  # 1st of each month
    MAX_TASK_STREAK_DAYS = 365
    DEFAULT_TASK_POINTS = 10

    # Financial
    CURRENCY_DECIMAL_PLACES = 2
    MAX_SPLIT_PERCENTAGE = 100
    MIN_SPLIT_PERCENTAGE = 0


# Expense Categories
class ExpenseCategory(Enum):
    GROCERIES = "groceries"
    UTILITIES = "utilities"
    RENT = "rent"
    CLEANING = "cleaning"
    ENTERTAINMENT = "entertainment"
    MAINTENANCE = "maintenance"
    INTERNET = "internet"
    TRANSPORTATION = "transportation"
    OTHER = "other"


# Task Categories
class TaskCategory(Enum):
    CLEANING = "cleaning"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    TRASH = "trash"
    MAINTENANCE = "maintenance"
    YARD_WORK = "yard_work"
    ORGANIZING = "organizing"
    OTHER = "other"


# Event Types
class EventType(Enum):
    PARTY = "party"
    MAINTENANCE = "maintenance"
    CLEANING = "cleaning"
    MEETING = "meeting"
    MOVIE_NIGHT = "movie_night"
    DINNER = "dinner"
    GAME_NIGHT = "game_night"
    STUDY_SESSION = "study_session"
    OTHER = "other"


# Notification Types
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


# User Roles
class UserRole(Enum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


# Bill Status
class BillStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"


# Priority Levels
class Priority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# RSVP Status
class RSVPStatus(Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"
    PENDING = "pending"


# Split Methods
class SplitMethod(Enum):
    EQUAL = "equal_split"
    BY_USAGE = "by_usage"
    SPECIFIC_AMOUNTS = "specific_amounts"
    PERCENTAGE = "percentage"


# Guest Policies
class GuestPolicy:
    DEFAULT_MAX_OVERNIGHT_GUESTS = 2
    DEFAULT_MAX_CONSECUTIVE_NIGHTS = 3
    DEFAULT_APPROVAL_REQUIRED = True
    DEFAULT_QUIET_HOURS_START = "22:00"
    DEFAULT_QUIET_HOURS_END = "08:00"


# Task Settings
class TaskSettings:
    DEFAULT_ROTATION_ENABLED = True
    DEFAULT_POINT_SYSTEM_ENABLED = True
    DEFAULT_PHOTO_PROOF_REQUIRED = False
    OVERDUE_REMINDER_FREQUENCY_HOURS = 12  # Twice daily


# API Response Messages
class Messages:
    # Success Messages
    SUCCESS_CREATED = "Created successfully"
    SUCCESS_UPDATED = "Updated successfully"
    SUCCESS_DELETED = "Deleted successfully"
    SUCCESS_APPROVED = "Approved successfully"
    SUCCESS_DENIED = "Denied successfully"

    # Error Messages
    ERROR_NOT_FOUND = "Resource not found"
    ERROR_UNAUTHORIZED = "Unauthorized access"
    ERROR_FORBIDDEN = "Forbidden operation"
    ERROR_VALIDATION = "Validation error"
    ERROR_CONFLICT = "Resource conflict"
    ERROR_SERVER = "Internal server error"

    # Specific Messages
    EXPENSE_SPLIT_CALCULATED = "Expense split calculated successfully"
    TASK_COMPLETED = "Task marked as completed"
    BILL_PAYMENT_RECORDED = "Bill payment recorded"
    GUEST_APPROVED_ALL = "Guest approved by all household members"
    EVENT_PUBLISHED = "Event approved and published"


# Default Settings
class DefaultSettings:
    # Household
    HOUSEHOLD_HEALTH_SCORE_THRESHOLD = 70

    # Notifications
    NOTIFICATION_BATCH_SIZE = 50
    EMAIL_RATE_LIMIT_PER_HOUR = 100

    # Dashboard
    DASHBOARD_ACTIVITY_FEED_LIMIT = 20
    DASHBOARD_UPCOMING_ITEMS_LIMIT = 5

    # Leaderboard
    LEADERBOARD_TOP_N = 10

    # Search
    SEARCH_RESULTS_LIMIT = 50


class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTH_ERROR"
    AUTHORIZATION_ERROR = "AUTHZ_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND"
    CONFLICT_ERROR = "CONFLICT"
    RATE_LIMIT_ERROR = "RATE_LIMIT"
    SERVER_ERROR = "SERVER_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_ERROR"
