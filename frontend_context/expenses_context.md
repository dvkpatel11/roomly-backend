# Expenses Page - Backend Context

## Overview
Expense tracking, bill splitting, payment management, and financial reports.

## Related Files:
## app/routers/expenses.py
```python
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from ..database import get_db
from ..services.expense_service import ExpenseService
from ..schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    SplitMethod,
    ExpenseCategory,
)
from ..dependencies.permissions import require_household_member
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    validate_pagination,
)
from ..models.user import User
from ..utils.constants import AppConstants

router = APIRouter(tags=["expenses"])


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def create_expense(
    expense_data: ExpenseCreate,
    custom_splits: Optional[Dict[int, float]] = Body(
        None, description="Custom split amounts or percentages"
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new expense with automatic splitting"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    expense = expense_service.create_expense_with_split(
        expense_data=expense_data,
        household_id=household_id,
        created_by=current_user.id,
        custom_splits=custom_splits or {},
    )

    return RouterResponse.created(
        data={"expense": expense},
        message="Expense created and split calculated successfully",
    )


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_expenses(
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None, description="Filter by expense category"),
    created_by: Optional[int] = Query(None, description="Filter by creator"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household expenses with filtering and pagination"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    result = expense_service.get_household_expenses(
        household_id=household_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        category=category,
        created_by=created_by,
    )

    return RouterResponse.success(data=result)


@router.get("/{expense_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_expense_details(
    expense_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get detailed expense information with split status and payments"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    expense_details = expense_service.get_expense_details(
        expense_id=expense_id, requested_by=current_user.id
    )

    return RouterResponse.success(data=expense_details)


@router.put("/{expense_id}", response_model=Dict[str, Any])
@handle_service_errors
async def update_expense(
    expense_id: int,
    expense_updates: ExpenseUpdate,
    custom_splits: Optional[Dict[int, float]] = Body(
        None, description="Custom split amounts"
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update expense details and recalculate splits if needed"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    expense = expense_service.update_expense(
        expense_id=expense_id,
        expense_updates=expense_updates,
        updated_by=current_user.id,
        custom_splits=custom_splits or {},
    )

    return RouterResponse.updated(
        data={"expense": expense}, message="Expense updated successfully"
    )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_service_errors
async def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Delete an expense (only if no payments have been made)"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    expense_service.delete_expense(expense_id=expense_id, deleted_by=current_user.id)


@router.post("/{expense_id}/payments", response_model=Dict[str, Any])
@handle_service_errors
async def record_expense_payment(
    expense_id: int,
    payment_data: Dict[str, Any] = Body(
        ...,
        example={
            "amount_paid": 50.00,
            "payment_method": "venmo",
            "notes": "My share of groceries",
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Record a payment towards an expense"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    amount_paid = payment_data.get("amount_paid")
    if not amount_paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="amount_paid is required"
        )

    payment = expense_service.record_expense_payment(
        expense_id=expense_id,
        paid_by=current_user.id,
        amount_paid=amount_paid,
        payment_method=payment_data.get("payment_method"),
        notes=payment_data.get("notes"),
    )

    return RouterResponse.created(
        data={
            "payment": {
                "id": payment.id,
                "amount_paid": payment.amount_paid,
                "payment_date": payment.payment_date,
                "payment_method": payment.payment_method,
            }
        },
        message="Payment recorded successfully",
    )


@router.put("/{expense_id}/split/{user_id}/mark-paid", response_model=Dict[str, Any])
@handle_service_errors
async def mark_split_paid(
    expense_id: int,
    user_id: int,
    payment_data: Dict[str, str] = Body(None, example={"payment_method": "cash"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Mark a user's portion of expense as paid (for cash/offline payments)"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    payment_method = None
    if payment_data:
        payment_method = payment_data.get("payment_method")

    success = expense_service.mark_split_paid(
        expense_id=expense_id, user_id=user_id, payment_method=payment_method
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update payment status",
        )

    return RouterResponse.success(message="Payment status updated successfully")


@router.get("/me/summary", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_expense_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get current user's expense summary (what they owe and what's owed to them)"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    summary = expense_service.get_user_expense_summary(
        user_id=current_user.id, household_id=household_id
    )

    return RouterResponse.success(data={"expense_summary": summary})


@router.get("/me/payment-history", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_payment_history(
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get current user's payment history"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    # Validate pagination
    limit, offset = validate_pagination(limit, offset, AppConstants.MAX_PAGE_SIZE)

    payment_history = expense_service.get_payment_history(
        user_id=current_user.id,
        household_id=household_id,
        limit=limit,
        offset=offset,
    )

    return RouterResponse.success(data=payment_history)


@router.post("/preview-split", response_model=Dict[str, Any])
@handle_service_errors
async def preview_expense_split(
    preview_data: Dict[str, Any] = Body(
        ...,
        example={
            "amount": 120.00,
            "split_method": "equal_split",
            "custom_splits": {1: 40.00, 2: 80.00},
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Preview how an expense would be split without creating it"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    amount = preview_data.get("amount")
    split_method_str = preview_data.get("split_method")
    custom_splits = preview_data.get("custom_splits", {})

    if not amount or not split_method_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount and split_method are required",
        )

    # Validate split method
    try:
        split_method = SplitMethod(split_method_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid split method. Must be one of: {[m.value for m in SplitMethod]}",
        )

    # Get household members for preview
    household_members = expense_service._get_household_members(household_id)

    # Calculate splits
    split_details = expense_service._calculate_splits(
        total_amount=amount,
        split_method=split_method,
        household_members=household_members,
        custom_splits=custom_splits,
    )

    return RouterResponse.success(
        data={
            "preview": {
                "total_amount": amount,
                "split_method": split_method.value,
                "splits": split_details["splits"],
                "calculation_details": split_details,
            }
        }
    )


@router.get("/config/categories", response_model=Dict[str, Any])
async def get_expense_categories():
    """Get available expense categories"""
    categories = [
        {"value": category.value, "label": category.value.replace("_", " ").title()}
        for category in ExpenseCategory
    ]

    return RouterResponse.success(data={"categories": categories})


@router.get("/config/split-methods", response_model=Dict[str, Any])
async def get_split_methods():
    """Get available split methods"""
    methods = [
        {"value": method.value, "label": method.value.replace("_", " ").title()}
        for method in SplitMethod
    ]

    return RouterResponse.success(data={"split_methods": methods})


@router.get("/statistics/household", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_expense_statistics(
    months_back: int = Query(6, ge=1, le=24, description="Months of data to analyze"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive expense statistics for household"""
    current_user, household_id = user_household
    expense_service = ExpenseService(db)

    # Get basic expense data
    expenses_result = expense_service.get_household_expenses(
        household_id=household_id,
        user_id=current_user.id,
        limit=1000,  # Get all for statistics
        offset=0,
    )

    expenses = expenses_result.get("expenses", [])

    # Calculate statistics
    total_expenses = len(expenses)
    total_amount = sum(exp.get("amount", 0) for exp in expenses)
    paid_expenses = len([exp for exp in expenses if exp.get("is_fully_paid", False)])

    statistics = {
        "household_id": household_id,
        "period_months": months_back,
        "total_expenses": total_expenses,
        "total_amount": total_amount,
        "paid_expenses": paid_expenses,
        "unpaid_expenses": total_expenses - paid_expenses,
        "average_expense_amount": (
            round(total_amount / total_expenses, 2) if total_expenses > 0 else 0
        ),
        "payment_completion_rate": (
            round((paid_expenses / total_expenses * 100), 1)
            if total_expenses > 0
            else 0
        ),
    }

    return RouterResponse.success(data={"statistics": statistics})
```

