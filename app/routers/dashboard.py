from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from ..database import get_db
from ..services.dashboard_service import DashboardService
from ..services.household_service import HouseholdService
from ..services.task_service import TaskService
from ..services.expense_service import ExpenseService
from ..services.notification_service import NotificationService
from ..dependencies.permissions import require_household_member
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
)
from ..models.user import User

router = APIRouter(tags=["dashboard"])


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive dashboard overview with all sections"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    return RouterResponse.success(
        data={"dashboard": dashboard_data},
        metadata={
            "user_id": current_user.id,
            "household_id": household_id,
            "generated_at": dashboard_data["generated_at"],
            "dashboard_version": "2.0",
        },
    )


@router.get("/mobile", response_model=Dict[str, Any])
@handle_service_errors
async def get_mobile_dashboard(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get simplified dashboard optimized for mobile devices"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    mobile_data = dashboard_service.get_mobile_dashboard(
        user_id=current_user.id, household_id=household_id
    )

    return RouterResponse.success(
        data={"mobile_dashboard": mobile_data},
        metadata={
            "optimized_for": "mobile",
            "user_id": current_user.id,
            "household_id": household_id,
        },
    )


@router.get("/quick-stats", response_model=Dict[str, Any])
@handle_service_errors
async def get_quick_stats(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get quick stats for header/widget display"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    # Get just the quick stats section
    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    quick_stats = dashboard_data.get("quick_stats", {})
    header = dashboard_data.get("header", {})

    return RouterResponse.success(
        data={
            "quick_stats": quick_stats,
            "user_info": {
                "name": header.get("greeting", "")
                .replace("Good morning, ", "")
                .replace("Good afternoon, ", "")
                .replace("Good evening, ", "")
                .replace("!", ""),
                "current_streak": header.get("current_streak", 0),
                "role": header.get("user_role", "member"),
            },
        }
    )


@router.get("/urgent-items", response_model=Dict[str, Any])
@handle_service_errors
async def get_urgent_items(
    limit: int = Query(5, ge=1, le=10, description="Maximum number of urgent items"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get urgent items requiring immediate attention"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    # Get urgent items from dashboard
    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    urgent_items = dashboard_data.get("urgent_items", [])[:limit]

    # Count by priority
    priority_counts = {
        "urgent": len(
            [item for item in urgent_items if item.get("priority") == "urgent"]
        ),
        "high": len([item for item in urgent_items if item.get("priority") == "high"]),
        "medium": len(
            [item for item in urgent_items if item.get("priority") == "medium"]
        ),
    }

    return RouterResponse.success(
        data={
            "urgent_items": urgent_items,
            "total_count": len(urgent_items),
            "priority_breakdown": priority_counts,
            "requires_immediate_attention": priority_counts["urgent"] > 0,
        }
    )


@router.get("/financial-snapshot", response_model=Dict[str, Any])
@handle_service_errors
async def get_financial_snapshot(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get financial overview and recent transactions"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    financial_snapshot = dashboard_data.get("financial_snapshot", {})

    return RouterResponse.success(
        data={
            "financial_snapshot": financial_snapshot,
            "summary": {
                "net_balance": financial_snapshot.get("net_balance", {}).get(
                    "amount", 0
                ),
                "balance_status": financial_snapshot.get("net_balance", {}).get(
                    "status", "neutral"
                ),
                "monthly_bills_total": financial_snapshot.get("monthly_bills", {}).get(
                    "total", 0
                ),
                "overdue_amount": financial_snapshot.get("overdue_amount", 0),
            },
        }
    )


@router.get("/task-progress", response_model=Dict[str, Any])
@handle_service_errors
async def get_task_progress(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get task progress and leaderboard information"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    task_progress = dashboard_data.get("task_progress", {})
    personal_stats = task_progress.get("personal_stats", {})

    return RouterResponse.success(
        data={
            "task_progress": task_progress,
            "performance_summary": {
                "completion_rate": personal_stats.get("completion_rate", 0),
                "current_streak": personal_stats.get("current_streak", 0),
                "rank": task_progress.get("leaderboard_position", {}).get("rank"),
                "total_members": task_progress.get("leaderboard_position", {}).get(
                    "total_members"
                ),
            },
        }
    )


@router.get("/upcoming-events", response_model=Dict[str, Any])
@handle_service_errors
async def get_upcoming_events(
    days_ahead: int = Query(14, ge=1, le=30, description="Days to look ahead"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of events"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get upcoming events for dashboard display"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    upcoming_events = dashboard_data.get("upcoming_events", [])[:limit]

    # Categorize events by timing
    today_events = [e for e in upcoming_events if e.get("time_until") == "Today"]
    tomorrow_events = [e for e in upcoming_events if e.get("time_until") == "Tomorrow"]
    this_week_events = [
        e
        for e in upcoming_events
        if "day" in e.get("time_until", "")
        and int(e.get("time_until", "0").split()[1]) <= 7
    ]

    return RouterResponse.success(
        data={
            "upcoming_events": upcoming_events,
            "total_count": len(upcoming_events),
            "timing_breakdown": {
                "today": len(today_events),
                "tomorrow": len(tomorrow_events),
                "this_week": len(this_week_events),
            },
            "next_event": upcoming_events[0] if upcoming_events else None,
        }
    )


@router.get("/recent-activity", response_model=Dict[str, Any])
@handle_service_errors
async def get_recent_activity(
    limit: int = Query(8, ge=1, le=20, description="Maximum number of activities"),
    activity_types: Optional[str] = Query(
        None, description="Filter by activity types (comma-separated)"
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get recent household activity feed"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    recent_activity = dashboard_data.get("recent_activity", [])

    # Filter by activity types if specified
    if activity_types:
        type_list = [t.strip() for t in activity_types.split(",")]
        recent_activity = [
            activity
            for activity in recent_activity
            if activity.get("type") in type_list
        ]

    recent_activity = recent_activity[:limit]

    # Count by type
    activity_counts = {}
    for activity in recent_activity:
        activity_type = activity.get("type", "unknown")
        activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1

    return RouterResponse.success(
        data={
            "recent_activity": recent_activity,
            "total_count": len(recent_activity),
            "activity_counts": activity_counts,
            "last_activity_time": (
                recent_activity[0].get("timestamp") if recent_activity else None
            ),
        }
    )


@router.get("/quick-actions", response_model=Dict[str, Any])
@handle_service_errors
async def get_quick_actions(
    include_urgent_only: bool = Query(False, description="Show only urgent actions"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get contextual quick actions for current user"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    quick_actions = dashboard_data.get("quick_actions", [])

    if include_urgent_only:
        quick_actions = [
            action for action in quick_actions if action.get("priority") == "urgent"
        ]

    # Group actions by priority
    priority_groups = {
        "urgent": [a for a in quick_actions if a.get("priority") == "urgent"],
        "high": [a for a in quick_actions if a.get("priority") == "high"],
        "medium": [a for a in quick_actions if a.get("priority") == "medium"],
        "low": [a for a in quick_actions if a.get("priority") == "low"],
    }

    return RouterResponse.success(
        data={
            "quick_actions": quick_actions,
            "priority_groups": priority_groups,
            "total_actions": len(quick_actions),
            "urgent_count": len(priority_groups["urgent"]),
            "has_urgent_actions": len(priority_groups["urgent"]) > 0,
        }
    )


@router.get("/household-pulse", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_pulse(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household health and activity metrics"""
    current_user, household_id = user_household
    dashboard_service = DashboardService(db)

    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    household_pulse = dashboard_data.get("household_pulse", {})
    overall_health = household_pulse.get("overall_health", {})

    # Determine health status message
    score = overall_health.get("score", 0)
    if score >= 90:
        status_message = "🏆 Excellent! Your household is thriving"
    elif score >= 75:
        status_message = "✅ Good! Things are running smoothly"
    elif score >= 60:
        status_message = "⚠️ Fair - Some areas need attention"
    else:
        status_message = "🚨 Needs attention - Time for improvement"

    return RouterResponse.success(
        data={
            "household_pulse": household_pulse,
            "health_summary": {
                "overall_score": score,
                "status": overall_health.get("status", "unknown"),
                "status_message": status_message,
                "trend": overall_health.get("trend", "stable"),
            },
            "weekly_activity": household_pulse.get("weekly_activity", {}),
            "top_improvements": household_pulse.get("improvement_tips", []),
        }
    )


@router.get("/notifications-summary", response_model=Dict[str, Any])
@handle_service_errors
async def get_notifications_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get notification summary for dashboard"""
    current_user, household_id = user_household
    notification_service = NotificationService(db)

    summary = notification_service.get_notification_summary(current_user.id)

    return RouterResponse.success(
        data={
            "notifications_summary": summary,
            "alert_level": (
                "high"
                if summary.get("high_priority_count", 0) > 0
                else "medium" if summary.get("unread_count", 0) > 5 else "low"
            ),
        }
    )


@router.post("/refresh", response_model=Dict[str, Any])
@handle_service_errors
async def refresh_dashboard_data(
    background_tasks: BackgroundTasks,
    sections: Optional[str] = Query(
        None, description="Specific sections to refresh (comma-separated)"
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Manually refresh dashboard data"""
    current_user, household_id = user_household

    # Add background task to refresh data if needed
    # For now, just return fresh data
    dashboard_service = DashboardService(db)

    if sections:
        # Refresh specific sections only
        section_list = [s.strip() for s in sections.split(",")]
        # This would be implemented based on specific section refresh needs
        refreshed_sections = section_list
    else:
        # Refresh all data
        refreshed_sections = ["all"]

    # Get fresh dashboard data
    dashboard_data = dashboard_service.get_dashboard_overview(
        user_id=current_user.id, household_id=household_id
    )

    return RouterResponse.success(
        data={
            "dashboard": dashboard_data,
            "refreshed_sections": refreshed_sections,
            "refresh_timestamp": datetime.utcnow(),
        },
        message="Dashboard data refreshed successfully",
    )


@router.get("/config/widgets", response_model=Dict[str, Any])
async def get_available_widgets():
    """Get available dashboard widgets configuration"""
    widgets = [
        {
            "id": "quick_stats",
            "name": "Quick Stats",
            "description": "Key metrics at a glance",
            "category": "overview",
            "default_size": "small",
            "configurable": True,
        },
        {
            "id": "urgent_items",
            "name": "Urgent Items",
            "description": "Items requiring immediate attention",
            "category": "alerts",
            "default_size": "medium",
            "configurable": True,
        },
        {
            "id": "financial_snapshot",
            "name": "Financial Overview",
            "description": "Money owed and financial status",
            "category": "financial",
            "default_size": "medium",
            "configurable": True,
        },
        {
            "id": "task_progress",
            "name": "Task Progress",
            "description": "Completion rates and leaderboard",
            "category": "tasks",
            "default_size": "large",
            "configurable": True,
        },
        {
            "id": "upcoming_events",
            "name": "Upcoming Events",
            "description": "Events in the next few weeks",
            "category": "events",
            "default_size": "medium",
            "configurable": True,
        },
        {
            "id": "household_pulse",
            "name": "Household Health",
            "description": "Overall household health score",
            "category": "analytics",
            "default_size": "large",
            "configurable": False,
        },
    ]

    return RouterResponse.success(
        data={
            "available_widgets": widgets,
            "categories": list(set(w["category"] for w in widgets)),
            "total_widgets": len(widgets),
        }
    )


@router.get("/config/layouts", response_model=Dict[str, Any])
async def get_dashboard_layouts():
    """Get available dashboard layout options"""
    layouts = [
        {
            "id": "default",
            "name": "Default Layout",
            "description": "Balanced view with all sections",
            "sections": [
                "header",
                "quick_stats",
                "urgent_items",
                "financial_snapshot",
                "task_progress",
            ],
            "is_default": True,
        },
        {
            "id": "financial_focused",
            "name": "Financial Focus",
            "description": "Emphasizes financial tracking",
            "sections": ["header", "quick_stats", "financial_snapshot", "urgent_items"],
            "is_default": False,
        },
        {
            "id": "task_focused",
            "name": "Task Management",
            "description": "Emphasizes task completion and progress",
            "sections": ["header", "task_progress", "quick_stats", "upcoming_events"],
            "is_default": False,
        },
        {
            "id": "minimal",
            "name": "Minimal View",
            "description": "Essential information only",
            "sections": ["header", "quick_stats", "urgent_items"],
            "is_default": False,
        },
    ]

    return RouterResponse.success(
        data={
            "available_layouts": layouts,
            "default_layout": next(l for l in layouts if l["is_default"]),
            "total_layouts": len(layouts),
        }
    )


@router.get("/health-check", response_model=Dict[str, Any])
@handle_service_errors
async def dashboard_health_check(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Health check for dashboard services and data availability"""
    current_user, household_id = user_household

    health_status = {
        "dashboard_service": "healthy",
        "data_sources": {},
        "last_updated": datetime.utcnow(),
    }

    try:
        # Test household service
        household_service = HouseholdService(db)
        household_info = household_service.get_user_household_info(current_user.id)
        health_status["data_sources"]["household"] = (
            "healthy" if household_info else "warning"
        )

        # Test task service
        task_service = TaskService(db)
        task_summary = task_service.get_user_task_summary(current_user.id, household_id)
        health_status["data_sources"]["tasks"] = (
            "healthy" if task_summary else "warning"
        )

        # Test expense service
        expense_service = ExpenseService(db)
        expense_summary = expense_service.get_user_expense_summary(
            current_user.id, household_id
        )
        health_status["data_sources"]["expenses"] = (
            "healthy" if expense_summary else "warning"
        )

        # Overall status
        all_healthy = all(
            status == "healthy" for status in health_status["data_sources"].values()
        )
        health_status["overall_status"] = "healthy" if all_healthy else "degraded"

    except Exception as e:
        health_status["overall_status"] = "unhealthy"
        health_status["error"] = str(e)

    return RouterResponse.success(
        data={"health_check": health_status},
        metadata={"check_timestamp": datetime.utcnow()},
    )
