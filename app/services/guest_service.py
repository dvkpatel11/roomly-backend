from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
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
