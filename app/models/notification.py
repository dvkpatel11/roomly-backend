from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)  # bill_due, task_overdue, event_reminder, etc.
    priority = Column(String, default="normal")  # low, normal, high, urgent
    is_read = Column(Boolean, default=False)
    
    # Delivery methods
    sent_in_app = Column(Boolean, default=True)
    sent_email = Column(Boolean, default=False)
    sent_push = Column(Boolean, default=False)
    
    # Additional data
    related_entity_type = Column(String)  # bill, task, event, etc.
    related_entity_id = Column(Integer)
    action_url = Column(String)  # Deep link for action
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    household = relationship("Household", back_populates="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(String, nullable=False)
    in_app_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences", foreign_keys=[user_id])
