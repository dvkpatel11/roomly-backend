from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..services.dashboard_service import DashboardService
from ..services.expense_service import ExpenseService
from ..services.task_service import TaskService
from ..services.billing_service import BillingService
from ..services.event_service import EventService
from ..services.communication_service import CommunicationService
from ..services.household_service import HouseholdService
from ..schemas.dashboard import DashboardData, DashboardQuickStats
from .auth import get_current_user
from ..models.user import User

router = APIRouter()

@router.get("/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive dashboard summary"""
    if not current_user.household_id:
        raise HTTPException(status_code=400, detail="User not in a household")
    
    try:
        dashboard_service = DashboardService(db)
        summary = dashboard_service.get_household_summary(current_user.household_id)
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load dashboard data")

@router.get("/quick-stats")
async def get_quick_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quick dashboard statistics"""
    if not current_user.household_id:
        raise HTTPException(status_code=400, detail="User not in a household")
    
    # Aggregate data from multiple services
    expense_service = ExpenseService(db)
    task_service = TaskService(db)
    billing_service = BillingService(db)
    event_service = EventService(db)
    
    # Get user expense summary
    expense_summary = expense_service.get_user_expense_summary(
        user_id=current_user.id,
        household_id=current_user.household_id
    )
    
    # Get task score
    task_score = task_service.get_user_task_score(current_user.id)
    
    # Get upcoming bills
    upcoming_bills = billing_service.get_upcoming_bills(current_user.household_id, 7)
    
    # Get upcoming events
    upcoming_events = event_service.get_household_events(
        household_id=current_user.household_id,
        include_pending=False,
        days_ahead=7
    )
    
    return {
        "total_owed": expense_summary.get("total_owed", 0),
        "overdue_tasks": task_score.get("overdue_tasks", 0),
        "upcoming_events": len(upcoming_events),
        "upcoming_bills": len(upcoming_bills),
        "task_score": task_score.get("total_points", 0)
    }

@router.get("/financial-overview")
async def get_financial_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed financial overview"""
    expense_service = ExpenseService(db)
    billing_service = BillingService(db)
    
    # User expense summary
    expense_summary = expense_service.get_user_expense_summary(
        user_id=current_user.id,
        household_id=current_user.household_id
    )
    
    # Billing summary
    billing_summary = billing_service.get_household_billing_summary(
        household_id=current_user.household_id
    )
    
    return {
        "personal": expense_summary,
        "household_bills": billing_summary,
        "net_balance": expense_summary.get("net_balance", 0)
    }

@router.get("/task-summary")
async def get_task_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task completion summary"""
    task_service = TaskService(db)
    
    # User task score
    user_score = task_service.get_user_task_score(current_user.id)
    
    # Household leaderboard
    leaderboard = task_service.get_household_leaderboard(current_user.household_id)
    
    return {
        "user_score": user_score,
        "leaderboard": leaderboard[:5],  # Top 5
        "user_rank": next(
            (i + 1 for i, entry in enumerate(leaderboard) 
             if entry["user_id"] == current_user.id), 
            len(leaderboard) + 1
        )
    }

@router.get("/activity-feed")
async def get_activity_feed(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent activity feed"""
    # This would aggregate recent activities from all services
    activities = []
    
    # Add recent expenses, task completions, events, etc.
    # This would be implemented in DashboardService
    
    return {"activities": activities}

@router.get("/household-health")
async def get_household_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household health score and metrics"""
    household_service = HouseholdService(db)
    
    health_score = household_service.calculate_household_health_score(
        household_id=current_user.household_id
    )
    
    return health_score

@router.get("/pending-approvals")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending approval items"""
    from ..services.approval_service import ApprovalService
    
    approval_service = ApprovalService(db)
    
    # Get pending guests
    pending_guests = approval_service.get_pending_guest_approvals(
        household_id=current_user.household_id
    )
    
    # Get pending events
    event_service = EventService(db)
    pending_events = event_service.get_pending_events_for_approval(
        household_id=current_user.household_id
    )
    
    return {
        "pending_guests": pending_guests,
        "pending_events": pending_events,
        "total_pending": len(pending_guests) + len(pending_events)
    }

@router.get("/communication-summary")
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

@router.get("/insights")
async def get_household_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get actionable insights for household improvement"""
    
    # This would analyze patterns and provide suggestions
    insights = []
    
    # Analyze financial patterns
    expense_service = ExpenseService(db)
    expense_summary = expense_service.get_user_expense_summary(
        user_id=current_user.id,
        household_id=current_user.household_id
    )
    
    if expense_summary.get("total_owed", 0) > 100:
        insights.append({
            "type": "financial",
            "priority": "high",
            "message": "You have outstanding payments over $100",
            "action": "Consider settling expenses to improve household harmony"
        })
    
    # Analyze task patterns
    task_service = TaskService(db)
    task_score = task_service.get_user_task_score(current_user.id)
    
    if task_score.get("completion_rate", 0) < 70:
        insights.append({
            "type": "tasks",
            "priority": "medium",
            "message": "Your task completion rate is below 70%",
            "action": "Try to complete tasks on time to boost your score"
        })
    
    return {"insights": insights}
