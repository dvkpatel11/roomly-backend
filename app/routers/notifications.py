from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..database import get_db
from ..services.notification_service import NotificationService
from ..schemas.notification import (
    NotificationResponse, NotificationPreferences,
    NotificationPreferencesUpdate, NotificationSummary
)
from .auth import get_current_user
from ..models.user import User
from ..utils.background_tasks import (
    trigger_bill_reminders, trigger_task_reminders, 
    trigger_event_reminders, scheduler
)

router = APIRouter()

@router.get("/")
async def get_user_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's notifications"""
    
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(
        Notification.created_at.desc()
    ).limit(limit).all()
    
    return {"notifications": notifications}

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark notification as read"""
    
    notification = db.query(Notification).filter(
        and_(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.put("/mark-all-read")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read"""
    
    updated_count = db.query(Notification).filter(
        and_(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    ).update({
        "is_read": True,
        "read_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {"message": f"{updated_count} notifications marked as read"}

@router.get("/preferences")
async def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's notification preferences"""
    
    notification_service = NotificationService(db)
    preferences = notification_service.get_user_preferences(current_user.id)
    
    return preferences

@router.put("/preferences")
async def update_notification_preferences(
    preferences_data: Dict[str, bool],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's notification preferences"""
    
    notification_service = NotificationService(db)
    success = notification_service.update_user_preferences(
        user_id=current_user.id,
        preferences=preferences_data
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update preferences")
    
    return {"message": "Notification preferences updated successfully"}

@router.get("/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of unread notifications"""
    
    count = db.query(Notification).filter(
        and_(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    ).count()
    
    return {"unread_count": count}

@router.get("/summary")
async def get_notification_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification summary with counts and recent notifications"""
    
    notification_service = NotificationService(db)
    summary = notification_service.get_notification_summary(current_user.id)
    
    return summary

# SYSTEM ENDPOINTS FOR BACKGROUND TASKS
@router.post("/system/trigger-bill-reminders")
async def trigger_bill_reminders_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger bill reminders (admin/system use)"""
    
    background_tasks.add_task(trigger_bill_reminders)
    return {"message": "Bill reminders triggered"}

@router.post("/system/trigger-task-reminders")
async def trigger_task_reminders_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger task reminders (admin/system use)"""
    
    background_tasks.add_task(trigger_task_reminders)
    return {"message": "Task reminders triggered"}

@router.post("/system/trigger-event-reminders")
async def trigger_event_reminders_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger event reminders (admin/system use)"""
    
    background_tasks.add_task(trigger_event_reminders)
    return {"message": "Event reminders triggered"}

@router.post("/system/trigger-all-reminders")
async def trigger_all_reminders_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger all notification checks (admin/system use)"""
    
    background_tasks.add_task(scheduler.run_immediate_check)
    return {"message": "All notification checks triggered"}

@router.get("/system/scheduler-status")
async def get_scheduler_status():
    """Get background task scheduler status"""
    
    return {
        "running": scheduler.running,
        "scheduled_tasks": len(schedule.jobs) if 'schedule' in globals() else 0,
        "last_check": "Real-time monitoring not implemented yet"
    }

from ..models.notification import Notification
from sqlalchemy import and_
from datetime import datetime
import schedule
