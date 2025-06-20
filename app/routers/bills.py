from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..services.billing_service import BillingService
from ..schemas.bill import BillCreate, BillUpdate, BillResponse
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
    validate_pagination,
)
from ..models.user import User
from ..utils.constants import AppConstants

router = APIRouter(prefix="/bills", tags=["bills"])


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
