from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from ..database import get_db
from ..services.guest_service import GuestService
from ..services.approval_service import ApprovalService
from ..schemas.guest import GuestCreate, GuestResponse
from ..schemas.guest_approval import GuestApprovalCreate
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    validate_pagination,
)
from ..models.user import User
from ..utils.constants import AppConstants

router = APIRouter(tags=["guests"])


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
    """Get household guests with filtering and pagination"""
    current_user, household_id = user_household

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    guest_service = GuestService(db)
    guests = guest_service.get_household_guests(
        household_id=household_id,
        upcoming_only=upcoming_only,
        include_pending=include_pending,
        limit=limit,
        offset=offset,
    )

    return RouterResponse.success(data=guests)


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
        guest_id=guest_id,
        approver_id=current_user.id,
        reason=approval_data.get("reason") if approval_data else None,
    )

    return RouterResponse.success(data=result, message="Guest approved successfully")


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

    return RouterResponse.success(data=result, message="Guest request denied")


@router.delete("/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def cancel_guest_request(
    guest_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Cancel a guest request (host only)"""
    current_user, household_id = user_household
    guest_service = GuestService(db)

    guest_service.cancel_guest_request(
        guest_id=guest_id, cancelled_by=current_user.id, household_id=household_id
    )


@router.get("/conflicts", response_model=Dict[str, Any])
@handle_service_errors
async def check_guest_conflicts(
    proposed_checkin: datetime = Query(..., description="Proposed check-in date"),
    proposed_checkout: Optional[datetime] = Query(
        None, description="Proposed check-out date"
    ),
    guest_count: int = Query(1, ge=1, le=10, description="Number of guests"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Check for guest conflicts before registration"""
    current_user, household_id = user_household
    guest_service = GuestService(db)

    conflicts = guest_service.check_guest_conflicts(
        household_id=household_id,
        proposed_checkin=proposed_checkin,
        proposed_checkout=proposed_checkout,
        guest_count=guest_count,
    )

    return RouterResponse.success(data={"conflicts": conflicts})


@router.get("/me/hosted", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_hosted_guests(
    upcoming_only: bool = Query(True, description="Show only upcoming guests"),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guests hosted by current user"""
    current_user, household_id = user_household
    guest_service = GuestService(db)

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    my_guests = guest_service.get_user_hosted_guests(
        user_id=current_user.id,
        household_id=household_id,
        upcoming_only=upcoming_only,
        limit=limit,
        offset=offset,
    )

    return RouterResponse.success(data=my_guests)


@router.get("/approvals/pending", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_pending_approvals(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guest requests requiring current user's approval"""
    current_user, household_id = user_household
    approval_service = ApprovalService(db)

    pending_approvals = approval_service.get_user_pending_approvals(
        user_id=current_user.id, household_id=household_id, approval_type="guest"
    )

    return RouterResponse.success(
        data={
            "pending_approvals": pending_approvals,
            "count": len(pending_approvals),
        }
    )


@router.get("/config/relationship-types", response_model=Dict[str, Any])
async def get_relationship_types():
    """Get available guest relationship types"""
    from ..models.enums import GuestRelationship

    relationship_types = [
        {"value": rel.value, "label": rel.value.replace("_", " ").title()}
        for rel in GuestRelationship
    ]

    return RouterResponse.success(data={"relationship_types": relationship_types})


@router.get("/templates", response_model=Dict[str, Any])
@handle_service_errors
async def get_guest_templates(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get guest registration templates for quick guest creation"""
    current_user, household_id = user_household
    guest_service = GuestService(db)

    templates = guest_service.get_guest_templates(
        household_id=household_id, user_id=current_user.id
    )

    return RouterResponse.success(data={"templates": templates})
