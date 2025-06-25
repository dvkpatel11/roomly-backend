# Communication Page - Backend Context

## Overview

Announcements, polls, notifications, and household communication.

## Related Files:

## app/routers/communications.py

```python
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
```

## app/routers/notifications.py

```python
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Body,
    BackgroundTasks,
)
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..database import get_db
from ..services.notification_service import NotificationService
from ..models.notification import Notification
from ..schemas.notification import (
    NotificationResponse,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationSummary,
)
from ..dependencies.permissions import require_household_member
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    validate_pagination,
)
from ..models.user import User
from ..utils.constants import AppConstants
from ..utils.background_tasks import (
    trigger_bill_reminders,
    trigger_task_reminders,
    trigger_event_reminders,
    scheduler,
)
from sqlalchemy import and_
from .auth import get_current_user

router = APIRouter(tags=["notifications"])


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_user_notifications(
    unread_only: bool = Query(False, description="Show only unread notifications"),
    priority: Optional[str] = Query(None, description="Filter by priority level"),
    notification_type: Optional[str] = Query(
        None, description="Filter by notification type"
    ),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get user's notifications with filtering and pagination"""
    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    # Build query
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    if priority:
        query = query.filter(Notification.priority == priority)

    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)

    # Get total count
    total_count = query.count()

    # Get notifications with pagination
    notifications = (
        query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    )

    notification_list = []
    for notification in notifications:
        notification_list.append(
            {
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "notification_type": notification.notification_type,
                "priority": notification.priority,
                "is_read": notification.is_read,
                "related_entity_type": notification.related_entity_type,
                "related_entity_id": notification.related_entity_id,
                "action_url": notification.action_url,
                "created_at": notification.created_at,
                "read_at": notification.read_at,
            }
        )

    return RouterResponse.success(
        data={
            "notifications": notification_list,
            "total_count": total_count,
            "unread_count": len([n for n in notification_list if not n["is_read"]]),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }
    )


@router.get("/{notification_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_notification_details(
    notification_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get detailed notification information"""
    notification = (
        db.query(Notification)
        .filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    notification_detail = {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "notification_type": notification.notification_type,
        "priority": notification.priority,
        "is_read": notification.is_read,
        "related_entity_type": notification.related_entity_type,
        "related_entity_id": notification.related_entity_id,
        "action_url": notification.action_url,
        "sent_in_app": notification.sent_in_app,
        "sent_email": notification.sent_email,
        "sent_push": notification.sent_push,
        "created_at": notification.created_at,
        "read_at": notification.read_at,
    }

    return RouterResponse.success(data={"notification": notification_detail})


@router.put("/{notification_id}/read", response_model=Dict[str, Any])
@handle_service_errors
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Mark notification as read"""
    notification = (
        db.query(Notification)
        .filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()

    return RouterResponse.success(message="Notification marked as read")


@router.put("/mark-all-read", response_model=Dict[str, Any])
@handle_service_errors
async def mark_all_notifications_read(
    notification_types: Optional[List[str]] = Body(
        None, description="Optional filter by notification types"
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Mark all (or filtered) notifications as read"""
    query = db.query(Notification).filter(
        and_(Notification.user_id == current_user.id, Notification.is_read == False)
    )

    if notification_types:
        query = query.filter(Notification.notification_type.in_(notification_types))

    updated_count = query.update({"is_read": True, "read_at": datetime.utcnow()})

    db.commit()

    return RouterResponse.success(
        data={"updated_count": updated_count},
        message=f"{updated_count} notifications marked as read",
    )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Delete a notification"""
    notification = (
        db.query(Notification)
        .filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    db.delete(notification)
    db.commit()


@router.get("/preferences", response_model=Dict[str, Any])
@handle_service_errors
async def get_notification_preferences(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get user's notification preferences"""
    notification_service = NotificationService(db)
    preferences = notification_service.get_user_preferences(current_user.id)

    return RouterResponse.success(data={"preferences": preferences})


@router.put("/preferences", response_model=Dict[str, Any])
@handle_service_errors
async def update_notification_preferences(
    preferences_data: Dict[str, bool] = Body(
        ...,
        example={
            "bill_reminders_email": True,
            "bill_reminders_push": True,
            "task_reminders_email": False,
            "task_reminders_push": True,
            "event_reminders_email": True,
            "event_reminders_push": True,
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update user's notification preferences"""
    notification_service = NotificationService(db)
    success = notification_service.update_user_preferences(
        user_id=current_user.id, preferences=preferences_data
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update preferences",
        )

    return RouterResponse.updated(
        data={"updated_preferences": preferences_data},
        message="Notification preferences updated successfully",
    )


@router.get("/unread-count", response_model=Dict[str, Any])
@handle_service_errors
async def get_unread_count(
    by_type: bool = Query(False, description="Group count by notification type"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get count of unread notifications"""
    if by_type:
        # Get counts grouped by type
        from sqlalchemy import func

        type_counts = (
            db.query(
                Notification.notification_type,
                func.count(Notification.id).label("count"),
            )
            .filter(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.is_read == False,
                )
            )
            .group_by(Notification.notification_type)
            .all()
        )

        counts_by_type = {type_name: count for type_name, count in type_counts}
        total_count = sum(counts_by_type.values())

        return RouterResponse.success(
            data={"total_unread_count": total_count, "counts_by_type": counts_by_type}
        )
    else:
        # Simple total count
        count = (
            db.query(Notification)
            .filter(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.is_read == False,
                )
            )
            .count()
        )

        return RouterResponse.success(data={"unread_count": count})


@router.get("/summary", response_model=Dict[str, Any])
@handle_service_errors
async def get_notification_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get notification summary with counts and recent notifications"""
    notification_service = NotificationService(db)
    summary = notification_service.get_notification_summary(current_user.id)

    return RouterResponse.success(data={"notification_summary": summary})


# SYSTEM ENDPOINTS FOR BACKGROUND TASKS
@router.post("/system/trigger/bill-reminders", response_model=Dict[str, Any])
@handle_service_errors
async def trigger_bill_reminders_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Manually trigger bill reminders (system use)"""
    background_tasks.add_task(trigger_bill_reminders)

    return RouterResponse.success(message="Bill reminders triggered")


@router.post("/system/trigger/task-reminders", response_model=Dict[str, Any])
@handle_service_errors
async def trigger_task_reminders_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Manually trigger task reminders (system use)"""
    background_tasks.add_task(trigger_task_reminders)

    return RouterResponse.success(message="Task reminders triggered")


@router.post("/system/trigger/event-reminders", response_model=Dict[str, Any])
@handle_service_errors
async def trigger_event_reminders_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Manually trigger event reminders (system use)"""
    background_tasks.add_task(trigger_event_reminders)

    return RouterResponse.success(message="Event reminders triggered")


@router.post("/system/trigger/all-reminders", response_model=Dict[str, Any])
@handle_service_errors
async def trigger_all_reminders_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Manually trigger all notification checks (system use)"""
    background_tasks.add_task(scheduler.run_immediate_check)

    return RouterResponse.success(message="All notification checks triggered")


@router.get("/system/scheduler-status", response_model=Dict[str, Any])
async def get_scheduler_status():
    """Get background task scheduler status"""
    try:
        import schedule

        scheduled_jobs_count = len(schedule.jobs)
    except ImportError:
        scheduled_jobs_count = 0

    status_info = {
        "running": scheduler.running,
        "scheduled_tasks": scheduled_jobs_count,
        "last_check_status": "Background scheduler monitoring not fully implemented",
    }

    return RouterResponse.success(data={"scheduler_status": status_info})


@router.get("/config/types", response_model=Dict[str, Any])
async def get_notification_types():
    """Get available notification types"""
    from ..utils.constants import NotificationType

    types = [
        {"value": ntype.value, "label": ntype.value.replace("_", " ").title()}
        for ntype in NotificationType
    ]

    return RouterResponse.success(data={"notification_types": types})


@router.get("/config/priorities", response_model=Dict[str, Any])
async def get_priority_levels():
    """Get available priority levels"""
    from ..utils.constants import Priority

    priorities = [
        {"value": priority.value, "label": priority.value.title()}
        for priority in Priority
    ]

    return RouterResponse.success(data={"priorities": priorities})
```

