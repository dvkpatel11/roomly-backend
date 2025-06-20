# Shared Context - Backend Context

## Overview
Common models, enums, authentication, and utilities used across all pages.

## Related Files:
## app/routers/auth.py
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from ..database import get_db
from ..models.user import User
from ..services.household_service import HouseholdService
from ..schemas.user import UserCreate, UserResponse
from ..utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from ..utils.validation import ValidationHelpers
from ..utils.router_helpers import handle_service_errors, RouterResponse
from jose import JWTError, jwt
import os

router = APIRouter(tags=["authentication"])
security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"


# Login request schema
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    )
    if user is None:
        raise credentials_exception

    return user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
@handle_service_errors
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Validate email format (additional validation beyond Pydantic)
    if not ValidationHelpers.validate_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format"
        )

    # Check if user already exists by email
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if phone number already exists (if provided)
    if user_data.phone:
        existing_phone = (
            db.query(User)
            .filter(
                User.phone == user_data.phone,
                User.phone.isnot(None),  # Only check non-null phone numbers
            )
            .first()
        )
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered",
            )

    # Validate password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    # Additional password validation (optional but recommended)
    if not ValidationHelpers.validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter, one lowercase letter, and one number",
        )

    # Validate phone number format (if provided)
    if user_data.phone and not ValidationHelpers.validate_phone_number(user_data.phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format",
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
        phone=user_data.phone,
        is_active=True,
    )

    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account",
        )

    return user


@router.post("/login", response_model=LoginResponse)
@handle_service_errors
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return access token"""
    # Find user
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Create access token
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=token_expires
    )

    # Get household info using proper service
    household_service = HouseholdService(db)
    household_info = household_service.get_user_household_info(user.id)

    # Format household info for response
    household_data = None
    if household_info:
        household_data = {
            "id": household_info["household_id"],
            "name": household_info["household_name"],
            "role": household_info["user_role"],
            "is_admin": household_info["is_admin"],
        }

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "household": household_data,
        },
    )


@router.get("/me", response_model=UserResponse)
@handle_service_errors
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)"""
    return RouterResponse.success(message="Logged out successfully")


@router.post("/refresh-token", response_model=dict)
@handle_service_errors
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token"""
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.id)}, expires_delta=token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/change-password")
@handle_service_errors
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change user password"""
    # Verify current password
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long",
        )

    # Update password
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()

    return RouterResponse.success(message="Password updated successfully")


@router.get("/profile", response_model=dict)
@handle_service_errors
async def get_user_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get comprehensive user profile with household info"""
    household_service = HouseholdService(db)
    household_info = household_service.get_user_household_info(current_user.id)

    profile = {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "phone": current_user.phone,
            "created_at": current_user.created_at,
            "is_active": current_user.is_active,
        },
        "household": household_info,
    }

    return RouterResponse.success(data=profile)
```

## app/models/enums.py
```python
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
```

## app/models/rsvp.py
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class RSVP(Base):
    __tablename__ = "rsvps"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)  # yes, no, maybe
    guest_count = Column(Integer, default=1)  # How many people they're bringing
    dietary_restrictions = Column(Text)
    special_requests = Column(Text)
    response_notes = Column(Text)

    # Foreign Keys
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    event = relationship("Event", back_populates="rsvps")
    user = relationship("User", back_populates="event_rsvps", foreign_keys=[user_id])
```

## app/models/event_approval.py
```python
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class EventApproval(Base):
    __tablename__ = "event_approvals"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved = Column(Boolean, nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    event = relationship("Event")
    user = relationship("User")
```

## app/schemas/rsvp.py
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class RSVPStatus(str, Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class RSVPBase(BaseModel):
    status: RSVPStatus
    guest_count: int = Field(1, ge=1, le=10, description="Number of people attending")
    dietary_restrictions: Optional[str] = Field(None, max_length=300)
    special_requests: Optional[str] = Field(None, max_length=300)
    response_notes: Optional[str] = Field(None, max_length=500)


class RSVPCreate(RSVPBase):
    event_id: int


class RSVPUpdate(BaseModel):
    status: Optional[RSVPStatus] = None
    guest_count: Optional[int] = Field(None, ge=1, le=10)
    dietary_restrictions: Optional[str] = Field(None, max_length=300)
    special_requests: Optional[str] = Field(None, max_length=300)
    response_notes: Optional[str] = Field(None, max_length=500)


class RSVPResponse(RSVPBase):
    id: int
    event_id: int
    event_title: str
    user_id: int
    user_name: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class EventRSVPSummary(BaseModel):
    event_id: int
    event_title: str
    total_responses: int
    yes_count: int
    no_count: int
    maybe_count: int
    total_guests: int
    responses: List[RSVPResponse]


class UserRSVPSummary(BaseModel):
    user_id: int
    upcoming_events: List[RSVPResponse]
    past_events_count: int
```

## app/schemas/event_approval.py
```python
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EventApprovalCreate(BaseModel):
    event_id: int
    approved: bool
    reason: Optional[str] = Field(None, max_length=500)


class EventApprovalResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    user_name: str
    approved: bool
    reason: Optional[str]
    created_at: datetime
```

