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

router = APIRouter(prefix="/notifications", tags=["notifications"])


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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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


# Import statements at the top
from .auth import get_current_user