## app/routers/bills.py
```python
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..services.billing_service import BillingService
from ..schemas.bill import BillCreate, BillUpdate
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
)
from ..models.user import User
from ..utils.constants import AppConstants

router = APIRouter(tags=["bills"])


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def create_recurring_bill(
    bill_data: BillCreate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Create a new recurring bill"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    bill = billing_service.create_recurring_bill(
        bill_data=bill_data,
        household_id=household_id,
        created_by=current_user.id,
    )

    return RouterResponse.created(
        data={"bill": bill}, message="Recurring bill created successfully"
    )


@router.get("/", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_bills(
    active_only: bool = Query(True, description="Show only active bills"),
    limit: int = Query(AppConstants.DEFAULT_PAGE_SIZE, le=AppConstants.MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household's recurring bills"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    bills = billing_service.get_household_bills(household_id, active_only=True)

    return RouterResponse.success(
        data={
            "bills": bills,
            "total_count": len(bills),
            "active_only": active_only,
        }
    )


@router.get("/upcoming", response_model=Dict[str, Any])
@handle_service_errors
async def get_upcoming_bills(
    days_ahead: int = Query(7, ge=1, le=30, description="Days to look ahead"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get bills due in the next N days"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    upcoming = billing_service.get_upcoming_bills(
        household_id=household_id, days_ahead=days_ahead
    )

    return RouterResponse.success(
        data={
            "upcoming_bills": upcoming,
            "days_ahead": days_ahead,
            "count": len(upcoming),
        }
    )


@router.get("/overdue", response_model=Dict[str, Any])
@handle_service_errors
async def get_overdue_bills(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get overdue bills for household"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    overdue = billing_service.get_overdue_bills(household_id=household_id)

    return RouterResponse.success(
        data={
            "overdue_bills": overdue,
            "count": len(overdue),
            "total_overdue_amount": sum(bill["amount_remaining"] for bill in overdue),
        }
    )


@router.get("/{bill_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_bill_details(
    bill_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed bill information"""
    billing_service = BillingService(db)

    details = billing_service.get_bill_details(bill_id)

    return RouterResponse.success(
        data={
            "bill_id": bill_id,
            "details": details,
        }
    )


@router.put("/{bill_id}", response_model=Dict[str, Any])
@handle_service_errors
async def update_bill(
    bill_id: int,
    bill_update: BillUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Update recurring bill"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    bill = billing_service.update_bill(bill_id, bill_update)

    return RouterResponse.updated(
        data={"bill": bill}, message="Bill updated successfully"
    )


@router.delete("/{bill_id}", response_model=Dict[str, Any])
@handle_service_errors
async def deactivate_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),  # Admin only
):
    """Deactivate a recurring bill (admin only)"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    success = billing_service.deactivate_bill(bill_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
        )

    return RouterResponse.success(message="Bill deactivated successfully")


@router.post("/{bill_id}/payments", response_model=Dict[str, Any])
@handle_service_errors
async def record_bill_payment(
    bill_id: int,
    payment_data: Dict[str, Any] = Body(
        ...,
        example={
            "amount_paid": 150.00,
            "payment_method": "venmo",
            "for_month": "2024-01",
            "notes": "January rent payment",
        },
    ),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Record a bill payment"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    # Validate required fields
    amount_paid = payment_data.get("amount_paid")
    payment_method = payment_data.get("payment_method")
    for_month = payment_data.get("for_month")

    if not all([amount_paid, payment_method, for_month]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount_paid, payment_method, and for_month are required",
        )

    payment = billing_service.record_bill_payment(
        bill_id=bill_id,
        paid_by=current_user.id,
        amount_paid=amount_paid,
        payment_method=payment_method,
        for_month=for_month,
        notes=payment_data.get("notes", ""),
    )

    return RouterResponse.created(
        data={
            "payment": {
                "id": payment.id,
                "amount_paid": payment.amount_paid,
                "payment_date": payment.payment_date,
                "payment_method": payment.payment_method,
            }
        },
        message="Payment recorded successfully",
    )


@router.get("/{bill_id}/payment-history", response_model=Dict[str, Any])
@handle_service_errors
async def get_bill_payment_history(
    bill_id: int,
    months_back: int = Query(12, ge=1, le=24, description="Months of history"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get payment history for a bill"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    history = billing_service.get_bill_payment_history(
        bill_id=bill_id, months_back=months_back
    )

    return RouterResponse.success(
        data={
            "payment_history": history,
            "bill_id": bill_id,
            "months_back": months_back,
        }
    )


@router.get("/summary", response_model=Dict[str, Any])
@handle_service_errors
async def get_billing_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive billing summary"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    summary = billing_service.get_household_billing_summary(household_id=household_id)

    return RouterResponse.success(data={"billing_summary": summary})


@router.get("/config/categories", response_model=Dict[str, Any])
async def get_bill_categories():
    """Get available bill categories"""
    from ..utils.constants import ExpenseCategory

    categories = [
        {"value": cat.value, "label": cat.value.replace("_", " ").title()}
        for cat in ExpenseCategory
        if cat.value in ["utilities", "rent", "internet", "maintenance"]
    ]

    return RouterResponse.success(data={"categories": categories})


@router.get("/config/split-methods", response_model=Dict[str, Any])
async def get_split_methods():
    """Get available split methods for bills"""
    from ..utils.constants import SplitMethod

    methods = [
        {"value": method.value, "label": method.value.replace("_", " ").title()}
        for method in SplitMethod
    ]

    return RouterResponse.success(data={"split_methods": methods})
```

