from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class RSVP(Base):
    __tablename__ = "rsvps"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)  # yes, no, maybe
    guest_count = Column(Integer, default=1)  # How many people they're bringing
    dietary_restrictions = Column(Text)
    special_requests = Column(Text)
    response_notes = Column(Text)
    
    # Foreign Keys
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="rsvps")
    user = relationship("User", back_populates="event_rsvps", foreign_keys=[user_id])
