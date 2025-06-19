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

    # Relationships - Use memberships instead of direct members
    memberships = relationship(
        "HouseholdMembership", back_populates="household", cascade="all, delete-orphan"
    )
    expenses = relationship("Expense", back_populates="household")
    bills = relationship("Bill", back_populates="household")
    tasks = relationship("Task", back_populates="household")
    events = relationship("Event", back_populates="household")
    guests = relationship("Guest", back_populates="household")
    announcements = relationship("Announcement", back_populates="household")
    polls = relationship("Poll", back_populates="household")
    notifications = relationship("Notification", back_populates="household")
    shopping_lists = relationship("ShoppingList", back_populates="household")

    # Helper methods
    def get_active_members(self):
        """Get all active members of this household"""
        return [m.user for m in self.memberships if m.is_active]

    def get_admins(self):
        """Get all admin members of this household"""
        return [m.user for m in self.memberships if m.is_active and m.role == "admin"]

    def is_member(self, user_id: int):
        """Check if user is an active member"""
        return any(m.user_id == user_id and m.is_active for m in self.memberships)

    def is_admin(self, user_id: int):
        """Check if user is an admin"""
        return any(
            m.user_id == user_id and m.is_active and m.role == "admin"
            for m in self.memberships
        )
