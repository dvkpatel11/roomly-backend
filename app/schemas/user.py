from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from ..utils.validation import ValidationHelpers
from .common import SuccessResponse, PaginatedResponse


class UserBase(BaseModel):
    email: str = Field(..., description="User's email address")
    name: str = Field(
        ..., min_length=1, max_length=100, description="User's display name"
    )
    phone: Optional[str] = Field(None, description="User's phone number")
    bio: Optional[str] = Field(None, max_length=500, description="User bio/description")


class UserCreate(BaseModel):
    """
    CLEAN: No password field needed - Supabase handles authentication
    This is used when creating a user record after Supabase signup
    """

    email: str
    name: str
    supabase_id: str = Field(..., description="Supabase user ID")
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

    @validator("email")
    def validate_email(cls, v):
        return ValidationHelpers.validate_email(v)

    @validator("phone")
    def validate_phone(cls, v):
        return ValidationHelpers.validate_phone(v)


class UserResponse(UserBase):
    """Public user information for API responses"""

    id: int
    supabase_id: str
    avatar_url: Optional[str] = None
    is_active: bool
    email_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Computed fields
    active_household_id: Optional[int] = None
    is_household_admin: bool = False

    class Config:
        from_attributes = True


class UserInvitation(BaseModel):
    """Schema for inviting new users to household"""

    email: str = Field(..., description="Email address to invite")
    role: str = Field("member", description="Initial role in household")
    personal_message: Optional[str] = Field(
        None, max_length=300, description="Personal invitation message"
    )

    @validator("email")
    def validate_email(cls, v):
        return ValidationHelpers.validate_email(v)

    @validator("role")
    def validate_role(cls, v):
        if v not in ["admin", "member"]:
            raise ValueError("Role must be either 'admin' or 'member'")
        return v


class AuthUser(BaseModel):
    """Current authenticated user info"""

    id: int
    supabase_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    email_verified: bool
    active_household_id: Optional[int] = None
    permissions: list[str] = []


UserDetailResponse = SuccessResponse[UserResponse]
UserListResponse = PaginatedResponse[UserResponse]
AuthUserResponse = SuccessResponse[AuthUser]
