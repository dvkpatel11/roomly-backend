from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..database import get_db
from ..services.household_service import HouseholdService
from ..schemas.household import (
    HouseholdCreate, HouseholdUpdate, HouseholdResponse,
    HouseholdInvitation, HouseholdSummary
)
from .auth import get_current_user
from ..models.user import User

router = APIRouter()

@router.post("/", response_model=HouseholdResponse)
async def create_household(
    household_data: HouseholdCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new household"""
    try:
        household_service = HouseholdService(db)
        household = household_service.create_household(
            household_data=household_data,
            creator_id=current_user.id
        )
        return household
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{household_id}")
async def get_household_details(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed household information"""
    try:
        # Check if user has access to this household
        if current_user.household_id != household_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        household_service = HouseholdService(db)
        details = household_service.get_household_details(household_id)
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/")
async def get_my_household(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's household"""
    if not current_user.household_id:
        raise HTTPException(status_code=404, detail="User not in any household")
    
    return await get_household_details(current_user.household_id, db, current_user)

@router.put("/{household_id}")
async def update_household(
    household_id: int,
    household_update: HouseholdUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update household settings"""
    try:
        # Check access and admin rights
        if current_user.household_id != household_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        household_service = HouseholdService(db)
        household = household_service.update_household_settings(
            household_id=household_id,
            settings_update=household_update
        )
        return household
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{household_id}/members")
async def get_household_members(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household members"""
    if current_user.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    household_service = HouseholdService(db)
    members = household_service.get_household_members(household_id)
    
    return {"members": members}

@router.post("/{household_id}/invite")
async def invite_member(
    household_id: int,
    invitation: HouseholdInvitation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invite new member to household"""
    if current_user.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # This would integrate with email service to send invitation
    return {"message": f"Invitation sent to {invitation.email}"}

@router.post("/{household_id}/members/{user_id}")
async def add_member(
    household_id: int,
    user_id: int,
    role: str = "member",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add user to household"""
    if current_user.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    household_service = HouseholdService(db)
    success = household_service.add_member_to_household(
        household_id=household_id,
        user_id=user_id,
        role=role
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add member")
    
    return {"message": "Member added successfully"}

@router.delete("/{household_id}/members/{user_id}")
async def remove_member(
    household_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove member from household"""
    if current_user.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    household_service = HouseholdService(db)
    success = household_service.remove_member_from_household(
        household_id=household_id,
        user_id=user_id,
        removed_by=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove member")
    
    return {"message": "Member removed successfully"}

@router.get("/{household_id}/health-score")
async def get_household_health_score(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household health score"""
    if current_user.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    household_service = HouseholdService(db)
    health_score = household_service.calculate_household_health_score(household_id)
    
    return health_score

@router.get("/{household_id}/statistics")
async def get_household_statistics(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household statistics"""
    if current_user.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    household_service = HouseholdService(db)
    stats = household_service.get_household_statistics(household_id)
    
    return stats
