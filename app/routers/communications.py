from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from ..database import get_db
from ..services.communication_service import CommunicationService
from ..services.household_service import HouseholdService
from ..schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
)
from ..schemas.poll import PollCreate, PollUpdate, PollVoteCreate
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    validate_pagination,
)
from ..models.user import User
from ..utils.constants import AppConstants

router = APIRouter(tags=["communications"])


# ANNOUNCEMENTS
@router.post(
    "/announcements", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED
)
@handle_service_errors
async def create_announcement(
    announcement_data: AnnouncementCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new household announcement"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    announcement = communication_service.create_announcement(
        announcement_data=announcement_data,
        household_id=household_id,
        created_by=current_user.id,
    )

    return RouterResponse.created(
        data={"announcement": announcement}, message="Announcement created successfully"
    )


@router.get("/announcements", response_model=Dict[str, Any])
@handle_service_errors
async def get_announcements(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_expired: bool = Query(False, description="Include expired announcements"),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household announcements with filtering and pagination"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    result = communication_service.get_household_announcements(
        household_id=household_id,
        user_id=current_user.id,
        category=category,
        include_expired=include_expired,
        limit=limit,
        offset=offset,
    )

    return RouterResponse.success(data=result)


@router.get("/announcements/{announcement_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_announcement_details(
    announcement_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get detailed announcement information"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    details = communication_service.get_announcement_details(
        announcement_id=announcement_id, user_id=current_user.id
    )

    return RouterResponse.success(data=details)


@router.put("/announcements/{announcement_id}", response_model=Dict[str, Any])
@handle_service_errors
async def update_announcement(
    announcement_id: int,
    announcement_updates: AnnouncementUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update announcement (creator or admin only)"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    announcement = communication_service.update_announcement(
        announcement_id=announcement_id,
        announcement_updates=announcement_updates,
        updated_by=current_user.id,
    )

    return RouterResponse.updated(
        data={"announcement": announcement}, message="Announcement updated successfully"
    )


@router.delete(
    "/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT
)
@handle_service_errors
async def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Delete announcement (creator or admin only)"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    communication_service.delete_announcement(
        announcement_id=announcement_id, deleted_by=current_user.id
    )


@router.put("/announcements/{announcement_id}/pin", response_model=Dict[str, Any])
@handle_service_errors
async def toggle_announcement_pin(
    announcement_id: int,
    pin_data: Dict[str, bool] = Body(..., example={"pinned": True}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Pin or unpin an announcement (admin only)"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    pinned = pin_data.get("pinned", True)

    success = communication_service.pin_announcement(
        announcement_id=announcement_id, user_id=current_user.id, pinned=pinned
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
        )

    action = "pinned" if pinned else "unpinned"
    return RouterResponse.success(message=f"Announcement {action} successfully")


# POLLS
@router.post(
    "/polls", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED
)
@handle_service_errors
async def create_poll(
    poll_data: PollCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new poll for household decision making"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    poll = communication_service.create_poll(
        poll_data=poll_data,
        household_id=household_id,
        created_by=current_user.id,
    )

    return RouterResponse.created(
        data={"poll": poll}, message="Poll created successfully"
    )


@router.get("/polls", response_model=Dict[str, Any])
@handle_service_errors
async def get_polls(
    active_only: bool = Query(True, description="Show only active polls"),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household polls with filtering and pagination"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    result = communication_service.get_household_polls(
        household_id=household_id,
        user_id=current_user.id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    return RouterResponse.success(data=result)


@router.get("/polls/{poll_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_poll_details(
    poll_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get poll details and results"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    details = communication_service.get_poll_details(
        poll_id=poll_id, user_id=current_user.id
    )

    return RouterResponse.success(data=details)


@router.put("/polls/{poll_id}", response_model=Dict[str, Any])
@handle_service_errors
async def update_poll(
    poll_id: int,
    poll_updates: PollUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update poll (creator or admin only)"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    poll = communication_service.update_poll(
        poll_id=poll_id,
        poll_updates=poll_updates,
        updated_by=current_user.id,
    )

    return RouterResponse.updated(
        data={"poll": poll}, message="Poll updated successfully"
    )


@router.delete("/polls/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def delete_poll(
    poll_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Delete poll (creator or admin only)"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    communication_service.delete_poll(poll_id=poll_id, deleted_by=current_user.id)


@router.post("/polls/{poll_id}/vote", response_model=Dict[str, Any])
@handle_service_errors
async def vote_on_poll(
    poll_id: int,
    vote_data: PollVoteCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Cast vote on a poll"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    result = communication_service.vote_on_poll(
        poll_id=poll_id, user_id=current_user.id, vote_data=vote_data
    )

    return RouterResponse.success(data=result, message="Vote recorded successfully")


@router.put("/polls/{poll_id}/close", response_model=Dict[str, Any])
@handle_service_errors
async def close_poll(
    poll_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Close a poll (creator or admin only)"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    success = communication_service.close_poll(
        poll_id=poll_id, closed_by=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found"
        )

    return RouterResponse.success(message="Poll closed successfully")


# HOUSE RULES
@router.get("/house-rules", response_model=Dict[str, Any])
@handle_service_errors
async def get_house_rules(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household rules"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    household = household_service.get_household_details(household_id)

    return RouterResponse.success(
        data={
            "house_rules": household.get("house_rules", ""),
            "last_updated": household.get("updated_at"),
        }
    )


@router.put("/house-rules", response_model=Dict[str, Any])
@handle_service_errors
async def update_house_rules(
    rules_data: Dict[str, str] = Body(
        ..., example={"house_rules": "New house rules text"}
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Update house rules (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    house_rules = rules_data.get("house_rules")
    if not house_rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="house_rules field is required",
        )

    from ..schemas.household import HouseholdUpdate

    update_data = HouseholdUpdate(house_rules=house_rules)

    household = household_service.update_household_settings(
        household_id=household_id,
        settings_update=update_data,
        updated_by=current_user.id,
    )

    return RouterResponse.updated(
        data={"house_rules": household.house_rules},
        message="House rules updated successfully",
    )


# SUMMARY ENDPOINTS
@router.get("/summary", response_model=Dict[str, Any])
@handle_service_errors
async def get_communication_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get communication activity summary"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    user_summary = communication_service.get_user_communication_summary(
        user_id=current_user.id, household_id=household_id
    )

    household_summary = communication_service.get_household_communication_summary(
        household_id=household_id, user_id=current_user.id
    )

    return RouterResponse.success(
        data={
            "user_activity": user_summary,
            "household_activity": household_summary,
        }
    )


@router.get("/config/categories", response_model=Dict[str, Any])
async def get_announcement_categories():
    """Get available announcement categories"""
    categories = [
        {"value": "general", "label": "General"},
        {"value": "maintenance", "label": "Maintenance"},
        {"value": "event", "label": "Event"},
        {"value": "rule", "label": "Rule Change"},
        {"value": "financial", "label": "Financial"},
        {"value": "urgent", "label": "Urgent"},
    ]

    return RouterResponse.success(data={"categories": categories})


@router.get("/config/priorities", response_model=Dict[str, Any])
async def get_priority_levels():
    """Get available priority levels"""
    from ..utils.constants import Priority

    priorities = [
        {"value": priority.value, "label": priority.value.title()}
        for priority in Priority
    ]

    return RouterResponse.success(data={"priorities": priorities})
