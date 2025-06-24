from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    relationship_to_host = Column(String)  # friend, family, partner, etc.

    # Visit details
    check_in = Column(DateTime, nullable=False)
    check_out = Column(DateTime)
    is_overnight = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)

    # Additional info
    notes = Column(Text)
    special_requests = Column(Text)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    hosted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="guests")
    host = relationship(
        "User", back_populates="hosted_guests", foreign_keys=[hosted_by]
    )
    approver = relationship(
        "User", back_populates="approved_guests", foreign_keys=[approved_by]
    )
