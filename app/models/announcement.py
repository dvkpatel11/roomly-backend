from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
from .enums import Priority


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    priority = Column(String, default=Priority.NORMAL.value)
    is_pinned = Column(Boolean, default=False)
    expires_at = Column(DateTime)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="announcements")
    author = relationship(
        "User", back_populates="announcements", foreign_keys=[created_by]
    )
