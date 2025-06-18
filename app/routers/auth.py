from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..models.user import User
from ..models.household import Household
from ..schemas.user import UserCreate, UserResponse
from ..utils.security import verify_password, get_password_hash, create_access_token
from ..utils.validation import ValidationHelpers
from jose import JWTError, jwt
import os

router = APIRouter()
security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        # Validate email format
        if not ValidationHelpers.validate_email(user_data.email):
            raise HTTPException(
                status_code=400, 
                detail="Invalid email format"
            )
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            name=user_data.name,
            hashed_password=hashed_password,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create user")

@router.post("/login")
async def login(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    """Login user and return access token"""
    try:
        # Find user
        user = db.query(User).filter(User.email == email).first()
        
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        # Get household info if user is in one
        household_info = None
        if user.household_id:
            household = db.query(Household).filter(Household.id == user.household_id).first()
            if household:
                household_info = {
                    "id": household.id,
                    "name": household.name
                }
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "household": household_info
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)"""
    return {"message": "Logged out successfully"}

@router.post("/refresh-token")
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """Refresh access token"""
    access_token = create_access_token(data={"sub": str(current_user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# Dependency function to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user
