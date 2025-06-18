from app.schemas.event import EventStatus
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    event_type = Column(String, nullable=False)  # party, maintenance, cleaning, etc.
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    location = Column(String)
    max_attendees = Column(Integer)
    is_public = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=True)
    status = Column(String, default=EventStatus.PENDING.value)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="events")
    creator = relationship(
        "User", back_populates="created_events", foreign_keys=[created_by]
    )
    rsvps = relationship("RSVP", back_populates="event")
