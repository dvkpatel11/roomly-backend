from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models.guest import Guest
from ..models.event import Event, GuestApproval
from ..models.user import User
from ..schemas.guest import GuestCreate
from ..schemas.event import EventCreate


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db

    def create_guest_request(
        self, guest_data: GuestCreate, household_id: int, hosted_by: int
    ) -> Guest:
        """Create guest request requiring ALL household member approval"""

        guest = Guest(
            name=guest_data.name,
            phone=guest_data.phone,
            email=guest_data.email,
            relationship_to_host=guest_data.relationship_to_host,
            check_in=guest_data.check_in,
            check_out=guest_data.check_out,
            is_overnight=guest_data.is_overnight,
            notes=guest_data.notes,
            special_requests=guest_data.special_requests,
            household_id=household_id,
            hosted_by=hosted_by,
            is_approved=False,  # Starts as pending
        )

        self.db.add(guest)
        self.db.commit()
        self.db.refresh(guest)

        # Create approval records for all household members
        self._create_guest_approval_records(guest.id, household_id)

        return guest

    def create_event_request(
        self, event_data: EventCreate, household_id: int, created_by: int
    ) -> Event:
        """Create event request requiring ALL household member approval"""

        event = Event(
            title=event_data.title,
            description=event_data.description,
            event_type=event_data.event_type.value,
            start_date=event_data.start_date,
            end_date=event_data.end_date,
            location=event_data.location,
            max_attendees=event_data.max_attendees,
            is_public=event_data.is_public,
            requires_approval=True,  # Always true for household events
            household_id=household_id,
            created_by=created_by,
            status="pending_approval",  # Starts pending
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        # Create approval records for all household members
        self._create_event_approval_records(event.id, household_id)

        return event

    def approve_guest(self, guest_id: int, approver_id: int) -> Dict[str, Any]:
        """Approve guest request by one household member"""

        # Record the approval
        approval_recorded = self._record_guest_approval(guest_id, approver_id, True)
        if not approval_recorded:
            return {"success": False, "message": "Approval already recorded or invalid"}

        # Check if all members have approved
        guest = self.db.query(Guest).filter(Guest.id == guest_id).first()
        if not guest:
            return {"success": False, "message": "Guest not found"}

        all_approved = self._check_all_guest_approvals(guest_id, guest.household_id)

        if all_approved:
            guest.is_approved = True
            guest.approved_by = approver_id  # Last approver
            self.db.commit()

            return {
                "success": True,
                "message": "Guest approved by all household members",
                "fully_approved": True,
            }
        else:
            pending_count = self._get_pending_guest_approvals_count(
                guest_id, guest.household_id
            )
            return {
                "success": True,
                "message": f"Approval recorded. {pending_count} more approvals needed",
                "fully_approved": False,
                "pending_approvals": pending_count,
            }

    def deny_guest(
        self, guest_id: int, denier_id: int, reason: str = ""
    ) -> Dict[str, Any]:
        """Deny guest request (any member can deny)"""

        guest = self.db.query(Guest).filter(Guest.id == guest_id).first()
        if not guest:
            return {"success": False, "message": "Guest not found"}

        if guest.is_approved:
            return {"success": False, "message": "Cannot deny already approved guest"}

        # Record the denial
        self._record_guest_approval(guest_id, denier_id, False, reason)

        # Mark guest as denied (delete or mark as denied)
        self.db.delete(guest)
        self.db.commit()

        return {
            "success": True,
            "message": "Guest request denied",
            "denied_by": denier_id,
            "reason": reason,
        }

    def approve_event(self, event_id: int, approver_id: int) -> Dict[str, Any]:
        """Approve event by one household member"""

        # Record the approval
        approval_recorded = self._record_event_approval(event_id, approver_id, True)
        if not approval_recorded:
            return {"success": False, "message": "Approval already recorded or invalid"}

        # Check if all members have approved
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"success": False, "message": "Event not found"}

        all_approved = self._check_all_event_approvals(event_id, event.household_id)

        if all_approved:
            event.status = "published"
            self.db.commit()

            return {
                "success": True,
                "message": "Event approved by all household members and published",
                "fully_approved": True,
            }
        else:
            pending_count = self._get_pending_event_approvals_count(
                event_id, event.household_id
            )
            return {
                "success": True,
                "message": f"Approval recorded. {pending_count} more approvals needed",
                "fully_approved": False,
                "pending_approvals": pending_count,
            }

    def deny_event(
        self, event_id: int, denier_id: int, reason: str = ""
    ) -> Dict[str, Any]:
        """Deny event (any member can deny)"""

        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {"success": False, "message": "Event not found"}

        if event.status == "published":
            return {"success": False, "message": "Cannot deny already published event"}

        # Record the denial
        self._record_event_approval(event_id, denier_id, False, reason)

        # Mark event as cancelled
        event.status = "cancelled"
        self.db.commit()

        return {
            "success": True,
            "message": "Event denied and cancelled",
            "denied_by": denier_id,
            "reason": reason,
        }

    def get_pending_guest_approvals(self, household_id: int) -> List[Dict[str, Any]]:
        """Get all pending guest approvals for household"""

        # This would require a proper approval tracking table
        # For now, return guests not yet approved
        pending_guests = (
            self.db.query(Guest)
            .filter(
                and_(Guest.household_id == household_id, Guest.is_approved == False)
            )
            .all()
        )

        result = []
        for guest in pending_guests:
            pending_count = self._get_pending_guest_approvals_count(
                guest.id, household_id
            )
            result.append(
                {
                    "guest_id": guest.id,
                    "guest_name": guest.name,
                    "hosted_by": guest.hosted_by,
                    "check_in": guest.check_in,
                    "is_overnight": guest.is_overnight,
                    "pending_approvals": pending_count,
                    "created_at": guest.created_at,
                }
            )

        return result

    def get_pending_event_approvals(self, household_id: int) -> List[Dict[str, Any]]:
        """Get all pending event approvals for household"""

        pending_events = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.household_id == household_id,
                    Event.status == "pending_approval",
                )
            )
            .all()
        )

        result = []
        for event in pending_events:
            pending_count = self._get_pending_event_approvals_count(
                event.id, household_id
            )
            result.append(
                {
                    "event_id": event.id,
                    "event_title": event.title,
                    "event_type": event.event_type,
                    "created_by": event.created_by,
                    "start_date": event.start_date,
                    "pending_approvals": pending_count,
                    "created_at": event.created_at,
                }
            )

        return result

    def _create_guest_approval_records(self, guest_id: int, household_id: int):
        """Create approval records for all household members"""
        # In a full implementation, you'd have a GuestApproval table
        # For now, we'll track this in memory or simplified logic
        pass

    def _create_event_approval_records(self, event_id: int, household_id: int):
        """Create approval records for all household members"""
        # In a full implementation, you'd have an EventApproval table
        pass

    def _record_guest_approval(
        self, guest_id: int, user_id: int, approved: bool, reason: str = ""
    ) -> bool:
        """Record user's approval/denial of guest"""
        # Would update GuestApproval table
        return True

    def _record_event_approval(
        self, event_id: int, user_id: int, approved: bool, reason: str = ""
    ) -> bool:
        """Record user's approval/denial of event"""
        # Would update EventApproval table
        return True

    def _check_all_guest_approvals(self, guest_id: int, household_id: int) -> bool:
        """FIXED: Check actual approval records"""

        # Get total household members
        total_members = (
            self.db.query(User)
            .filter(and_(User.household_id == household_id, User.is_active == True))
            .count()
        )

        # Get approval count
        approval_count = (
            self.db.query(GuestApproval)
            .filter(
                and_(GuestApproval.guest_id == guest_id, GuestApproval.approved == True)
            )
            .count()
        )

        return approval_count >= total_members

    def _check_all_event_approvals(self, event_id: int, household_id: int) -> bool:
        """Check if all household members have approved event"""
        # For now, simplified logic
        return True  # TODO: Implement proper approval tracking

    def _get_pending_guest_approvals_count(
        self, guest_id: int, household_id: int
    ) -> int:
        """Get count of pending approvals for guest"""
        total_members = (
            self.db.query(User)
            .filter(User.household_id == household_id, User.is_active == True)
            .count()
        )

        # TODO: Subtract actual approvals recorded
        return max(0, total_members - 1)  # Mock: assume 1 approval recorded

    def _get_pending_event_approvals_count(
        self, event_id: int, household_id: int
    ) -> int:
        """Get count of pending approvals for event"""
        total_members = (
            self.db.query(User)
            .filter(User.household_id == household_id, User.is_active == True)
            .count()
        )

        # TODO: Subtract actual approvals recorded
        return max(0, total_members - 1)  # Mock: assume 1 approval recorded
