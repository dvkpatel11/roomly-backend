from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.household import Household
from ..models.user import User
from ..models.expense import Expense
from ..models.task import Task
from ..models.event import Event
from ..schemas.household import HouseholdCreate, HouseholdUpdate

class HouseholdService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_household(
        self, 
        household_data: HouseholdCreate, 
        creator_id: int
    ) -> Household:
        """Create a new household"""
        
        household = Household(
            name=household_data.name,
            address=household_data.address,
            house_rules=household_data.house_rules
        )
        
        self.db.add(household)
        self.db.commit()
        self.db.refresh(household)
        
        # Add creator as admin
        creator = self.db.query(User).filter(User.id == creator_id).first()
        if creator:
            creator.household_id = household.id
            # You might want to add a role field to User model
            self.db.commit()
        
        return household
    
    def add_member_to_household(
        self, 
        household_id: int, 
        user_id: int,
        role: str = "member"
    ) -> bool:
        """Add a user to household"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        if user.household_id:
            return False  # User already in a household
        
        user.household_id = household_id
        self.db.commit()
        
        return True
    
    def remove_member_from_household(
        self, 
        household_id: int, 
        user_id: int,
        removed_by: int
    ) -> bool:
        """Remove a user from household"""
        
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.household_id == household_id
            )
        ).first()
        
        if not user:
            return False
        
        # Check if user has pending responsibilities
        pending_tasks = self.db.query(Task).filter(
            and_(
                Task.assigned_to == user_id,
                Task.completed == False
            )
        ).count()
        
        if pending_tasks > 0:
            # You might want to reassign tasks or require completion first
            pass
        
        user.household_id = None
        user.is_active = False
        self.db.commit()
        
        return True
    
    def get_household_members(self, household_id: int) -> List[Dict[str, Any]]:
        """Get all members of a household"""
        
        members = self.db.query(User).filter(
            User.household_id == household_id
        ).order_by(User.name).all()
        
        result = []
        for member in members:
            # Get member statistics
            stats = self._get_member_statistics(member.id)
            
            result.append({
                "id": member.id,
                "name": member.name,
                "email": member.email,
                "is_active": member.is_active,
                "joined_at": member.created_at,
                "role": "admin" if member.id == self._get_household_admin(household_id) else "member",
                "statistics": stats
            })
        
        return result
    
    def get_household_details(self, household_id: int) -> Dict[str, Any]:
        """Get detailed household information"""
        
        household = self.db.query(Household).filter(Household.id == household_id).first()
        if not household:
            raise ValueError("Household not found")
        
        members = self.get_household_members(household_id)
        health_score = self.calculate_household_health_score(household_id)
        statistics = self.get_household_statistics(household_id)
        
        return {
            "id": household.id,
            "name": household.name,
            "address": household.address,
            "house_rules": household.house_rules,
            "created_at": household.created_at,
            "member_count": len([m for m in members if m["is_active"]]),
            "members": members,
            "health_score": health_score,
            "statistics": statistics
        }
    
    def update_household_settings(
        self, 
        household_id: int, 
        settings_update: HouseholdUpdate
    ) -> Household:
        """Update household settings"""
        
        household = self.db.query(Household).filter(Household.id == household_id).first()
        if not household:
            raise ValueError("Household not found")
        
        # Update fields
        for field, value in settings_update.dict(exclude_unset=True).items():
            setattr(household, field, value)
        
        self.db.commit()
        self.db.refresh(household)
        
        return household
    
    def calculate_household_health_score(self, household_id: int) -> Dict[str, Any]:
        """Calculate overall household health score"""
        
        now = datetime.utcnow()
        last_month = now - timedelta(days=30)
        
        # Financial health (40% weight)
        financial_score = self._calculate_financial_health(household_id, last_month)
        
        # Task completion health (30% weight)
        task_score = self._calculate_task_health(household_id, last_month)
        
        # Communication activity (20% weight)
        communication_score = self._calculate_communication_health(household_id, last_month)
        
        # Member satisfaction (10% weight) - simplified
        member_score = self._calculate_member_satisfaction(household_id)
        
        # Weighted overall score
        overall_score = (
            financial_score * 0.4 +
            task_score * 0.3 +
            communication_score * 0.2 +
            member_score * 0.1
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
            "last_calculated": now
        }
    
    def _calculate_financial_health(self, household_id: int, since_date: datetime) -> float:
        """Calculate financial health score"""
        
        # Get recent expenses
        expenses = self.db.query(Expense).filter(
            and_(
                Expense.household_id == household_id,
                Expense.created_at >= since_date
            )
        ).all()
        
        if not expenses:
            return 85  # Neutral score for no activity
        
        total_expenses = len(expenses)
        fully_paid_expenses = 0
        
        for expense in expenses:
            if expense.split_details and expense.split_details.get("all_paid"):
                fully_paid_expenses += 1
        
        payment_rate = (fully_paid_expenses / total_expenses) * 100 if total_expenses > 0 else 85
        
        # Adjust score based on overdue payments
        overdue_count = total_expenses - fully_paid_expenses
        if overdue_count > 5:
            payment_rate -= 20
        elif overdue_count > 2:
            payment_rate -= 10
        
        return max(0, min(100, payment_rate))
    
    def _calculate_task_health(self, household_id: int, since_date: datetime) -> float:
        """Calculate task completion health score"""
        
        tasks = self.db.query(Task).filter(
            and_(
                Task.household_id == household_id,
                Task.created_at >= since_date
            )
        ).all()
        
        if not tasks:
            return 80  # Neutral score for no activity
        
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.completed])
        overdue_tasks = len([t for t in tasks if not t.completed and t.due_date and t.due_date < datetime.utcnow()])
        
        completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 80
        
        # Penalty for overdue tasks
        if overdue_tasks > 0:
            completion_rate -= (overdue_tasks / total_tasks) * 30
        
        return max(0, min(100, completion_rate))
    
    def _calculate_communication_health(self, household_id: int, since_date: datetime) -> float:
        """Calculate communication activity score"""
        
        # This would integrate with communication service
        # For now, simplified logic
        
        from ..models.announcement import Announcement
        
        recent_announcements = self.db.query(Announcement).filter(
            and_(
                Announcement.household_id == household_id,
                Announcement.created_at >= since_date
            )
        ).count()
        
        # Score based on communication activity
        if recent_announcements >= 5:
            return 90
        elif recent_announcements >= 2:
            return 75
        elif recent_announcements >= 1:
            return 60
        else:
            return 40
    
    def _calculate_member_satisfaction(self, household_id: int) -> float:
        """Calculate member satisfaction score"""
        
        # Simplified satisfaction score based on activity
        active_members = self.db.query(User).filter(
            and_(
                User.household_id == household_id,
                User.is_active == True
            )
        ).count()
        
        # More members generally indicates better satisfaction
        if active_members >= 4:
            return 85
        elif active_members >= 2:
            return 75
        else:
            return 60
    
    def _generate_improvement_suggestions(
        self, 
        financial: float, 
        task: float, 
        communication: float, 
        member: float
    ) -> List[str]:
        """Generate improvement suggestions based on scores"""
        
        suggestions = []
        
        if financial < 70:
            suggestions.append("Improve payment tracking - set up automatic reminders for overdue expenses")
        
        if task < 70:
            suggestions.append("Increase task completion rate - consider adjusting task assignments or deadlines")
        
        if communication < 60:
            suggestions.append("Boost household communication - try weekly announcements or house meetings")
        
        if member < 70:
            suggestions.append("Focus on member engagement - consider fun events or better task distribution")
        
        if not suggestions:
            suggestions.append("Great work! Your household is running smoothly")
        
        return suggestions
    
    def _get_member_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a household member"""
        
        now = datetime.utcnow()
        last_month = now - timedelta(days=30)
        
        # Task statistics
        tasks_assigned = self.db.query(Task).filter(
            and_(
                Task.assigned_to == user_id,
                Task.created_at >= last_month
            )
        ).count()
        
        tasks_completed = self.db.query(Task).filter(
            and_(
                Task.assigned_to == user_id,
                Task.completed == True,
                Task.completed_at >= last_month
            )
        ).count()
        
        # Expense statistics
        expenses_created = self.db.query(Expense).filter(
            and_(
                Expense.created_by == user_id,
                Expense.created_at >= last_month
            )
        ).count()
        
        return {
            "tasks_assigned_last_month": tasks_assigned,
            "tasks_completed_last_month": tasks_completed,
            "completion_rate": (tasks_completed / tasks_assigned * 100) if tasks_assigned > 0 else 0,
            "expenses_created_last_month": expenses_created
        }
    
    def _get_household_admin(self, household_id: int) -> Optional[int]:
        """Get household admin user ID (simplified - first member)"""
        
        admin = self.db.query(User).filter(
            User.household_id == household_id
        ).order_by(User.created_at).first()
        
        return admin.id if admin else None
    
    def get_household_statistics(self, household_id: int) -> Dict[str, Any]:
        """Get comprehensive household statistics"""
        
        now = datetime.utcnow()
        last_month = now - timedelta(days=30)
        
        # Financial stats
        total_expenses = self.db.query(func.sum(Expense.amount)).filter(
            and_(
                Expense.household_id == household_id,
                Expense.created_at >= last_month
            )
        ).scalar() or 0
        
        # Task stats
        total_tasks = self.db.query(Task).filter(
            Task.household_id == household_id
        ).count()
        
        completed_tasks = self.db.query(Task).filter(
            and_(
                Task.household_id == household_id,
                Task.completed == True
            )
        ).count()
        
        # Event stats
        upcoming_events = self.db.query(Event).filter(
            and_(
                Event.household_id == household_id,
                Event.start_date >= now,
                Event.status == "published"
            )
        ).count()
        
        return {
            "total_monthly_expenses": total_expenses,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "task_completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "upcoming_events": upcoming_events,
            "household_age_days": (now - self.db.query(Household).filter(Household.id == household_id).first().created_at).days
        }
