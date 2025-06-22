from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..models.task import Task
from ..models.expense import Expense
from ..models.guest import Guest
from ..models.announcement import Announcement
from ..models.user import User
from ..models.household_membership import HouseholdMembership
from ..models.enums import TaskStatus
from .household_service import HouseholdService
from .expense_service import ExpenseService
from .billing_service import BillingService
from .task_service import TaskService
from .event_service import EventService
from .notification_service import NotificationService
from .communication_service import CommunicationService
from .shopping_service import ShoppingService


class DashboardService:
    """Modern dashboard with clean, actionable insights"""

    def __init__(self, db: Session):
        self.db = db
        # Initialize service dependencies
        self.household_service = HouseholdService(db)
        self.expense_service = ExpenseService(db)
        self.billing_service = BillingService(db)
        self.task_service = TaskService(db)
        self.event_service = EventService(db)
        self.notification_service = NotificationService(db)
        self.communication_service = CommunicationService(db)
        self.shopping_service = ShoppingService(db)

    def get_dashboard_overview(self, user_id: int, household_id: int) -> Dict[str, Any]:
        """Get comprehensive dashboard overview with modern design"""

        # Verify user permissions
        if not self.household_service.check_member_permissions(user_id, household_id):
            raise PermissionError("User cannot access this household dashboard")

        return {
            "header": self._get_dashboard_header(user_id, household_id),
            "quick_stats": self._get_quick_stats(user_id, household_id),
            "urgent_items": self._get_urgent_items(user_id, household_id),
            "financial_snapshot": self._get_financial_snapshot(user_id, household_id),
            "task_progress": self._get_task_progress(user_id, household_id),
            "upcoming_events": self._get_upcoming_events(household_id),
            "recent_activity": self._get_recent_activity(household_id),
            "quick_actions": self._get_quick_actions(user_id, household_id),
            "household_pulse": self._get_household_pulse(household_id),
            "generated_at": datetime.utcnow(),
        }

    def _get_dashboard_header(self, user_id: int, household_id: int) -> Dict[str, Any]:
        """Get personalized dashboard header"""

        user = self.db.query(User).filter(User.id == user_id).first()
        household_info = self.household_service.get_user_household_info(user_id)

        # Get user's current streak
        task_summary = self.task_service.get_user_task_summary(user_id, household_id)

        # Time-based greeting
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        return {
            "greeting": f"{greeting}, {user.name}!",
            "household_name": (
                household_info["household_name"] if household_info else "Unknown"
            ),
            "user_role": household_info["user_role"] if household_info else "member",
            "current_streak": task_summary["current_streak"],
            "is_admin": household_info["is_admin"] if household_info else False,
        }

    def _get_quick_stats(self, user_id: int, household_id: int) -> Dict[str, Any]:
        """Get key metrics at a glance"""

        now = datetime.utcnow()

        # Financial quick stats
        expense_summary = self.expense_service.get_user_expense_summary(
            user_id, household_id
        )

        # Task quick stats
        task_summary = self.task_service.get_user_task_summary(user_id, household_id)

        # Notification quick stats
        notification_summary = self.notification_service.get_notification_summary(
            user_id
        )

        # Upcoming bills count
        upcoming_bills = self.billing_service.get_upcoming_bills(household_id, 7)

        return {
            "money_owed": {
                "amount": expense_summary["total_owed"],
                "trend": "down" if expense_summary["total_owed"] < 50 else "up",
                "description": "You owe",
            },
            "money_owed_to_you": {
                "amount": expense_summary["total_owed_to_user"],
                "trend": (
                    "up" if expense_summary["total_owed_to_user"] > 0 else "neutral"
                ),
                "description": "Owed to you",
            },
            "pending_tasks": {
                "count": task_summary["pending_count"]
                + task_summary["in_progress_count"],
                "trend": "down" if task_summary["overdue_count"] == 0 else "up",
                "description": "Pending tasks",
            },
            "task_score": {
                "score": int(task_summary["completion_rate"]),
                "trend": "up" if task_summary["completion_rate"] > 75 else "neutral",
                "description": "Completion rate",
            },
            "notifications": {
                "count": notification_summary["unread_count"],
                "urgent_count": notification_summary["high_priority_count"],
                "description": "Unread alerts",
            },
            "upcoming_bills": {
                "count": len(upcoming_bills),
                "description": "Bills due soon",
            },
        }

    def _get_urgent_items(
        self, user_id: int, household_id: int
    ) -> List[Dict[str, Any]]:
        """Get urgent items requiring immediate attention"""

        urgent_items = []
        now = datetime.utcnow()

        # Overdue bills
        overdue_bills = self.billing_service.get_overdue_bills(household_id)
        for bill in overdue_bills[:3]:  # Top 3 most urgent
            urgent_items.append(
                {
                    "type": "overdue_bill",
                    "title": f"Overdue: {bill['name']}",
                    "description": f"${bill['amount_remaining']:.2f} past due by {bill['days_overdue']} days",
                    "priority": "high",
                    "action_url": f"/bills/{bill['bill_id']}",
                    "icon": "💸",
                }
            )

        # Overdue tasks
        overdue_tasks = self.task_service.get_overdue_tasks_for_reminders(household_id)
        user_overdue = [t for t in overdue_tasks if t["assigned_to"] == user_id][:2]
        for task in user_overdue:
            urgent_items.append(
                {
                    "type": "overdue_task",
                    "title": f"Overdue: {task['title']}",
                    "description": f"{task['days_overdue']} days past due",
                    "priority": "medium",
                    "action_url": f"/tasks/{task['task_id']}",
                    "icon": "⏰",
                }
            )

        # Bills due today
        bills_due_today = [
            b
            for b in self.billing_service.get_upcoming_bills(household_id, 1)
            if b["days_until_due"] == 0
        ]
        for bill in bills_due_today:
            urgent_items.append(
                {
                    "type": "bill_due_today",
                    "title": f"Due Today: {bill['name']}",
                    "description": f"${bill['amount']:.2f} payment due",
                    "priority": "high",
                    "action_url": f"/bills/{bill['bill_id']}/pay",
                    "icon": "🔔",
                }
            )

        # Pending guest approvals (for admins)
        if self.household_service.check_admin_permissions(user_id, household_id):
            pending_guests = (
                self.db.query(Guest)
                .filter(
                    and_(
                        Guest.household_id == household_id,
                        Guest.is_approved == False,
                        Guest.check_in >= now,
                    )
                )
                .count()
            )

            if pending_guests > 0:
                urgent_items.append(
                    {
                        "type": "guest_approval",
                        "title": f"{pending_guests} Guest Request{'s' if pending_guests > 1 else ''}",
                        "description": "Waiting for approval",
                        "priority": "medium",
                        "action_url": "/guests/pending",
                        "icon": "👥",
                    }
                )

        # Sort by priority and limit to 5 most urgent
        priority_order = {"high": 3, "medium": 2, "low": 1}
        urgent_items.sort(
            key=lambda x: priority_order.get(x["priority"], 0), reverse=True
        )

        return urgent_items[:5]

    def _get_financial_snapshot(
        self, user_id: int, household_id: int
    ) -> Dict[str, Any]:
        """Get clean financial overview"""

        # Get user expense summary
        expense_summary = self.expense_service.get_user_expense_summary(
            user_id, household_id
        )

        # Get household billing summary
        billing_summary = self.billing_service.get_household_billing_summary(
            household_id
        )

        # Get recent payments (last 30 days)
        payment_history = self.expense_service.get_payment_history(
            user_id, household_id, 10, 0
        )
        recent_payments = payment_history["payments"][:5]

        # Calculate net balance
        net_balance = expense_summary["net_balance"]

        return {
            "net_balance": {
                "amount": net_balance,
                "status": (
                    "positive"
                    if net_balance > 0
                    else "negative" if net_balance < 0 else "neutral"
                ),
                "description": (
                    "You're owed"
                    if net_balance > 0
                    else "You owe" if net_balance < 0 else "All settled"
                ),
            },
            "monthly_bills": {
                "total": billing_summary["total_monthly_bills"],
                "count": billing_summary["active_bill_count"],
            },
            "recent_expenses": expense_summary["unpaid_expenses"][:3],
            "recent_payments": [
                {
                    "description": p["expense"]["description"],
                    "amount": p["amount_paid"],
                    "date": p["payment_date"],
                }
                for p in recent_payments
            ],
            "overdue_amount": billing_summary["total_overdue_amount"],
        }

    def _get_task_progress(self, user_id: int, household_id: int) -> Dict[str, Any]:
        """Get task progress and leaderboard"""

        # Get user task summary
        task_summary = self.task_service.get_user_task_summary(user_id, household_id)

        # Get household leaderboard (current month)
        leaderboard = self.task_service.get_household_leaderboard(household_id, user_id)

        # Find user's rank
        user_rank = next(
            (entry["rank"] for entry in leaderboard if entry["user_id"] == user_id),
            None,
        )

        # Get top performers
        top_performers = leaderboard[:3]

        return {
            "personal_stats": {
                "completion_rate": task_summary["completion_rate"],
                "current_streak": task_summary["current_streak"],
                "pending_tasks": task_summary["pending_count"],
                "overdue_tasks": task_summary["overdue_count"],
            },
            "leaderboard_position": {
                "rank": user_rank,
                "total_members": len(leaderboard),
            },
            "top_performers": [
                {
                    "name": p["user_name"],
                    "completion_rate": p["completion_rate"],
                }
                for p in top_performers
            ],
            "upcoming_tasks": task_summary["upcoming_tasks"],
        }

    def _get_upcoming_events(self, household_id: int) -> List[Dict[str, Any]]:
        """Get upcoming events in clean format"""

        events_data = self.event_service.get_household_events(
            household_id=household_id,
            user_id=1,  # We'll get the actual user_id from auth context
            include_pending=True,
            days_ahead=14,
            limit=5,
        )

        upcoming = []
        for event in events_data["events"]:
            # Calculate days until event
            days_until = (event["start_date"] - datetime.utcnow()).days

            # Format time until
            if days_until == 0:
                time_until = "Today"
            elif days_until == 1:
                time_until = "Tomorrow"
            else:
                time_until = f"In {days_until} days"

            upcoming.append(
                {
                    "id": event["id"],
                    "title": event["title"],
                    "type": event["event_type"],
                    "date": event["start_date"],
                    "time_until": time_until,
                    "status": event["status"],
                    "attendees": event["rsvp_summary"]["yes_count"],
                    "is_full": event["is_full"],
                }
            )

        return upcoming

    def _get_recent_activity(self, household_id: int) -> List[Dict[str, Any]]:
        """Get recent household activity feed"""

        activities = []
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        # Recent task completions
        recent_completions = (
            self.db.query(Task, User.name)
            .join(User, Task.assigned_to == User.id)
            .filter(
                and_(
                    Task.household_id == household_id,
                    Task.status == TaskStatus.COMPLETED.value,
                    Task.completed_at >= cutoff_date,
                )
            )
            .order_by(desc(Task.completed_at))
            .limit(5)
            .all()
        )

        for task, user_name in recent_completions:
            activities.append(
                {
                    "type": "task_completed",
                    "icon": "✅",
                    "message": f"{user_name} completed '{task.title}'",
                    "timestamp": task.completed_at,
                }
            )

        # Recent expenses
        recent_expenses = (
            self.db.query(Expense, User.name)
            .join(User, Expense.created_by == User.id)
            .filter(
                and_(
                    Expense.household_id == household_id,
                    Expense.created_at >= cutoff_date,
                )
            )
            .order_by(desc(Expense.created_at))
            .limit(3)
            .all()
        )

        for expense, user_name in recent_expenses:
            activities.append(
                {
                    "type": "expense_added",
                    "icon": "💰",
                    "message": f"{user_name} added expense: {expense.description}",
                    "timestamp": expense.created_at,
                    "metadata": {"amount": expense.amount},
                }
            )

        # Recent announcements
        recent_announcements = (
            self.db.query(Announcement, User.name)
            .join(User, Announcement.created_by == User.id)
            .filter(
                and_(
                    Announcement.household_id == household_id,
                    Announcement.created_at >= cutoff_date,
                )
            )
            .order_by(desc(Announcement.created_at))
            .limit(3)
            .all()
        )

        for announcement, user_name in recent_announcements:
            activities.append(
                {
                    "type": "announcement",
                    "icon": "📢",
                    "message": f"{user_name} posted: {announcement.title}",
                    "timestamp": announcement.created_at,
                    "metadata": {"category": announcement.category},
                }
            )

        # Sort all activities by timestamp
        activities.sort(key=lambda x: x["timestamp"], reverse=True)

        return activities[:8]  # Return 8 most recent

    def _get_quick_actions(
        self, user_id: int, household_id: int
    ) -> List[Dict[str, Any]]:
        """Get contextual quick actions"""

        actions = []

        # Always available actions
        actions.extend(
            [
                {
                    "id": "add_expense",
                    "title": "Add Expense",
                    "description": "Log a shared expense",
                    "icon": "💳",
                    "url": "/expenses/create",
                    "priority": "high",
                },
                {
                    "id": "mark_task_complete",
                    "title": "Complete Task",
                    "description": "Mark a task as done",
                    "icon": "✅",
                    "url": "/tasks/my-tasks",
                    "priority": "medium",
                },
            ]
        )

        # Conditional actions based on user role and household state
        if self.household_service.check_admin_permissions(user_id, household_id):
            actions.extend(
                [
                    {
                        "id": "create_announcement",
                        "title": "Make Announcement",
                        "description": "Share news with household",
                        "icon": "📢",
                        "url": "/announcements/create",
                        "priority": "medium",
                    },
                    {
                        "id": "assign_task",
                        "title": "Assign Task",
                        "description": "Create new household task",
                        "icon": "📋",
                        "url": "/tasks/create",
                        "priority": "medium",
                    },
                ]
            )

        # Check if user has overdue items
        task_summary = self.task_service.get_user_task_summary(user_id, household_id)
        if task_summary["overdue_count"] > 0:
            actions.insert(
                0,
                {
                    "id": "handle_overdue",
                    "title": "Handle Overdue Tasks",
                    "description": f"{task_summary['overdue_count']} tasks need attention",
                    "icon": "⚠️",
                    "url": "/tasks/overdue",
                    "priority": "urgent",
                },
            )

        # Check for unpaid expenses
        expense_summary = self.expense_service.get_user_expense_summary(
            user_id, household_id
        )
        if expense_summary["total_owed"] > 0:
            actions.append(
                {
                    "id": "pay_expenses",
                    "title": "Pay Outstanding",
                    "description": f"${expense_summary['total_owed']:.2f} to pay",
                    "icon": "💸",
                    "url": "/expenses/unpaid",
                    "priority": "high",
                }
            )

        # Sort by priority
        priority_order = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        actions.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)

        return actions[:6]

    def _get_household_pulse(self, household_id: int) -> Dict[str, Any]:
        """Get household health and activity pulse"""

        # Get health score from household service
        health_data = self.household_service.calculate_household_health_score(
            household_id
        )

        # Get recent activity metrics
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        # Activity counts
        recent_tasks_completed = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.household_id == household_id,
                    Task.status == TaskStatus.COMPLETED.value,
                    Task.completed_at >= week_ago,
                )
            )
            .count()
        )

        recent_expenses = (
            self.db.query(Expense)
            .filter(
                and_(
                    Expense.household_id == household_id, Expense.created_at >= week_ago
                )
            )
            .count()
        )

        # Get member engagement
        active_members = (
            self.db.query(User.id)
            .join(HouseholdMembership, User.id == HouseholdMembership.user_id)
            .join(Task, User.id == Task.assigned_to)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                    Task.completed_at >= week_ago,
                )
            )
            .distinct()
            .count()
        )

        total_members = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .count()
        )

        engagement_rate = (
            (active_members / total_members * 100) if total_members > 0 else 0
        )

        return {
            "overall_health": {
                "score": health_data["overall_score"],
                "status": self._get_health_status(health_data["overall_score"]),
                "trend": "improving" if health_data["overall_score"] > 75 else "stable",
            },
            "component_scores": {
                "financial": health_data["financial_health"],
                "tasks": health_data["task_completion"],
                "communication": health_data["communication_activity"],
                "satisfaction": health_data["member_satisfaction"],
            },
            "weekly_activity": {
                "tasks_completed": recent_tasks_completed,
                "expenses_added": recent_expenses,
                "engagement_rate": round(engagement_rate, 1),
                "active_members": f"{active_members}/{total_members}",
            },
            "improvement_tips": health_data["improvement_suggestions"][
                :2
            ],  # Top 2 suggestions
        }

    def _get_health_status(self, score: int) -> str:
        """Convert health score to status"""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "fair"
        else:
            return "needs_attention"

    def get_mobile_dashboard(self, user_id: int, household_id: int) -> Dict[str, Any]:
        """Get simplified dashboard for mobile view"""

        if not self.household_service.check_member_permissions(user_id, household_id):
            raise PermissionError("User cannot access this household dashboard")

        # Get essential data only
        quick_stats = self._get_quick_stats(user_id, household_id)
        urgent_items = self._get_urgent_items(user_id, household_id)

        # Simplified financial snapshot
        expense_summary = self.expense_service.get_user_expense_summary(
            user_id, household_id
        )

        # Simplified task progress
        task_summary = self.task_service.get_user_task_summary(user_id, household_id)

        return {
            "summary": {
                "net_balance": expense_summary["net_balance"],
                "pending_tasks": task_summary["pending_count"],
                "completion_rate": task_summary["completion_rate"],
                "urgent_count": len(urgent_items),
            },
            "urgent_items": urgent_items[:3],  # Top 3 only
            "quick_actions": self._get_quick_actions(user_id, household_id)[:4],
            "next_due": self._get_next_due_items(user_id, household_id),
        }

    def _get_next_due_items(
        self, user_id: int, household_id: int
    ) -> List[Dict[str, Any]]:
        """Get next items due for mobile view"""

        items = []
        now = datetime.utcnow()
        next_week = now + timedelta(days=7)

        # Next tasks due
        next_tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.household_id == household_id,
                    Task.status != TaskStatus.COMPLETED.value,
                    Task.due_date >= now,
                    Task.due_date <= next_week,
                )
            )
            .order_by(Task.due_date)
            .limit(2)
            .all()
        )

        for task in next_tasks:
            days_until = (task.due_date - now).days
            items.append(
                {
                    "type": "task",
                    "title": task.title,
                    "due": f"Due in {days_until} day{'s' if days_until != 1 else ''}",
                    "priority": task.priority,
                }
            )

        # Next bills due
        upcoming_bills = self.billing_service.get_upcoming_bills(household_id, 7)
        for bill in upcoming_bills[:2]:
            items.append(
                {
                    "type": "bill",
                    "title": bill["name"],
                    "due": f"Due in {bill['days_until_due']} day{'s' if bill['days_until_due'] != 1 else ''}",
                    "amount": bill["amount"],
                }
            )

        return sorted(items, key=lambda x: x["due"])
