from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..services.task_service import TaskService
from ..schemas.task import (
    TaskCreate,
    TaskStatusUpdate,
    TaskUpdate,
    TaskComplete,
    TaskResponse,
    TaskLeaderboard,
    TaskStatistics,
    TaskReassignment,
    TaskStatistics,
)
from ..schemas.common import (
    SuccessResponse,
    PaginatedResponse,
    ResponseFactory,
    PaginationParams,
    ConfigResponse,
    ConfigOption,
)
from ..dependencies.permissions import require_household_member
from ..utils.router_helpers import (
    handle_service_errors,
)
from ..models.user import User
from ..models.enums import TaskStatus
from ..utils.constants import ResponseMessages

router = APIRouter(tags=["tasks"])


@router.post("/", response_model=SuccessResponse[TaskResponse])
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

    return ResponseFactory.created(data=task, message=ResponseMessages.TASK_CREATED)


@router.get("/", response_model=PaginatedResponse[TaskResponse])
@handle_service_errors
async def get_household_tasks(
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None, description="Filter by task status"),
    assigned_to: Optional[int] = Query(None, description="Filter by assignee"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    overdue_only: bool = Query(False, description="Show only overdue tasks"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household tasks with filtering and pagination"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    result = task_service.get_household_tasks(
        household_id=household_id,
        user_id=current_user.id,
        limit=pagination.limit,
        offset=pagination.offset,
        status=status,
        assigned_to=assigned_to,
        priority=priority,
        overdue_only=overdue_only,
    )

    # Create pagination info from result
    from ..schemas.common import PaginationInfo

    tasks = result.get("tasks", [])
    total_count = result.get("total_count", 0)

    pagination_info = PaginationInfo(
        current_page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_count,
        total_pages=(total_count + pagination.page_size - 1) // pagination.page_size,
        has_next=pagination.offset + pagination.page_size < total_count,
        has_previous=pagination.page > 1,
    )

    return ResponseFactory.paginated(data=tasks, pagination=pagination_info)


@router.get("/me", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(data=summary)


@router.get("/{task_id}", response_model=SuccessResponse[dict])
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

        return ResponseFactory.success(data={"task": task_details})

    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        raise


@router.put("/{task_id}", response_model=SuccessResponse[TaskResponse])
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

    return ResponseFactory.success(data=task, message=ResponseMessages.TASK_UPDATED)


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


@router.put("/{task_id}/complete", response_model=SuccessResponse[dict])
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

    completion_response = {
        "task": {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "completed_at": task.completed_at,
        },
        "completion_time": task.completed_at,
    }

    return ResponseFactory.success(
        data=completion_response,
        message=ResponseMessages.TASK_COMPLETED,
    )


@router.put("/{task_id}/status", response_model=SuccessResponse[TaskResponse])
@handle_service_errors
async def update_task_status(
    task_id: int,
    status_data: TaskStatusUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update task status"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.update_task_status(
        task_id=task_id,
        user_id=current_user.id,
        status=status_data.status,
    )

    return ResponseFactory.success(data=task, message=ResponseMessages.TASK_UPDATED)


@router.put("/{task_id}/reassign", response_model=SuccessResponse[TaskResponse])
@handle_service_errors
async def reassign_task(
    task_id: int,
    reassign_data: TaskReassignment,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Reassign task to different user"""
    current_user, household_id = user_household
    task_service = TaskService(db)

    task = task_service.reassign_task(
        task_id=task_id,
        new_assignee_id=reassign_data.new_assignee_id,
        reassigned_by=current_user.id,
    )

    return ResponseFactory.success(data=task, message=ResponseMessages.TASK_UPDATED)


@router.get(
    "/leaderboard/current", response_model=SuccessResponse[List[TaskLeaderboard]]
)
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

    return ResponseFactory.success(data=leaderboard)


@router.get("/me/score", response_model=SuccessResponse[TaskLeaderboard])
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

    return ResponseFactory.success(data=score)


@router.get("/rotation/schedule", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(data=schedule)


@router.get("/overdue", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(
        data={"overdue_tasks": overdue_tasks, "count": len(overdue_tasks)}
    )


@router.get("/config/priorities", response_model=SuccessResponse[ConfigResponse])
async def get_task_priorities():
    """Get available task priority levels"""
    from ..schemas.task import Priority

    options = [
        ConfigOption(
            value=priority.value, label=priority.value.replace("_", " ").title()
        )
        for priority in Priority
    ]

    return ResponseFactory.success(
        data=ConfigResponse(options=options, total_count=len(options))
    )


@router.get("/config/statuses", response_model=SuccessResponse[ConfigResponse])
async def get_task_statuses():
    """Get available task status options"""
    options = [
        ConfigOption(value=status.value, label=status.value.replace("_", " ").title())
        for status in TaskStatus
    ]

    return ResponseFactory.success(
        data=ConfigResponse(options=options, total_count=len(options))
    )


@router.get("/statistics/household", response_model=SuccessResponse[TaskStatistics])
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

    statistics = TaskStatistics(
        household_id=household_id,
        period_months=months_back,
        total_members=total_members,
        total_completed_tasks=total_completed_tasks,
        average_completion_rate=round(avg_completion_rate, 1),
        overdue_tasks_count=len(overdue_tasks),
        leaderboard_preview=leaderboard[:3],  # Top 3
        most_productive_member=leaderboard[0] if leaderboard else None,
    )

    return ResponseFactory.success(data=statistics)
