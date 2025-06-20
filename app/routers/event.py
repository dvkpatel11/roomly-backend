from app.dependencies.permissions import require_household_member
from app.utils.router_helpers import handle_service_errors
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..database import get_db
from ..services.event_service import EventService
from ..services.scheduling_service import SchedulingService
from ..services.approval_service import ApprovalService
from ..schemas.event import EventCreate, EventUpdate, EventResponse
from ..schemas.rsvp import RSVPCreate, RSVPUpdate, RSVPResponse
from .auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/", response_model=Dict[str, Any])
@handle_service_errors
async def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    current_user, household_id = user_household
    """Create a new event (requires household approval)"""
    try:
        # Check for scheduling conflicts first
        scheduling_service = SchedulingService(db)
        conflicts = scheduling_service.check_event_conflicts(
            household_id=current_user.household_id,
            start_date=event_data.start_date,
            end_date=event_data.end_date,
        )

        if conflicts["has_conflict"]:
            return {
                "warning": "Scheduling conflicts detected",
                "conflicts": conflicts["conflicts"],
                "suggestions": scheduling_service.suggest_alternative_times(
                    current_user.household_id, event_data.start_date
                ),
            }

        # Create event (will be pending approval)
        approval_service = ApprovalService(db)
        event = approval_service.create_event_request(
            event_data=event_data,
            household_id=current_user.household_id,
            created_by=current_user.id,
        )

        return event
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events")
async def get_events(
    include_pending: bool = True,
    days_ahead: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get household events"""
    event_service = EventService(db)

    events = event_service.get_household_events(
        household_id=current_user.household_id,
        include_pending=include_pending,
        days_ahead=days_ahead,
    )

    return {"events": events}


@router.get("/events/pending-approval")
async def get_pending_events(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get events pending approval"""
    event_service = EventService(db)

    pending_events = event_service.get_pending_events_for_approval(
        household_id=current_user.household_id
    )

    return {"pending_events": pending_events}


@router.put("/events/{event_id}/approve")
async def approve_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve an event"""
    approval_service = ApprovalService(db)

    result = approval_service.approve_event(
        event_id=event_id, approver_id=current_user.id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.put("/events/{event_id}/deny")
async def deny_event(
    event_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deny an event"""
    approval_service = ApprovalService(db)

    result = approval_service.deny_event(
        event_id=event_id, denier_id=current_user.id, reason=reason
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.put("/events/{event_id}/cancel")
async def cancel_event(
    event_id: int,
    reason: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel an event"""
    event_service = EventService(db)

    success = event_service.cancel_event(
        event_id=event_id, cancelled_by=current_user.id, reason=reason
    )

    if not success:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"message": "Event cancelled successfully"}


# RSVP Management
@router.post("/events/{event_id}/rsvp", response_model=RSVPResponse)
async def create_rsvp(
    event_id: int,
    rsvp_data: RSVPCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """RSVP to an event"""
    try:
        # Set the event ID
        rsvp_data.event_id = event_id

        event_service = EventService(db)
        rsvp = event_service.create_rsvp(rsvp_data=rsvp_data, user_id=current_user.id)
        return rsvp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events/{event_id}/rsvps")
async def get_event_rsvps(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all RSVPs for an event"""
    try:
        event_service = EventService(db)
        rsvps = event_service.get_event_rsvps(event_id)
        return rsvps
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/my-events")
async def get_my_upcoming_events(
    days_ahead: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's upcoming events"""
    event_service = EventService(db)

    events = event_service.get_user_upcoming_events(
        user_id=current_user.id, days_ahead=days_ahead
    )

    return {"my_events": events}


# Scheduling Utilities
@router.post("/check-conflicts")
async def check_scheduling_conflicts(
    start_date: datetime,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check for scheduling conflicts"""
    scheduling_service = SchedulingService(db)

    conflicts = scheduling_service.check_event_conflicts(
        household_id=current_user.household_id, start_date=start_date, end_date=end_date
    )

    return conflicts


@router.post("/suggest-times")
async def suggest_alternative_times(
    preferred_date: datetime,
    duration_hours: int = 2,
    days_to_check: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alternative time suggestions"""
    scheduling_service = SchedulingService(db)

    suggestions = scheduling_service.suggest_alternative_times(
        household_id=current_user.household_id,
        preferred_date=preferred_date,
        duration_hours=duration_hours,
        days_to_check=days_to_check,
    )

    return {"suggestions": suggestions}


@router.get("/schedule-overview")
async def get_schedule_overview(
    start_date: Optional[datetime] = None,
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get household schedule overview"""
    scheduling_service = SchedulingService(db)

    if not start_date:
        start_date = datetime.utcnow()

    overview = scheduling_service.get_household_schedule_overview(
        household_id=current_user.household_id, start_date=start_date, days=days
    )

    return overview


@router.get("/statistics")
async def get_event_statistics(
    months_back: int = 6,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get event statistics"""
    event_service = EventService(db)

    stats = event_service.get_event_statistics(
        household_id=current_user.household_id, months_back=months_back
    )

    return stats
