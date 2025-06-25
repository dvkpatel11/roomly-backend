from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from ..database import get_db
from ..services.task_service import TaskService
from ..schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskComplete,
    TaskResponse,
)
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    validate_pagination,
)
from ..models.user import User
from ..models.enums import TaskStatus
from ..utils.constants import AppConstants

router = APIRouter(tags=["tasks"])


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
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household tasks with filtering and pagination"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    result = task_service.get_household_tasks(
        household_id=household_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status,
        assigned_to=assigned_to,
        priority=priority,
        overdue_only=overdue_only,
    )

    return RouterResponse.success(data=result)


@router.get("/me", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_task_summary(
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

    return RouterResponse.success(data=summary)


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

    try:
        # Get specific task using the internal method (needs to be added to service)
        task = task_service._get_task_or_raise(task_id)

        # Verify user has access to this task's household
        if task.household_id != household_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this task",
            )

        # Build detailed response
        task_details = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "assigned_to": task.assigned_to,
            "created_by": task.created_by,
            "due_date": task.due_date,
            "estimated_duration": task.estimated_duration,
            "recurring": task.recurring,
            "recurrence_pattern": task.recurrence_pattern,
            "completion_notes": task.completion_notes,
            "photo_proof_url": task.photo_proof_url,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
            # Permission flags
            "can_edit": (
                current_user.id == task.assigned_to
                or current_user.id == task.created_by
            ),
            "can_complete": current_user.id == task.assigned_to,
            "can_reassign": current_user.id == task.created_by,
        }

        return RouterResponse.success(data={"task": task_details})

    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        raise


@router.put("/{task_id}", response_model=Dict[str, Any])
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

    return RouterResponse.updated(data={"task": task})


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
    """Mark task as completed"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.complete_task(
        task_id=task_id, user_id=current_user.id, completion_data=completion_data
    )

    return RouterResponse.success(
        data={
            "task": {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "completed_at": task.completed_at,
            },
            "completion_time": task.completed_at,
        },
        message="Task completed successfully",
    )


@router.put("/{task_id}/status", response_model=Dict[str, Any])
@handle_service_errors
async def update_task_status(
    task_id: int,
    status_data: Dict[str, str] = Body(..., example={"status": "in_progress"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update task status"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.update_task_status(
        task_id=task_id,
        user_id=current_user.id,
        **status_data,
    )

    return RouterResponse.updated(data={"task": task})


@router.put("/{task_id}/reassign", response_model=Dict[str, Any])
@handle_service_errors
async def reassign_task(
    task_id: int,
    reassign_data: Dict[str, Any] = Body(
        ..., example={"new_assignee_id": 2, "reason": "Better availability"}
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Reassign task to different user"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    new_assignee_id = reassign_data.get("new_assignee_id")
    if not new_assignee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_assignee_id is required",
        )

    task = task_service.reassign_task(
        task_id=task_id,
        new_assignee_id=new_assignee_id,
        reassigned_by=current_user.id,
    )

    return RouterResponse.updated(
        data={"task": task}, message=f"Task reassigned successfully"
    )


@router.get("/leaderboard/current", response_model=Dict[str, Any])
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

    return RouterResponse.success(
        data={
            "leaderboard": leaderboard,
            "month": month,
            "year": year,
            "total_members": len(leaderboard),
        }
    )


@router.get("/me/score", response_model=Dict[str, Any])
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

    return RouterResponse.success(data=score)


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

    return RouterResponse.success(data=schedule)


@router.get("/overdue", response_model=Dict[str, Any])
@handle_service_errors
async def get_overdue_tasks(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get all overdue tasks for the household"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    overdue_tasks = task_service.get_overdue_tasks_for_reminders(
        household_id=household_id
    )

    return RouterResponse.success(
        data={"overdue_tasks": overdue_tasks, "count": len(overdue_tasks)}
    )


@router.get("/config/priorities", response_model=Dict[str, Any])
async def get_task_priorities():
    """Get available task priority levels"""
    from ..schemas.task import Priority

    priorities = [
        {"value": priority.value, "label": priority.value.replace("_", " ").title()}
        for priority in Priority
    ]

    return RouterResponse.success(data={"priorities": priorities})


@router.get("/config/statuses", response_model=Dict[str, Any])
async def get_task_statuses():
    """Get available task status options"""
    statuses = [
        {"value": status.value, "label": status.value.replace("_", " ").title()}
        for status in TaskStatus
    ]

    return RouterResponse.success(data={"statuses": statuses})


@router.post("/bulk/reassign", response_model=Dict[str, Any])
@handle_service_errors
async def bulk_reassign_tasks(
    bulk_data: Dict[str, Any] = Body(
        ...,
        example={
            "task_ids": [1, 2, 3],
            "new_assignee_id": 2,
            "reason": "Workload rebalancing",
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Bulk reassign multiple tasks to a user (admin only)"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task_ids = bulk_data.get("task_ids", [])
    new_assignee_id = bulk_data.get("new_assignee_id")

    if not task_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="task_ids list is required"
        )

    if not new_assignee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_assignee_id is required",
        )

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

    return RouterResponse.success(
        data={
            "updated_count": len(updated_tasks),
            "failed_count": len(failed_tasks),
            "updated_tasks": updated_tasks,
            "failed_tasks": failed_tasks,
        },
        message=f"Bulk reassignment completed: {len(updated_tasks)} successful, {len(failed_tasks)} failed",
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
    task_service = TaskService(db)

    # Get current month leaderboard
    leaderboard = task_service.get_household_leaderboard(
        household_id=household_id, user_id=current_user.id
    )

    # Get overdue tasks
    overdue_tasks = task_service.get_overdue_tasks_for_reminders(household_id)

    # Calculate statistics
    total_members = len(leaderboard) if leaderboard else 0
    total_completed_tasks = sum(
        entry.get("tasks_completed", 0) for entry in leaderboard
    )
    avg_completion_rate = (
        sum(entry.get("completion_rate", 0) for entry in leaderboard) / total_members
        if total_members > 0
        else 0
    )

    statistics = {
        "household_id": household_id,
        "period_months": months_back,
        "total_members": total_members,
        "total_completed_tasks": total_completed_tasks,
        "average_completion_rate": round(avg_completion_rate, 1),
        "overdue_tasks_count": len(overdue_tasks),
        "leaderboard_preview": leaderboard[:3],  # Top 3
        "most_productive_member": leaderboard[0] if leaderboard else None,
    }

    return RouterResponse.success(data=statistics)
