from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(Text)
    house_rules = Column(Text)
    settings = Column(JSON, default=dict)  # Guest policies, notification settings, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    members = relationship("User", back_populates="household")
    expenses = relationship("Expense", back_populates="household")
    bills = relationship("Bill", back_populates="household")
    tasks = relationship("Task", back_populates="household")
    events = relationship("Event", back_populates="household")
    guests = relationship("Guest", back_populates="household")
    announcements = relationship("Announcement", back_populates="household")
    polls = relationship("Poll", back_populates="household")
    notifications = relationship("Notification", back_populates="household")
    shopping_lists = relationship("ShoppingList", back_populates="household")
    memberships = relationship("HouseholdMembership", back_populates="household")
