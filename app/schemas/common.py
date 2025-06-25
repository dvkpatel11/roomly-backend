from ..utils.constants import AppConstants
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    limit: int = Field(
        AppConstants.DEFAULT_PAGE_SIZE, ge=1, le=AppConstants.MAX_PAGE_SIZE
    )
    offset: int = Field(0, ge=0)
