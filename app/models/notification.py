from sqlalchemy import (
    Index,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
from .enums import Priority


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)
    priority = Column(String, default=Priority.NORMAL.value)
    is_read = Column(Boolean, default=False)

    # Delivery methods
    sent_in_app = Column(Boolean, default=True)
    sent_email = Column(Boolean, default=False)
    sent_push = Column(Boolean, default=False)

    # Additional data
    related_entity_type = Column(String)
    related_entity_id = Column(Integer)
    action_url = Column(String)

    # Foreign Keys with proper cascade
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    household_id = Column(
        Integer, ForeignKey("households.id", ondelete="CASCADE"), nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    household = relationship("Household", back_populates="notifications")


class NotificationPreference(Base):
    """
    FIXED: Aligned with schema - stores specific preference types instead of generic
    Each user has ONE record with all their notification preferences
    """

    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)

    # User relationship with cascade delete
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Each user has exactly one preference record
    )

    # BILL REMINDERS
    bill_reminders_email = Column(Boolean, default=True)
    bill_reminders_push = Column(Boolean, default=True)
    bill_reminders_in_app = Column(Boolean, default=True)

    # TASK REMINDERS
    task_reminders_email = Column(Boolean, default=True)
    task_reminders_push = Column(Boolean, default=True)
    task_reminders_in_app = Column(Boolean, default=True)

    # EVENT REMINDERS
    event_reminders_email = Column(Boolean, default=True)
    event_reminders_push = Column(Boolean, default=True)
    event_reminders_in_app = Column(Boolean, default=True)

    # ANNOUNCEMENTS
    announcements_email = Column(Boolean, default=True)
    announcements_push = Column(Boolean, default=False)
    announcements_in_app = Column(Boolean, default=True)

    # GUEST REQUESTS
    guest_requests_email = Column(Boolean, default=True)
    guest_requests_push = Column(Boolean, default=True)
    guest_requests_in_app = Column(Boolean, default=True)

    # EXPENSE UPDATES
    expense_updates_email = Column(Boolean, default=False)
    expense_updates_push = Column(Boolean, default=True)
    expense_updates_in_app = Column(Boolean, default=True)

    # PAYMENT NOTIFICATIONS
    payment_received_email = Column(Boolean, default=False)
    payment_received_push = Column(Boolean, default=True)
    payment_received_in_app = Column(Boolean, default=True)

    # POLL NOTIFICATIONS
    poll_created_email = Column(Boolean, default=False)
    poll_created_push = Column(Boolean, default=True)
    poll_created_in_app = Column(Boolean, default=True)

    # SYSTEM NOTIFICATIONS
    system_updates_email = Column(Boolean, default=True)
    system_updates_push = Column(Boolean, default=False)
    system_updates_in_app = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="notification_preferences")

    def get_preference(
        self, notification_type: str, delivery_method: str = "email"
    ) -> bool:
        """
        Helper method to get preference for a specific notification type and delivery method

        Args:
            notification_type: bill_due, task_overdue, event_reminder, etc.
            delivery_method: email, push, in_app

        Returns:
            Boolean preference value
        """
        # Map notification types to preference fields
        type_mapping = {
            "bill_due": "bill_reminders",
            "bill_reminder": "bill_reminders",
            "task_overdue": "task_reminders",
            "task_assigned": "task_reminders",
            "task_reminder": "task_reminders",
            "event_reminder": "event_reminders",
            "event_created": "event_reminders",
            "announcement": "announcements",
            "guest_request": "guest_requests",
            "guest_approved": "guest_requests",
            "expense_added": "expense_updates",
            "expense_updated": "expense_updates",
            "payment_received": "payment_received",
            "payment_reminder": "payment_received",
            "poll_created": "poll_created",
            "poll_closed": "poll_created",
            "system": "system_updates",
        }

        base_type = type_mapping.get(notification_type)
        if not base_type:
            return True  # Default to enabled for unknown types

        field_name = f"{base_type}_{delivery_method}"
        return getattr(self, field_name, True)

    @classmethod
    def create_default_preferences(cls, user_id: int, db_session):
        """Create default notification preferences for a new user"""
        preferences = cls(user_id=user_id)
        db_session.add(preferences)
        db_session.commit()
        return preferences

    __table_args__ = (
        Index("idx_notification_user_unread", "user_id", "is_read", "created_at"),
        Index("idx_notification_household_priority", "household_id", "priority"),
    )
