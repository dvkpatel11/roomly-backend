from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from ..utils.validation import ValidationHelpers


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


class UserUpdate(BaseModel):
    """Update user profile information"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)

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


class UserProfile(UserResponse):
    """Extended user profile with additional details"""

    total_households: int = 0
    total_expenses_created: int = 0
    total_tasks_completed: int = 0
    total_events_created: int = 0
    household_role: Optional[str] = None


class UserSummary(BaseModel):
    """Minimal user info for lists and references"""

    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None
    is_active: bool


class SupabaseUserSync(BaseModel):
    """Schema for syncing Supabase user data"""

    supabase_id: str
    email: str
    email_verified: bool
    user_metadata: dict = {}


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


class UserSettings(BaseModel):
    """User preference settings"""

    timezone: str = Field("UTC", description="User's timezone")
    date_format: str = Field("YYYY-MM-DD", description="Preferred date format")
    currency: str = Field("USD", description="Preferred currency")
    language: str = Field("en", description="Preferred language")

    # Privacy settings
    show_email_to_household: bool = Field(
        True, description="Show email to household members"
    )
    show_phone_to_household: bool = Field(
        False, description="Show phone to household members"
    )
    allow_task_assignment: bool = Field(
        True, description="Allow others to assign tasks"
    )

    # Notification delivery preferences (high-level)
    email_notifications_enabled: bool = Field(
        True, description="Enable email notifications"
    )
    push_notifications_enabled: bool = Field(
        True, description="Enable push notifications"
    )
    quiet_hours_start: Optional[str] = Field(
        None, description="Quiet hours start time (HH:MM)"
    )
    quiet_hours_end: Optional[str] = Field(
        None, description="Quiet hours end time (HH:MM)"
    )


class UserSettingsUpdate(BaseModel):
    """Update user settings"""

    timezone: Optional[str] = None
    date_format: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    show_email_to_household: Optional[bool] = None
    show_phone_to_household: Optional[bool] = None
    allow_task_assignment: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    push_notifications_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


# AUTHENTICATION SCHEMAS (Supabase Integration)


class AuthUser(BaseModel):
    """Current authenticated user info"""

    id: int
    supabase_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    email_verified: bool
    active_household_id: Optional[int] = None
    permissions: list[str] = []  # ["household:admin", "task:create", etc.]


class AuthToken(BaseModel):
    """Authentication token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    user: AuthUser


class AuthCallback(BaseModel):
    """Handle auth callback from Supabase"""

    access_token: str
    refresh_token: str
    user_info: dict  # Raw Supabase user object


# Export all schemas
__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserProfile",
    "UserSummary",
    "SupabaseUserSync",
    "UserInvitation",
    "UserSettings",
    "UserSettingsUpdate",
    "AuthUser",
    "AuthToken",
    "AuthCallback",
]
