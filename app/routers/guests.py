from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..services.approval_service import ApprovalService
from ..schemas.guest import GuestCreate, GuestResponse
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    validate_pagination,
)
from ..models.user import User
from ..utils.constants import AppConstants, GuestPolicy

router = APIRouter(prefix="/guests", tags=["guests"])


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def register_guest(
    guest_data: GuestCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Register a new guest (requires household approval)"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    guest = approval_service.create_guest_request(
        guest_data=guest_data,
        household_id=household_id,
        hosted_by=current_user.id,
    )

    return RouterResponse.created(
        data={"guest": guest}, message="Guest registration submitted for approval"
    )


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_guests(
    upcoming_only: bool = Query(True, description="Show only upcoming guests"),
    include_pending: bool = Query(True, description="Include pending approvals"),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guests for household with filtering and pagination"""
    current_user, household_id = user_household

    # TODO: Add get_household_guests method to ApprovalService
    # For now, return empty structure
    guests = []

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    return RouterResponse.success(
        data={
            "guests": guests,
            "total_count": len(guests),
            "upcoming_only": upcoming_only,
            "include_pending": include_pending,
        }
    )


@router.get("/pending", response_model=Dict[str, Any])
@handle_service_errors
async def get_pending_guest_approvals(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guests pending approval"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    pending_guests = approval_service.get_pending_guest_approvals(
        household_id=household_id
    )

    return RouterResponse.success(
        data={
            "pending_guests": pending_guests,
            "count": len(pending_guests),
        }
    )


@router.get("/{guest_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_details(
    guest_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get detailed guest information"""
    current_user, household_id = user_household

    # TODO: Add get_guest_details method to ApprovalService
    # For now, return placeholder
    guest_details = {
        "guest_id": guest_id,
        "household_id": household_id,
        "message": "Guest details not yet implemented",
    }

    return RouterResponse.success(data={"guest": guest_details})


@router.put("/{guest_id}/approve", response_model=Dict[str, Any])
@handle_service_errors
async def approve_guest(
    guest_id: int,
    approval_data: Dict[str, str] = Body(None, example={"reason": "Looks good to me!"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Approve a guest request"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    result = approval_service.approve_guest(
        guest_id=guest_id, approver_id=current_user.id
    )

    return RouterResponse.success(
        data=result, message=result.get("message", "Guest approval processed")
    )


@router.put("/{guest_id}/deny", response_model=Dict[str, Any])
@handle_service_errors
async def deny_guest(
    guest_id: int,
    denial_data: Dict[str, str] = Body(
        ..., example={"reason": "Conflicts with existing plans"}
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Deny a guest request"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    reason = denial_data.get("reason", "")

    result = approval_service.deny_guest(
        guest_id=guest_id, denier_id=current_user.id, reason=reason
    )

    return RouterResponse.success(
        data=result, message=result.get("message", "Guest request denied")
    )


@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def cancel_guest_request(
    guest_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Cancel a guest request (host only)"""
    current_user, household_id = user_household

    # TODO: Add cancel_guest_request method to ApprovalService
    # This should verify the current user is the host
    pass


@router.get("/policies", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_policies(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household guest policies"""
    current_user, household_id = user_household

    # TODO: Get from household settings instead of defaults
    policies = {
        "max_overnight_guests": GuestPolicy.DEFAULT_MAX_OVERNIGHT_GUESTS,
        "max_consecutive_nights": GuestPolicy.DEFAULT_MAX_CONSECUTIVE_NIGHTS,
        "approval_required": GuestPolicy.DEFAULT_APPROVAL_REQUIRED,
        "quiet_hours_start": GuestPolicy.DEFAULT_QUIET_HOURS_START,
        "quiet_hours_end": GuestPolicy.DEFAULT_QUIET_HOURS_END,
    }

    return RouterResponse.success(data={"guest_policies": policies})


@router.put("/policies", response_model=Dict[str, Any])
@handle_service_errors
async def update_guest_policies(
    policies_data: Dict[str, Any] = Body(
        ...,
        example={
            "max_overnight_guests": 3,
            "max_consecutive_nights": 5,
            "approval_required": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Update household guest policies (admin only)"""
    current_user, household_id = user_household

    # TODO: Integrate with household service to update settings
    # For now, return success message

    return RouterResponse.updated(
        data={"updated_policies": policies_data},
        message="Guest policies updated successfully",
    )


@router.get("/calendar", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_calendar(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guest calendar showing upcoming stays"""
    current_user, household_id = user_household

    # TODO: Add get_guest_calendar method to ApprovalService
    calendar_data = {
        "start_date": start_date,
        "end_date": end_date,
        "guest_stays": [],
        "conflicts": [],
    }

    return RouterResponse.success(data={"guest_calendar": calendar_data})


@router.get("/statistics", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_statistics(
    months_back: int = Query(6, ge=1, le=24, description="Months of data to analyze"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guest statistics for household"""
    current_user, household_id = user_household

    # TODO: Add get_guest_statistics method to ApprovalService
    statistics = {
        "household_id": household_id,
        "period_months": months_back,
        "total_guest_requests": 0,
        "approved_guests": 0,
        "denied_guests": 0,
        "overnight_stays": 0,
        "average_stay_duration": 0,
        "most_active_host": None,
        "approval_rate": 0,
    }

    return RouterResponse.success(data={"guest_statistics": statistics})


@router.get("/config/relationship-types", response_model=Dict[str, Any])
async def get_relationship_types():
    """Get available guest relationship types"""
    relationship_types = [
        {"value": "friend", "label": "Friend"},
        {"value": "family", "label": "Family"},
        {"value": "partner", "label": "Partner"},
        {"value": "colleague", "label": "Colleague"},
        {"value": "acquaintance", "label": "Acquaintance"},
        {"value": "other", "label": "Other"},
    ]

    return RouterResponse.success(data={"relationship_types": relationship_types})
