# app/routers/event.py - COMPLETE REWRITE

from app.dependencies.permissions import (
    require_household_member,
)
from app.utils.router_helpers import handle_service_errors, RouterResponse
from fastapi import APIRouter, Depends, Query, Body, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from ..database import get_db
from ..services.event_service import EventService
from ..services.scheduling_service import SchedulingService
from ..services.approval_service import ApprovalService
from ..schemas.event import EventCreate
from ..schemas.rsvp import RSVPCreate
from ..models.user import User

router = APIRouter(tags=["events"])


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new event (requires household approval)"""
    current_user, household_id = user_household

    # Let service handle conflict checking and creation
    approval_service = ApprovalService(db)
    event = approval_service.create_event_request(
        event_data=event_data,
        household_id=household_id,
        created_by=current_user.id,
    )

    return RouterResponse.created(
        data={"event": event}, message="Event created successfully"
    )


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_events(
    include_pending: bool = Query(True, description="Include pending events"),
    days_ahead: int = Query(30, ge=1, le=365, description="Days to look ahead"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household events"""
    current_user, household_id = user_household

    event_service = EventService(db)
    events = event_service.get_household_events(
        household_id=household_id,
        include_pending=include_pending,
        days_ahead=days_ahead,
    )

    return RouterResponse.success(data={"events": events})


@router.get("/pending-approval", response_model=Dict[str, Any])
@handle_service_errors
async def get_pending_events(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get events pending approval"""
    current_user, household_id = user_household

    event_service = EventService(db)
    pending_events = event_service.get_pending_events_for_approval(
        household_id=household_id
    )

    return RouterResponse.success(data={"pending_events": pending_events})


@router.put("/{event_id}/approve", response_model=Dict[str, Any])
@handle_service_errors
async def approve_event(
    event_id: int,
    approval_data: Dict[str, str] = Body(None, example={"reason": "Looks good!"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Approve an event"""
    current_user, household_id = user_household

    approval_service = ApprovalService(db)
    result = approval_service.approve_event(
        event_id=event_id,
        approver_id=current_user.id,
        reason=approval_data.get("reason") if approval_data else None,
    )

    return RouterResponse.success(data=result, message="Event approved successfully")


@router.put("/{event_id}/deny", response_model=Dict[str, Any])
@handle_service_errors
async def deny_event(
    event_id: int,
    denial_data: Dict[str, str] = Body(
        ..., example={"reason": "Conflicts with existing plans"}
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Deny an event"""
    current_user, household_id = user_household

    reason = denial_data.get("reason", "")
    approval_service = ApprovalService(db)
    result = approval_service.deny_event(
        event_id=event_id, denier_id=current_user.id, reason=reason
    )

    return RouterResponse.success(data=result, message="Event denied successfully")


@router.put("/{event_id}/cancel", response_model=Dict[str, Any])
@handle_service_errors
async def cancel_event(
    event_id: int,
    cancellation_data: Dict[str, str] = Body(None, example={"reason": "Plans changed"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Cancel an event"""
    current_user, household_id = user_household

    reason = cancellation_data.get("reason", "") if cancellation_data else ""
    event_service = EventService(db)
    event_service.cancel_event(
        event_id=event_id, cancelled_by=current_user.id, reason=reason
    )

    return RouterResponse.success(message="Event cancelled successfully")


# RSVP Management
@router.post("/{event_id}/rsvp", response_model=Dict[str, Any])
@handle_service_errors
async def create_rsvp(
    event_id: int,
    rsvp_data: RSVPCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """RSVP to an event"""
    current_user, household_id = user_household

    # Set the event ID
    rsvp_data.event_id = event_id

    event_service = EventService(db)
    rsvp = event_service.create_rsvp(rsvp_data=rsvp_data, user_id=current_user.id)

    return RouterResponse.created(
        data={"rsvp": rsvp}, message="RSVP recorded successfully"
    )


@router.get("/{event_id}/rsvps", response_model=Dict[str, Any])
@handle_service_errors
async def get_event_rsvps(
    event_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get all RSVPs for an event"""
    current_user, household_id = user_household

    event_service = EventService(db)
    rsvps = event_service.get_event_rsvps(event_id)

    return RouterResponse.success(data={"rsvps": rsvps})


@router.get("/me/upcoming", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_upcoming_events(
    days_ahead: int = Query(30, ge=1, le=365, description="Days to look ahead"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get user's upcoming events"""
    current_user, household_id = user_household

    event_service = EventService(db)
    events = event_service.get_user_upcoming_events(
        user_id=current_user.id, household_id=household_id, days_ahead=days_ahead
    )

    return RouterResponse.success(data={"my_events": events})


# Scheduling Utilities
@router.post("/check-conflicts", response_model=Dict[str, Any])
@handle_service_errors
async def check_scheduling_conflicts(
    conflict_data: Dict[str, datetime] = Body(
        ...,
        example={
            "start_date": "2024-01-15T18:00:00",
            "end_date": "2024-01-15T22:00:00",
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Check for scheduling conflicts"""
    current_user, household_id = user_household

    start_date = conflict_data.get("start_date")
    end_date = conflict_data.get("end_date")

    scheduling_service = SchedulingService(db)
    conflicts = scheduling_service.check_event_conflicts(
        household_id=household_id, start_date=start_date, end_date=end_date
    )

    return RouterResponse.success(data={"conflicts": conflicts})


@router.post("/suggest-times", response_model=Dict[str, Any])
@handle_service_errors
async def suggest_alternative_times(
    suggestion_data: Dict[str, Any] = Body(
        ...,
        example={
            "preferred_date": "2024-01-15T18:00:00",
            "duration_hours": 2,
            "days_to_check": 7,
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get alternative time suggestions"""
    current_user, household_id = user_household

    preferred_date = suggestion_data.get("preferred_date")
    duration_hours = suggestion_data.get("duration_hours", 2)
    days_to_check = suggestion_data.get("days_to_check", 7)

    scheduling_service = SchedulingService(db)
    suggestions = scheduling_service.suggest_alternative_times(
        household_id=household_id,
        preferred_date=preferred_date,
        duration_hours=duration_hours,
        days_to_check=days_to_check,
    )

    return RouterResponse.success(data={"suggestions": suggestions})


@router.get("/schedule-overview", response_model=Dict[str, Any])
@handle_service_errors
async def get_schedule_overview(
    start_date: Optional[datetime] = Query(None, description="Start date for overview"),
    days: int = Query(7, ge=1, le=30, description="Number of days to show"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household schedule overview"""
    current_user, household_id = user_household

    if not start_date:
        start_date = datetime.utcnow()

    scheduling_service = SchedulingService(db)
    overview = scheduling_service.get_household_schedule_overview(
        household_id=household_id, start_date=start_date, days=days
    )

    return RouterResponse.success(data={"schedule_overview": overview})


@router.get("/statistics", response_model=Dict[str, Any])
@handle_service_errors
async def get_event_statistics(
    months_back: int = Query(6, ge=1, le=24, description="Months of history"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get event statistics"""
    current_user, household_id = user_household

    event_service = EventService(db)
    stats = event_service.get_event_statistics(
        household_id=household_id, months_back=months_back
    )

    return RouterResponse.success(data={"statistics": stats})
