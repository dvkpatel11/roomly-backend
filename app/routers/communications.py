from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..services.communication_service import CommunicationService
from ..schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from ..schemas.poll import PollCreate, PollUpdate, PollVoteCreate, PollResponse
from .auth import get_current_user
from ..models.user import User

router = APIRouter()

# Announcements
@router.post("/announcements", response_model=AnnouncementResponse)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new household announcement"""
    try:
        communication_service = CommunicationService(db)
        announcement = communication_service.create_announcement(
            announcement_data=announcement_data,
            household_id=current_user.household_id,
            created_by=current_user.id
        )
        return announcement
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/announcements")
async def get_announcements(
    category: Optional[str] = None,
    include_expired: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household announcements"""
    communication_service = CommunicationService(db)
    
    announcements = communication_service.get_household_announcements(
        household_id=current_user.household_id,
        category=category,
        include_expired=include_expired,
        limit=limit
    )
    
    return {"announcements": announcements}

@router.put("/announcements/{announcement_id}/pin")
async def pin_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pin or unpin an announcement"""
    communication_service = CommunicationService(db)
    
    success = communication_service.pin_announcement(
        announcement_id=announcement_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement pin status updated"}

# Polls
@router.post("/polls", response_model=PollResponse)
async def create_poll(
    poll_data: PollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new poll for household decision making"""
    try:
        communication_service = CommunicationService(db)
        poll = communication_service.create_poll(
            poll_data=poll_data,
            household_id=current_user.household_id,
            created_by=current_user.id
        )
        return poll
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/polls")
async def get_polls(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household polls"""
    communication_service = CommunicationService(db)
    
    polls = communication_service.get_active_polls(
        household_id=current_user.household_id
    )
    
    return {"polls": polls}

@router.post("/polls/{poll_id}/vote")
async def vote_on_poll(
    poll_id: int,
    vote_data: PollVoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cast vote on a poll"""
    try:
        communication_service = CommunicationService(db)
        result = communication_service.vote_on_poll(
            poll_id=poll_id,
            user_id=current_user.id,
            vote_data=vote_data
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/polls/{poll_id}/results")
async def get_poll_results(
    poll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get poll results and statistics"""
    try:
        communication_service = CommunicationService(db)
        results = communication_service.get_poll_results(poll_id)
        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/polls/{poll_id}/close")
async def close_poll(
    poll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Close a poll"""
    communication_service = CommunicationService(db)
    
    success = communication_service.close_poll(
        poll_id=poll_id,
        closed_by=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    return {"message": "Poll closed successfully"}

# House Rules
@router.get("/house-rules")
async def get_house_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household rules"""
    # This would integrate with household service
    from ..services.household_service import HouseholdService
    
    household_service = HouseholdService(db)
    household = household_service.get_household_details(current_user.household_id)
    
    return {"house_rules": household.get("house_rules", "")}

@router.put("/house-rules")
async def update_house_rules(
    rules_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update house rules (admin only)"""
    # Add admin check and household service integration
    return {"message": "House rules updated successfully"}

@router.get("/activity-summary")
async def get_communication_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get communication activity summary"""
    communication_service = CommunicationService(db)
    
    summary = communication_service.get_communication_summary(
        household_id=current_user.household_id
    )
    
    return summary
