from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.task import Task
from ..models.user import User
from ..schemas.task import TaskCreate, TaskUpdate, TaskComplete, RecurrencePattern
import calendar

class TaskService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_task_with_rotation(
        self, 
        task_data: TaskCreate, 
        household_id: int, 
        created_by: int
    ) -> Task:
        """Create task with automatic rotation assignment if not specified"""
        
        # If assigned_to not specified, use rotation
        if not task_data.assigned_to:
            assigned_to = self._get_next_assignee(household_id)
        else:
            assigned_to = task_data.assigned_to
        
        # Check for conflicts (same person, same day, same type of task)
        if task_data.due_date and self._has_task_conflict(assigned_to, task_data.due_date):
            # Try next person in rotation
            assigned_to = self._get_next_assignee(household_id, exclude_user_id=assigned_to)
        
        task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority.value,
            estimated_duration=task_data.estimated_duration,
            points=task_data.points,
            assigned_to=assigned_to,
            created_by=created_by,
            household_id=household_id,
            due_date=task_data.due_date,
            recurring=task_data.recurring,
            recurrence_pattern=task_data.recurrence_pattern.value if task_data.recurrence_pattern else None
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        # Create recurring instances if needed
        if task.recurring and task.recurrence_pattern:
            self._create_recurring_instances(task)
        
        return task
    
    def _get_next_assignee(self, household_id: int, exclude_user_id: int = None) -> int:
        """Get next person in rotation using round-robin algorithm"""
        
        # Get all active household members
        query = self.db.query(User).filter(
            User.household_id == household_id,
            User.is_active == True
        )
        
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        
        members = query.order_by(User.id).all()
        
        if not members:
            raise ValueError("No active household members found")
        
        # Get the last assigned task to determine rotation position
        last_task = self.db.query(Task).filter(
            Task.household_id == household_id
        ).order_by(Task.created_at.desc()).first()
        
        if not last_task:
            # First task, assign to first member
            return members[0].id
        
        # Find current assignee position and get next
        current_assignee_index = 0
        for i, member in enumerate(members):
            if member.id == last_task.assigned_to:
                current_assignee_index = i
                break
        
        # Round-robin: next person in list, wrap to start if at end
        next_index = (current_assignee_index + 1) % len(members)
        return members[next_index].id
    
    def _has_task_conflict(self, user_id: int, due_date: datetime) -> bool:
        """Check if user already has a task due on the same day"""
        
        if not due_date:
            return False
        
        start_of_day = due_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        existing_task = self.db.query(Task).filter(
            and_(
                Task.assigned_to == user_id,
                Task.due_date >= start_of_day,
                Task.due_date < end_of_day,
                Task.completed == False
            )
        ).first()
        
        return existing_task is not None
    
    def complete_task(
        self, 
        task_id: int, 
        user_id: int, 
        completion_data: TaskComplete
    ) -> Task:
        """Mark task as completed and award points"""
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        if task.assigned_to != user_id:
            raise ValueError("Only assigned user can complete this task")
        
        if task.completed:
            raise ValueError("Task already completed")
        
        # Mark as completed
        task.completed = True
        task.completed_at = datetime.utcnow()
        task.completion_notes = completion_data.completion_notes
        task.photo_proof_url = completion_data.photo_proof_url
        
        # Award points (handled by point system)
        self._award_points(user_id, task.points)
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def _award_points(self, user_id: int, points: int):
        """Award points to user (stored in user profile or separate points table)"""
        # For now, we'll track this in the task completion
        # In a more complex system, you'd have a separate UserPoints table
        pass
    
    def get_user_task_score(self, user_id: int, month: int = None, year: int = None) -> Dict[str, Any]:
        """Calculate user's task score for the specified month/year"""
        
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
        
        # Get completed tasks for the month
        completed_tasks = self.db.query(Task).filter(
            and_(
                Task.assigned_to == user_id,
                Task.completed == True,
                Task.completed_at >= start_date,
                Task.completed_at < end_date
            )
        ).all()
        
        # Get assigned tasks for the month (for completion rate)
        assigned_tasks = self.db.query(Task).filter(
            and_(
                Task.assigned_to == user_id,
                Task.created_at >= start_date,
                Task.created_at < end_date
            )
        ).all()
        
        total_points = sum(task.points for task in completed_tasks)
        tasks_completed = len(completed_tasks)
        tasks_assigned = len(assigned_tasks)
        completion_rate = (tasks_completed / tasks_assigned * 100) if tasks_assigned > 0 else 0
        
        # Calculate streak (consecutive days with completed tasks)
        streak = self._calculate_completion_streak(user_id)
        
        return {
            "user_id": user_id,
            "month": month,
            "year": year,
            "total_points": total_points,
            "tasks_completed": tasks_completed,
            "tasks_assigned": tasks_assigned,
            "completion_rate": round(completion_rate, 1),
            "current_streak": streak,
            "overdue_tasks": self._count_overdue_tasks(user_id)
        }
    
    def get_household_leaderboard(self, household_id: int, month: int = None, year: int = None) -> List[Dict[str, Any]]:
        """Get task completion leaderboard for household"""
        
        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year
        
        members = self.db.query(User).filter(
            User.household_id == household_id,
            User.is_active == True
        ).all()
        
        leaderboard = []
        for member in members:
            score = self.get_user_task_score(member.id, month, year)
            score["user_name"] = member.name
            leaderboard.append(score)
        
        # Sort by points (descending), then by completion rate
        leaderboard.sort(key=lambda x: (x["total_points"], x["completion_rate"]), reverse=True)
        
        # Add rankings
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1
        
        return leaderboard
    
    def reset_monthly_points(self, household_id: int):
        """Reset points for new month (called by scheduler)"""
        # This would typically update a separate points tracking table
        # For now, points are inherent in task completion history
        pass
    
    def _calculate_completion_streak(self, user_id: int) -> int:
        """Calculate consecutive days with completed tasks"""
        
        today = datetime.now().date()
        streak = 0
        current_date = today
        
        # Look back day by day to find consecutive completion days
        for _ in range(30):  # Check last 30 days max
            start_of_day = datetime.combine(current_date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)
            
            completed_today = self.db.query(Task).filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.completed == True,
                    Task.completed_at >= start_of_day,
                    Task.completed_at < end_of_day
                )
            ).first()
            
            if completed_today:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        return streak
    
    def _count_overdue_tasks(self, user_id: int) -> int:
        """Count overdue tasks for user"""
        
        now = datetime.utcnow()
        return self.db.query(Task).filter(
            and_(
                Task.assigned_to == user_id,
                Task.completed == False,
                Task.due_date < now
            )
        ).count()
    
    def _create_recurring_instances(self, task: Task):
        """Create future instances of recurring tasks"""
        
        if not task.due_date or not task.recurrence_pattern:
            return
        
        # Create next 3 months of instances
        instances_to_create = 12  # 3 months worth for weekly/monthly tasks
        
        current_date = task.due_date
        
        for i in range(instances_to_create):
            if task.recurrence_pattern == RecurrencePattern.DAILY:
                next_date = current_date + timedelta(days=1)
            elif task.recurrence_pattern == RecurrencePattern.WEEKLY:
                next_date = current_date + timedelta(weeks=1)
            elif task.recurrence_pattern == RecurrencePattern.BIWEEKLY:
                next_date = current_date + timedelta(weeks=2)
            elif task.recurrence_pattern == RecurrencePattern.MONTHLY:
                # Add one month
                if current_date.month == 12:
                    next_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    next_date = current_date.replace(month=current_date.month + 1)
            else:
                break
            
            # Get next assignee in rotation
            next_assignee = self._get_next_assignee(task.household_id)
            
            # Create recurring task instance
            recurring_task = Task(
                title=task.title,
                description=task.description,
                priority=task.priority,
                estimated_duration=task.estimated_duration,
                points=task.points,
                assigned_to=next_assignee,
                created_by=task.created_by,
                household_id=task.household_id,
                due_date=next_date,
                recurring=True,
                recurrence_pattern=task.recurrence_pattern
            )
            
            self.db.add(recurring_task)
            current_date = next_date
        
        self.db.commit()
    
    def get_overdue_tasks_for_reminders(self) -> List[Task]:
        """Get all overdue tasks that need reminders"""
        
        now = datetime.utcnow()
        return self.db.query(Task).filter(
            and_(
                Task.completed == False,
                Task.due_date < now
            )
        ).all()
    
    def reassign_task(self, task_id: int, new_assignee_id: int, reassigned_by: int) -> Task:
        """Reassign task to different user"""
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        if task.completed:
            raise ValueError("Cannot reassign completed task")
        
        task.assigned_to = new_assignee_id
        # Could track reassignment history if needed
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