## app/schemas/expense.py
```python
from pydantic import BaseModel, validator, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SplitMethod(str, Enum):
    EQUAL = "equal_split"
    BY_USAGE = "by_usage"
    SPECIFIC = "specific_amounts"
    PERCENTAGE = "percentage"

class ExpenseCategory(str, Enum):
    GROCERIES = "groceries"
    UTILITIES = "utilities"
    RENT = "rent"
    CLEANING = "cleaning"
    ENTERTAINMENT = "entertainment"
    MAINTENANCE = "maintenance"
    OTHER = "other"

class ExpenseBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0, description="Amount must be positive")
    category: ExpenseCategory
    split_method: SplitMethod
    receipt_url: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)

class ExpenseCreate(ExpenseBase):
    @validator('description')
    def description_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()

class ExpenseUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[ExpenseCategory] = None
    split_method: Optional[SplitMethod] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)

class ExpenseResponse(ExpenseBase):
    id: int
    household_id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime]
    split_details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class ExpenseSplit(BaseModel):
    user_id: int
    user_name: str
    amount_owed: float
    is_paid: bool = False
    payment_date: Optional[datetime] = None

class ExpenseSplitCalculation(BaseModel):
    expense_id: int
    total_amount: float
    split_method: SplitMethod
    splits: list[ExpenseSplit]
    calculation_details: Dict[str, Any]
```

## app/schemas/bill.py
```python
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class BillBase(BaseModel):
    name: str
    amount: float
    category: str
    due_day: int
    split_method: str
    notes: Optional[str] = None


class BillCreate(BillBase):
    @validator("due_day")
    def validate_due_day(cls, v):
        if not 1 <= v <= 31:
            raise ValueError("Due day must be between 1 and 31")
        return v


class BillUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    due_day: Optional[int] = None
    split_method: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @validator("due_day")
    def validate_due_day(cls, v):
        if v is not None and not 1 <= v <= 31:
            raise ValueError("Due day must be between 1 and 31")
        return v

    @validator("amount")
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive")
        return v


class BillResponse(BillBase):
    id: int
    household_id: int
    created_by: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


__all__ = ["BillBase", "BillCreate", "BillUpdate", "BillResponse"]
```

## app/models/expense.py
```python
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
```

## app/models/bill.py
```python
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
```

