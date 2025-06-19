from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any
from datetime import datetime, timedelta
from ..models.event import Event
from ..models.rsvp import RSVP
from ..models.user import User
from ..schemas.event import EventCreate
from ..schemas.rsvp import RSVPCreate


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def create_event(
        self, event_data: EventCreate, household_id: int, created_by: int
    ) -> Event:
        """Create a new event (pending approval)"""

        event = Event(
            title=event_data.title,
            description=event_data.description,
            event_type=event_data.event_type.value,
            start_date=event_data.start_date,
            end_date=event_data.end_date,
            location=event_data.location,
            max_attendees=event_data.max_attendees,
            is_public=event_data.is_public,
            requires_approval=True,  # All events require approval
            household_id=household_id,
            created_by=created_by,
            status="pending_approval",
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        return event

    def get_household_events(
        self, household_id: int, include_pending: bool = True, days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get events for household"""

        now = datetime.utcnow()
        future_cutoff = now + timedelta(days=days_ahead)

        query = self.db.query(Event).filter(
            and_(
                Event.household_id == household_id,
                Event.start_date >= now,
                Event.start_date <= future_cutoff,
            )
        )

        if not include_pending:
            query = query.filter(Event.status == "published")

        events = query.order_by(Event.start_date).all()

        result = []
        for event in events:
            creator = self.db.query(User).filter(User.id == event.created_by).first()
            rsvp_summary = self._get_event_rsvp_summary(event.id)

            result.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "event_type": event.event_type,
                    "start_date": event.start_date,
                    "end_date": event.end_date,
                    "location": event.location,
                    "status": event.status,
                    "creator_name": creator.name if creator else "Unknown",
                    "max_attendees": event.max_attendees,
                    "rsvp_summary": rsvp_summary,
                    "is_full": self._is_event_full(event, rsvp_summary),
                    "created_at": event.created_at,
                }
            )

        return result

    def create_rsvp(self, rsvp_data: RSVPCreate, user_id: int) -> RSVP:
        """Create or update RSVP for event"""

        event = self.db.query(Event).filter(Event.id == rsvp_data.event_id).first()
        if not event:
            raise ValueError("Event not found")

        if event.status != "published":
            raise ValueError("Cannot RSVP to unpublished event")

        # Check for existing RSVP
        existing_rsvp = (
            self.db.query(RSVP)
            .filter(and_(RSVP.event_id == rsvp_data.event_id, RSVP.user_id == user_id))
            .first()
        )

        if existing_rsvp:
            # Update existing RSVP
            existing_rsvp.status = rsvp_data.status.value
            existing_rsvp.guest_count = rsvp_data.guest_count
            existing_rsvp.dietary_restrictions = rsvp_data.dietary_restrictions
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
                dietary_restrictions=rsvp_data.dietary_restrictions,
                special_requests=rsvp_data.special_requests,
                response_notes=rsvp_data.response_notes,
            )

            self.db.add(rsvp)
            self.db.commit()
            self.db.refresh(rsvp)

            return rsvp

    def get_event_rsvps(self, event_id: int) -> Dict[str, Any]:
        """Get all RSVPs for an event"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError("Event not found")

        rsvps = self.db.query(RSVP).filter(RSVP.event_id == event_id).all()

        rsvp_details = []
        for rsvp in rsvps:
            user = self.db.query(User).filter(User.id == rsvp.user_id).first()

            rsvp_details.append(
                {
                    "user_id": rsvp.user_id,
                    "user_name": user.name if user else "Unknown",
                    "status": rsvp.status,
                    "guest_count": rsvp.guest_count,
                    "dietary_restrictions": rsvp.dietary_restrictions,
                    "special_requests": rsvp.special_requests,
                    "response_notes": rsvp.response_notes,
                    "responded_at": rsvp.created_at,
                }
            )

        summary = self._get_event_rsvp_summary(event_id)

        return {
            "event_id": event_id,
            "event_title": event.title,
            "rsvp_summary": summary,
            "rsvp_details": rsvp_details,
            "is_full": self._is_event_full(event, summary),
        }

    def cancel_event(self, event_id: int, cancelled_by: int, reason: str = "") -> bool:
        """Cancel an event"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return False

        if event.status == "cancelled":
            return True

        event.status = "cancelled"
        # Could add cancellation reason and cancelled_by fields
        self.db.commit()

        # Notify all attendees (integrate with notification service)
        self._notify_event_cancelled(event_id, reason)

        return True

    def get_user_upcoming_events(
        self, user_id: int, days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get upcoming events for a user (based on RSVPs)"""

        now = datetime.utcnow()
        future_cutoff = now + timedelta(days=days_ahead)

        # Get events user has RSVP'd "yes" to
        rsvps = (
            self.db.query(RSVP)
            .join(Event)
            .filter(
                and_(
                    RSVP.user_id == user_id,
                    RSVP.status == "yes",
                    Event.status == "published",
                    Event.start_date >= now,
                    Event.start_date <= future_cutoff,
                )
            )
            .all()
        )

        result = []
        for rsvp in rsvps:
            event = rsvp.event

            result.append(
                {
                    "event_id": event.id,
                    "title": event.title,
                    "start_date": event.start_date,
                    "end_date": event.end_date,
                    "location": event.location,
                    "event_type": event.event_type,
                    "guest_count": rsvp.guest_count,
                    "your_rsvp": {
                        "status": rsvp.status,
                        "guest_count": rsvp.guest_count,
                        "dietary_restrictions": rsvp.dietary_restrictions,
                    },
                }
            )

        return sorted(result, key=lambda x: x["start_date"])

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

    def _is_event_full(self, event: Event, rsvp_summary: Dict[str, Any]) -> bool:
        """Check if event is at capacity"""

        if not event.max_attendees:
            return False

        return rsvp_summary["total_guests_attending"] >= event.max_attendees

    def _notify_event_cancelled(self, event_id: int, reason: str):
        """Notify attendees that event was cancelled"""
        # Integrate with notification service
        pass

    def get_event_statistics(
        self, household_id: int, months_back: int = 6
    ) -> Dict[str, Any]:
        """Get event statistics for household"""

        since_date = datetime.utcnow() - timedelta(days=months_back * 30)

        events = (
            self.db.query(Event)
            .filter(
                and_(Event.household_id == household_id, Event.created_at >= since_date)
            )
            .all()
        )

        published_events = [e for e in events if e.status == "published"]
        cancelled_events = [e for e in events if e.status == "cancelled"]

        # Calculate average attendance
        total_attendance = 0
        events_with_rsvps = 0

        for event in published_events:
            summary = self._get_event_rsvp_summary(event.id)
            if summary["total_responses"] > 0:
                total_attendance += summary["yes_count"]
                events_with_rsvps += 1

        avg_attendance = (
            total_attendance / events_with_rsvps if events_with_rsvps > 0 else 0
        )

        # Most popular event type
        event_types = {}
        for event in published_events:
            event_type = event.event_type
            if event_type not in event_types:
                event_types[event_type] = 0
            event_types[event_type] += 1

        most_popular_type = (
            max(event_types, key=event_types.get) if event_types else None
        )

        return {
            "total_events_created": len(events),
            "published_events": len(published_events),
            "cancelled_events": len(cancelled_events),
            "average_attendance": round(avg_attendance, 1),
            "most_popular_event_type": most_popular_type,
            "events_per_month": (
                len(published_events) / months_back if months_back > 0 else 0
            ),
        }

    def get_pending_events_for_approval(
        self, household_id: int
    ) -> List[Dict[str, Any]]:
        """Get events pending approval"""

        pending_events = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.household_id == household_id,
                    Event.status == "pending_approval",
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
                    "creator_name": creator.name if creator else "Unknown",
                    "created_at": event.created_at,
                }
            )

        return result
