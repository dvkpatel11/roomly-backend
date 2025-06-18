from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Poll(Base):
    __tablename__ = "polls"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    description = Column(Text)
    options = Column(JSON, nullable=False)  # List of option strings
    is_multiple_choice = Column(Boolean, default=False)
    is_anonymous = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    closes_at = Column(DateTime)
    
    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    household = relationship("Household", back_populates="polls")
    creator = relationship("User", back_populates="created_polls", foreign_keys=[created_by])
    votes = relationship("PollVote", back_populates="poll")


class PollVote(Base):
    __tablename__ = "poll_votes"
    
    id = Column(Integer, primary_key=True, index=True)
    selected_options = Column(JSON, nullable=False)  # List of selected option indices
    
    # Foreign Keys
    poll_id = Column(Integer, ForeignKey("polls.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    poll = relationship("Poll", back_populates="votes")
    user = relationship("User", back_populates="poll_votes", foreign_keys=[user_id])
