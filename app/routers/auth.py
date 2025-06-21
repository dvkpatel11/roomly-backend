from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from ..database import get_db, get_supabase
from ..models.user import User
from ..services.household_service import HouseholdService
from ..schemas.user import UserResponse
from ..utils.router_helpers import handle_service_errors, RouterResponse
from supabase import Client
import logging

router = APIRouter(tags=["authentication"])
security = HTTPBearer()
logger = logging.getLogger(__name__)


# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: str = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# Auth Helper Functions
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    supabase: Client = Depends(get_supabase),
) -> User:
    """Get current authenticated user from Supabase token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token with Supabase
        auth_response = supabase.auth.get_user(credentials.credentials)

        if not auth_response.user:
            raise credentials_exception

        supabase_user = auth_response.user

        # Find user in our database by Supabase ID
        user = (
            db.query(User)
            .filter(User.supabase_id == supabase_user.id, User.is_active == True)
            .first()
        )

        # If user doesn't exist in our DB, create them
        if not user:
            user = User.create_from_supabase(supabase_user, db)

        return user

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception


# Auth Endpoints
@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def register_user(
    user_data: RegisterRequest,
    db: Session = Depends(get_db),
    supabase: Client = Depends(get_supabase),
):
    """Register a new user with Supabase Auth"""

    # Check if user already exists in our database
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    try:
        # Register with Supabase Auth
        auth_response = supabase.auth.sign_up(
            {
                "email": user_data.email,
                "password": user_data.password,
                "options": {"data": {"name": user_data.name, "phone": user_data.phone}},
            }
        )

        if auth_response.user:
            # Create user in our database
            user = User(
                email=user_data.email,
                name=user_data.name,
                phone=user_data.phone,
                supabase_id=auth_response.user.id,
                is_active=True,
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            return {
                "message": "Registration successful. Please check your email to verify your account.",
                "user_id": user.id,
                "email": user.email,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed"
            )

    except Exception as e:
        logger.error(f"Registration error: {e}")
        # If Supabase registration fails, make sure we don't leave orphaned DB records
        if "user" in locals():
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login", response_model=LoginResponse)
@handle_service_errors
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    supabase: Client = Depends(get_supabase),
):
    """Login user with Supabase Auth"""

    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password(
            {"email": login_data.email, "password": login_data.password}
        )

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Get or create user in our database
        user = db.query(User).filter(User.supabase_id == auth_response.user.id).first()

        if not user:
            # Create user if they don't exist (shouldn't happen normally)
            user = User.create_from_supabase(auth_response.user, db)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
            )

        # Get household info
        household_service = HouseholdService(db)
        household_info = household_service.get_user_household_info(user.id)

        household_data = None
        if household_info:
            household_data = {
                "id": household_info["household_id"],
                "name": household_info["household_name"],
                "role": household_info["user_role"],
                "is_admin": household_info["is_admin"],
            }

        return LoginResponse(
            access_token=auth_response.session.access_token,
            token_type="bearer",
            expires_in=auth_response.session.expires_in,
            user={
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "household": household_data,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
@handle_service_errors
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase),
):
    """Logout user (invalidate Supabase session)"""
    try:
        # Sign out from Supabase (invalidates the token)
        supabase.auth.sign_out()
        return RouterResponse.success(message="Logged out successfully")
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Even if Supabase logout fails, we can still return success
        # since the client will remove the token
        return RouterResponse.success(message="Logged out successfully")


@router.post("/refresh-token", response_model=dict)
@handle_service_errors
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase),
):
    """Refresh access token"""
    try:
        # Refresh the session with Supabase
        refresh_response = supabase.auth.refresh_session()

        if refresh_response.session:
            return {
                "access_token": refresh_response.session.access_token,
                "token_type": "bearer",
                "expires_in": refresh_response.session.expires_in,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh token",
            )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token refresh failed"
        )


@router.post("/change-password")
@handle_service_errors
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
):
    """Change user password"""

    # Validate new password
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long",
        )

    try:
        # Update password in Supabase
        supabase.auth.update_user({"password": password_data.new_password})

        return RouterResponse.success(message="Password updated successfully")

    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password change failed"
        )


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
            "auth_provider": "supabase" if current_user.is_supabase_user else "legacy",
        },
        "household": household_info,
    }

    return RouterResponse.success(data=profile)


# Password Reset (using Supabase)
@router.post("/reset-password")
@handle_service_errors
async def reset_password(email: EmailStr, supabase: Client = Depends(get_supabase)):
    """Send password reset email"""
    try:
        supabase.auth.reset_password_email(email)
        return RouterResponse.success(
            message="Password reset email sent. Please check your inbox."
        )
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        # Don't reveal if email exists or not for security
        return RouterResponse.success(
            message="If the email exists, a password reset link has been sent."
        )
