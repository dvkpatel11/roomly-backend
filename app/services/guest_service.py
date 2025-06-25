from app.models.guest_approval import GuestApproval
from app.models.household import Household
from app.models.household_membership import HouseholdMembership
from app.models.user import User
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from ..models.guest import Guest
from ..schemas.guest import GuestCreate


class GuestService:
    def __init__(self, db: Session):
        self.db = db

    def create_guest_request(
        self, guest_data: GuestCreate, household_id: int, hosted_by: int
    ) -> Guest:
        """Create guest request with overlap checking"""

        # Check for overlapping guest stays
        overlapping_guests = self._check_guest_overlaps(
            household_id, guest_data.check_in, guest_data.check_out
        )

        if overlapping_guests and guest_data.is_overnight:
            raise ValueError(f"Conflicts with existing guests: {overlapping_guests}")

        guest = Guest(
            name=guest_data.name,
            phone=guest_data.phone,
            email=guest_data.email,
            relationship_to_host=guest_data.relationship_to_host,
            check_in=guest_data.check_in,
            check_out=guest_data.check_out,
            is_overnight=guest_data.is_overnight,
            notes=guest_data.notes,
            household_id=household_id,
            hosted_by=hosted_by,
            is_approved=False,
        )

        self.db.add(guest)
        self.db.commit()
        self.db.refresh(guest)

        return guest

    def _check_guest_overlaps(
        self, household_id: int, check_in: datetime, check_out: Optional[datetime]
    ) -> List[str]:
        """Check for overlapping guest stays"""

        if not check_out:
            check_out = check_in + timedelta(days=1)

        overlapping = (
            self.db.query(Guest)
            .filter(
                and_(
                    Guest.household_id == household_id,
                    Guest.is_approved == True,
                    Guest.is_overnight == True,
                    or_(
                        and_(Guest.check_in <= check_in, Guest.check_out > check_in),
                        and_(Guest.check_in < check_out, Guest.check_out >= check_out),
                        and_(Guest.check_in >= check_in, Guest.check_out <= check_out),
                    ),
                )
            )
            .all()
        )

        return [f"{guest.name} ({guest.check_in.date()})" for guest in overlapping]

    def get_household_guests(
        self,
        household_id: int,
        upcoming_only: bool = True,
        include_pending: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get guests for household with filtering and pagination"""

        now = datetime.utcnow()
        query = self.db.query(Guest).filter(Guest.household_id == household_id)

        if upcoming_only:
            query = query.filter(Guest.check_in >= now)

        if not include_pending:
            query = query.filter(Guest.is_approved == True)

        # Get total count for pagination
        total_count = query.count()

        # Get guests with pagination
        guests = query.order_by(Guest.check_in.asc()).offset(offset).limit(limit).all()

        # Enrich with host info and approval status
        guest_list = []
        for guest in guests:
            host = self.db.query(User).filter(User.id == guest.hosted_by).first()
            approver = None
            if guest.approved_by:
                approver = (
                    self.db.query(User).filter(User.id == guest.approved_by).first()
                )

            # Get approval status details if pending
            approval_details = None
            if not guest.is_approved:
                approval_details = self._get_guest_approval_status(
                    guest.id, household_id
                )

            # Calculate stay duration
            stay_duration = None
            if guest.check_out:
                stay_duration = (guest.check_out - guest.check_in).days

            # Check for conflicts with other guests
            conflicts = self._check_guest_conflicts(guest, household_id)

            guest_list.append(
                {
                    "id": guest.id,
                    "name": guest.name,
                    "phone": guest.phone,
                    "email": guest.email,
                    "relationship_to_host": guest.relationship_to_host,
                    "check_in": guest.check_in,
                    "check_out": guest.check_out,
                    "is_overnight": guest.is_overnight,
                    "is_approved": guest.is_approved,
                    "notes": guest.notes,
                    "special_requests": guest.special_requests,
                    "hosted_by": guest.hosted_by,
                    "host_name": host.name if host else "Unknown",
                    "approved_by": guest.approved_by,
                    "approver_name": approver.name if approver else None,
                    "created_at": guest.created_at,
                    "updated_at": guest.updated_at,
                    "stay_duration_days": stay_duration,
                    "approval_status": approval_details,
                    "has_conflicts": len(conflicts) > 0,
                    "conflicts": conflicts,
                    "days_until_arrival": (
                        (guest.check_in - now).days if guest.check_in > now else None
                    ),
                    "is_current": now >= guest.check_in
                    and (not guest.check_out or now <= guest.check_out),
                }
            )

        return {
            "guests": guest_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
            "upcoming_only": upcoming_only,
            "include_pending": include_pending,
            "current_guests": len([g for g in guest_list if g["is_current"]]),
            "pending_approval": len([g for g in guest_list if not g["is_approved"]]),
        }

    def get_guest_details(self, guest_id: int) -> Dict[str, Any]:
        """Get detailed guest information with approval history"""

        guest = self.db.query(Guest).filter(Guest.id == guest_id).first()
        if not guest:
            raise ValueError("Guest not found")

        # Get host and approver info
        host = self.db.query(User).filter(User.id == guest.hosted_by).first()
        approver = None
        if guest.approved_by:
            approver = self.db.query(User).filter(User.id == guest.approved_by).first()

        # Get all approval records
        approval_records = (
            self.db.query(GuestApproval, User.name)
            .join(User, GuestApproval.user_id == User.id)
            .filter(GuestApproval.guest_id == guest_id)
            .order_by(GuestApproval.created_at.desc())
            .all()
        )

        approval_history = []
        for approval, user_name in approval_records:
            approval_history.append(
                {
                    "user_id": approval.user_id,
                    "user_name": user_name,
                    "approved": approval.approved,
                    "reason": approval.reason,
                    "voted_at": approval.created_at,
                }
            )

        # Check current approval status
        if not guest.is_approved:
            approval_status = self._get_guest_approval_status(
                guest.id, guest.household_id
            )
        else:
            approval_status = {
                "fully_approved": True,
                "pending_approvals": 0,
                "total_required": len(approval_history),
            }

        # Check for scheduling conflicts
        conflicts = self._check_guest_conflicts(guest, guest.household_id)

        # Get household guest policies
        household = (
            self.db.query(Household).filter(Household.id == guest.household_id).first()
        )
        guest_policies = (
            household.settings.get("guest_policy", {})
            if household and household.settings
            else {}
        )

        # Calculate stay statistics
        now = datetime.utcnow()
        stay_duration = None
        if guest.check_out:
            stay_duration = (guest.check_out - guest.check_in).days

        return {
            "guest": {
                "id": guest.id,
                "name": guest.name,
                "phone": guest.phone,
                "email": guest.email,
                "relationship_to_host": guest.relationship_to_host,
                "check_in": guest.check_in,
                "check_out": guest.check_out,
                "is_overnight": guest.is_overnight,
                "is_approved": guest.is_approved,
                "notes": guest.notes,
                "special_requests": guest.special_requests,
                "created_at": guest.created_at,
                "updated_at": guest.updated_at,
                "stay_duration_days": stay_duration,
                "days_until_arrival": (
                    (guest.check_in - now).days if guest.check_in > now else None
                ),
                "is_current": now >= guest.check_in
                and (not guest.check_out or now <= guest.check_out),
                "is_past": guest.check_out and now > guest.check_out,
            },
            "host_info": {
                "id": guest.hosted_by,
                "name": host.name if host else "Unknown",
                "email": host.email if host else None,
            },
            "approval_info": {
                "is_approved": guest.is_approved,
                "approved_by": guest.approved_by,
                "approver_name": approver.name if approver else None,
                "approval_status": approval_status,
                "approval_history": approval_history,
            },
            "conflicts": conflicts,
            "household_policies": guest_policies,
            "can_edit": True,  # This would be determined by user permissions in the router
            "can_approve": not guest.is_approved,
            "can_cancel": not guest.is_approved or guest.check_in > now,
        }

    def _get_guest_approval_status(
        self, guest_id: int, household_id: int
    ) -> Dict[str, Any]:
        """Get detailed approval status for a guest"""

        total_members = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .count()
        )

        approvals_received = (
            self.db.query(GuestApproval)
            .filter(
                and_(GuestApproval.guest_id == guest_id, GuestApproval.approved == True)
            )
            .count()
        )

        pending_approvals = total_members - approvals_received

        return {
            "total_required": total_members,
            "approvals_received": approvals_received,
            "pending_approvals": pending_approvals,
            "fully_approved": pending_approvals == 0,
            "approval_percentage": (
                round((approvals_received / total_members * 100), 1)
                if total_members > 0
                else 0
            ),
        }

    def _check_guest_conflicts(
        self, guest: Guest, household_id: int
    ) -> List[Dict[str, Any]]:
        """Check for conflicts with other guests"""

        if not guest.check_out:
            check_out = guest.check_in + timedelta(days=1)  # Default 1 day
        else:
            check_out = guest.check_out

        # Find overlapping guests
        overlapping = (
            self.db.query(Guest)
            .filter(
                and_(
                    Guest.household_id == household_id,
                    Guest.id != guest.id,  # Exclude self
                    Guest.is_approved == True,
                    Guest.is_overnight == True,
                    or_(
                        and_(
                            Guest.check_in <= guest.check_in,
                            Guest.check_out > guest.check_in,
                        ),
                        and_(Guest.check_in < check_out, Guest.check_out >= check_out),
                        and_(
                            Guest.check_in >= guest.check_in,
                            Guest.check_out <= check_out,
                        ),
                    ),
                )
            )
            .all()
        )

        conflicts = []
        for conflict in overlapping:
            conflicts.append(
                {
                    "guest_id": conflict.id,
                    "guest_name": conflict.name,
                    "check_in": conflict.check_in,
                    "check_out": conflict.check_out,
                    "hosted_by": conflict.hosted_by,
                }
            )

        return conflicts

    def cancel_guest_request(
        self, guest_id: int, cancelled_by: int, household_id: int
    ) -> None:
        """Cancel a guest request (host only)"""

        guest = (
            self.db.query(Guest)
            .filter(
                Guest.id == guest_id,
                Guest.household_id == household_id,
                Guest.hosted_by == cancelled_by,
            )
            .first()
        )

        if not guest:
            raise ValueError("Guest not found or not authorized to cancel")

        if guest.is_approved:
            raise ValueError("Cannot cancel an approved guest")

        self.db.delete(guest)
        self.db.commit()

    def check_guest_conflicts(
        self,
        household_id: int,
        proposed_checkin: datetime,
        proposed_checkout: Optional[datetime],
        guest_count: int = 1,
    ) -> List[Dict[str, Any]]:
        """Public-facing check for proposed guest stay conflicts"""

        dummy_guest = Guest(
            id=-1,
            household_id=household_id,
            check_in=proposed_checkin,
            check_out=proposed_checkout,
            is_overnight=True,
        )
        return self._check_guest_conflicts(dummy_guest, household_id)

    def get_guest_templates(
        self, household_id: int, user_id: int
    ) -> List[Dict[str, Any]]:
        """Return recently hosted guest entries for reuse as templates"""

        recent_guests = (
            self.db.query(Guest)
            .filter(
                Guest.household_id == household_id,
                Guest.hosted_by == user_id,
            )
            .order_by(Guest.created_at.desc())
            .limit(5)
            .all()
        )

        return [
            {
                "name": g.name,
                "email": g.email,
                "phone": g.phone,
                "relationship_to_host": g.relationship_to_host,
                "is_overnight": g.is_overnight,
                "notes": g.notes,
                "special_requests": g.special_requests,
            }
            for g in recent_guests
        ]

    def get_user_hosted_guests(
        self,
        user_id: int,
        household_id: int,
        upcoming_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get upcoming guests hosted by the user"""

        now = datetime.utcnow()
        query = self.db.query(Guest).filter(
            Guest.household_id == household_id,
            Guest.hosted_by == user_id,
        )

        if upcoming_only:
            query = query.filter(Guest.check_in >= now)

        total_count = query.count()
        guests = query.order_by(Guest.check_in.asc()).offset(offset).limit(limit).all()

        guest_list = [
            {
                "id": g.id,
                "name": g.name,
                "check_in": g.check_in,
                "check_out": g.check_out,
                "is_approved": g.is_approved,
                "is_overnight": g.is_overnight,
                "notes": g.notes,
                "created_at": g.created_at,
            }
            for g in guests
        ]

        return {
            "guests": guest_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }
