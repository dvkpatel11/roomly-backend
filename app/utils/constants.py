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
