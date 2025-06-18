from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # utilities, rent, internet, etc.
    due_day = Column(Integer, nullable=False)  # Day of month (1-31)
    split_method = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    split_details = Column(JSON)

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="bills")
    created_by_user = relationship(
        "User", back_populates="created_bills", foreign_keys=[created_by]
    )
    payments = relationship("BillPayment", back_populates="bill")

    __table_args__ = (
        Index("idx_bill_household_active", "household_id", "is_active"),
        Index("idx_bill_due_day", "due_day"),
    )


class BillPayment(Base):
    __tablename__ = "bill_payments"

    id = Column(Integer, primary_key=True, index=True)
    amount_paid = Column(Float, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    payment_method = Column(String)  # venmo, cash, check, etc.
    notes = Column(Text)
    for_month = Column(String, nullable=False)  # "2025-06" format

    # Foreign Keys
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    bill = relationship("Bill", back_populates="payments")
    paid_by_user = relationship(
        "User", back_populates="bill_payments", foreign_keys=[paid_by]
    )
