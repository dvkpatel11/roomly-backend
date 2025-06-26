class AppConstants:
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    DEFAULT_PAGE = 1

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


class TimeConstants:
    # Dashboard intervals
    DASHBOARD_ACTIVITY_DAYS = 7
    HEALTH_CALCULATION_DAYS = 30

    # Task calculations
    TASK_FAIRNESS_WINDOW_DAYS = 30
    TASK_STREAK_MAX_DAYS = 30
    TASK_OVERDUE_GRACE_HOURS = 24

    # Notification timing
    BILL_REMINDER_DAYS = 3
    EVENT_REMINDER_HOURS = [24, 2]  # 24 hours and 2 hours before
    TASK_REMINDER_HOURS = [9, 18]  # 9 AM and 6 PM
    NOTIFICATION_DUPLICATE_THRESHOLD_HOURS = 23

    # Financial precision
    CURRENCY_TOLERANCE = Decimal("0.01")

    # Pagination
    DEFAULT_HISTORY_LIMIT = 20
    MAX_RECURRING_INSTANCES = 4

    # Date validation
    MAX_FUTURE_BOOKING_DAYS = 365
    MAX_GUEST_STAY_DAYS = 30


class NotificationTiming:
    BILL_REMINDER_DAYS_BEFORE = 3
    BILL_OVERDUE_REMINDER_HOURS = [10, 18]  # 10 AM and 6 PM daily
    EVENT_REMINDER_HOURS_BEFORE = [24, 2]
    TASK_OVERDUE_REMINDER_HOURS = [9, 18]