## app/schemas/announcement.py

```python
from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class AnnouncementCategory(str, Enum):
    GENERAL = "general"
    MAINTENANCE = "maintenance"
    EVENT = "event"
    RULE = "rule"
    URGENT = "urgent"
    FINANCIAL = "financial"

class AnnouncementPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    category: AnnouncementCategory
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    is_pinned: bool = False
    expires_at: Optional[datetime] = None

class AnnouncementCreate(AnnouncementBase):
    @validator('expires_at')
    def expires_in_future(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Expiration date must be in the future')
        return v

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[AnnouncementCategory] = None
    priority: Optional[AnnouncementPriority] = None
    is_pinned: Optional[bool] = None
    expires_at: Optional[datetime] = None

class AnnouncementResponse(AnnouncementBase):
    id: int
    household_id: int
    created_by: int
    author_name: str
    is_expired: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AnnouncementSummary(BaseModel):
    id: int
    title: str
    category: AnnouncementCategory
    priority: AnnouncementPriority
    is_pinned: bool
    created_at: datetime
    author_name: str
```

## app/schemas/poll.py

```python
from pydantic import BaseModel, validator, Field
from typing import Any, Optional, List, Dict
from datetime import datetime


class PollBase(BaseModel):
    question: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    options: List[str] = Field(..., min_items=2, max_items=10)
    is_multiple_choice: bool = False
    is_anonymous: bool = False
    closes_at: Optional[datetime] = None


class PollCreate(PollBase):
    @validator("options")
    def validate_options(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("Poll options must be unique")
        for option in v:
            if not option.strip():
                raise ValueError("Poll options cannot be empty")
        return [option.strip() for option in v]

    @validator("closes_at")
    def closes_in_future(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError("Close date must be in the future")
        return v


class PollUpdate(BaseModel):
    question: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    closes_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class PollVoteCreate(BaseModel):
    selected_options: List[int] = Field(..., min_items=1)

    @validator("selected_options")
    def validate_selections(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("Cannot select the same option multiple times")
        return v


class PollResponse(PollBase):
    id: int
    household_id: int
    created_by: int
    creator_name: str
    is_active: bool
    total_votes: int
    user_has_voted: bool
    user_votes: Optional[List[int]]
    created_at: datetime

    class Config:
        from_attributes = True


class PollResults(BaseModel):
    poll_id: int
    question: str
    total_votes: int
    is_closed: bool
    results: List[
        Dict[str, Any]
    ]  # [{"option": "text", "votes": 5, "percentage": 50.0}]


class PollSummary(BaseModel):
    id: int
    question: str
    total_votes: int
    is_active: bool
    closes_at: Optional[datetime]
    created_at: datetime
```

