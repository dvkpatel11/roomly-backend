# Calendar Page - Backend Context

## Overview

Calendar handles scheduling, events, bill due dates, and user schedules.
Frontend toggles: Schedule | Events

## Related Files:

## app/routers/event.py

```python
from app.dependencies.permissions import require_household_member
from app.utils.router_helpers import handle_service_errors
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from ..database import get_db
from ..services.event_service import EventService
from ..services.scheduling_service import SchedulingService
from ..services.approval_service import ApprovalService
from ..schemas.event import EventCreate
from ..schemas.rsvp import RSVPCreate, RSVPResponse
from .auth import get_current_user
from ..models.user import User

router = APIRouter(tags=["events"])


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
```

## app/routers/bills.py

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..services.billing_service import BillingService
from ..schemas.bill import BillCreate, BillUpdate
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
)
from ..models.user import User
from ..utils.constants import AppConstants

router = APIRouter(tags=["bills"])


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def create_recurring_bill(
    bill_data: BillCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new recurring bill"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    bill = billing_service.create_recurring_bill(
        bill_data=bill_data,
        household_id=household_id,
        created_by=current_user.id,
    )

    return RouterResponse.created(
        data={"bill": bill}, message="Recurring bill created successfully"
    )


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_bills(
    active_only: bool = Query(True, description="Show only active bills"),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household's recurring bills"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    bills = billing_service.get_household_bills(household_id, active_only=True)

    return RouterResponse.success(
        data={
            "bills": bills,
            "total_count": len(bills),
            "active_only": active_only,
        }
    )


@router.get("/upcoming", response_model=Dict[str, Any])
@handle_service_errors
async def get_upcoming_bills(
    days_ahead: int = Query(7, ge=1, le=30, description="Days to look ahead"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get bills due in the next N days"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    upcoming = billing_service.get_upcoming_bills(
        household_id=household_id, days_ahead=days_ahead
    )

    return RouterResponse.success(
        data={
            "upcoming_bills": upcoming,
            "days_ahead": days_ahead,
            "count": len(upcoming),
        }
    )


@router.get("/overdue", response_model=Dict[str, Any])
@handle_service_errors
async def get_overdue_bills(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get overdue bills for household"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    overdue = billing_service.get_overdue_bills(household_id=household_id)

    return RouterResponse.success(
        data={
            "overdue_bills": overdue,
            "count": len(overdue),
            "total_overdue_amount": sum(bill["amount_remaining"] for bill in overdue),
        }
    )


@router.get("/{bill_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_bill_details(
    bill_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed bill information"""
    billing_service = BillingService(db)

    details = billing_service.get_bill_details(bill_id)

    return RouterResponse.success(
        data={
            "bill_id": bill_id,
            "details": details,
        }
    )


@router.put("/{bill_id}", response_model=Dict[str, Any])
@handle_service_errors
async def update_bill(
    bill_id: int,
    bill_update: BillUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update recurring bill"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    bill = billing_service.update_bill(bill_id, bill_update)

    return RouterResponse.updated(
        data={"bill": bill}, message="Bill updated successfully"
    )


@router.delete("/{bill_id}", response_model=Dict[str, Any])
@handle_service_errors
async def deactivate_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Deactivate a recurring bill (admin only)"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    success = billing_service.deactivate_bill(bill_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
        )

    return RouterResponse.success(message="Bill deactivated successfully")


@router.post("/{bill_id}/payments", response_model=Dict[str, Any])
@handle_service_errors
async def record_bill_payment(
    bill_id: int,
    payment_data: Dict[str, Any] = Body(
        ...,
        example={
            "amount_paid": 150.00,
            "payment_method": "venmo",
            "for_month": "2024-01",
            "notes": "January rent payment",
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Record a bill payment"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    # Validate required fields
    amount_paid = payment_data.get("amount_paid")
    payment_method = payment_data.get("payment_method")
    for_month = payment_data.get("for_month")

    if not all([amount_paid, payment_method, for_month]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount_paid, payment_method, and for_month are required",
        )

    payment = billing_service.record_bill_payment(
        bill_id=bill_id,
        paid_by=current_user.id,
        amount_paid=amount_paid,
        payment_method=payment_method,
        for_month=for_month,
        notes=payment_data.get("notes", ""),
    )

    return RouterResponse.created(
        data={
            "payment": {
                "id": payment.id,
                "amount_paid": payment.amount_paid,
                "payment_date": payment.payment_date,
                "payment_method": payment.payment_method,
            }
        },
        message="Payment recorded successfully",
    )


@router.get("/{bill_id}/payment-history", response_model=Dict[str, Any])
@handle_service_errors
async def get_bill_payment_history(
    bill_id: int,
    months_back: int = Query(12, ge=1, le=24, description="Months of history"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get payment history for a bill"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    history = billing_service.get_bill_payment_history(
        bill_id=bill_id, months_back=months_back
    )

    return RouterResponse.success(
        data={
            "payment_history": history,
            "bill_id": bill_id,
            "months_back": months_back,
        }
    )


@router.get("/summary", response_model=Dict[str, Any])
@handle_service_errors
async def get_billing_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive billing summary"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    summary = billing_service.get_household_billing_summary(household_id=household_id)

    return RouterResponse.success(data={"billing_summary": summary})


@router.get("/config/categories", response_model=Dict[str, Any])
async def get_bill_categories():
    """Get available bill categories"""
    from ..utils.constants import ExpenseCategory

    categories = [
        {"value": cat.value, "label": cat.value.replace("_", " ").title()}
        for cat in ExpenseCategory
        if cat.value in ["utilities", "rent", "internet", "maintenance"]
    ]

    return RouterResponse.success(data={"categories": categories})


@router.get("/config/split-methods", response_model=Dict[str, Any])
async def get_split_methods():
    """Get available split methods for bills"""
    from ..utils.constants import SplitMethod

    methods = [
        {"value": method.value, "label": method.value.replace("_", " ").title()}
        for method in SplitMethod
    ]

    return RouterResponse.success(data={"split_methods": methods})
```

## app/schemas/event.py

```python
from pydantic import BaseModel, validator, Field
from typing import Optional
from datetime import datetime
from enum import Enum

from app.models.enums import EventStatus


class EventType(str, Enum):
    PARTY = "party"
    MAINTENANCE = "maintenance"
    CLEANING = "cleaning"
    MEETING = "meeting"
    MOVIE_NIGHT = "movie_night"
    DINNER = "dinner"
    GAME_NIGHT = "game_night"
    OTHER = "other"


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    event_type: EventType
    location: Optional[str] = Field(None, max_length=200)
    max_attendees: Optional[int] = Field(None, gt=0)
    is_public: bool = True
    requires_approval: bool = False


class EventCreate(EventBase):
    start_date: datetime
    end_date: Optional[datetime] = None

    @validator("end_date")
    def end_after_start(cls, v, values):
        if v and "start_date" in values and v <= values["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    event_type: Optional[EventType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    max_attendees: Optional[int] = Field(None, gt=0)
    is_public: Optional[bool] = None
    requires_approval: Optional[bool] = None
    status: Optional[EventStatus] = None


class EventResponse(EventBase):
    id: int
    household_id: int
    created_by: int
    creator_name: str
    start_date: datetime
    end_date: Optional[datetime]
    status: EventStatus
    attendee_count: int
    rsvp_yes: int
    rsvp_no: int
    rsvp_maybe: int
    created_at: datetime

    class Config:
        from_attributes = True


class EventSummary(BaseModel):
    id: int
    title: str
    event_type: EventType
    start_date: datetime
    attendee_count: int
    user_rsvp_status: Optional[str]
```

## app/schemas/bill.py

```python
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class BillBase(BaseModel):
    name: str
    amount: float
    category: str
    due_day: int
    split_method: str
    notes: Optional[str] = None


class BillCreate(BillBase):
    @validator("due_day")
    def validate_due_day(cls, v):
        if not 1 <= v <= 31:
            raise ValueError("Due day must be between 1 and 31")
        return v


class BillUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    due_day: Optional[int] = None
    split_method: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @validator("due_day")
    def validate_due_day(cls, v):
        if v is not None and not 1 <= v <= 31:
            raise ValueError("Due day must be between 1 and 31")
        return v

    @validator("amount")
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive")
        return v


class BillResponse(BillBase):
    id: int
    household_id: int
    created_by: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


__all__ = ["BillBase", "BillCreate", "BillUpdate", "BillResponse"]
```

## app/models/event.py

```python
from app.models.enums import EventStatus
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    event_type = Column(String, nullable=False)  # party, maintenance, cleaning, etc.
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    location = Column(String)
    max_attendees = Column(Integer)
    is_public = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=True)
    status = Column(String, default=EventStatus.PENDING.value)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="events")
    creator = relationship(
        "User", back_populates="created_events", foreign_keys=[created_by]
    )
    rsvps = relationship("RSVP", back_populates="event", cascade="all, delete-orphan")
```

## app/models/bill.py

```python
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # utilities, rent, internet, etc.
    due_day = Column(Integer, nullable=False)  # Day of month (1-31)
    split_method = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    split_details = Column(JSON)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="bills")
    created_by_user = relationship(
        "User", back_populates="created_bills", foreign_keys=[created_by]
    )
    payments = relationship("BillPayment", back_populates="bill")

    __table_args__ = (
        Index("idx_bill_household_active", "household_id", "is_active"),
        Index("idx_bill_due_day", "due_day"),
    )


class BillPayment(Base):
    __tablename__ = "bill_payments"

    id = Column(Integer, primary_key=True, index=True)
    amount_paid = Column(Float, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_method = Column(String)  # venmo, cash, check, etc.
    notes = Column(Text)
    for_month = Column(String, nullable=False)  # "2025-06" format

    # Foreign Keys
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bill = relationship("Bill", back_populates="payments")
    paid_by_user = relationship(
        "User", back_populates="bill_payments", foreign_keys=[paid_by]
    )
```

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

```
