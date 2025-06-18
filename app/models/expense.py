from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    split_method = Column(String, nullable=False)
    receipt_url = Column(String)
    notes = Column(Text)
    split_details = Column(JSON)  # Store split calculations

    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    household = relationship("Household", back_populates="expenses")
    created_by_user = relationship(
        "User", back_populates="created_expenses", foreign_keys=[created_by]
    )
    payments = relationship("ExpensePayment", back_populates="expense")
    __table_args__ = (
        Index("idx_expense_household_created", "household_id", "created_at"),
        Index("idx_expense_category_amount", "category", "amount"),
    )


class ExpensePayment(Base):
    __tablename__ = "expense_payments"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_paid = Column(Float, nullable=False)
    payment_date = Column(DateTime, server_default=func.now())
    payment_method = Column(String)  # venmo, cash, etc.

    # Relationships
    expense = relationship("Expense", back_populates="payments")
    user = relationship("User", back_populates="expense_payments")
