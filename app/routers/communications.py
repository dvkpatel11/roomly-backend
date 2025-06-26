from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..services.communication_service import CommunicationService
from ..services.household_service import HouseholdService
from ..schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    AnnouncementPin,
)
from ..schemas.household import HouseholdUpdate
from ..schemas.poll import (
    PollCreate,
    PollUpdate,
    PollVoteCreate,
    PollResponse,
)
from ..schemas.common import (
    SuccessResponse,
    PaginatedResponse,
    ResponseFactory,
    PaginationParams,
    ConfigResponse,
    ConfigOption,
)
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import handle_service_errors
from ..models.user import User
from ..utils.constants import ResponseMessages

router = APIRouter(tags=["communications"])


@router.post("/announcements", response_model=SuccessResponse[AnnouncementResponse])
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

    return ResponseFactory.created(
        data=announcement, message=ResponseMessages.ANNOUNCEMENT_CREATED
    )


@router.get("/announcements", response_model=PaginatedResponse[AnnouncementResponse])
@handle_service_errors
async def get_announcements(
    pagination: PaginationParams = Depends(),
    category: Optional[str] = Query(None, description="Filter by category"),
    include_expired: bool = Query(False, description="Include expired announcements"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household announcements with filtering and pagination"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    result = communication_service.get_household_announcements(
        household_id=household_id,
        user_id=current_user.id,
        category=category,
        include_expired=include_expired,
        limit=pagination.limit,
        offset=pagination.offset,
    )

    # Create pagination info from result
    from ..schemas.common import PaginationInfo

    announcements = result.get("announcements", [])
    total_count = result.get("total_count", 0)

    pagination_info = PaginationInfo(
        current_page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_count,
        total_pages=(total_count + pagination.page_size - 1) // pagination.page_size,
        has_next=pagination.offset + pagination.page_size < total_count,
        has_previous=pagination.page > 1,
    )

    return ResponseFactory.paginated(data=announcements, pagination=pagination_info)


@router.get("/announcements/{announcement_id}", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(data=details)


@router.put(
    "/announcements/{announcement_id}",
    response_model=SuccessResponse[AnnouncementResponse],
)
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

    return ResponseFactory.success(
        data=announcement, message=ResponseMessages.ANNOUNCEMENT_UPDATED
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


@router.put(
    "/announcements/{announcement_id}/pin", response_model=SuccessResponse[dict]
)
@handle_service_errors
async def toggle_announcement_pin(
    announcement_id: int,
    pin_data: AnnouncementPin,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Pin or unpin an announcement (admin only)"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    success = communication_service.pin_announcement(
        announcement_id=announcement_id, user_id=current_user.id, pinned=pin_data.pinned
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
        )

    action = "pinned" if pin_data.pinned else "unpinned"
    return ResponseFactory.success(
        data={"announcement_id": announcement_id, "pinned": pin_data.pinned},
        message=f"Announcement {action} successfully",
    )


# =============================================================================
# POLL ENDPOINTS
# =============================================================================


@router.post("/polls", response_model=SuccessResponse[PollResponse])
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

    return ResponseFactory.created(data=poll, message=ResponseMessages.POLL_CREATED)


@router.get("/polls", response_model=PaginatedResponse[PollResponse])
@handle_service_errors
async def get_polls(
    pagination: PaginationParams = Depends(),
    active_only: bool = Query(True, description="Show only active polls"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household polls with filtering and pagination"""
    current_user, household_id = user_household
    communication_service = CommunicationService(db)

    result = communication_service.get_household_polls(
        household_id=household_id,
        user_id=current_user.id,
        active_only=active_only,
        limit=pagination.limit,
        offset=pagination.offset,
    )

    # Create pagination info from result
    from ..schemas.common import PaginationInfo

    polls = result.get("polls", [])
    total_count = result.get("total_count", 0)

    pagination_info = PaginationInfo(
        current_page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_count,
        total_pages=(total_count + pagination.page_size - 1) // pagination.page_size,
        has_next=pagination.offset + pagination.page_size < total_count,
        has_previous=pagination.page > 1,
    )

    return ResponseFactory.paginated(data=polls, pagination=pagination_info)


@router.get("/polls/{poll_id}", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(data=details)


@router.put("/polls/{poll_id}", response_model=SuccessResponse[PollResponse])
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

    return ResponseFactory.success(data=poll, message=ResponseMessages.POLL_UPDATED)


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


@router.post("/polls/{poll_id}/vote", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(data=result, message=ResponseMessages.VOTE_RECORDED)


@router.put("/polls/{poll_id}/close", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(
        data={"poll_id": poll_id, "closed": True}, message="Poll closed successfully"
    )


# =============================================================================
# HOUSE RULES ENDPOINTS
# =============================================================================


@router.get("/house-rules", response_model=SuccessResponse[dict])
@handle_service_errors
async def get_house_rules(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household rules"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    household = household_service.get_household_details(household_id)

    return ResponseFactory.success(
        data={
            "house_rules": household.get("house_rules", ""),
            "last_updated": household.get("updated_at"),
        }
    )


@router.put("/house-rules", response_model=SuccessResponse[dict])
@handle_service_errors
async def update_house_rules(
    rules_data: HouseholdUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Update house rules (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)
    update_data = HouseholdUpdate(house_rules=rules_data.house_rules)

    household = household_service.update_household_settings(
        household_id=household_id,
        settings_update=update_data,
        updated_by=current_user.id,
    )

    return ResponseFactory.success(
        data={"house_rules": household.house_rules},
        message=ResponseMessages.HOUSEHOLD_UPDATED,
    )


# =============================================================================
# SUMMARY ENDPOINTS
# =============================================================================


@router.get("/summary", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(
        data={
            "user_activity": user_summary,
            "household_activity": household_summary,
        }
    )


# =============================================================================
# CONFIGURATION ENDPOINTS
# =============================================================================


@router.get("/config/categories", response_model=SuccessResponse[ConfigResponse])
async def get_announcement_categories():
    """Get available announcement categories"""
    categories_data = [
        {
            "value": "general",
            "label": "General",
            "description": "General household announcements",
        },
        {
            "value": "maintenance",
            "label": "Maintenance",
            "description": "Maintenance and repairs",
        },
        {
            "value": "event",
            "label": "Event",
            "description": "Upcoming events and activities",
        },
        {
            "value": "rule",
            "label": "Rule Change",
            "description": "Changes to house rules",
        },
        {
            "value": "financial",
            "label": "Financial",
            "description": "Financial matters and bills",
        },
        {
            "value": "urgent",
            "label": "Urgent",
            "description": "Urgent announcements requiring immediate attention",
        },
    ]

    options = [
        ConfigOption(
            value=cat["value"], label=cat["label"], description=cat["description"]
        )
        for cat in categories_data
    ]

    return ResponseFactory.success(
        data=ConfigResponse(
            options=options,
            total_count=len(options),
            category="Announcement Categories",
        )
    )


@router.get("/config/priorities", response_model=SuccessResponse[ConfigResponse])
async def get_priority_levels():
    """Get available priority levels"""
    from ..schemas.enums import Priority

    options = [
        ConfigOption(
            value=priority.value,
            label=priority.value.title(),
            description=f"Priority level: {priority.value}",
        )
        for priority in Priority
    ]

    return ResponseFactory.success(
        data=ConfigResponse(
            options=options, total_count=len(options), category="Priority Levels"
        )
    )
