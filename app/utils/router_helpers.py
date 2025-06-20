# app/utils/router_helpers.py

from fastapi import HTTPException, status
from typing import Callable, Any
from functools import wraps
import logging

# Import all service exceptions
from ..services.task_service import (
    TaskServiceError,
    TaskNotFoundError,
    PermissionDeniedError,
    BusinessRuleViolationError,
)
from ..services.expense_service import ExpenseServiceError, ExpenseNotFoundError
from ..services.event_service import EventServiceError, EventNotFoundError
from ..services.household_service import (
    HouseholdServiceError,
    HouseholdNotFoundError,
    UserNotFoundError,
)
from ..services.communication_service import (
    CommunicationServiceError,
    AnnouncementNotFoundError,
    PollNotFoundError,
)
from ..services.billing_service import BillingService  # Assuming similar error pattern
from ..services.approval_service import (
    ApprovalService,
)  # Assuming similar error pattern

logger = logging.getLogger(__name__)


def handle_service_errors(func: Callable) -> Callable:
    """Decorator to standardize service error handling in routers"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)

        # Permission/Access Errors -> 403 Forbidden
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied: {str(e)}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

        # Not Found Errors -> 404 Not Found
        except (
            TaskNotFoundError,
            ExpenseNotFoundError,
            EventNotFoundError,
            HouseholdNotFoundError,
            UserNotFoundError,
            AnnouncementNotFoundError,
            PollNotFoundError,
        ) as e:
            logger.warning(f"Resource not found: {str(e)}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

        # Business Rule Violations -> 400 Bad Request
        except BusinessRuleViolationError as e:
            logger.warning(f"Business rule violation: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # General Service Errors -> 400 Bad Request
        except (
            TaskServiceError,
            ExpenseServiceError,
            EventServiceError,
            HouseholdServiceError,
            CommunicationServiceError,
        ) as e:
            logger.warning(f"Service error: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Validation Errors -> 400 Bad Request
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Unexpected errors -> 500 Internal Server Error
        except Exception as e:
            logger.error(
                f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred",
            )

    return wrapper


def validate_pagination(
    limit: int, offset: int, max_limit: int = 100
) -> tuple[int, int]:
    """Validate and normalize pagination parameters"""
    if limit <= 0:
        limit = 10
    elif limit > max_limit:
        limit = max_limit

    if offset < 0:
        offset = 0

    return limit, offset


def create_pagination_response(
    items: list, total_count: int, limit: int, offset: int, key_name: str = "items"
) -> dict:
    """Create standardized pagination response"""
    return {
        key_name: items,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total_count,
        "page": (offset // limit) + 1 if limit > 0 else 1,
        "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1,
    }


def extract_error_message(error: Exception) -> str:
    """Extract user-friendly error message from exception"""
    error_str = str(error).lower()

    # Common error message mappings
    if "not found" in error_str:
        return "The requested resource was not found"
    elif "permission" in error_str or "access denied" in error_str:
        return "You don't have permission to perform this action"
    elif "already exists" in error_str:
        return "This resource already exists"
    elif "invalid" in error_str:
        return "Invalid input provided"
    elif "required" in error_str:
        return "Required information is missing"
    else:
        return str(error)


class RouterResponse:
    """Helper class for creating standardized API responses"""

    @staticmethod
    def success(data: Any = None, message: str = "Success") -> dict:
        """Create success response"""
        response = {"success": True, "message": message}
        if data is not None:
            response["data"] = data
        return response

    @staticmethod
    def created(data: Any, message: str = "Resource created successfully") -> dict:
        """Create resource creation response"""
        return {"success": True, "message": message, "data": data}

    @staticmethod
    def updated(
        data: Any = None, message: str = "Resource updated successfully"
    ) -> dict:
        """Create resource update response"""
        response = {"success": True, "message": message}
        if data is not None:
            response["data"] = data
        return response

    @staticmethod
    def deleted(message: str = "Resource deleted successfully") -> dict:
        """Create resource deletion response"""
        return {"success": True, "message": message}

    @staticmethod
    def error(message: str, details: Any = None) -> dict:
        """Create error response"""
        response = {"success": False, "error": message}
        if details is not None:
            response["details"] = details
        return response
