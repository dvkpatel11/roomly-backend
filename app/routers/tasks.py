from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
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
)
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    create_pagination_response,
)
from ..models.user import User
from ..models.enums import TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def create_task(
    task_data: TaskCreate,
    use_rotation: bool = Query(
        True, description="Use automatic rotation for assignment"
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new task with automatic rotation assignment"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.create_task(
        task_data=task_data,
        household_id=household_id,
        created_by=current_user.id,
        use_rotation=use_rotation,
    )
    return task


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    assigned_to: Optional[int] = Query(None, description="Filter by assignee"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    overdue_only: bool = Query(False, description="Show only overdue tasks"),
    limit: int = Query(50, le=100, description="Number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household tasks with filtering and pagination"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    tasks = task_service.get_household_tasks(
        household_id=household_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status,
        assigned_to=assigned_to,
        priority=priority,
        overdue_only=overdue_only,
    )
    return tasks


@router.get("/my-tasks", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_tasks(
    include_completed: bool = Query(False, description="Include completed tasks"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive summary of tasks assigned to current user"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    summary = task_service.get_user_task_summary(
        user_id=current_user.id, household_id=household_id
    )
    return summary


@router.get("/{task_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_task_details(
    task_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get specific task details with all related information"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    # Get the specific task - this should be a proper service method
    # For now, we'll use the existing method and filter
    tasks_response = task_service.get_household_tasks(
        household_id=household_id,
        user_id=current_user.id,
        limit=1000,  # Get all tasks to find the specific one
        offset=0,
    )

    task = next((t for t in tasks_response["tasks"] if t["id"] == task_id), None)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Add additional task details that might not be in the list view
    task_details = {
        "task": task,
        "can_edit": current_user.id == task["assigned_to"]
        or current_user.id == task["created_by"],
        "can_complete": current_user.id == task["assigned_to"],
        "can_reassign": current_user.id == task["created_by"],
    }

    return task_details


@router.put("/{task_id}", response_model=TaskResponse)
@handle_service_errors
async def update_task(
    task_id: int,
    task_updates: TaskUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update task details"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.update_task(
        task_id=task_id, task_updates=task_updates, updated_by=current_user.id
    )
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Delete a task"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task_service.delete_task(task_id=task_id, deleted_by=current_user.id)


@router.put("/{task_id}/complete", response_model=Dict[str, Any])
@handle_service_errors
async def complete_task(
    task_id: int,
    completion_data: TaskComplete,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Mark task as completed and award points"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.complete_task(
        task_id=task_id, user_id=current_user.id, completion_data=completion_data
    )

    return RouterResponse.success(
        {
            "task": task,
            "points_earned": task.points,
            "completion_time": task.completed_at,
        },
        "Task completed successfully",
    )


@router.put("/{task_id}/status", response_model=TaskResponse)
@handle_service_errors
async def update_task_status(
    task_id: int,
    new_status: TaskStatus,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update task status"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.update_task_status(
        task_id=task_id, new_status=new_status.value, user_id=current_user.id
    )
    return task


@router.put("/{task_id}/reassign", response_model=TaskResponse)
@handle_service_errors
async def reassign_task(
    task_id: int,
    new_assignee_id: int = Body(..., description="ID of the new assignee"),
    reason: Optional[str] = Body(None, description="Reason for reassignment"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Reassign task to different user"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.reassign_task(
        task_id=task_id,
        new_assignee_id=new_assignee_id,
        reassigned_by=current_user.id,
    )
    return task


@router.get("/leaderboard/current", response_model=List[Dict[str, Any]])
@handle_service_errors
async def get_task_leaderboard(
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (1-12)"),
    year: Optional[int] = Query(None, ge=2020, le=2030, description="Year"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get task completion leaderboard for household"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    leaderboard = task_service.get_household_leaderboard(
        household_id=household_id, user_id=current_user.id, month=month, year=year
    )
    return leaderboard


@router.get("/user/score", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_task_score(
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (1-12)"),
    year: Optional[int] = Query(None, ge=2020, le=2030, description="Year"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get current user's task score and statistics"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    score = task_service.get_user_task_score(
        user_id=current_user.id, household_id=household_id, month=month, year=year
    )
    return score


@router.get("/rotation/schedule", response_model=Dict[str, Any])
@handle_service_errors
async def get_rotation_schedule(
    weeks_ahead: int = Query(4, ge=1, le=12, description="Weeks to show"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get upcoming task rotation schedule for planning"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    schedule = task_service.get_rotation_schedule(
        household_id=household_id, user_id=current_user.id, weeks_ahead=weeks_ahead
    )
    return schedule


@router.get("/overdue/all", response_model=Dict[str, Any])
@handle_service_errors
async def get_all_overdue_tasks(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get all overdue tasks for the household"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    overdue_tasks = task_service.get_overdue_tasks_for_reminders(
        household_id=household_id
    )
    return {"overdue_tasks": overdue_tasks}


@router.get("/categories", response_model=List[Dict[str, str]])
async def get_task_priorities():
    """Get available task priority levels"""
    from ..schemas.task import TaskPriority

    priorities = [
        {"value": priority.value, "label": priority.value.replace("_", " ").title()}
        for priority in TaskPriority
    ]
    return priorities


@router.get("/statuses", response_model=List[Dict[str, str]])
async def get_task_statuses():
    """Get available task status options"""
    from ..models.enums import TaskStatus

    statuses = [
        {"value": status.value, "label": status.value.replace("_", " ").title()}
        for status in TaskStatus
    ]
    return statuses


@router.post("/bulk-assign", response_model=Dict[str, Any])
@handle_service_errors
async def bulk_assign_tasks(
    task_ids: List[int] = Body(..., description="List of task IDs to reassign"),
    new_assignee_id: int = Body(..., description="ID of the new assignee"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Bulk reassign multiple tasks to a user (admin only)"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    updated_tasks = []
    failed_tasks = []

    for task_id in task_ids:
        try:
            task = task_service.reassign_task(
                task_id=task_id,
                new_assignee_id=new_assignee_id,
                reassigned_by=current_user.id,
            )
            updated_tasks.append({"task_id": task_id, "success": True})
        except Exception as e:
            failed_tasks.append({"task_id": task_id, "error": str(e)})

    return {
        "message": f"Bulk assignment completed",
        "updated_count": len(updated_tasks),
        "failed_count": len(failed_tasks),
        "updated_tasks": updated_tasks,
        "failed_tasks": failed_tasks,
    }


# Admin-only endpoints
@router.post("/admin/reset-points", response_model=Dict[str, Any])
@handle_service_errors
async def reset_monthly_points(
    confirm: bool = Body(False, description="Confirmation flag"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Reset monthly points for all household members (admin only)"""
    current_user, household_id = user_household

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must confirm point reset by setting confirm=true",
        )

    # This would need to be implemented in TaskService
    return RouterResponse.success(
        message="Monthly points reset functionality not yet implemented",
        data={"household_id": household_id, "reset_by": current_user.id},
    )


@router.get("/statistics/household", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_task_statistics(
    months_back: int = Query(6, ge=1, le=24, description="Months of data to analyze"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive task statistics for household"""
    current_user, household_id = user_household

    # Get basic stats using existing methods
    task_service = TaskService(db)

    # Get leaderboard for current month
    leaderboard = task_service.get_household_leaderboard(
        household_id=household_id, user_id=current_user.id
    )

    # Get overdue tasks
    overdue_tasks = task_service.get_overdue_tasks_for_reminders(household_id)

    # Calculate basic statistics
    total_members = len(leaderboard) if leaderboard else 0
    total_completed_tasks = sum(
        entry.get("tasks_completed", 0) for entry in leaderboard
    )
    total_points = sum(entry.get("total_points", 0) for entry in leaderboard)
    avg_completion_rate = (
        sum(entry.get("completion_rate", 0) for entry in leaderboard) / total_members
        if total_members > 0
        else 0
    )

    return {
        "household_id": household_id,
        "period_months": months_back,
        "total_members": total_members,
        "total_completed_tasks": total_completed_tasks,
        "total_points_awarded": total_points,
        "average_completion_rate": round(avg_completion_rate, 1),
        "overdue_tasks_count": len(overdue_tasks),
        "leaderboard_preview": leaderboard[:3],  # Top 3
        "most_productive_member": leaderboard[0] if leaderboard else None,
        "generated_at": "2024-01-01T00:00:00Z",  # This would be datetime.utcnow()
    }