## app/schemas/notification.py

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    BILL_DUE = "bill_due"
    TASK_OVERDUE = "task_overdue"
    TASK_ASSIGNED = "task_assigned"
    EVENT_REMINDER = "event_reminder"
    GUEST_REQUEST = "guest_request"
    EXPENSE_ADDED = "expense_added"
    PAYMENT_RECEIVED = "payment_received"
    ANNOUNCEMENT = "announcement"
    POLL_CREATED = "poll_created"
    SYSTEM = "system"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=500)
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    action_url: Optional[str] = None


class NotificationCreate(NotificationBase):
    user_id: int
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    household_id: int
    is_read: bool
    sent_in_app: bool
    sent_email: bool
    sent_push: bool
    related_entity_type: Optional[str]
    related_entity_id: Optional[int]
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationPreferences(BaseModel):
    bill_reminders_email: bool = True
    bill_reminders_push: bool = True
    task_reminders_email: bool = True
    task_reminders_push: bool = True
    event_reminders_email: bool = True
    event_reminders_push: bool = True
    announcements_email: bool = True
    announcements_push: bool = False
    guest_requests_email: bool = True
    guest_requests_push: bool = True
    expense_updates_email: bool = False
    expense_updates_push: bool = True


class NotificationPreferencesUpdate(BaseModel):
    bill_reminders_email: Optional[bool] = None
    bill_reminders_push: Optional[bool] = None
    task_reminders_email: Optional[bool] = None
    task_reminders_push: Optional[bool] = None
    event_reminders_email: Optional[bool] = None
    event_reminders_push: Optional[bool] = None
    announcements_email: Optional[bool] = None
    announcements_push: Optional[bool] = None
    guest_requests_email: Optional[bool] = None
    guest_requests_push: Optional[bool] = None
    expense_updates_email: Optional[bool] = None
    expense_updates_push: Optional[bool] = None


class NotificationSummary(BaseModel):
    unread_count: int
    high_priority_count: int
    recent_notifications: List[NotificationResponse]
```

## app/models/announcement.py

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)  # general, maintenance, event, rule
    priority = Column(String, default="normal")  # low, normal, high, urgent
    is_pinned = Column(Boolean, default=False)
    expires_at = Column(DateTime)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="announcements")
    author = relationship("User", back_populates="announcements", foreign_keys=[created_by])
```

## app/models/poll.py

```python
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Poll(Base):
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    description = Column(Text)
    options = Column(JSON, nullable=False)  # List of option strings
    is_multiple_choice = Column(Boolean, default=False)
    is_anonymous = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    closes_at = Column(DateTime)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="polls")
    creator = relationship(
        "User", back_populates="created_polls", foreign_keys=[created_by]
    )
    votes = relationship(
        "PollVote", back_populates="poll", cascade="all, delete-orphan"
    )


class PollVote(Base):
    __tablename__ = "poll_votes"

    id = Column(Integer, primary_key=True, index=True)
    selected_options = Column(JSON, nullable=False)  # List of selected option indices

    # Foreign Keys
    poll_id = Column(Integer, ForeignKey("polls.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    poll = relationship("Poll", back_populates="votes")
    user = relationship("User", back_populates="poll_votes", foreign_keys=[user_id])
```

## app/models/notification.py

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)  # bill_due, task_overdue, event_reminder, etc.
    priority = Column(String, default="normal")  # low, normal, high, urgent
    is_read = Column(Boolean, default=False)

    # Delivery methods
    sent_in_app = Column(Boolean, default=True)
    sent_email = Column(Boolean, default=False)
    sent_push = Column(Boolean, default=False)

    # Additional data
    related_entity_type = Column(String)  # bill, task, event, etc.
    related_entity_id = Column(Integer)
    action_url = Column(String)  # Deep link for action

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    household = relationship("Household", back_populates="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String, nullable=False)
    in_app_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="notification_preferences", foreign_keys=[user_id])
```
