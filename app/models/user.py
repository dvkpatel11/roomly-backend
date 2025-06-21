from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    phone = Column(String, index=True)  # Added index for better query performance
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Add unique constraint for phone numbers (excluding NULL values)
    __table_args__ = (
        UniqueConstraint(
            "phone", name="uq_user_phone", sqlite_on_conflict="ABORT"
        ),  # For SQLite
    )

    # Relationships - Use household_memberships instead of direct household relationship
    household_memberships = relationship("HouseholdMembership", back_populates="user")

    # Expenses
    created_expenses = relationship(
        "Expense",
        back_populates="created_by_user",
        foreign_keys="Expense.created_by",
        cascade="all, delete-orphan",
    )
    expense_payments = relationship("ExpensePayment", back_populates="user")

    # Bills
    created_bills = relationship(
        "Bill", back_populates="created_by_user", foreign_keys="Bill.created_by"
    )
    bill_payments = relationship(
        "BillPayment", back_populates="paid_by_user", foreign_keys="BillPayment.paid_by"
    )

    # Tasks
    assigned_tasks = relationship(
        "Task", back_populates="assigned_user", foreign_keys="Task.assigned_to"
    )
    created_tasks = relationship(
        "Task", back_populates="created_by_user", foreign_keys="Task.created_by"
    )

    # Events
    created_events = relationship(
        "Event", back_populates="creator", foreign_keys="Event.created_by"
    )
    event_rsvps = relationship("RSVP", back_populates="user")

    # Guests
    hosted_guests = relationship(
        "Guest", back_populates="host", foreign_keys="Guest.hosted_by"
    )
    approved_guests = relationship(
        "Guest", back_populates="approver", foreign_keys="Guest.approved_by"
    )

    # Communications
    announcements = relationship("Announcement", back_populates="author")
    created_polls = relationship("Poll", back_populates="creator")
    poll_votes = relationship("PollVote", back_populates="user")

    # Notifications
    notifications = relationship("Notification", back_populates="user")
    notification_preferences = relationship(
        "NotificationPreference", back_populates="user"
    )

    # Shopping
    created_shopping_lists = relationship(
        "ShoppingList", back_populates="creator", foreign_keys="ShoppingList.created_by"
    )
    assigned_shopping_lists = relationship(
        "ShoppingList",
        back_populates="shopper",
        foreign_keys="ShoppingList.assigned_shopper",
    )
    requested_shopping_items = relationship("ShoppingItem", back_populates="requester")

    # Helper methods
    def get_active_household(self):
        """Get the user's currently active household"""
        active_membership = next(
            (m for m in self.household_memberships if m.is_active), None
        )
        return active_membership.household if active_membership else None

    def get_household_role(self, household_id: int):
        """Get user's role in a specific household"""
        membership = next(
            (
                m
                for m in self.household_memberships
                if m.household_id == household_id and m.is_active
            ),
            None,
        )
        return membership.role if membership else None
