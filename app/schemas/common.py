from datetime import datetime
from typing import Any, Dict, Generic, List, Optional
from ..utils.constants import AppConstants, ResponseMessages
from pydantic import BaseModel, Field
from typing import TypeVar

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Base response model for all API responses"""

    success: bool = True
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[T] = None


class SuccessResponse(BaseResponse[T]):
    """Standard success response with typed data"""

    success: bool = True


class ErrorResponse(BaseResponse[None]):
    """Standard error response"""

    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    data: None = None


class PaginatedResponse(BaseResponse[List[T]]):
    """Paginated response with typed data"""

    pagination: "PaginationInfo"


class PaginationInfo(BaseModel):
    """Pagination information"""

    current_page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginationParams(BaseModel):
    """Pagination query parameters with constants"""

    page: int = Field(default=AppConstants.DEFAULT_PAGE, ge=1)
    page_size: int = Field(
        default=AppConstants.DEFAULT_PAGE_SIZE, ge=1, le=AppConstants.MAX_PAGE_SIZE
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class ConfigOption(BaseModel):
    """Single configuration option (for dropdowns, enums, etc.)"""

    value: str = Field(..., description="The actual value to use in API calls")
    label: str = Field(..., description="Human-readable display name")
    description: Optional[str] = Field(
        None, description="Optional description of the option"
    )
    disabled: bool = Field(
        False, description="Whether this option is currently disabled"
    )


class ConfigResponse(BaseModel):
    """Standard response for configuration endpoints"""

    options: List[ConfigOption] = Field(..., description="List of available options")
    total_count: int = Field(..., description="Total number of options")
    category: Optional[str] = Field(None, description="Category name for these options")


class ResponseFactory:
    """Factory for creating consistent API responses"""

    @staticmethod
    def success(
        data: T = None, message: str = ResponseMessages.SUCCESS
    ) -> SuccessResponse[T]:
        return SuccessResponse(data=data, message=message)

    @staticmethod
    def created(
        data: T = None, message: str = ResponseMessages.CREATED
    ) -> SuccessResponse[T]:
        return SuccessResponse(data=data, message=message)

    @staticmethod
    def error(
        message: str, error_code: str = None, details: Dict[str, Any] = None
    ) -> ErrorResponse:
        return ErrorResponse(message=message, error_code=error_code, details=details)

    @staticmethod
    def paginated(
        data: List[T],
        pagination: PaginationInfo,
        message: str = ResponseMessages.SUCCESS,
    ) -> PaginatedResponse[T]:
        return PaginatedResponse(data=data, pagination=pagination, message=message)
