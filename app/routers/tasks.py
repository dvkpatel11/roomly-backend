from app.models.enums import TaskStatus
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..services.task_service import TaskService
from ..schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskComplete,
    TaskResponse,
    TaskLeaderboard,
    TaskPriority,
)
from .auth import get_current_user
from ..models.user import User

router = APIRouter()


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new task with automatic rotation assignment"""
    try:
        task_service = TaskService(db)
        task = task_service.create_task_with_rotation(
            task_data=task_data,
            household_id=current_user.household_id,
            created_by=current_user.id,
        )
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=Dict[str, List[TaskResponse]])
async def get_tasks(
    status: Optional[TaskStatus] = None,
    assigned_to: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get household tasks with filtering"""
    task_service = TaskService(db)

    # Add method to TaskService
    tasks = (
        []
    )  # task_service.get_household_tasks(current_user.household_id, status, assigned_to, skip, limit)

    return {"tasks": tasks}


@router.get("/my-tasks")
async def get_my_tasks(
    include_completed: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get tasks assigned to current user"""
    task_service = TaskService(db)

    # Add method to TaskService
    tasks = []  # task_service.get_user_tasks(current_user.id, include_completed)

    return {"my_tasks": tasks}


@router.put("/{task_id}/complete")
async def complete_task(
    task_id: int,
    completion_data: TaskComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark task as completed"""
    try:
        task_service = TaskService(db)
        task = task_service.complete_task(
            task_id=task_id, user_id=current_user.id, completion_data=completion_data
        )
        return {"message": "Task completed successfully", "points_earned": task.points}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{task_id}/reassign")
async def reassign_task(
    task_id: int,
    new_assignee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reassign task to different user"""
    try:
        task_service = TaskService(db)
        task = task_service.reassign_task(
            task_id=task_id,
            new_assignee_id=new_assignee_id,
            reassigned_by=current_user.id,
        )
        return {"message": "Task reassigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/leaderboard")
async def get_task_leaderboard(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get task completion leaderboard"""
    task_service = TaskService(db)

    leaderboard = task_service.get_household_leaderboard(
        household_id=current_user.household_id, month=month, year=year
    )

    return {"leaderboard": leaderboard}


@router.get("/my-score")
async def get_my_task_score(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's task score"""
    task_service = TaskService(db)

    score = task_service.get_user_task_score(
        user_id=current_user.id, month=month, year=year
    )

    return score


@router.get("/overdue")
async def get_overdue_tasks(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get overdue tasks for reminder system"""
    task_service = TaskService(db)

    overdue_tasks = task_service.get_overdue_tasks_for_reminders()

    # Filter for current household
    household_overdue = [
        task for task in overdue_tasks if task.household_id == current_user.household_id
    ]

    return {"overdue_tasks": household_overdue}


@router.post("/reset-monthly-points")
async def reset_monthly_points(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Reset monthly points (admin only)"""
    # Add admin check here
    task_service = TaskService(db)

    task_service.reset_monthly_points(current_user.household_id)

    return {"message": "Monthly points reset successfully"}
