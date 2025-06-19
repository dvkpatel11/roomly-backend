from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.household import Household
from ..models.user import User
from ..models.expense import Expense
from ..models.task import Task
from ..models.event import Event
from ..models.household_membership import HouseholdMembership
from ..schemas.household import HouseholdCreate, HouseholdUpdate


class HouseholdService:
    def __init__(self, db: Session):
        self.db = db

    def create_household(
        self, household_data: HouseholdCreate, creator_id: int
    ) -> Household:
        """Create a new household with creator as admin"""

        household = Household(
            name=household_data.name,
            address=household_data.address,
            house_rules=household_data.house_rules,
        )

        self.db.add(household)
        self.db.commit()
        self.db.refresh(household)

        # Add creator as admin using the membership system
        self.add_member_to_household(
            household_id=household.id,
            user_id=creator_id,
            role="admin",
            added_by=creator_id,  # Self-added
        )

        return household

    def add_member_to_household(
        self,
        household_id: int,
        user_id: int,
        role: str = "member",
        added_by: int = None,
    ) -> bool:
        """Add member using HouseholdMembership model with proper validation"""

        # Validate household exists
        household = (
            self.db.query(Household).filter(Household.id == household_id).first()
        )
        if not household:
            raise ValueError("Household not found")

        # Validate user exists and is not already in another household
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        if user.household_id and user.household_id != household_id:
            raise ValueError("User is already a member of another household")

        # Check if already a member (including inactive memberships)
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

        if existing_membership:
            if existing_membership.is_active:
                return False  # Already an active member
            else:
                # Reactivate inactive membership
                existing_membership.is_active = True
                existing_membership.role = role
                existing_membership.joined_at = datetime.utcnow()
        else:
            # Create new membership record
            membership = HouseholdMembership(
                user_id=user_id, household_id=household_id, role=role, is_active=True
            )
            self.db.add(membership)

        # Update user table for backward compatibility
        user.household_id = household_id
        user.household_role = role
        user.is_active = True

        self.db.commit()
        return True

    def remove_member_from_household(
        self, household_id: int, user_id: int, removed_by: int
    ) -> Dict[str, Any]:
        """Remove a user from household with proper cleanup"""

        # Validate permissions (only admin or self can remove)
        if removed_by != user_id:
            remover_membership = (
                self.db.query(HouseholdMembership)
                .filter(
                    and_(
                        HouseholdMembership.user_id == removed_by,
                        HouseholdMembership.household_id == household_id,
                        HouseholdMembership.is_active == True,
                        HouseholdMembership.role == "admin",
                    )
                )
                .first()
            )

            if not remover_membership:
                raise ValueError(
                    "Only admin or the user themselves can remove a member"
                )

        # Find the membership
        membership = (
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

        if not membership:
            return {
                "success": False,
                "message": "User is not a member of this household",
            }

        # Check if this is the last admin
        if membership.role == "admin":
            admin_count = (
                self.db.query(HouseholdMembership)
                .filter(
                    and_(
                        HouseholdMembership.household_id == household_id,
                        HouseholdMembership.role == "admin",
                        HouseholdMembership.is_active == True,
                    )
                )
                .count()
            )

            if admin_count <= 1:
                return {
                    "success": False,
                    "message": "Cannot remove the last admin from household",
                }

        # Check for pending responsibilities
        pending_tasks = (
            self.db.query(Task)
            .filter(and_(Task.assigned_to == user_id, Task.completed == False))
            .count()
        )

        warnings = []
        if pending_tasks > 0:
            warnings.append(
                f"User has {pending_tasks} incomplete tasks that may need reassignment"
            )

        # Get user for cleanup
        user = self.db.query(User).filter(User.id == user_id).first()

        # Deactivate membership (don't delete for audit trail)
        membership.is_active = False

        # Update user table
        if user:
            user.household_id = None
            user.household_role = None

        self.db.commit()

        return {
            "success": True,
            "message": "Member removed successfully",
            "warnings": warnings,
            "pending_tasks": pending_tasks,
        }

    def update_member_role(
        self, household_id: int, user_id: int, new_role: str, updated_by: int
    ) -> bool:
        """Update member role with validation"""

        # Check permissions (only admin can change roles)
        updater_membership = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == updated_by,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                    HouseholdMembership.role == "admin",
                )
            )
            .first()
        )

        if not updater_membership:
            raise ValueError("Only admins can update member roles")

        # Find target membership
        membership = (
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

        if not membership:
            raise ValueError("User is not a member of this household")

        # Prevent removing admin role if it's the last admin
        if membership.role == "admin" and new_role != "admin":
            admin_count = (
                self.db.query(HouseholdMembership)
                .filter(
                    and_(
                        HouseholdMembership.household_id == household_id,
                        HouseholdMembership.role == "admin",
                        HouseholdMembership.is_active == True,
                    )
                )
                .count()
            )

            if admin_count <= 1:
                raise ValueError("Cannot remove admin role from the last admin")

        # Update role
        membership.role = new_role

        # Update user table for consistency
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.household_role = new_role

        self.db.commit()
        return True

    def get_household_members(self, household_id: int) -> List[Dict[str, Any]]:
        """Get all members using HouseholdMembership model"""

        # Join User and HouseholdMembership for efficient querying
        members_query = (
            self.db.query(User, HouseholdMembership)
            .join(HouseholdMembership, User.id == HouseholdMembership.user_id)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .order_by(HouseholdMembership.role.desc(), User.name)  # Admins first
        )

        result = []
        for user, membership in members_query:
            # Get member statistics
            stats = self._get_member_statistics(user.id)

            result.append(
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "is_active": user.is_active,
                    "joined_at": membership.joined_at,
                    "role": membership.role,
                    "statistics": stats,
                    "phone": user.phone,
                }
            )

        return result

    def get_household_details(self, household_id: int) -> Dict[str, Any]:
        """Get detailed household information"""

        household = (
            self.db.query(Household).filter(Household.id == household_id).first()
        )
        if not household:
            raise ValueError("Household not found")

        members = self.get_household_members(household_id)
        health_score = self.calculate_household_health_score(household_id)
        statistics = self.get_household_statistics(household_id)

        # Count active vs inactive members
        active_members = [m for m in members if m["is_active"]]
        admin_count = len([m for m in members if m["role"] == "admin"])

        return {
            "id": household.id,
            "name": household.name,
            "address": household.address,
            "house_rules": household.house_rules,
            "settings": household.settings or {},
            "created_at": household.created_at,
            "member_count": len(active_members),
            "admin_count": admin_count,
            "members": members,
            "health_score": health_score,
            "statistics": statistics,
        }

    def update_household_settings(
        self, household_id: int, settings_update: HouseholdUpdate, updated_by: int
    ) -> Household:
        """Update household settings with permission check"""

        # Check permissions (only admin can update settings)
        updater_membership = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == updated_by,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                    HouseholdMembership.role == "admin",
                )
            )
            .first()
        )

        if not updater_membership:
            raise ValueError("Only admins can update household settings")

        household = (
            self.db.query(Household).filter(Household.id == household_id).first()
        )
        if not household:
            raise ValueError("Household not found")

        # Update fields
        for field, value in settings_update.dict(exclude_unset=True).items():
            setattr(household, field, value)

        household.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(household)

        return household

    def check_admin_permissions(self, user_id: int, household_id: int) -> bool:
        """Check if user has admin permissions for household"""

        membership = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                    HouseholdMembership.role == "admin",
                )
            )
            .first()
        )

        return membership is not None

    def get_user_household_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's current household information"""

        membership = (
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

        if not membership:
            return None

        membership_obj, household = membership

        return {
            "household_id": household.id,
            "household_name": household.name,
            "user_role": membership_obj.role,
            "joined_at": membership_obj.joined_at,
            "is_admin": membership_obj.role == "admin",
        }

    def calculate_household_health_score(self, household_id: int) -> Dict[str, Any]:
        """Calculate overall household health score"""

        now = datetime.utcnow()
        last_month = now - timedelta(days=30)

        # Financial health (40% weight)
        financial_score = self._calculate_financial_health(household_id, last_month)

        # Task completion health (30% weight)
        task_score = self._calculate_task_health(household_id, last_month)

        # Communication activity (20% weight)
        communication_score = self._calculate_communication_health(
            household_id, last_month
        )

        # Member satisfaction (10% weight) - enhanced
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

    def _get_member_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a household member"""

        now = datetime.utcnow()
        last_month = now - timedelta(days=30)

        # Task statistics
        tasks_assigned = (
            self.db.query(Task)
            .filter(and_(Task.assigned_to == user_id, Task.created_at >= last_month))
            .count()
        )

        tasks_completed = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.completed == True,
                    Task.completed_at >= last_month,
                )
            )
            .count()
        )

        # Points earned
        points_earned = (
            self.db.query(func.sum(Task.points))
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.completed == True,
                    Task.completed_at >= last_month,
                )
            )
            .scalar()
            or 0
        )

        # Expense statistics
        expenses_created = (
            self.db.query(Expense)
            .filter(
                and_(Expense.created_by == user_id, Expense.created_at >= last_month)
            )
            .count()
        )

        total_expenses_amount = (
            self.db.query(func.sum(Expense.amount))
            .filter(
                and_(Expense.created_by == user_id, Expense.created_at >= last_month)
            )
            .scalar()
            or 0
        )

        return {
            "tasks_assigned_last_month": tasks_assigned,
            "tasks_completed_last_month": tasks_completed,
            "completion_rate": round(
                (tasks_completed / tasks_assigned * 100) if tasks_assigned > 0 else 0, 1
            ),
            "points_earned_last_month": int(points_earned),
            "expenses_created_last_month": expenses_created,
            "total_expenses_amount_last_month": float(total_expenses_amount),
        }

    def get_household_statistics(self, household_id: int) -> Dict[str, Any]:
        """Get comprehensive household statistics"""

        now = datetime.utcnow()
        last_month = now - timedelta(days=30)

        # Financial stats
        total_expenses = (
            self.db.query(func.sum(Expense.amount))
            .filter(
                and_(
                    Expense.household_id == household_id,
                    Expense.created_at >= last_month,
                )
            )
            .scalar()
            or 0
        )

        expense_count = (
            self.db.query(Expense)
            .filter(
                and_(
                    Expense.household_id == household_id,
                    Expense.created_at >= last_month,
                )
            )
            .count()
        )

        # Task stats
        total_tasks = (
            self.db.query(Task).filter(Task.household_id == household_id).count()
        )

        completed_tasks = (
            self.db.query(Task)
            .filter(and_(Task.household_id == household_id, Task.completed == True))
            .count()
        )

        overdue_tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.household_id == household_id,
                    Task.completed == False,
                    Task.due_date < now,
                )
            )
            .count()
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

        # Member stats
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

        # Household age
        household = (
            self.db.query(Household).filter(Household.id == household_id).first()
        )
        household_age_days = (now - household.created_at).days if household else 0

        return {
            "total_monthly_expenses": float(total_expenses),
            "expense_count_last_month": expense_count,
            "average_expense_amount": (
                float(total_expenses / expense_count) if expense_count > 0 else 0
            ),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "task_completion_rate": round(
                (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1
            ),
            "upcoming_events": upcoming_events,
            "active_members": active_members,
            "household_age_days": household_age_days,
        }
