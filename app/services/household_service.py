from app.models.enums import HouseholdRole
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.household import Household
from ..models.user import User
from ..models.expense import Expense
from ..models.task import Task
from ..models.event import Event
from ..models.household_membership import HouseholdMembership
from ..schemas.household import HouseholdCreate, HouseholdUpdate
from ..utils.service_helpers import ServiceHelpers


# Custom Exceptions for better error handling
class HouseholdServiceError(Exception):
    """Base exception for household service errors"""

    pass


class HouseholdNotFoundError(HouseholdServiceError):
    """Household not found"""

    pass


class UserNotFoundError(HouseholdServiceError):
    """User not found"""

    pass


class PermissionDeniedError(HouseholdServiceError):
    """Permission denied for operation"""

    pass


class BusinessRuleViolationError(HouseholdServiceError):
    """Business rule violation"""

    pass


class HouseholdService:
    def __init__(self, db: Session):
        self.db = db

    def create_household(
        self, household_data: HouseholdCreate, creator_id: int
    ) -> Household:
        """Create a new household with creator as admin"""

        # Validate creator exists and is not already in a household
        creator = self._get_user_or_raise(creator_id)

        if self._user_has_active_household(creator_id):
            raise BusinessRuleViolationError("User is already a member of a household")

        try:
            household = Household(
                name=household_data.name,
                address=household_data.address,
                house_rules=household_data.house_rules,
                settings=self._get_default_household_settings(),
            )

            self.db.add(household)
            self.db.flush()  # Get ID without committing

            # Add creator as admin
            self._create_membership(
                user_id=creator_id,
                household_id=household.id,
                role=HouseholdRole.ADMIN.value,
            )

            self.db.commit()
            self.db.refresh(household)
            return household

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to create household: {str(e)}")

    def add_member_to_household(
        self,
        household_id: int,
        user_id: int,
        role: str = HouseholdRole.MEMBER.value,
        added_by: int = None,
    ) -> bool:
        """Add member to household with single household business rule"""

        # Validate inputs
        household = self._get_household_or_raise(household_id)
        user = self._get_user_or_raise(user_id)

        # Validate role
        if role not in [r.value for r in HouseholdRole]:
            raise BusinessRuleViolationError(f"Invalid role: {role}")

        # Check permissions if added_by is specified
        if added_by and not self.check_admin_permissions(added_by, household_id):
            raise PermissionDeniedError("Only admins can add members")

        # Single household business rule
        if self._user_has_active_household(user_id):
            raise BusinessRuleViolationError("User is already a member of a household")

        # Check if user was previously a member (for reactivation)
        existing_membership = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == household_id,
                )
            )
            .first()
        )

        try:
            if existing_membership:
                if existing_membership.is_active:
                    return False  # Already active member
                else:
                    # Reactivate previous membership
                    existing_membership.is_active = True
                    existing_membership.role = role
                    existing_membership.joined_at = datetime.utcnow()
            else:
                # Create new membership
                self._create_membership(user_id, household_id, role)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to add member: {str(e)}")

    def remove_member_from_household(
        self, household_id: int, user_id: int, removed_by: int
    ) -> Dict[str, Any]:
        """Remove member with proper validation and cleanup"""

        # Validate permissions
        if not self._can_remove_member(household_id, user_id, removed_by):
            raise PermissionDeniedError(
                "Only admin or the user themselves can remove a member"
            )

        # Get membership
        membership = self._get_active_membership(user_id, household_id)
        if not membership:
            raise BusinessRuleViolationError("User is not a member of this household")

        # Prevent removing last admin
        if membership.role == HouseholdRole.ADMIN.value and self._is_last_admin(
            household_id
        ):
            raise BusinessRuleViolationError(
                "Cannot remove the last admin from household"
            )

        try:
            # Check for pending responsibilities
            warnings = self._check_pending_responsibilities(user_id)

            # Deactivate membership (preserve audit trail)
            membership.is_active = False

            self.db.commit()

            return {
                "success": True,
                "message": "Member removed successfully",
                "warnings": warnings.get("warnings", []),
                "pending_tasks": warnings.get("pending_tasks", 0),
            }

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to remove member: {str(e)}")

    def update_member_role(
        self, household_id: int, user_id: int, new_role: str, updated_by: int
    ) -> bool:
        """Update member role with proper validation"""

        # Validate role
        if new_role not in [r.value for r in HouseholdRole]:
            raise BusinessRuleViolationError(f"Invalid role: {new_role}")

        # Check permissions
        if not self.check_admin_permissions(updated_by, household_id):
            raise PermissionDeniedError("Only admins can update member roles")

        # Get target membership
        membership = self._get_active_membership(user_id, household_id)
        if not membership:
            raise BusinessRuleViolationError("User is not a member of this household")

        # Prevent removing last admin
        if (
            membership.role == HouseholdRole.ADMIN.value
            and new_role != HouseholdRole.ADMIN.value
            and self._is_last_admin(household_id)
        ):
            raise BusinessRuleViolationError(
                "Cannot remove admin role from the last admin"
            )

        try:
            membership.role = new_role
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to update member role: {str(e)}")

    def get_household_details(self, household_id: int) -> Dict[str, Any]:
        """Get comprehensive household information"""

        household = self._get_household_or_raise(household_id)
        members = ServiceHelpers.get_household_members(household_id)
        health_score = self.calculate_household_health_score(household_id)
        statistics = self.get_household_statistics(household_id)

        return {
            "id": household.id,
            "name": household.name,
            "address": household.address,
            "house_rules": household.house_rules,
            "settings": household.settings or {},
            "created_at": household.created_at,
            "updated_at": household.updated_at,
            "member_count": len([m for m in members if m["is_active"]]),
            "admin_count": len(
                [m for m in members if m["role"] == HouseholdRole.ADMIN.value]
            ),
            "members": members,
            "health_score": health_score,
            "statistics": statistics,
        }

    def check_admin_permissions(self, user_id: int, household_id: int) -> bool:
        """Check if user has admin permissions for household"""
        membership = self._get_active_membership(user_id, household_id)
        return membership is not None and membership.role == HouseholdRole.ADMIN.value

    def check_member_permissions(self, user_id: int, household_id: int) -> bool:
        """Check if user is a member (any role) of household"""
        return self._get_active_membership(user_id, household_id) is not None

    def get_user_household_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's current household information (single household)"""

        membership_query = (
            self.db.query(HouseholdMembership, Household)
            .join(Household, HouseholdMembership.household_id == Household.id)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        )

        if not membership_query:
            return None

        membership, household = membership_query

        return {
            "household_id": household.id,
            "household_name": household.name,
            "user_role": membership.role,
            "joined_at": membership.joined_at,
            "is_admin": membership.role == HouseholdRole.ADMIN.value,
            "is_guest": membership.role == HouseholdRole.GUEST.value,
            "member_count": self._get_active_member_count(household.id),
        }

    def transfer_household_ownership(
        self, household_id: int, current_admin_id: int, new_admin_id: int
    ) -> bool:
        """Transfer household ownership to another member"""

        # Validate current admin permissions
        if not self.check_admin_permissions(current_admin_id, household_id):
            raise PermissionDeniedError("Only current admin can transfer ownership")

        # Validate new admin is a member
        new_admin_membership = self._get_active_membership(new_admin_id, household_id)
        if not new_admin_membership:
            raise BusinessRuleViolationError("New admin must be a household member")

        try:
            # Update new admin role
            new_admin_membership.role = HouseholdRole.ADMIN.value

            # Optionally demote current admin to member
            current_admin_membership = self._get_active_membership(
                current_admin_id, household_id
            )
            if current_admin_membership:
                current_admin_membership.role = HouseholdRole.MEMBER.value

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to transfer ownership: {str(e)}")

    # === PRIVATE HELPER METHODS ===

    def _get_household_or_raise(self, household_id: int) -> Household:
        """Get household or raise exception"""
        household = (
            self.db.query(Household).filter(Household.id == household_id).first()
        )
        if not household:
            raise HouseholdNotFoundError(f"Household {household_id} not found")
        return household

    def _get_user_or_raise(self, user_id: int) -> User:
        """Get user or raise exception"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")
        return user

    def _get_active_membership(
        self, user_id: int, household_id: int
    ) -> Optional[HouseholdMembership]:
        """Get active membership for user in household"""
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
        )

    def _create_membership(
        self, user_id: int, household_id: int, role: str
    ) -> HouseholdMembership:
        """Create new membership record"""
        membership = HouseholdMembership(
            user_id=user_id, household_id=household_id, role=role, is_active=True
        )
        self.db.add(membership)
        return membership

    def _is_user_already_member(self, user_id: int, household_id: int) -> bool:
        """Check if user is already an active member"""
        return self._get_active_membership(user_id, household_id) is not None

    def _user_has_active_household(self, user_id: int) -> bool:
        """Check if user has any active household membership (single household rule)"""
        return (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        ) is not None

    def _can_remove_member(
        self, household_id: int, user_id: int, removed_by: int
    ) -> bool:
        """Check if remover has permission to remove member"""
        if removed_by == user_id:
            return True  # Self-removal always allowed
        return self.check_admin_permissions(removed_by, household_id)

    def _is_last_admin(self, household_id: int) -> bool:
        """Check if there's only one admin left"""
        admin_count = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.role == HouseholdRole.ADMIN.value,
                    HouseholdMembership.is_active == True,
                )
            )
            .count()
        )
        return admin_count <= 1

    def _check_pending_responsibilities(self, user_id: int) -> Dict[str, Any]:
        """Check for pending responsibilities before removal"""
        pending_tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.status.in_(["pending", "in_progress", "overdue"]),
                )
            )
            .count()
        )

        warnings = []
        if pending_tasks > 0:
            warnings.append(
                f"User has {pending_tasks} incomplete tasks that may need reassignment"
            )

        return {
            "warnings": warnings,
            "pending_tasks": pending_tasks,
        }

    def _get_batch_member_statistics(
        self, user_ids: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """Get statistics for multiple users efficiently"""
        if not user_ids:
            return {}

        now = datetime.utcnow()
        last_month = now - timedelta(days=30)

        # Batch query for task statistics
        task_stats = (
            self.db.query(
                Task.assigned_to,
                func.count(Task.id).label("tasks_assigned"),
                func.sum(func.case([(Task.status == "completed", 1)], else_=0)).label(
                    "tasks_completed"
                ),
            )
            .filter(and_(Task.assigned_to.in_(user_ids), Task.created_at >= last_month))
            .group_by(Task.assigned_to)
            .all()
        )

        # Batch query for expense statistics
        expense_stats = (
            self.db.query(
                Expense.created_by,
                func.count(Expense.id).label("expenses_created"),
                func.sum(Expense.amount).label("total_expenses_amount"),
            )
            .filter(
                and_(Expense.created_by.in_(user_ids), Expense.created_at >= last_month)
            )
            .group_by(Expense.created_by)
            .all()
        )

        # Build comprehensive result
        result = {user_id: self._get_empty_member_stats() for user_id in user_ids}

        # Update with task stats
        for stat in task_stats:
            user_id = stat.assigned_to
            tasks_assigned = stat.tasks_assigned or 0
            tasks_completed = stat.tasks_completed or 0

            result[user_id].update(
                {
                    "tasks_assigned_last_month": tasks_assigned,
                    "tasks_completed_last_month": tasks_completed,
                    "completion_rate": round(
                        (
                            (tasks_completed / tasks_assigned * 100)
                            if tasks_assigned > 0
                            else 0
                        ),
                        1,
                    ),
                }
            )

        # Update with expense stats
        for stat in expense_stats:
            user_id = stat.created_by
            result[user_id].update(
                {
                    "expenses_created_last_month": stat.expenses_created or 0,
                    "total_expenses_amount_last_month": float(
                        stat.total_expenses_amount or 0
                    ),
                }
            )

        return result

    def _get_empty_member_stats(self) -> Dict[str, Any]:
        """Get empty member statistics structure"""
        return {
            "tasks_assigned_last_month": 0,
            "tasks_completed_last_month": 0,
            "completion_rate": 0.0,
            "expenses_created_last_month": 0,
            "total_expenses_amount_last_month": 0.0,
        }

    def _get_default_household_settings(self) -> Dict[str, Any]:
        """Get default household settings"""
        return {
            "guest_policy": {
                "max_overnight_guests": 2,
                "max_consecutive_nights": 3,
                "approval_required": True,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00",
            },
            "notification_settings": {
                "bill_reminder_days": 3,
                "task_overdue_hours": 24,
                "event_reminder_hours": 24,
            },
            "task_settings": {
                "rotation_enabled": True,
                "photo_proof_required": False,
            },
        }

    def _enforce_single_household(self) -> bool:
        """Business rule: enforce single household per user"""
        return True  # Change this based on your business requirements

    def calculate_household_health_score(self, household_id: int) -> Dict[str, Any]:
        """Calculate comprehensive household health score"""

        now = datetime.utcnow()
        last_month = now - timedelta(days=30)

        # Calculate individual health components
        financial_score = self._calculate_financial_health(household_id, last_month)
        task_score = self._calculate_task_health(household_id, last_month)
        communication_score = self._calculate_communication_health(
            household_id, last_month
        )
        member_score = self._calculate_member_satisfaction(household_id)

        # Weighted overall score
        overall_score = (
            financial_score * 0.4
            + task_score * 0.3
            + communication_score * 0.2
            + member_score * 0.1
        )

        # Generate improvement suggestions
        suggestions = self._generate_improvement_suggestions(
            financial_score, task_score, communication_score, member_score
        )

        return {
            "overall_score": round(overall_score),
            "financial_health": round(financial_score),
            "task_completion": round(task_score),
            "communication_activity": round(communication_score),
            "member_satisfaction": round(member_score),
            "improvement_suggestions": suggestions,
            "last_calculated": now,
        }

    def _calculate_financial_health(
        self, household_id: int, since_date: datetime
    ) -> float:
        """Calculate financial health score with ExpensePayment integration"""

        # Get recent expenses
        expenses = (
            self.db.query(Expense)
            .filter(
                and_(
                    Expense.household_id == household_id,
                    Expense.created_at >= since_date,
                )
            )
            .all()
        )

        if not expenses:
            return 85  # Neutral score for no activity

        total_expenses = len(expenses)
        fully_paid_expenses = 0

        for expense in expenses:
            # Check both split_details and actual ExpensePayment records
            is_fully_paid = False

            if expense.split_details and expense.split_details.get("all_paid"):
                is_fully_paid = True
            else:
                # Check ExpensePayment records
                from ..models.expense import ExpensePayment

                total_payments = (
                    self.db.query(func.sum(ExpensePayment.amount_paid))
                    .filter(ExpensePayment.expense_id == expense.id)
                    .scalar()
                    or 0
                )

                if total_payments >= expense.amount:
                    is_fully_paid = True

            if is_fully_paid:
                fully_paid_expenses += 1

        payment_rate = (
            (fully_paid_expenses / total_expenses) * 100 if total_expenses > 0 else 85
        )

        # Adjust score based on overdue payments
        overdue_count = total_expenses - fully_paid_expenses
        if overdue_count > 5:
            payment_rate -= 20
        elif overdue_count > 2:
            payment_rate -= 10

        return max(0, min(100, payment_rate))

    def _calculate_task_health(self, household_id: int, since_date: datetime) -> float:
        """Calculate task completion health score with status awareness"""

        tasks = (
            self.db.query(Task)
            .filter(
                and_(Task.household_id == household_id, Task.created_at >= since_date)
            )
            .all()
        )

        if not tasks:
            return 80  # Neutral score for no activity

        total_tasks = len(tasks)
        completed_tasks = len(
            [t for t in tasks if t.status == "completed" or t.completed]
        )
        overdue_tasks = len(
            [
                t
                for t in tasks
                if t.status == "overdue"
                or (not t.completed and t.due_date and t.due_date < datetime.utcnow())
            ]
        )

        completion_rate = (
            (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 80
        )

        # Penalty for overdue tasks
        if overdue_tasks > 0:
            completion_rate -= (overdue_tasks / total_tasks) * 30

        return max(0, min(100, completion_rate))

    def _calculate_communication_health(
        self, household_id: int, since_date: datetime
    ) -> float:
        """Calculate communication activity score"""

        from ..models.announcement import Announcement
        from ..models.poll import Poll

        recent_announcements = (
            self.db.query(Announcement)
            .filter(
                and_(
                    Announcement.household_id == household_id,
                    Announcement.created_at >= since_date,
                )
            )
            .count()
        )

        recent_polls = (
            self.db.query(Poll)
            .filter(
                and_(Poll.household_id == household_id, Poll.created_at >= since_date)
            )
            .count()
        )

        total_communication = recent_announcements + (
            recent_polls * 2
        )  # Polls weighted more

        # Score based on communication activity
        if total_communication >= 8:
            return 95
        elif total_communication >= 5:
            return 85
        elif total_communication >= 3:
            return 70
        elif total_communication >= 1:
            return 55
        else:
            return 35

    def _calculate_member_satisfaction(self, household_id: int) -> float:
        """Calculate member satisfaction score based on multiple factors"""

        # Get active member count
        active_members = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .count()
        )

        # Base score on member count
        base_score = 0
        if active_members >= 4:
            base_score = 85
        elif active_members >= 2:
            base_score = 75
        else:
            base_score = 60

        # Adjust based on recent activity (last 30 days)
        since_date = datetime.utcnow() - timedelta(days=30)

        # Members who completed tasks recently
        active_task_members = (
            self.db.query(Task.assigned_to)
            .filter(
                and_(
                    Task.household_id == household_id,
                    Task.completed_at >= since_date,
                    Task.completed == True,
                )
            )
            .distinct()
            .count()
        )

        # Members who created expenses recently
        active_expense_members = (
            self.db.query(Expense.created_by)
            .filter(
                and_(
                    Expense.household_id == household_id,
                    Expense.created_at >= since_date,
                )
            )
            .distinct()
            .count()
        )

        # Activity bonus
        activity_rate = (
            (active_task_members + active_expense_members) / (active_members * 2)
            if active_members > 0
            else 0
        )
        activity_bonus = activity_rate * 15  # Up to 15 point bonus

        return min(100, base_score + activity_bonus)

    def _generate_improvement_suggestions(
        self, financial: float, task: float, communication: float, member: float
    ) -> List[str]:
        """Generate improvement suggestions based on scores"""

        suggestions = []

        if financial < 70:
            suggestions.append(
                "Improve payment tracking - set up automatic reminders for overdue expenses"
            )

        if task < 70:
            suggestions.append(
                "Increase task completion rate - consider adjusting task assignments or deadlines"
            )

        if communication < 60:
            suggestions.append(
                "Boost household communication - try weekly announcements or house meetings"
            )

        if member < 70:
            suggestions.append(
                "Focus on member engagement - consider fun events or better task distribution"
            )

        # Add positive reinforcement
        if all(score >= 80 for score in [financial, task, communication, member]):
            suggestions.append("Excellent work! Your household is a model for others")
        elif not suggestions:
            suggestions.append("Great work! Your household is running smoothly")

        return suggestions

    def _get_active_member_count(self, household_id: int) -> int:
        """Get count of active members"""
        return (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .count()
        )

    def get_household_statistics(self, household_id: int) -> Dict[str, Any]:
        """Get comprehensive household statistics for the last 30 days"""

        now = datetime.utcnow()
        last_month = now - timedelta(days=30)

        # Financial stats
        financial_stats = (
            self.db.query(
                func.sum(Expense.amount).label("total_expenses"),
                func.count(Expense.id).label("expense_count"),
            )
            .filter(
                and_(
                    Expense.household_id == household_id,
                    Expense.created_at >= last_month,
                )
            )
            .first()
        )

        total_expenses = float(financial_stats.total_expenses or 0)
        expense_count = financial_stats.expense_count or 0

        # Task stats
        task_stats = (
            self.db.query(
                func.count(Task.id).label("total_tasks"),
                func.sum(func.case([(Task.status == "completed", 1)], else_=0)).label(
                    "completed_tasks"
                ),
                func.sum(
                    func.case(
                        [(and_(Task.status != "completed", Task.due_date < now), 1)],
                        else_=0,
                    )
                ).label("overdue_tasks"),
            )
            .filter(Task.household_id == household_id)
            .first()
        )

        # Event stats
        upcoming_events = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.household_id == household_id,
                    Event.start_date >= now,
                    Event.status == "published",
                )
            )
            .count()
        )

        # Household age
        household = self._get_household_or_raise(household_id)
        household_age_days = (now - household.created_at).days

        return {
            "total_monthly_expenses": total_expenses,
            "expense_count_last_month": expense_count,
            "average_expense_amount": (
                round(total_expenses / expense_count, 2) if expense_count > 0 else 0
            ),
            "total_tasks": task_stats.total_tasks or 0,
            "completed_tasks": task_stats.completed_tasks or 0,
            "overdue_tasks": task_stats.overdue_tasks or 0,
            "task_completion_rate": round(
                (
                    (task_stats.completed_tasks or 0)
                    / (task_stats.total_tasks or 1)
                    * 100
                ),
                1,
            ),
            "upcoming_events": upcoming_events,
            "active_members": self._get_active_member_count(household_id),
            "household_age_days": household_age_days,
        }

    def update_household_settings(
        self, household_id: int, settings_update: HouseholdUpdate, updated_by: int
    ) -> Household:
        """Update household settings (admin only)"""

        if not self.check_admin_permissions(updated_by, household_id):
            raise PermissionDeniedError("Only admins can update household settings")

        household = self._get_household_or_raise(household_id)

        try:
            # Update fields that were provided
            update_data = settings_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(household, field, value)

            household.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(household)
            return household

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to update household: {str(e)}")

    # TODO: Migration helper for future multi-household support
    def _prepare_for_multi_household_migration(self) -> Dict[str, Any]:
        """Future: Prepare data for multi-household migration"""
        # This method will help when you want to support multiple households
        # For now, it's just a placeholder for future development
        return {
            "migration_needed": False,
            "current_model": "single_household",
            "target_model": "multi_household",
        }
