from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.task import Task
from ..models.event import Event
from ..models.user import User
from ..models.household_membership import HouseholdMembership


class SchedulingService:
    def __init__(self, db: Session):
        self.db = db

    def check_task_conflicts(
        self, user_id: int, due_date: datetime, exclude_task_id: int = None
    ) -> Dict[str, Any]:
        """Check for task scheduling conflicts for a user"""

        if not due_date:
            return {"has_conflict": False, "conflicts": []}

        start_of_day = due_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Find conflicting tasks (same day, same user, not completed)
        query = self.db.query(Task).filter(
            and_(
                Task.assigned_to == user_id,
                Task.due_date >= start_of_day,
                Task.due_date < end_of_day,
                Task.completed == False,
            )
        )

        if exclude_task_id:
            query = query.filter(Task.id != exclude_task_id)

        conflicting_tasks = query.all()

        conflicts = []
        for task in conflicting_tasks:
            conflicts.append(
                {
                    "type": "task",
                    "id": task.id,
                    "title": task.title,
                    "due_date": task.due_date,
                    "priority": task.priority,
                }
            )

        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
        }

    def check_event_conflicts(
        self,
        household_id: int,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        exclude_event_id: int = None,
    ) -> Dict[str, Any]:
        """Check for event scheduling conflicts"""

        if not end_date:
            end_date = start_date + timedelta(hours=2)  # Default 2-hour event

        # Find overlapping events
        query = self.db.query(Event).filter(
            and_(
                Event.household_id == household_id,
                Event.status.in_(["published", "pending_approval"]),
                or_(
                    # Event starts during our event
                    and_(Event.start_date >= start_date, Event.start_date < end_date),
                    # Event ends during our event
                    and_(Event.end_date > start_date, Event.end_date <= end_date),
                    # Event encompasses our event
                    and_(Event.start_date <= start_date, Event.end_date >= end_date),
                ),
            )
        )

        if exclude_event_id:
            query = query.filter(Event.id != exclude_event_id)

        conflicting_events = query.all()

        conflicts = []
        for event in conflicting_events:
            conflicts.append(
                {
                    "type": "event",
                    "id": event.id,
                    "title": event.title,
                    "start_date": event.start_date,
                    "end_date": event.end_date,
                    "event_type": event.event_type,
                    "status": event.status,
                }
            )

        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
        }

    def suggest_alternative_times(
        self,
        household_id: int,
        preferred_date: datetime,
        duration_hours: int = 2,
        days_to_check: int = 7,
    ) -> List[Dict[str, Any]]:
        """Suggest alternative times when no conflicts exist"""

        suggestions = []
        current_date = preferred_date.date()

        for day_offset in range(days_to_check):
            check_date = current_date + timedelta(days=day_offset)

            # Try different time slots throughout the day
            time_slots = [
                (9, 0),  # 9 AM
                (12, 0),  # 12 PM
                (15, 0),  # 3 PM
                (18, 0),  # 6 PM
                (20, 0),  # 8 PM
            ]

            for hour, minute in time_slots:
                slot_start = datetime.combine(
                    check_date, datetime.min.time().replace(hour=hour, minute=minute)
                )
                slot_end = slot_start + timedelta(hours=duration_hours)

                # Check for conflicts
                conflicts = self.check_event_conflicts(
                    household_id, slot_start, slot_end
                )

                if not conflicts["has_conflict"]:
                    suggestions.append(
                        {
                            "start_time": slot_start,
                            "end_time": slot_end,
                            "day_offset": day_offset,
                            "time_description": slot_start.strftime(
                                "%A, %B %d at %I:%M %p"
                            ),
                        }
                    )

        return suggestions[:5]  # Return top 5 suggestions

    def get_optimal_task_assignment(
        self, household_id: int, due_date: datetime, exclude_user_ids: List[int] = None
    ) -> Dict[str, Any]:
        """FIXED: Find optimal user assignment considering conflicts and workload"""

        # Get all active household members using HouseholdMembership
        query = (
            self.db.query(User)
            .join(HouseholdMembership, User.id == HouseholdMembership.user_id)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                    User.is_active == True,
                )
            )
        )

        if exclude_user_ids:
            query = query.filter(~User.id.in_(exclude_user_ids))

        members = query.all()

        if not members:
            return {"recommended_user": None, "reason": "No available users"}

        user_scores = []

        for member in members:
            score = self._calculate_assignment_score(member.id, due_date)
            user_scores.append(
                {
                    "user_id": member.id,
                    "user_name": member.name,
                    "score": score["total_score"],
                    "conflicts": score["conflicts"],
                    "current_workload": score["workload"],
                    "recent_completions": score["recent_completions"],
                }
            )

        # Sort by score (higher is better)
        user_scores.sort(key=lambda x: x["score"], reverse=True)

        return {
            "recommended_user": user_scores[0] if user_scores else None,
            "all_options": user_scores,
            "assignment_reason": self._get_assignment_reason(
                user_scores[0] if user_scores else None
            ),
        }

    def _calculate_assignment_score(
        self, user_id: int, due_date: datetime
    ) -> Dict[str, Any]:
        """Calculate assignment score for a user based on multiple factors"""

        score = 100  # Start with perfect score

        # Check for conflicts (reduce score significantly)
        conflicts = self.check_task_conflicts(user_id, due_date)
        conflict_penalty = len(conflicts["conflicts"]) * 30
        score -= conflict_penalty

        # Check current workload (tasks assigned but not completed)
        current_workload = self._get_user_current_workload(user_id)
        workload_penalty = min(current_workload * 5, 30)  # Max 30 point penalty
        score -= workload_penalty

        # Check recent completion rate (boost for good performers)
        recent_completion_rate = self._get_recent_completion_rate(user_id)
        completion_bonus = (recent_completion_rate - 0.5) * 20
        score += completion_bonus

        # Prevent negative scores
        score = max(0, score)

        return {
            "total_score": score,
            "conflicts": len(conflicts["conflicts"]),
            "workload": current_workload,
            "recent_completions": recent_completion_rate,
        }

    def _get_user_current_workload(self, user_id: int) -> int:
        """Get number of incomplete tasks assigned to user"""

        return (
            self.db.query(Task)
            .filter(and_(Task.assigned_to == user_id, Task.completed == False))
            .count()
        )

    def _get_recent_completion_rate(self, user_id: int, days: int = 30) -> float:
        """Get user's task completion rate over recent period"""

        since_date = datetime.utcnow() - timedelta(days=days)

        # Tasks assigned in period
        assigned_tasks = (
            self.db.query(Task)
            .filter(and_(Task.assigned_to == user_id, Task.created_at >= since_date))
            .count()
        )

        # Tasks completed in period
        completed_tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.completed == True,
                    Task.completed_at >= since_date,
                )
            )
            .count()
        )

        if assigned_tasks == 0:
            return 0.5  # Neutral score for new users

        return completed_tasks / assigned_tasks

    def _get_assignment_reason(self, recommended_user: Dict[str, Any]) -> str:
        """Generate human-readable reason for assignment recommendation"""

        if not recommended_user:
            return "No available users"

        if (
            recommended_user["conflicts"] == 0
            and recommended_user["current_workload"] <= 2
        ):
            return (
                f"{recommended_user['user_name']} has no conflicts and light workload"
            )
        elif recommended_user["conflicts"] == 0:
            return f"{recommended_user['user_name']} has no conflicts"
        elif recommended_user["current_workload"] <= 1:
            return f"{recommended_user['user_name']} has the lowest workload"
        else:
            return f"{recommended_user['user_name']} has the best overall availability"

    def get_household_schedule_overview(
        self, household_id: int, start_date: datetime, days: int = 7
    ) -> Dict[str, Any]:
        """Get comprehensive schedule overview for household"""

        end_date = start_date + timedelta(days=days)

        # Get all events in period
        events = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.household_id == household_id,
                    Event.start_date >= start_date,
                    Event.start_date < end_date,
                    Event.status.in_(["published", "pending_approval"]),
                )
            )
            .order_by(Event.start_date)
            .all()
        )

        # Get all tasks due in period
        tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.household_id == household_id,
                    Task.due_date >= start_date,
                    Task.due_date < end_date,
                    Task.completed == False,
                )
            )
            .order_by(Task.due_date)
            .all()
        )

        # Organize by day
        schedule_by_day = {}
        current_date = start_date.date()

        for day_offset in range(days):
            day = current_date + timedelta(days=day_offset)
            schedule_by_day[day.isoformat()] = {
                "date": day,
                "events": [],
                "tasks": [],
                "conflicts": 0,
            }

        # Add events to schedule
        for event in events:
            day_key = event.start_date.date().isoformat()
            if day_key in schedule_by_day:
                schedule_by_day[day_key]["events"].append(
                    {
                        "id": event.id,
                        "title": event.title,
                        "start_time": event.start_date,
                        "end_time": event.end_date,
                        "type": event.event_type,
                        "status": event.status,
                    }
                )

        # Add tasks to schedule
        for task in tasks:
            if task.due_date:
                day_key = task.due_date.date().isoformat()
                if day_key in schedule_by_day:
                    schedule_by_day[day_key]["tasks"].append(
                        {
                            "id": task.id,
                            "title": task.title,
                            "due_time": task.due_date,
                            "assigned_to": task.assigned_to,
                            "priority": task.priority,
                        }
                    )

        # Calculate conflicts per day
        for day_data in schedule_by_day.values():
            day_data["conflicts"] = len(
                [
                    task
                    for task in day_data["tasks"]
                    if len(
                        [
                            t
                            for t in day_data["tasks"]
                            if t["assigned_to"] == task["assigned_to"]
                        ]
                    )
                    > 1
                ]
            )

        return {
            "start_date": start_date,
            "end_date": end_date,
            "schedule": schedule_by_day,
            "total_events": len(events),
            "total_tasks": len(tasks),
            "busiest_day": max(
                schedule_by_day.values(),
                key=lambda x: len(x["events"]) + len(x["tasks"]),
            )["date"].isoformat(),
        }
