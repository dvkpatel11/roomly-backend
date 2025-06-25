from app.models.enums import TaskStatus
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
from .enums import Priority


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    priority = Column(String, default=Priority.NORMAL.value)
    estimated_duration = Column(Integer)
    recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String)
    completion_notes = Column(Text)
    photo_proof_url = Column(String)
    status = Column(String, default=TaskStatus.PENDING.value)

    household_id = Column(
        Integer, ForeignKey("households.id", ondelete="CASCADE"), nullable=False
    )
    assigned_to = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="tasks")
    assigned_user = relationship(
        "User", back_populates="assigned_tasks", foreign_keys=[assigned_to]
    )
    created_by_user = relationship(
        "User", back_populates="created_tasks", foreign_keys=[created_by]
    )

    __table_args__ = (
        Index("idx_task_household_status_due", "household_id", "status", "due_date"),
        Index("idx_task_assigned_status", "assigned_to", "status"),
    )
