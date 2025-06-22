from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta
from ..models.task import Task
from ..models.user import User
from ..models.household_membership import HouseholdMembership
from ..models.enums import TaskStatus, HouseholdRole
from ..schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskComplete,
    RecurrencePattern,
)
from dataclasses import dataclass


# Custom Exceptions
class TaskServiceError(Exception):
    """Base exception for task service errors"""

    pass


class TaskNotFoundError(TaskServiceError):
    """Task not found"""

    pass


class PermissionDeniedError(TaskServiceError):
    """Permission denied for operation"""

    pass


class BusinessRuleViolationError(TaskServiceError):
    """Business rule violation"""

    pass


@dataclass
class HouseholdMember:
    """Task service household member representation"""

    id: int
    name: str
    email: str
    role: str
    joined_at: datetime


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        task_data: TaskCreate,
        household_id: int,
        created_by: int,
        use_rotation: bool = True,
    ) -> Task:
        """Create task with optional automatic rotation assignment"""

        # Validate permissions
        if not self._user_can_create_tasks(created_by, household_id):
            raise PermissionDeniedError("User is not a member of this household")

        # Get household members for assignment
        household_members = self._get_household_members(household_id)
        if not household_members:
            raise BusinessRuleViolationError("Household has no active members")

        # Determine assignee
        if task_data.assigned_to:
            # Validate specified assignee is a household member
            if not self._is_household_member(task_data.assigned_to, household_id):
                raise BusinessRuleViolationError(
                    "Assigned user is not a household member"
                )
            assigned_to = task_data.assigned_to
        elif use_rotation:
            assigned_to = self._get_next_assignee_by_rotation(household_id)
        else:
            assigned_to = created_by  # Default to creator

        # Check for conflicts if due date specified
        if task_data.due_date and self._has_task_conflict(
            assigned_to, task_data.due_date
        ):
            if use_rotation:
                # Try next person in rotation
                assigned_to = self._get_next_assignee_by_rotation(
                    household_id, exclude_user_id=assigned_to
                )
            # If still conflicts, allow it but could add warning

        try:
            task = Task(
                title=task_data.title,
                description=task_data.description,
                priority=task_data.priority.value,
                estimated_duration=task_data.estimated_duration,
                assigned_to=assigned_to,
                created_by=created_by,
                household_id=household_id,
                due_date=task_data.due_date,
                recurring=task_data.recurring,
                recurrence_pattern=(
                    task_data.recurrence_pattern.value
                    if task_data.recurrence_pattern
                    else None
                ),
                status=TaskStatus.PENDING.value,
            )

            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)

            # Create recurring instances if needed
            if task.recurring and task.recurrence_pattern:
                self._create_recurring_instances(task)

            return task

        except Exception as e:
            self.db.rollback()
            raise TaskServiceError(f"Failed to create task: {str(e)}")

    def update_task(
        self, task_id: int, task_updates: TaskUpdate, updated_by: int
    ) -> Task:
        """Update task with permission validation"""

        task = self._get_task_or_raise(task_id)

        # Check permissions (creator, assignee, or household admin can edit)
        if not self._user_can_edit_task(updated_by, task):
            raise PermissionDeniedError(
                "Only task creator, assignee, or household admin can edit"
            )

        # Prevent editing completed tasks
        if task.status == TaskStatus.COMPLETED.value:
            raise BusinessRuleViolationError("Cannot edit completed tasks")

        try:
            # Update basic fields
            update_data = task_updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field == "assigned_to":
                    # Validate new assignee is household member
                    if not self._is_household_member(value, task.household_id):
                        raise BusinessRuleViolationError(
                            "New assignee is not a household member"
                        )

                setattr(task, field, value.value if hasattr(value, "value") else value)

            task.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(task)
            return task

        except Exception as e:
            self.db.rollback()
            raise TaskServiceError(f"Failed to update task: {str(e)}")

    def delete_task(self, task_id: int, deleted_by: int) -> bool:
        """Delete task with proper validation"""

        task = self._get_task_or_raise(task_id)

        if not self._user_can_edit_task(deleted_by, task):
            raise PermissionDeniedError(
                "Only task creator, assignee, or household admin can delete"
            )

        if task.status == TaskStatus.COMPLETED.value:
            raise BusinessRuleViolationError("Cannot delete completed tasks")

        try:
            self.db.delete(task)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise TaskServiceError(f"Failed to delete task: {str(e)}")

    def complete_task(
        self, task_id: int, user_id: int, completion_data: TaskComplete
    ) -> Task:
        """Mark task as completed"""

        task = self._get_task_or_raise(task_id)

        # Validate permissions
        if not self._user_can_complete_task(user_id, task):
            raise PermissionDeniedError(
                "Only assigned user or household admin can complete this task"
            )

        if task.status == TaskStatus.COMPLETED.value:
            raise BusinessRuleViolationError("Task already completed")

        try:
            # Mark as completed - use status as single source of truth
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()
            task.completion_notes = completion_data.completion_notes
            task.photo_proof_url = completion_data.photo_proof_url

            # Keep completed boolean for backward compatibility
            task.completed = True

            self.db.commit()
            self.db.refresh(task)

            return task

        except Exception as e:
            self.db.rollback()
            raise TaskServiceError(f"Failed to complete task: {str(e)}")

    def update_task_status(self, task_id: int, new_status: str, user_id: int) -> Task:
        """Update task status with proper validation"""

        task = self._get_task_or_raise(task_id)

        if not self._user_can_edit_task(user_id, task):
            raise PermissionDeniedError("User cannot update this task")

        # Validate status transitions
        if not self._is_valid_status_transition(task.status, new_status):
            raise BusinessRuleViolationError(
                f"Cannot change status from {task.status} to {new_status}"
            )

        try:
            task.status = new_status

            # Update completion fields when marking as completed
            if new_status == TaskStatus.COMPLETED.value:
                task.completed = True
                task.completed_at = datetime.utcnow()
            elif (
                task.status == TaskStatus.COMPLETED.value
                and new_status != TaskStatus.COMPLETED.value
            ):
                # Uncompleting task
                task.completed = False
                task.completed_at = None

            self.db.commit()
            self.db.refresh(task)
            return task

        except Exception as e:
            self.db.rollback()
            raise TaskServiceError(f"Failed to update task status: {str(e)}")

    def reassign_task(
        self, task_id: int, new_assignee_id: int, reassigned_by: int
    ) -> Task:
        """Reassign task to different user"""

        task = self._get_task_or_raise(task_id)

        if not self._user_can_edit_task(reassigned_by, task):
            raise PermissionDeniedError("User cannot reassign this task")

        if task.status == TaskStatus.COMPLETED.value:
            raise BusinessRuleViolationError("Cannot reassign completed task")

        if not self._is_household_member(new_assignee_id, task.household_id):
            raise BusinessRuleViolationError("New assignee is not a household member")

        try:
            task.assigned_to = new_assignee_id
            task.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(task)
            return task

        except Exception as e:
            self.db.rollback()
            raise TaskServiceError(f"Failed to reassign task: {str(e)}")

    def get_household_tasks(
        self,
        household_id: int,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: str = None,
        assigned_to: int = None,
        priority: str = None,
        overdue_only: bool = False,
    ) -> Dict[str, Any]:
        """Get household tasks with filtering and pagination"""

        if not self._user_can_view_tasks(user_id, household_id):
            raise PermissionDeniedError("User cannot view household tasks")

        # Build query with filters
        query = self.db.query(Task).filter(Task.household_id == household_id)

        if status:
            query = query.filter(Task.status == status)

        if assigned_to:
            query = query.filter(Task.assigned_to == assigned_to)

        if priority:
            query = query.filter(Task.priority == priority)

        if overdue_only:
            now = datetime.utcnow()
            query = query.filter(
                and_(Task.status != TaskStatus.COMPLETED.value, Task.due_date < now)
            )

        # Get total count for pagination
        total_count = query.count()

        # Get tasks with pagination
        tasks = (
            query.order_by(
                Task.due_date.asc().nullslast(),  # Due date first, nulls last
                desc(Task.created_at),  # Then by created date
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Enrich with assignee and creator names
        task_list = []
        for task in tasks:
            assignee = self.db.query(User).filter(User.id == task.assigned_to).first()
            creator = self.db.query(User).filter(User.id == task.created_by).first()

            # Check if overdue
            is_overdue = (
                task.due_date
                and task.due_date < datetime.utcnow()
                and task.status != TaskStatus.COMPLETED.value
            )

            task_list.append(
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "priority": task.priority,
                    "status": task.status,
                    "assigned_to": task.assigned_to,
                    "assigned_to_name": assignee.name if assignee else "Unknown",
                    "created_by": task.created_by,
                    "created_by_name": creator.name if creator else "Unknown",
                    "due_date": task.due_date,
                    "is_overdue": is_overdue,
                    "estimated_duration": task.estimated_duration,
                    "recurring": task.recurring,
                    "recurrence_pattern": task.recurrence_pattern,
                    "created_at": task.created_at,
                    "completed_at": task.completed_at,
                }
            )

        return {
            "tasks": task_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    def get_user_task_summary(self, user_id: int, household_id: int) -> Dict[str, Any]:
        """Get comprehensive summary of user's tasks"""

        if not self._user_can_view_tasks(user_id, household_id):
            raise PermissionDeniedError("User cannot view household tasks")

        now = datetime.utcnow()

        # Get user's tasks
        user_tasks = (
            self.db.query(Task)
            .filter(
                and_(Task.assigned_to == user_id, Task.household_id == household_id)
            )
            .all()
        )

        # Calculate statistics
        total_assigned = len(user_tasks)
        completed_tasks = [
            t for t in user_tasks if t.status == TaskStatus.COMPLETED.value
        ]
        overdue_tasks = [
            t
            for t in user_tasks
            if t.due_date
            and t.due_date < now
            and t.status != TaskStatus.COMPLETED.value
        ]
        pending_tasks = [t for t in user_tasks if t.status == TaskStatus.PENDING.value]
        in_progress_tasks = [
            t for t in user_tasks if t.status == TaskStatus.IN_PROGRESS.value
        ]

        completion_rate = (
            (len(completed_tasks) / total_assigned * 100) if total_assigned > 0 else 0
        )

        # Get current streak
        streak = self._calculate_completion_streak(user_id)

        # Get upcoming tasks (next 7 days)
        upcoming_due = datetime.utcnow() + timedelta(days=7)
        upcoming_tasks = [
            t
            for t in user_tasks
            if t.due_date
            and now <= t.due_date <= upcoming_due
            and t.status != TaskStatus.COMPLETED.value
        ]

        return {
            "user_id": user_id,
            "household_id": household_id,
            "total_assigned": total_assigned,
            "completed_count": len(completed_tasks),
            "overdue_count": len(overdue_tasks),
            "pending_count": len(pending_tasks),
            "in_progress_count": len(in_progress_tasks),
            "upcoming_count": len(upcoming_tasks),
            "completion_rate": round(completion_rate, 1),
            "current_streak": streak,
            "upcoming_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "due_date": t.due_date,
                    "priority": t.priority,
                }
                for t in sorted(upcoming_tasks, key=lambda x: x.due_date)[:5]
            ],
        }

    def get_household_leaderboard(
        self, household_id: int, user_id: int, month: int = None, year: int = None
    ) -> List[Dict[str, Any]]:
        """Get task completion leaderboard for household"""

        if not self._user_can_view_tasks(user_id, household_id):
            raise PermissionDeniedError("User cannot view household tasks")

        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

        # Get month boundaries
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        members = self._get_household_members(household_id)
        leaderboard = []

        for member in members:
            # Get member's tasks for the month
            member_tasks = (
                self.db.query(Task)
                .filter(
                    and_(
                        Task.assigned_to == member.id,
                        Task.household_id == household_id,
                        Task.created_at >= start_date,
                        Task.created_at < end_date,
                    )
                )
                .all()
            )

            completed = [
                t for t in member_tasks if t.status == TaskStatus.COMPLETED.value
            ]
            completion_rate = (
                (len(completed) / len(member_tasks) * 100) if member_tasks else 0
            )

            leaderboard.append(
                {
                    "user_id": member.id,
                    "user_name": member.name,
                    "tasks_completed": len(completed),
                    "tasks_assigned": len(member_tasks),
                    "completion_rate": round(completion_rate, 1),
                    "current_streak": self._calculate_completion_streak(member.id),
                }
            )

        # Sort by completion rate
        leaderboard.sort(key=lambda x: (x["completion_rate"]), reverse=True)

        # Add rankings
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return leaderboard

    def get_overdue_tasks_for_reminders(
        self, household_id: int = None
    ) -> List[Dict[str, Any]]:
        """Get overdue tasks that need reminders"""

        now = datetime.utcnow()
        query = (
            self.db.query(Task, User.name, User.email)
            .join(User, Task.assigned_to == User.id)
            .filter(
                and_(Task.status != TaskStatus.COMPLETED.value, Task.due_date < now)
            )
        )

        if household_id:
            query = query.filter(Task.household_id == household_id)

        overdue_tasks = query.all()

        result = []
        for task, user_name, user_email in overdue_tasks:
            days_overdue = (now - task.due_date).days if task.due_date else 0

            result.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "household_id": task.household_id,
                    "assigned_to": task.assigned_to,
                    "assigned_to_name": user_name,
                    "assigned_to_email": user_email,
                    "due_date": task.due_date,
                    "days_overdue": days_overdue,
                    "priority": task.priority,
                }
            )

        return result

    # === ROTATION AND ASSIGNMENT LOGIC ===

    def _get_next_assignee_by_rotation(
        self, household_id: int, exclude_user_id: int = None
    ) -> int:
        """Get next person in rotation using improved round-robin algorithm"""

        members = self._get_household_members(household_id)
        if not members:
            raise BusinessRuleViolationError("No active household members found")

        # Filter out excluded user
        if exclude_user_id:
            members = [m for m in members if m.id != exclude_user_id]
            if not members:
                raise BusinessRuleViolationError(
                    "No available household members for assignment"
                )

        # Get task assignment counts for the last 30 days for fairness
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        assignment_counts = {}
        for member in members:
            count = (
                self.db.query(Task)
                .filter(
                    and_(
                        Task.assigned_to == member.id,
                        Task.household_id == household_id,
                        Task.created_at >= thirty_days_ago,
                    )
                )
                .count()
            )
            assignment_counts[member.id] = count

        # Assign to member with fewest recent assignments
        next_assignee = min(members, key=lambda m: assignment_counts[m.id])
        return next_assignee.id

    def get_rotation_schedule(
        self, household_id: int, user_id: int, weeks_ahead: int = 4
    ) -> Dict[str, Any]:
        """Get upcoming rotation schedule for planning"""

        if not self._user_can_view_tasks(user_id, household_id):
            raise PermissionDeniedError("User cannot view household tasks")

        members = self._get_household_members(household_id)
        if not members:
            return {"schedule": [], "members": []}

        # Simple round-robin for future planning
        schedule = []
        current_date = datetime.now().date()

        for week in range(weeks_ahead):
            week_start = current_date + timedelta(weeks=week)
            member_index = week % len(members)
            assigned_member = members[member_index]

            schedule.append(
                {
                    "week_start": week_start,
                    "assigned_to": assigned_member.id,
                    "assigned_to_name": assigned_member.name,
                }
            )

        return {
            "schedule": schedule,
            "members": [{"id": m.id, "name": m.name} for m in members],
            "rotation_period_days": 7 * len(members),
        }

    # === HELPER METHODS ===

    def _get_household_members(self, household_id: int) -> List[HouseholdMember]:
        """Get all active members using HouseholdMembership"""

        members_query = (
            self.db.query(User, HouseholdMembership)
            .join(HouseholdMembership, User.id == HouseholdMembership.user_id)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                    User.is_active == True,
                )
            )
            .order_by(User.id)  # Consistent ordering for rotation
            .all()
        )

        return [
            HouseholdMember(
                id=user.id,
                name=user.name,
                email=user.email,
                role=membership.role,
                joined_at=membership.joined_at,
            )
            for user, membership in members_query
        ]

    def _get_task_or_raise(self, task_id: int) -> Task:
        """Get task or raise exception"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return task

    def _user_can_create_tasks(self, user_id: int, household_id: int) -> bool:
        """Check if user can create tasks for household"""
        return (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        ) is not None

    def _user_can_edit_task(self, user_id: int, task: Task) -> bool:
        """Check if user can edit task (creator, assignee, or admin)"""
        if task.created_by == user_id or task.assigned_to == user_id:
            return True

        # Check if user is household admin
        admin_membership = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == task.household_id,
                    HouseholdMembership.role == HouseholdRole.ADMIN.value,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        )
        return admin_membership is not None

    def _user_can_complete_task(self, user_id: int, task: Task) -> bool:
        """Check if user can complete task (assignee or admin)"""
        if task.assigned_to == user_id:
            return True

        # Check if user is household admin
        admin_membership = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == task.household_id,
                    HouseholdMembership.role == HouseholdRole.ADMIN.value,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        )
        return admin_membership is not None

    def _user_can_view_tasks(self, user_id: int, household_id: int) -> bool:
        """Check if user can view household tasks"""
        return self._user_can_create_tasks(user_id, household_id)

    def _is_household_member(self, user_id: int, household_id: int) -> bool:
        """Check if user is an active household member"""
        return (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        ) is not None

    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """Validate status transitions"""
        valid_transitions = {
            TaskStatus.PENDING.value: [
                TaskStatus.IN_PROGRESS.value,
                TaskStatus.COMPLETED.value,
            ],
            TaskStatus.IN_PROGRESS.value: [
                TaskStatus.COMPLETED.value,
                TaskStatus.PENDING.value,
            ],
            TaskStatus.COMPLETED.value: [
                TaskStatus.PENDING.value
            ],  # Allow uncompleting
            TaskStatus.OVERDUE.value: [
                TaskStatus.COMPLETED.value,
                TaskStatus.IN_PROGRESS.value,
            ],
        }

        return new_status in valid_transitions.get(current_status, [])

    def _has_task_conflict(self, user_id: int, due_date: datetime) -> bool:
        """Check if user already has a task due on the same day"""
        if not due_date:
            return False

        start_of_day = due_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        existing_task = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.due_date >= start_of_day,
                    Task.due_date < end_of_day,
                    Task.status != TaskStatus.COMPLETED.value,
                )
            )
            .first()
        )

        return existing_task is not None

    def _calculate_completion_streak(self, user_id: int) -> int:
        """Calculate consecutive days with completed tasks"""
        today = datetime.now().date()
        streak = 0
        current_date = today

        # Look back day by day to find consecutive completion days
        for _ in range(30):  # Check last 30 days max
            start_of_day = datetime.combine(current_date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)

            completed_today = (
                self.db.query(Task)
                .filter(
                    and_(
                        Task.assigned_to == user_id,
                        Task.status == TaskStatus.COMPLETED.value,
                        Task.completed_at >= start_of_day,
                        Task.completed_at < end_of_day,
                    )
                )
                .first()
            )

            if completed_today:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break

        return streak

    def _create_recurring_instances(self, task: Task):
        """Create limited future instances of recurring tasks"""
        if not task.due_date or not task.recurrence_pattern:
            return

        # Create only a few instances ahead to avoid clutter
        if task.recurrence_pattern == RecurrencePattern.DAILY.value:
            instances_to_create = 7  # 1 week ahead
        elif task.recurrence_pattern == RecurrencePattern.WEEKLY.value:
            instances_to_create = 4  # 4 weeks ahead
        elif task.recurrence_pattern == RecurrencePattern.BIWEEKLY.value:
            instances_to_create = 3  # 6 weeks ahead
        else:  # MONTHLY
            instances_to_create = 3  # 3 months ahead

        current_date = task.due_date
        members = self._get_household_members(task.household_id)

        if not members:
            return

        member_index = 0

        for i in range(instances_to_create):
            # Calculate next date
            if task.recurrence_pattern == RecurrencePattern.DAILY.value:
                next_date = current_date + timedelta(days=1)
            elif task.recurrence_pattern == RecurrencePattern.WEEKLY.value:
                next_date = current_date + timedelta(weeks=1)
            elif task.recurrence_pattern == RecurrencePattern.BIWEEKLY.value:
                next_date = current_date + timedelta(weeks=2)
            elif task.recurrence_pattern == RecurrencePattern.MONTHLY.value:
                # Add one month (handle edge cases)
                try:
                    if current_date.month == 12:
                        next_date = current_date.replace(
                            year=current_date.year + 1, month=1
                        )
                    else:
                        next_date = current_date.replace(month=current_date.month + 1)
                except ValueError:
                    # Handle day overflow (e.g., Jan 31 -> Feb 28)
                    if current_date.month == 12:
                        next_date = current_date.replace(
                            year=current_date.year + 1, month=1, day=1
                        )
                    else:
                        next_date = current_date.replace(
                            month=current_date.month + 1, day=1
                        )
            else:
                break

            # Rotate assignee for fair distribution
            next_assignee = members[member_index % len(members)]
            member_index += 1

            # Create recurring task instance
            recurring_task = Task(
                title=task.title,
                description=task.description,
                priority=task.priority,
                estimated_duration=task.estimated_duration,
                assigned_to=next_assignee.id,
                created_by=task.created_by,
                household_id=task.household_id,
                due_date=next_date,
                recurring=True,
                recurrence_pattern=task.recurrence_pattern,
                status=TaskStatus.PENDING.value,
            )

            self.db.add(recurring_task)
            current_date = next_date

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # Log error but don't fail the main task creation
            print(f"Failed to create recurring instances: {e}")

    def get_user_task_score(
        self, user_id: int, household_id: int, month: int = None, year: int = None
    ) -> Dict[str, Any]:
        """Calculate user's task score for the specified month/year"""

        if not self._user_can_view_tasks(user_id, household_id):
            raise PermissionDeniedError("User cannot view household tasks")

        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

        # Get month boundaries
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Get completed tasks for the month (use status, not completed boolean)
        completed_tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.household_id == household_id,
                    Task.status == TaskStatus.COMPLETED.value,
                    Task.completed_at >= start_date,
                    Task.completed_at < end_date,
                )
            )
            .all()
        )

        # Get assigned tasks for the month (for completion rate)
        assigned_tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.household_id == household_id,
                    Task.created_at >= start_date,
                    Task.created_at < end_date,
                )
            )
            .all()
        )

        tasks_completed = len(completed_tasks)
        tasks_assigned = len(assigned_tasks)
        completion_rate = (
            (tasks_completed / tasks_assigned * 100) if tasks_assigned > 0 else 0
        )

        # Calculate streak (consecutive days with completed tasks)
        streak = self._calculate_completion_streak(user_id)

        # Count overdue tasks (use status consistently)
        now = datetime.utcnow()
        overdue_count = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.household_id == household_id,
                    Task.status != TaskStatus.COMPLETED.value,
                    Task.due_date < now,
                )
            )
            .count()
        )

        return {
            "user_id": user_id,
            "household_id": household_id,
            "month": month,
            "year": year,
            "tasks_completed": tasks_completed,
            "tasks_assigned": tasks_assigned,
            "completion_rate": round(completion_rate, 1),
            "current_streak": streak,
            "overdue_tasks": overdue_count,
        }
