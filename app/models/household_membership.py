from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from ..database import Base
from sqlalchemy import Index


class HouseholdMembership(Base):
    __tablename__ = "household_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    role = Column(String, default="member")  # admin, member
    joined_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Unique constraint
    __table_args__ = (
        Index("idx_unique_household_member", "user_id", "household_id", unique=True),
    )
