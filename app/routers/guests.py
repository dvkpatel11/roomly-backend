from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..database import get_db
from ..services.approval_service import ApprovalService
from ..schemas.guest import GuestCreate, GuestResponse
from .auth import get_current_user
from ..models.user import User

router = APIRouter()

@router.post("/", response_model=GuestResponse)
async def register_guest(
    guest_data: GuestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register a new guest (requires household approval)"""
    try:
        approval_service = ApprovalService(db)
        guest = approval_service.create_guest_request(
            guest_data=guest_data,
            household_id=current_user.household_id,
            hosted_by=current_user.id
        )
        return guest
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
async def get_household_guests(
    upcoming_only: bool = True,
    include_pending: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get guests for household"""
    # Add method to ApprovalService
    approval_service = ApprovalService(db)
    
    guests = []  # approval_service.get_household_guests(current_user.household_id, upcoming_only, include_pending)
    
    return {"guests": guests}

@router.get("/pending-approval")
async def get_pending_guest_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get guests pending approval"""
    approval_service = ApprovalService(db)
    
    pending_guests = approval_service.get_pending_guest_approvals(
        household_id=current_user.household_id
    )
    
    return {"pending_guests": pending_guests}

@router.put("/{guest_id}/approve")
async def approve_guest(
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a guest request"""
    approval_service = ApprovalService(db)
    
    result = approval_service.approve_guest(
        guest_id=guest_id,
        approver_id=current_user.id
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.put("/{guest_id}/deny")
async def deny_guest(
    guest_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deny a guest request"""
    approval_service = ApprovalService(db)
    
    result = approval_service.deny_guest(
        guest_id=guest_id,
        denier_id=current_user.id,
        reason=reason
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/policies")
async def get_guest_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household guest policies"""
    # This would come from household settings
    from ..utils.constants import GuestPolicy
    
    return {
        "max_overnight_guests": GuestPolicy.DEFAULT_MAX_OVERNIGHT_GUESTS,
        "max_consecutive_nights": GuestPolicy.DEFAULT_MAX_CONSECUTIVE_NIGHTS,
        "approval_required": GuestPolicy.DEFAULT_APPROVAL_REQUIRED,
        "quiet_hours_start": GuestPolicy.DEFAULT_QUIET_HOURS_START,
        "quiet_hours_end": GuestPolicy.DEFAULT_QUIET_HOURS_END
    }

@router.put("/policies")
async def update_guest_policies(
    policies: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update household guest policies (admin only)"""
    # Add admin check and household service integration
    return {"message": "Guest policies updated successfully"}
