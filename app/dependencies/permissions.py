# app/dependencies/permissions.py

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..services.household_service import HouseholdService, HouseholdServiceError
from ..routers.auth import get_current_user


async def require_household_member(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> tuple[User, int]:
    """Ensure user is a household member and return user + household_id"""
    try:
        household_service = HouseholdService(db)
        household_info = household_service.get_user_household_info(current_user.id)

        if not household_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be a member of a household",
            )

        return current_user, household_info["household_id"]
    except HouseholdServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify household membership",
        )


async def require_household_admin(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> tuple[User, int]:
    """Ensure user is a household admin and return user + household_id"""
    try:
        # First check if user is a household member
        current_user, household_id = await require_household_member(current_user, db)

        # Then check admin permissions
        household_service = HouseholdService(db)
        if not household_service.check_admin_permissions(current_user.id, household_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permissions required",
            )

        return current_user, household_id
    except HTTPException:
        raise
    except HouseholdServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify admin permissions",
        )
