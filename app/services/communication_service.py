from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.announcement import Announcement
from ..models.poll import Poll, PollVote
from ..models.user import User
from ..models.household_membership import HouseholdMembership
from ..models.enums import HouseholdRole
from ..schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from ..schemas.poll import PollCreate, PollUpdate, PollVoteCreate
from dataclasses import dataclass


# Custom Exceptions
class CommunicationServiceError(Exception):
    """Base exception for communication service errors"""

    pass


class AnnouncementNotFoundError(CommunicationServiceError):
    """Announcement not found"""

    pass


class PollNotFoundError(CommunicationServiceError):
    """Poll not found"""

    pass


class PermissionDeniedError(CommunicationServiceError):
    """Permission denied for operation"""

    pass


class BusinessRuleViolationError(CommunicationServiceError):
    """Business rule violation"""

    pass


class VotingError(CommunicationServiceError):
    """Voting validation error"""

    pass


@dataclass
class HouseholdMember:
    """Communication service household member representation"""

    id: int
    name: str
    email: str
    role: str


class CommunicationService:
    def __init__(self, db: Session):
        self.db = db

    def create_announcement(
        self, announcement_data: AnnouncementCreate, household_id: int, created_by: int
    ) -> Announcement:
        """Create a new announcement with proper validation"""

        # Validate permissions
        if not self._user_can_create_announcements(created_by, household_id):
            raise PermissionDeniedError("User is not a member of this household")

        # Validate expiration date
        if (
            announcement_data.expires_at
            and announcement_data.expires_at <= datetime.utcnow()
        ):
            raise BusinessRuleViolationError("Expiration date must be in the future")

        try:
            announcement = Announcement(
                title=announcement_data.title,
                content=announcement_data.content,
                category=announcement_data.category.value,
                priority=announcement_data.priority.value,
                is_pinned=announcement_data.is_pinned,
                expires_at=announcement_data.expires_at,
                household_id=household_id,
                created_by=created_by,
            )

            self.db.add(announcement)
            self.db.commit()
            self.db.refresh(announcement)

            # Trigger notifications for household members
            self._notify_announcement(announcement)

            return announcement

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to create announcement: {str(e)}")

    def update_announcement(
        self,
        announcement_id: int,
        announcement_updates: AnnouncementUpdate,
        updated_by: int,
    ) -> Announcement:
        """Update announcement with permission validation"""

        announcement = self._get_announcement_or_raise(announcement_id)

        # Check permissions (creator or household admin can edit)
        if not self._user_can_edit_announcement(updated_by, announcement):
            raise PermissionDeniedError(
                "Only announcement creator or household admin can edit"
            )

        try:
            # Update fields
            update_data = announcement_updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field == "expires_at" and value and value <= datetime.utcnow():
                    raise BusinessRuleViolationError(
                        "Expiration date must be in the future"
                    )

                setattr(
                    announcement,
                    field,
                    value.value if hasattr(value, "value") else value,
                )

            announcement.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(announcement)
            return announcement

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to update announcement: {str(e)}")

    def delete_announcement(self, announcement_id: int, deleted_by: int) -> bool:
        """Delete announcement with proper validation"""

        announcement = self._get_announcement_or_raise(announcement_id)

        if not self._user_can_edit_announcement(deleted_by, announcement):
            raise PermissionDeniedError(
                "Only announcement creator or household admin can delete"
            )

        try:
            self.db.delete(announcement)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to delete announcement: {str(e)}")

    def pin_announcement(
        self, announcement_id: int, user_id: int, pinned: bool = True
    ) -> bool:
        """Pin or unpin an announcement (admin only)"""

        announcement = self._get_announcement_or_raise(announcement_id)

        # Only admins can pin announcements
        if not self._is_household_admin(user_id, announcement.household_id):
            raise PermissionDeniedError("Only household admins can pin announcements")

        try:
            announcement.is_pinned = pinned
            announcement.updated_at = datetime.utcnow()
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to pin announcement: {str(e)}")

    def get_household_announcements(
        self,
        household_id: int,
        user_id: int,
        category: Optional[str] = None,
        include_expired: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get announcements for household with filtering and pagination"""

        if not self._user_can_view_announcements(user_id, household_id):
            raise PermissionDeniedError("User cannot view household announcements")

        query = self.db.query(Announcement).filter(
            Announcement.household_id == household_id
        )

        if category:
            query = query.filter(Announcement.category == category)

        if not include_expired:
            now = datetime.utcnow()
            query = query.filter(
                or_(Announcement.expires_at.is_(None), Announcement.expires_at > now)
            )

        # Get total count for pagination
        total_count = query.count()

        # Order by: pinned first, then by creation date (newest first)
        announcements = (
            query.order_by(desc(Announcement.is_pinned), desc(Announcement.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        announcement_list = []
        for announcement in announcements:
            author = (
                self.db.query(User).filter(User.id == announcement.created_by).first()
            )

            announcement_list.append(
                {
                    "id": announcement.id,
                    "title": announcement.title,
                    "content": announcement.content,
                    "category": announcement.category,
                    "priority": announcement.priority,
                    "is_pinned": announcement.is_pinned,
                    "created_by": announcement.created_by,
                    "author_name": author.name if author else "Unknown",
                    "created_at": announcement.created_at,
                    "updated_at": announcement.updated_at,
                    "expires_at": announcement.expires_at,
                    "is_expired": self._is_announcement_expired(announcement),
                    "can_edit": self._user_can_edit_announcement(user_id, announcement),
                }
            )

        return {
            "announcements": announcement_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    def get_announcement_details(
        self, announcement_id: int, user_id: int
    ) -> Dict[str, Any]:
        """Get detailed announcement information"""

        announcement = self._get_announcement_or_raise(announcement_id)

        if not self._user_can_view_announcements(user_id, announcement.household_id):
            raise PermissionDeniedError("User cannot view this announcement")

        author = self.db.query(User).filter(User.id == announcement.created_by).first()

        return {
            "announcement": {
                "id": announcement.id,
                "title": announcement.title,
                "content": announcement.content,
                "category": announcement.category,
                "priority": announcement.priority,
                "is_pinned": announcement.is_pinned,
                "created_by": announcement.created_by,
                "author_name": author.name if author else "Unknown",
                "created_at": announcement.created_at,
                "updated_at": announcement.updated_at,
                "expires_at": announcement.expires_at,
                "is_expired": self._is_announcement_expired(announcement),
            },
            "can_edit": self._user_can_edit_announcement(user_id, announcement),
            "can_pin": self._is_household_admin(user_id, announcement.household_id),
        }

    def create_poll(
        self, poll_data: PollCreate, household_id: int, created_by: int
    ) -> Poll:
        """Create a new poll with proper validation"""

        # Validate permissions
        if not self._user_can_create_polls(created_by, household_id):
            raise PermissionDeniedError("User is not a member of this household")

        # Validate poll options
        if len(poll_data.options) < 2:
            raise BusinessRuleViolationError("Poll must have at least 2 options")

        if len(set(poll_data.options)) != len(poll_data.options):
            raise BusinessRuleViolationError("Poll options must be unique")

        # Validate closing date
        if poll_data.closes_at and poll_data.closes_at <= datetime.utcnow():
            raise BusinessRuleViolationError("Poll closing date must be in the future")

        try:
            poll = Poll(
                question=poll_data.question,
                description=poll_data.description,
                options=poll_data.options,
                is_multiple_choice=poll_data.is_multiple_choice,
                is_anonymous=poll_data.is_anonymous,
                closes_at=poll_data.closes_at,
                household_id=household_id,
                created_by=created_by,
                is_active=True,
            )

            self.db.add(poll)
            self.db.commit()
            self.db.refresh(poll)

            # Notify household members about new poll
            self._notify_poll_created(poll)

            return poll

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to create poll: {str(e)}")

    def update_poll(
        self, poll_id: int, poll_updates: PollUpdate, updated_by: int
    ) -> Poll:
        """Update poll with permission validation"""

        poll = self._get_poll_or_raise(poll_id)

        # Check permissions (creator or household admin can edit)
        if not self._user_can_edit_poll(updated_by, poll):
            raise PermissionDeniedError("Only poll creator or household admin can edit")

        # Prevent editing polls with votes (unless it's just description/close date)
        has_votes = (
            self.db.query(PollVote).filter(PollVote.poll_id == poll_id).first()
            is not None
        )

        if has_votes:
            # Only allow updating description and closes_at
            allowed_fields = {"description", "closes_at", "is_active"}
            update_fields = set(poll_updates.dict(exclude_unset=True).keys())

            if not update_fields.issubset(allowed_fields):
                raise BusinessRuleViolationError(
                    "Cannot modify question or options after votes are cast"
                )

        try:
            # Update fields
            update_data = poll_updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field == "closes_at" and value and value <= datetime.utcnow():
                    raise BusinessRuleViolationError(
                        "Poll closing date must be in the future"
                    )

                setattr(poll, field, value.value if hasattr(value, "value") else value)

            poll.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(poll)
            return poll

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to update poll: {str(e)}")

    def delete_poll(self, poll_id: int, deleted_by: int) -> bool:
        """Delete poll with proper validation"""

        poll = self._get_poll_or_raise(poll_id)

        if not self._user_can_edit_poll(deleted_by, poll):
            raise PermissionDeniedError(
                "Only poll creator or household admin can delete"
            )

        # Check if poll has votes
        has_votes = (
            self.db.query(PollVote).filter(PollVote.poll_id == poll_id).first()
            is not None
        )

        if has_votes:
            # Close instead of delete to preserve vote history
            return self.close_poll(poll_id, deleted_by)

        try:
            self.db.delete(poll)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to delete poll: {str(e)}")

    def vote_on_poll(
        self, poll_id: int, user_id: int, vote_data: PollVoteCreate
    ) -> Dict[str, Any]:
        """Cast vote on a poll with comprehensive validation"""

        poll = self._get_poll_or_raise(poll_id)

        # Validate permissions
        if not self._user_can_vote_on_poll(user_id, poll):
            raise PermissionDeniedError("User cannot vote on this poll")

        if not poll.is_active:
            raise VotingError("Poll is not active")

        if poll.closes_at and poll.closes_at <= datetime.utcnow():
            raise VotingError("Poll is closed")

        # Validate vote options
        if not vote_data.selected_options:
            raise VotingError("Must select at least one option")

        if max(vote_data.selected_options) >= len(poll.options):
            raise VotingError("Invalid option selected")

        if not poll.is_multiple_choice and len(vote_data.selected_options) > 1:
            raise VotingError("Poll allows only one selection")

        try:
            # Check if user already voted
            existing_vote = (
                self.db.query(PollVote)
                .filter(and_(PollVote.poll_id == poll_id, PollVote.user_id == user_id))
                .first()
            )

            if existing_vote:
                # Update existing vote
                existing_vote.selected_options = vote_data.selected_options
                existing_vote.updated_at = datetime.utcnow()
                self.db.commit()

                return {
                    "success": True,
                    "message": "Vote updated successfully",
                    "vote_updated": True,
                }
            else:
                # Create new vote
                vote = PollVote(
                    poll_id=poll_id,
                    user_id=user_id,
                    selected_options=vote_data.selected_options,
                )

                self.db.add(vote)
                self.db.commit()

                return {
                    "success": True,
                    "message": "Vote recorded successfully",
                    "vote_updated": False,
                }

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to record vote: {str(e)}")

    def get_poll_details(self, poll_id: int, user_id: int) -> Dict[str, Any]:
        """Get detailed poll information with results"""

        poll = self._get_poll_or_raise(poll_id)

        if not self._user_can_view_polls(user_id, poll.household_id):
            raise PermissionDeniedError("User cannot view this poll")

        creator = self.db.query(User).filter(User.id == poll.created_by).first()
        user_vote = self._get_user_vote(poll_id, user_id)
        results = self._get_poll_results_data(poll_id, poll)

        return {
            "poll": {
                "id": poll.id,
                "question": poll.question,
                "description": poll.description,
                "options": poll.options,
                "is_multiple_choice": poll.is_multiple_choice,
                "is_anonymous": poll.is_anonymous,
                "is_active": poll.is_active,
                "created_by": poll.created_by,
                "creator_name": creator.name if creator else "Unknown",
                "created_at": poll.created_at,
                "updated_at": poll.updated_at,
                "closes_at": poll.closes_at,
                "is_closed": poll.closes_at and poll.closes_at <= datetime.utcnow(),
            },
            "results": results,
            "user_vote": user_vote,
            "can_vote": self._user_can_vote_on_poll(user_id, poll) and poll.is_active,
            "can_edit": self._user_can_edit_poll(user_id, poll),
        }

    def get_household_polls(
        self,
        household_id: int,
        user_id: int,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get polls for household with filtering and pagination"""

        if not self._user_can_view_polls(user_id, household_id):
            raise PermissionDeniedError("User cannot view household polls")

        query = self.db.query(Poll).filter(Poll.household_id == household_id)

        if active_only:
            now = datetime.utcnow()
            query = query.filter(
                and_(
                    Poll.is_active == True,
                    or_(Poll.closes_at.is_(None), Poll.closes_at > now),
                )
            )

        # Get total count for pagination
        total_count = query.count()

        polls = query.order_by(desc(Poll.created_at)).offset(offset).limit(limit).all()

        poll_list = []
        for poll in polls:
            creator = self.db.query(User).filter(User.id == poll.created_by).first()
            vote_count = (
                self.db.query(PollVote).filter(PollVote.poll_id == poll.id).count()
            )
            user_vote = self._get_user_vote(poll.id, user_id)

            poll_list.append(
                {
                    "id": poll.id,
                    "question": poll.question,
                    "description": poll.description,
                    "created_by": poll.created_by,
                    "creator_name": creator.name if creator else "Unknown",
                    "total_votes": vote_count,
                    "closes_at": poll.closes_at,
                    "is_multiple_choice": poll.is_multiple_choice,
                    "is_anonymous": poll.is_anonymous,
                    "is_active": poll.is_active,
                    "is_closed": poll.closes_at and poll.closes_at <= datetime.utcnow(),
                    "user_has_voted": user_vote is not None,
                    "created_at": poll.created_at,
                    "can_edit": self._user_can_edit_poll(user_id, poll),
                }
            )

        return {
            "polls": poll_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    def close_poll(self, poll_id: int, closed_by: int) -> bool:
        """Close a poll (creator or admin only)"""

        poll = self._get_poll_or_raise(poll_id)

        if not self._user_can_edit_poll(closed_by, poll):
            raise PermissionDeniedError(
                "Only poll creator or household admin can close poll"
            )

        try:
            poll.is_active = False
            poll.closes_at = datetime.utcnow()
            poll.updated_at = datetime.utcnow()
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise CommunicationServiceError(f"Failed to close poll: {str(e)}")

    def get_user_communication_summary(
        self, user_id: int, household_id: int
    ) -> Dict[str, Any]:
        """Get user's communication activity summary"""

        if not self._user_can_view_announcements(user_id, household_id):
            raise PermissionDeniedError("User cannot view household communication")

        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # User's announcements created
        announcements_created = (
            self.db.query(Announcement)
            .filter(
                and_(
                    Announcement.created_by == user_id,
                    Announcement.household_id == household_id,
                    Announcement.created_at >= month_ago,
                )
            )
            .count()
        )

        # User's polls created
        polls_created = (
            self.db.query(Poll)
            .filter(
                and_(
                    Poll.created_by == user_id,
                    Poll.household_id == household_id,
                    Poll.created_at >= month_ago,
                )
            )
            .count()
        )

        # User's poll participation
        polls_voted = (
            self.db.query(PollVote)
            .join(Poll, PollVote.poll_id == Poll.id)
            .filter(
                and_(
                    PollVote.user_id == user_id,
                    Poll.household_id == household_id,
                    PollVote.created_at >= month_ago,
                )
            )
            .count()
        )

        # Total polls available to vote on
        total_polls = (
            self.db.query(Poll)
            .filter(
                and_(
                    Poll.household_id == household_id,
                    Poll.created_at >= month_ago,
                )
            )
            .count()
        )

        participation_rate = (polls_voted / total_polls * 100) if total_polls > 0 else 0

        return {
            "user_id": user_id,
            "household_id": household_id,
            "announcements_created_last_month": announcements_created,
            "polls_created_last_month": polls_created,
            "polls_voted_last_month": polls_voted,
            "total_polls_last_month": total_polls,
            "poll_participation_rate": round(participation_rate, 1),
            "communication_activity_score": min(
                100,
                (announcements_created * 10) + (polls_created * 15) + (polls_voted * 5),
            ),
        }

    def get_household_communication_summary(
        self, household_id: int, user_id: int
    ) -> Dict[str, Any]:
        """Get household communication activity summary"""

        if not self._user_can_view_announcements(user_id, household_id):
            raise PermissionDeniedError("User cannot view household communication")

        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        # Recent announcements
        recent_announcements = (
            self.db.query(Announcement)
            .filter(
                and_(
                    Announcement.household_id == household_id,
                    Announcement.created_at >= week_ago,
                )
            )
            .count()
        )

        # Active polls
        active_polls = (
            self.db.query(Poll)
            .filter(and_(Poll.household_id == household_id, Poll.is_active == True))
            .count()
        )

        # Pinned announcements
        pinned_announcements = (
            self.db.query(Announcement)
            .filter(
                and_(
                    Announcement.household_id == household_id,
                    Announcement.is_pinned == True,
                )
            )
            .count()
        )

        # Unread announcements (last 3 days)
        recent_cutoff = now - timedelta(days=3)
        unread_announcements = (
            self.db.query(Announcement)
            .filter(
                and_(
                    Announcement.household_id == household_id,
                    Announcement.created_at >= recent_cutoff,
                    or_(
                        Announcement.expires_at.is_(None), Announcement.expires_at > now
                    ),
                )
            )
            .count()
        )

        return {
            "household_id": household_id,
            "recent_announcements": recent_announcements,
            "active_polls": active_polls,
            "pinned_announcements": pinned_announcements,
            "unread_announcements": unread_announcements,
            "communication_activity_score": min(
                100, (recent_announcements * 10) + (active_polls * 20)
            ),
        }

    # === HELPER METHODS ===

    def _get_announcement_or_raise(self, announcement_id: int) -> Announcement:
        """Get announcement or raise exception"""
        announcement = (
            self.db.query(Announcement)
            .filter(Announcement.id == announcement_id)
            .first()
        )
        if not announcement:
            raise AnnouncementNotFoundError(f"Announcement {announcement_id} not found")
        return announcement

    def _get_poll_or_raise(self, poll_id: int) -> Poll:
        """Get poll or raise exception"""
        poll = self.db.query(Poll).filter(Poll.id == poll_id).first()
        if not poll:
            raise PollNotFoundError(f"Poll {poll_id} not found")
        return poll

    def _user_can_create_announcements(self, user_id: int, household_id: int) -> bool:
        """Check if user can create announcements for household"""
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

    def _user_can_edit_announcement(
        self, user_id: int, announcement: Announcement
    ) -> bool:
        """Check if user can edit announcement (creator or admin)"""
        if announcement.created_by == user_id:
            return True
        return self._is_household_admin(user_id, announcement.household_id)

    def _user_can_view_announcements(self, user_id: int, household_id: int) -> bool:
        """Check if user can view household announcements"""
        return self._user_can_create_announcements(user_id, household_id)

    def _user_can_create_polls(self, user_id: int, household_id: int) -> bool:
        """Check if user can create polls for household"""
        return self._user_can_create_announcements(user_id, household_id)

    def _user_can_edit_poll(self, user_id: int, poll: Poll) -> bool:
        """Check if user can edit poll (creator or admin)"""
        if poll.created_by == user_id:
            return True
        return self._is_household_admin(user_id, poll.household_id)

    def _user_can_view_polls(self, user_id: int, household_id: int) -> bool:
        """Check if user can view household polls"""
        return self._user_can_create_announcements(user_id, household_id)

    def _user_can_vote_on_poll(self, user_id: int, poll: Poll) -> bool:
        """Check if user can vote on poll"""
        return self._user_can_view_polls(user_id, poll.household_id)

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

    def _is_announcement_expired(self, announcement: Announcement) -> bool:
        """Check if announcement is expired"""
        if not announcement.expires_at:
            return False
        return announcement.expires_at <= datetime.utcnow()

    def _get_user_vote(self, poll_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's vote for a poll"""
        vote = (
            self.db.query(PollVote)
            .filter(and_(PollVote.poll_id == poll_id, PollVote.user_id == user_id))
            .first()
        )

        if not vote:
            return None

        return {
            "selected_options": vote.selected_options,
            "voted_at": vote.created_at,
            "updated_at": vote.updated_at,
        }

    def _get_poll_results_data(self, poll_id: int, poll: Poll) -> Dict[str, Any]:
        """Get comprehensive poll results"""

        votes = self.db.query(PollVote).filter(PollVote.poll_id == poll_id).all()
        total_votes = len(votes)

        results = []

        # Count votes for each option
        for i, option in enumerate(poll.options):
            vote_count = sum(1 for vote in votes if i in vote.selected_options)
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0

            results.append(
                {
                    "option_index": i,
                    "option_text": option,
                    "vote_count": vote_count,
                    "percentage": round(percentage, 1),
                }
            )

        # Get voter details (if not anonymous)
        voter_details = []
        if not poll.is_anonymous:
            for vote in votes:
                user = self.db.query(User).filter(User.id == vote.user_id).first()
                voter_details.append(
                    {
                        "user_id": vote.user_id,
                        "user_name": user.name if user else "Unknown",
                        "selected_options": vote.selected_options,
                        "voted_at": vote.created_at,
                    }
                )

        return {
            "total_votes": total_votes,
            "is_closed": poll.closes_at and poll.closes_at <= datetime.utcnow(),
            "option_results": results,
            "voter_details": voter_details if not poll.is_anonymous else None,
        }

    def _notify_announcement(self, announcement: Announcement):
        """Trigger notifications for new announcement"""
        # Integration point with notification service
        pass

    def _notify_poll_created(self, poll: Poll):
        """Trigger notifications for new poll"""
        # Integration point with notification service
        pass
