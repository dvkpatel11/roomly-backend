from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.announcement import Announcement
from ..models.poll import Poll, PollVote
from ..models.user import User
from ..schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from ..schemas.poll import PollCreate, PollUpdate, PollVoteCreate

class CommunicationService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_announcement(
        self, 
        announcement_data: AnnouncementCreate, 
        household_id: int, 
        created_by: int
    ) -> Announcement:
        """Create a new announcement"""
        
        announcement = Announcement(
            title=announcement_data.title,
            content=announcement_data.content,
            category=announcement_data.category.value,
            priority=announcement_data.priority.value,
            is_pinned=announcement_data.is_pinned,
            expires_at=announcement_data.expires_at,
            household_id=household_id,
            created_by=created_by
        )
        
        self.db.add(announcement)
        self.db.commit()
        self.db.refresh(announcement)
        
        # Trigger notifications for household members
        self._notify_announcement(announcement)
        
        return announcement
    
    def get_household_announcements(
        self, 
        household_id: int,
        category: Optional[str] = None,
        include_expired: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get announcements for household"""
        
        query = self.db.query(Announcement).filter(
            Announcement.household_id == household_id
        )
        
        if category:
            query = query.filter(Announcement.category == category)
        
        if not include_expired:
            now = datetime.utcnow()
            query = query.filter(
                or_(
                    Announcement.expires_at.is_(None),
                    Announcement.expires_at > now
                )
            )
        
        # Order by: pinned first, then by creation date (newest first)
        query = query.order_by(
            desc(Announcement.is_pinned),
            desc(Announcement.created_at)
        ).limit(limit)
        
        announcements = query.all()
        
        result = []
        for announcement in announcements:
            author = self.db.query(User).filter(User.id == announcement.created_by).first()
            
            result.append({
                "id": announcement.id,
                "title": announcement.title,
                "content": announcement.content,
                "category": announcement.category,
                "priority": announcement.priority,
                "is_pinned": announcement.is_pinned,
                "author_name": author.name if author else "Unknown",
                "created_at": announcement.created_at,
                "expires_at": announcement.expires_at,
                "is_expired": self._is_announcement_expired(announcement)
            })
        
        return result
    
    def pin_announcement(self, announcement_id: int, user_id: int) -> bool:
        """Pin or unpin an announcement"""
        
        announcement = self.db.query(Announcement).filter(
            Announcement.id == announcement_id
        ).first()
        
        if not announcement:
            return False
        
        # Toggle pin status
        announcement.is_pinned = not announcement.is_pinned
        self.db.commit()
        
        return True
    
    def create_poll(
        self, 
        poll_data: PollCreate, 
        household_id: int, 
        created_by: int
    ) -> Poll:
        """Create a new poll"""
        
        poll = Poll(
            question=poll_data.question,
            description=poll_data.description,
            options=poll_data.options,
            is_multiple_choice=poll_data.is_multiple_choice,
            is_anonymous=poll_data.is_anonymous,
            closes_at=poll_data.closes_at,
            household_id=household_id,
            created_by=created_by,
            is_active=True
        )
        
        self.db.add(poll)
        self.db.commit()
        self.db.refresh(poll)
        
        # Notify household members about new poll
        self._notify_poll_created(poll)
        
        return poll
    
    def vote_on_poll(
        self, 
        poll_id: int, 
        user_id: int, 
        vote_data: PollVoteCreate
    ) -> Dict[str, Any]:
        """Cast vote on a poll"""
        
        poll = self.db.query(Poll).filter(Poll.id == poll_id).first()
        if not poll:
            raise ValueError("Poll not found")
        
        if not poll.is_active:
            raise ValueError("Poll is not active")
        
        if poll.closes_at and poll.closes_at <= datetime.utcnow():
            raise ValueError("Poll is closed")
        
        # Check if user already voted
        existing_vote = self.db.query(PollVote).filter(
            and_(
                PollVote.poll_id == poll_id,
                PollVote.user_id == user_id
            )
        ).first()
        
        if existing_vote:
            # Update existing vote
            existing_vote.selected_options = vote_data.selected_options
            self.db.commit()
            
            return {
                "success": True,
                "message": "Vote updated successfully",
                "vote_updated": True
            }
        else:
            # Create new vote
            vote = PollVote(
                poll_id=poll_id,
                user_id=user_id,
                selected_options=vote_data.selected_options
            )
            
            self.db.add(vote)
            self.db.commit()
            
            return {
                "success": True,
                "message": "Vote recorded successfully",
                "vote_updated": False
            }
    
    def get_poll_results(self, poll_id: int) -> Dict[str, Any]:
        """Get poll results and statistics"""
        
        poll = self.db.query(Poll).filter(Poll.id == poll_id).first()
        if not poll:
            raise ValueError("Poll not found")
        
        votes = self.db.query(PollVote).filter(PollVote.poll_id == poll_id).all()
        
        total_votes = len(votes)
        results = []
        
        # Count votes for each option
        for i, option in enumerate(poll.options):
            vote_count = 0
            
            for vote in votes:
                if i in vote.selected_options:
                    vote_count += 1
            
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
            
            results.append({
                "option_index": i,
                "option_text": option,
                "vote_count": vote_count,
                "percentage": round(percentage, 1)
            })
        
        # Get voter details (if not anonymous)
        voter_details = []
        if not poll.is_anonymous:
            for vote in votes:
                user = self.db.query(User).filter(User.id == vote.user_id).first()
                voter_details.append({
                    "user_name": user.name if user else "Unknown",
                    "selected_options": vote.selected_options,
                    "voted_at": vote.created_at
                })
        
        return {
            "poll_id": poll.id,
            "question": poll.question,
            "total_votes": total_votes,
            "is_closed": poll.closes_at and poll.closes_at <= datetime.utcnow(),
            "results": results,
            "voter_details": voter_details if not poll.is_anonymous else None
        }
    
    def get_active_polls(self, household_id: int) -> List[Dict[str, Any]]:
        """Get active polls for household"""
        
        now = datetime.utcnow()
        
        polls = self.db.query(Poll).filter(
            and_(
                Poll.household_id == household_id,
                Poll.is_active == True,
                or_(
                    Poll.closes_at.is_(None),
                    Poll.closes_at > now
                )
            )
        ).order_by(desc(Poll.created_at)).all()
        
        result = []
        for poll in polls:
            creator = self.db.query(User).filter(User.id == poll.created_by).first()
            vote_count = self.db.query(PollVote).filter(PollVote.poll_id == poll.id).count()
            
            result.append({
                "id": poll.id,
                "question": poll.question,
                "description": poll.description,
                "creator_name": creator.name if creator else "Unknown",
                "total_votes": vote_count,
                "closes_at": poll.closes_at,
                "is_multiple_choice": poll.is_multiple_choice,
                "created_at": poll.created_at
            })
        
        return result
    
    def close_poll(self, poll_id: int, closed_by: int) -> bool:
        """Close a poll"""
        
        poll = self.db.query(Poll).filter(Poll.id == poll_id).first()
        if not poll:
            return False
        
        poll.is_active = False
        poll.closes_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def get_user_poll_participation(self, user_id: int, household_id: int) -> Dict[str, Any]:
        """Get user's poll participation statistics"""
        
        # Get all polls in household
        total_polls = self.db.query(Poll).filter(
            Poll.household_id == household_id
        ).count()
        
        # Get polls user voted on
        user_votes = self.db.query(PollVote).join(Poll).filter(
            and_(
                PollVote.user_id == user_id,
                Poll.household_id == household_id
            )
        ).count()
        
        participation_rate = (user_votes / total_polls * 100) if total_polls > 0 else 0
        
        return {
            "user_id": user_id,
            "total_polls": total_polls,
            "polls_voted": user_votes,
            "participation_rate": round(participation_rate, 1)
        }
    
    def _notify_announcement(self, announcement: Announcement):
        """Trigger notifications for new announcement"""
        # This would integrate with notification service
        # For now, just placeholder
        pass
    
    def _notify_poll_created(self, poll: Poll):
        """Trigger notifications for new poll"""
        # This would integrate with notification service
        pass
    
    def _is_announcement_expired(self, announcement: Announcement) -> bool:
        """Check if announcement is expired"""
        if not announcement.expires_at:
            return False
        
        return announcement.expires_at <= datetime.utcnow()
    
    def get_communication_summary(self, household_id: int) -> Dict[str, Any]:
        """Get communication activity summary"""
        
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        
        # Recent announcements
        recent_announcements = self.db.query(Announcement).filter(
            and_(
                Announcement.household_id == household_id,
                Announcement.created_at >= week_ago
            )
        ).count()
        
        # Active polls
        active_polls = self.db.query(Poll).filter(
            and_(
                Poll.household_id == household_id,
                Poll.is_active == True
            )
        ).count()
        
        # Pinned announcements
        pinned_announcements = self.db.query(Announcement).filter(
            and_(
                Announcement.household_id == household_id,
                Announcement.is_pinned == True
            )
        ).count()
        
        return {
            "recent_announcements": recent_announcements,
            "active_polls": active_polls,
            "pinned_announcements": pinned_announcements,
            "communication_activity_score": min(100, (recent_announcements * 10) + (active_polls * 20))
        }
