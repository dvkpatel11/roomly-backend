from app.models.enums import HouseholdRole
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
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
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    phone = Column(String)
    household_role = Column(String, default=HouseholdRole.MEMBER.value)

    # Relationships
    household = relationship("Household", back_populates="members")

    # Expenses
    created_expenses = relationship(
        "Expense",
        back_populates="created_by_user",
        foreign_keys="Expense.created_by",
        cascade="all, delete-orphan",
    )

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

    # Schedules
    personal_schedules = relationship("UserSchedule", back_populates="user")

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
    expense_payments = relationship("ExpensePayment", back_populates="user")
