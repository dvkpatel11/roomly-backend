from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.event import Event
from ..models.rsvp import RSVP
from ..models.user import User
from ..models.household_membership import HouseholdMembership
from ..schemas.enums import EventStatus, HouseholdRole
from ..schemas.event import EventCreate, EventUpdate
from ..schemas.rsvp import RSVPCreate, RSVPUpdate
from dataclasses import dataclass


class EventServiceError(Exception):
    """Base exception for event service errors"""

    pass


class EventNotFoundError(EventServiceError):
    """Event not found"""

    pass


class PermissionDeniedError(EventServiceError):
    """Permission denied for operation"""

    pass


class BusinessRuleViolationError(EventServiceError):
    """Business rule violation"""

    pass


class RSVPValidationError(EventServiceError):
    """RSVP validation error"""

    pass


@dataclass
class HouseholdMember:
    """Event service household member representation"""

    id: int
    name: str
    email: str
    role: str


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def create_event(
        self, event_data: EventCreate, household_id: int, created_by: int
    ) -> Event:
        """Create a new event with proper validation"""

        # Validate permissions
        if not self._user_can_create_events(created_by, household_id):
            raise PermissionDeniedError("User is not a member of this household")

        # Validate event dates
        if event_data.end_date and event_data.end_date <= event_data.start_date:
            raise BusinessRuleViolationError("End date must be after start date")

        # Check for conflicting events
        if self._has_scheduling_conflict(
            household_id, event_data.start_date, event_data.end_date
        ):
            raise BusinessRuleViolationError(
                "Event conflicts with existing household event"
            )

        try:
            event = Event(
                title=event_data.title,
                description=event_data.description,
                event_type=event_data.event_type.value,
                start_date=event_data.start_date,
                end_date=event_data.end_date,
                location=event_data.location,
                max_attendees=event_data.max_attendees,
                is_public=event_data.is_public,
                requires_approval=event_data.requires_approval,
                household_id=household_id,
                created_by=created_by,
                status=(
                    EventStatus.PENDING.value
                    if event_data.requires_approval
                    else EventStatus.PUBLISHED.value
                ),
            )

            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)

            # Auto-approve if creator is admin and doesn't require approval
            if not event_data.requires_approval or self._is_household_admin(
                created_by, household_id
            ):
                self._publish_event(event.id, created_by)

            return event

        except Exception as e:
            self.db.rollback()
            raise EventServiceError(f"Failed to create event: {str(e)}")

    def update_event(
        self, event_id: int, event_updates: EventUpdate, updated_by: int
    ) -> Event:
        """Update event with permission validation"""

        event = self._get_event_or_raise(event_id)

        # Check permissions (creator or household admin can edit)
        if not self._user_can_edit_event(updated_by, event):
            raise PermissionDeniedError(
                "Only event creator or household admin can edit"
            )

        # Prevent editing completed events
        if event.status == EventStatus.COMPLETED.value:
            raise BusinessRuleViolationError("Cannot edit completed events")

        try:
            # Update basic fields
            update_data = event_updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field in ["start_date", "end_date"]:
                    # Validate date changes
                    if field == "start_date" and event_updates.end_date:
                        if event_updates.end_date <= value:
                            raise BusinessRuleViolationError(
                                "End date must be after start date"
                            )
                    elif field == "end_date" and value:
                        start_date = event_updates.start_date or event.start_date
                        if value <= start_date:
                            raise BusinessRuleViolationError(
                                "End date must be after start date"
                            )

                setattr(event, field, value.value if hasattr(value, "value") else value)

            event.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(event)
            return event

        except Exception as e:
            self.db.rollback()
            raise EventServiceError(f"Failed to update event: {str(e)}")

    def delete_event(self, event_id: int, deleted_by: int) -> bool:
        """Delete event with proper validation"""

        event = self._get_event_or_raise(event_id)

        if not self._user_can_edit_event(deleted_by, event):
            raise PermissionDeniedError(
                "Only event creator or household admin can delete"
            )

        if event.status == EventStatus.COMPLETED.value:
            raise BusinessRuleViolationError("Cannot delete completed events")

        # Check if event has RSVPs
        rsvp_count = self.db.query(RSVP).filter(RSVP.event_id == event_id).count()
        if rsvp_count > 0:
            # Cancel instead of delete to preserve RSVP history
            return self.cancel_event(event_id, deleted_by, "Event deleted by organizer")

        try:
            self.db.delete(event)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise EventServiceError(f"Failed to delete event: {str(e)}")

    def approve_event(
        self, event_id: int, approved_by: int, approved: bool = True
    ) -> Event:
        """Approve or reject an event"""

        event = self._get_event_or_raise(event_id)

        # Check permissions (household admin can approve)
        if not self._is_household_admin(approved_by, event.household_id):
            raise PermissionDeniedError("Only household admins can approve events")

        if event.status != EventStatus.PENDING.value:
            raise BusinessRuleViolationError("Only pending events can be approved")

        try:
            if approved:
                event.status = EventStatus.PUBLISHED.value
            else:
                event.status = EventStatus.CANCELLED.value

            event.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(event)

            # Notify creator and household members
            self._notify_event_status_change(event_id, approved)

            return event

        except Exception as e:
            self.db.rollback()
            raise EventServiceError(f"Failed to approve event: {str(e)}")

    def cancel_event(self, event_id: int, cancelled_by: int, reason: str = "") -> bool:
        """Cancel an event"""

        event = self._get_event_or_raise(event_id)

        if not self._user_can_edit_event(cancelled_by, event):
            raise PermissionDeniedError(
                "Only event creator or household admin can cancel"
            )

        if event.status == EventStatus.CANCELLED.value:
            return True

        if event.status == EventStatus.COMPLETED.value:
            raise BusinessRuleViolationError("Cannot cancel completed events")

        try:
            event.status = EventStatus.CANCELLED.value
            event.updated_at = datetime.utcnow()
            self.db.commit()

            # Notify all attendees
            self._notify_event_cancelled(event_id, reason)

            return True

        except Exception as e:
            self.db.rollback()
            raise EventServiceError(f"Failed to cancel event: {str(e)}")

    def complete_event(self, event_id: int, completed_by: int) -> Event:
        """Mark event as completed"""

        event = self._get_event_or_raise(event_id)

        if not self._user_can_edit_event(completed_by, event):
            raise PermissionDeniedError(
                "Only event creator or household admin can complete"
            )

        if event.status != EventStatus.PUBLISHED.value:
            raise BusinessRuleViolationError("Only published events can be completed")

        try:
            event.status = EventStatus.COMPLETED.value
            event.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(event)
            return event

        except Exception as e:
            self.db.rollback()
            raise EventServiceError(f"Failed to complete event: {str(e)}")

    def create_rsvp(self, rsvp_data: RSVPCreate, user_id: int) -> RSVP:
        """Create or update RSVP for event"""

        event = self._get_event_or_raise(rsvp_data.event_id)

        # Validate permissions
        if not self._user_can_rsvp_to_event(user_id, event):
            raise PermissionDeniedError("User cannot RSVP to this event")

        if event.status != EventStatus.PUBLISHED.value:
            raise RSVPValidationError("Cannot RSVP to unpublished event")

        # Check capacity if RSVPing yes
        if rsvp_data.status.value == "yes":
            if self._would_exceed_capacity(event, rsvp_data.guest_count, user_id):
                raise RSVPValidationError("Event is at capacity")

        try:
            # Check for existing RSVP
            existing_rsvp = (
                self.db.query(RSVP)
                .filter(
                    and_(RSVP.event_id == rsvp_data.event_id, RSVP.user_id == user_id)
                )
                .first()
            )

            if existing_rsvp:
                # Update existing RSVP
                existing_rsvp.status = rsvp_data.status.value
                existing_rsvp.guest_count = rsvp_data.guest_count
                existing_rsvp.special_requests = rsvp_data.special_requests
                existing_rsvp.response_notes = rsvp_data.response_notes
                existing_rsvp.updated_at = datetime.utcnow()

                self.db.commit()
                self.db.refresh(existing_rsvp)
                return existing_rsvp
            else:
                # Create new RSVP
                rsvp = RSVP(
                    event_id=rsvp_data.event_id,
                    user_id=user_id,
                    status=rsvp_data.status.value,
                    guest_count=rsvp_data.guest_count,
                    special_requests=rsvp_data.special_requests,
                    response_notes=rsvp_data.response_notes,
                )

                self.db.add(rsvp)
                self.db.commit()
                self.db.refresh(rsvp)
                return rsvp

        except Exception as e:
            self.db.rollback()
            raise EventServiceError(f"Failed to create RSVP: {str(e)}")

    def update_rsvp(
        self, event_id: int, rsvp_updates: RSVPUpdate, user_id: int
    ) -> RSVP:
        """Update existing RSVP"""

        rsvp = (
            self.db.query(RSVP)
            .filter(and_(RSVP.event_id == event_id, RSVP.user_id == user_id))
            .first()
        )

        if not rsvp:
            raise EventNotFoundError("RSVP not found")

        event = self._get_event_or_raise(event_id)

        if event.status != EventStatus.PUBLISHED.value:
            raise RSVPValidationError("Cannot update RSVP for unpublished event")

        try:
            # Update fields
            update_data = rsvp_updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(rsvp, field, value.value if hasattr(value, "value") else value)

            rsvp.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(rsvp)
            return rsvp

        except Exception as e:
            self.db.rollback()
            raise EventServiceError(f"Failed to update RSVP: {str(e)}")

    def get_household_events(
        self,
        household_id: int,
        user_id: int,
        include_pending: bool = True,
        days_ahead: int = 30,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get events for household with filtering and pagination"""

        if not self._user_can_view_events(user_id, household_id):
            raise PermissionDeniedError("User cannot view household events")

        now = datetime.utcnow()
        future_cutoff = now + timedelta(days=days_ahead)

        # Build query
        query = self.db.query(Event).filter(
            and_(
                Event.household_id == household_id,
                Event.start_date >= now,
                Event.start_date <= future_cutoff,
            )
        )

        if not include_pending:
            query = query.filter(Event.status == EventStatus.PUBLISHED.value)

        # Get total count for pagination
        total_count = query.count()

        # Get events with pagination
        events = query.order_by(Event.start_date).offset(offset).limit(limit).all()

        # Enrich with details
        event_list = []
        for event in events:
            creator = self.db.query(User).filter(User.id == event.created_by).first()
            rsvp_summary = self._get_event_rsvp_summary(event.id)
            user_rsvp = self._get_user_rsvp(event.id, user_id)

            event_list.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "event_type": event.event_type,
                    "start_date": event.start_date,
                    "end_date": event.end_date,
                    "location": event.location,
                    "status": event.status,
                    "created_by": event.created_by,
                    "creator_name": creator.name if creator else "Unknown",
                    "max_attendees": event.max_attendees,
                    "is_public": event.is_public,
                    "requires_approval": event.requires_approval,
                    "rsvp_summary": rsvp_summary,
                    "is_full": self._is_event_full(event, rsvp_summary),
                    "user_rsvp": user_rsvp,
                    "created_at": event.created_at,
                    "updated_at": event.updated_at,
                }
            )

        return {
            "events": event_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    def get_event_details(self, event_id: int, user_id: int) -> Dict[str, Any]:
        """Get detailed event information"""

        event = self._get_event_or_raise(event_id)

        if not self._user_can_view_events(user_id, event.household_id):
            raise PermissionDeniedError("User cannot view this event")

        creator = self.db.query(User).filter(User.id == event.created_by).first()
        rsvp_summary = self._get_event_rsvp_summary(event_id)
        user_rsvp = self._get_user_rsvp(event_id, user_id)

        # Get RSVP details if user can see them
        rsvp_details = []
        if self._user_can_view_rsvps(user_id, event):
            rsvps = (
                self.db.query(RSVP, User.name)
                .join(User, RSVP.user_id == User.id)
                .filter(RSVP.event_id == event_id)
                .all()
            )

            rsvp_details = [
                {
                    "user_id": rsvp.user_id,
                    "user_name": user_name,
                    "status": rsvp.status,
                    "guest_count": rsvp.guest_count,
                    "special_requests": rsvp.special_requests,
                    "responded_at": rsvp.created_at,
                }
                for rsvp, user_name in rsvps
            ]

        return {
            "event": {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "event_type": event.event_type,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "location": event.location,
                "status": event.status,
                "created_by": event.created_by,
                "creator_name": creator.name if creator else "Unknown",
                "max_attendees": event.max_attendees,
                "is_public": event.is_public,
                "requires_approval": event.requires_approval,
                "created_at": event.created_at,
                "updated_at": event.updated_at,
            },
            "rsvp_summary": rsvp_summary,
            "rsvp_details": rsvp_details,
            "user_rsvp": user_rsvp,
            "is_full": self._is_event_full(event, rsvp_summary),
            "can_edit": self._user_can_edit_event(user_id, event),
        }

    def get_user_upcoming_events(
        self, user_id: int, household_id: int, days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get upcoming events for a user"""

        if not self._user_can_view_events(user_id, household_id):
            raise PermissionDeniedError("User cannot view household events")

        now = datetime.utcnow()
        future_cutoff = now + timedelta(days=days_ahead)

        # Get events user has RSVP'd "yes" to
        rsvps = (
            self.db.query(RSVP, Event)
            .join(Event, RSVP.event_id == Event.id)
            .filter(
                and_(
                    RSVP.user_id == user_id,
                    RSVP.status == "yes",
                    Event.household_id == household_id,
                    Event.status == EventStatus.PUBLISHED.value,
                    Event.start_date >= now,
                    Event.start_date <= future_cutoff,
                )
            )
            .order_by(Event.start_date)
            .all()
        )

        result = []
        for rsvp, event in rsvps:
            result.append(
                {
                    "event_id": event.id,
                    "title": event.title,
                    "start_date": event.start_date,
                    "end_date": event.end_date,
                    "location": event.location,
                    "event_type": event.event_type,
                    "your_rsvp": {
                        "status": rsvp.status,
                        "guest_count": rsvp.guest_count,
                    },
                }
            )

        return result

    def get_pending_events_for_approval(
        self, household_id: int, user_id: int
    ) -> List[Dict[str, Any]]:
        """Get events pending approval (admin only)"""

        if not self._is_household_admin(user_id, household_id):
            raise PermissionDeniedError("Only household admins can view pending events")

        pending_events = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.household_id == household_id,
                    Event.status == EventStatus.PENDING.value,
                )
            )
            .order_by(Event.created_at)
            .all()
        )

        result = []
        for event in pending_events:
            creator = self.db.query(User).filter(User.id == event.created_by).first()

            result.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "event_type": event.event_type,
                    "start_date": event.start_date,
                    "end_date": event.end_date,
                    "location": event.location,
                    "created_by": event.created_by,
                    "creator_name": creator.name if creator else "Unknown",
                    "created_at": event.created_at,
                    "requires_approval": event.requires_approval,
                }
            )

        return result

    # === HELPER METHODS ===
    def _get_event_or_raise(self, event_id: int) -> Event:
        """Get event or raise exception"""
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise EventNotFoundError(f"Event {event_id} not found")
        return event

    def _user_can_create_events(self, user_id: int, household_id: int) -> bool:
        """Check if user can create events for household"""
        return (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        ) is not None

    def _user_can_edit_event(self, user_id: int, event: Event) -> bool:
        """Check if user can edit event (creator or admin)"""
        if event.created_by == user_id:
            return True
        return self._is_household_admin(user_id, event.household_id)

    def _user_can_view_events(self, user_id: int, household_id: int) -> bool:
        """Check if user can view household events"""
        return self._user_can_create_events(user_id, household_id)

    def _user_can_rsvp_to_event(self, user_id: int, event: Event) -> bool:
        """Check if user can RSVP to event"""
        if not event.is_public:
            # Private events require household membership
            return self._user_can_create_events(user_id, event.household_id)
        return True

    def _user_can_view_rsvps(self, user_id: int, event: Event) -> bool:
        """Check if user can view RSVP details"""
        return event.created_by == user_id or self._is_household_admin(
            user_id, event.household_id
        )

    def _is_household_admin(self, user_id: int, household_id: int) -> bool:
        """Check if user is household admin"""
        admin_membership = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.role == HouseholdRole.ADMIN.value,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        )
        return admin_membership is not None

    def _has_scheduling_conflict(
        self, household_id: int, start_date: datetime, end_date: datetime = None
    ) -> bool:
        """Check for scheduling conflicts with existing events"""

        # Simple conflict check - can be made more sophisticated
        end_check = end_date or start_date + timedelta(hours=1)

        conflicts = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.household_id == household_id,
                    Event.status == EventStatus.PUBLISHED.value,
                    Event.start_date < end_check,
                    func.coalesce(Event.end_date, Event.start_date + timedelta(hours=1))
                    > start_date,
                )
            )
            .first()
        )

        return conflicts is not None

    def _would_exceed_capacity(
        self, event: Event, guest_count: int, user_id: int
    ) -> bool:
        """Check if RSVP would exceed event capacity"""
        if not event.max_attendees:
            return False

        current_summary = self._get_event_rsvp_summary(event.id)

        # Subtract current user's guest count if they already RSVP'd
        existing_rsvp = (
            self.db.query(RSVP)
            .filter(and_(RSVP.event_id == event.id, RSVP.user_id == user_id))
            .first()
        )

        current_guests = current_summary["total_guests_attending"]
        if existing_rsvp and existing_rsvp.status == "yes":
            current_guests -= existing_rsvp.guest_count

        return current_guests + guest_count > event.max_attendees

    def _get_event_rsvp_summary(self, event_id: int) -> Dict[str, Any]:
        """Get RSVP summary for an event"""

        rsvps = self.db.query(RSVP).filter(RSVP.event_id == event_id).all()

        yes_count = len([r for r in rsvps if r.status == "yes"])
        no_count = len([r for r in rsvps if r.status == "no"])
        maybe_count = len([r for r in rsvps if r.status == "maybe"])

        total_guests = sum(r.guest_count for r in rsvps if r.status == "yes")

        return {
            "total_responses": len(rsvps),
            "yes_count": yes_count,
            "no_count": no_count,
            "maybe_count": maybe_count,
            "total_guests_attending": total_guests,
        }

    def _get_user_rsvp(self, event_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's RSVP for event"""

        rsvp = (
            self.db.query(RSVP)
            .filter(and_(RSVP.event_id == event_id, RSVP.user_id == user_id))
            .first()
        )

        if not rsvp:
            return None

        return {
            "status": rsvp.status,
            "guest_count": rsvp.guest_count,
            "special_requests": rsvp.special_requests,
            "response_notes": rsvp.response_notes,
            "responded_at": rsvp.created_at,
            "updated_at": rsvp.updated_at,
        }

    def _is_event_full(self, event: Event, rsvp_summary: Dict[str, Any]) -> bool:
        """Check if event is at capacity"""
        if not event.max_attendees:
            return False
        return rsvp_summary["total_guests_attending"] >= event.max_attendees

    def _publish_event(self, event_id: int, published_by: int) -> None:
        """Publish an event (internal method)"""
        event = self._get_event_or_raise(event_id)
        event.status = EventStatus.PUBLISHED.value
        event.updated_at = datetime.utcnow()
        self.db.commit()

    def _notify_event_status_change(self, event_id: int, approved: bool):
        """Notify about event status change"""
        # Integration point with notification service
        pass

    def _notify_event_cancelled(self, event_id: int, reason: str):
        """Notify attendees that event was cancelled"""
        # Integration point with notification service
        pass

    def get_event_statistics(
        self, household_id: int, user_id: int, months_back: int = 6
    ) -> Dict[str, Any]:
        """Get event statistics for household"""

        if not self._user_can_view_events(user_id, household_id):
            raise PermissionDeniedError("User cannot view household events")

        since_date = datetime.utcnow() - timedelta(days=months_back * 30)

        events = (
            self.db.query(Event)
            .filter(
                and_(Event.household_id == household_id, Event.created_at >= since_date)
            )
            .all()
        )

        published_events = [
            e for e in events if e.status == EventStatus.PUBLISHED.value
        ]
        cancelled_events = [
            e for e in events if e.status == EventStatus.CANCELLED.value
        ]
        completed_events = [
            e for e in events if e.status == EventStatus.COMPLETED.value
        ]

        # Calculate average attendance
        total_attendance = 0
        events_with_rsvps = 0

        for event in published_events + completed_events:
            summary = self._get_event_rsvp_summary(event.id)
            if summary["total_responses"] > 0:
                total_attendance += summary["yes_count"]
                events_with_rsvps += 1

        avg_attendance = (
            total_attendance / events_with_rsvps if events_with_rsvps > 0 else 0
        )

        # Most popular event type
        event_types = {}
        for event in published_events + completed_events:
            event_type = event.event_type
            event_types[event_type] = event_types.get(event_type, 0) + 1

        most_popular_type = (
            max(event_types, key=event_types.get) if event_types else None
        )

        return {
            "total_events_created": len(events),
            "published_events": len(published_events),
            "completed_events": len(completed_events),
            "cancelled_events": len(cancelled_events),
            "pending_events": len(
                [e for e in events if e.status == EventStatus.PENDING.value]
            ),
            "average_attendance": round(avg_attendance, 1),
            "most_popular_event_type": most_popular_type,
            "events_per_month": (
                round(len(published_events + completed_events) / months_back, 1)
                if months_back > 0
                else 0
            ),
        }

    def get_event_rsvps(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all RSVPs for a given event with user names"""

        rsvps = (
            self.db.query(RSVP, User)
            .join(User, RSVP.user_id == User.id)
            .filter(RSVP.event_id == event_id)
            .order_by(RSVP.created_at)
            .all()
        )

        return [
            {
                "user_id": user.id,
                "user_name": user.name,
                "status": rsvp.status,
                "guest_count": rsvp.guest_count,
                "special_requests": rsvp.special_requests,
                "response_notes": rsvp.response_notes,
                "responded_at": rsvp.created_at,
                "updated_at": rsvp.updated_at,
            }
            for rsvp, user in rsvps
        ]
