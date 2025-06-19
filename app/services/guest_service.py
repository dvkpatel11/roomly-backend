from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.event import Event
from ..models.rsvp import RSVP
from ..models.user import User
from ..schemas.event import EventCreate, EventUpdate
from ..schemas.rsvp import RSVPCreate, RSVPUpdate




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
