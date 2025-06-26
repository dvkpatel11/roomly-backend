from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.billing_service import BillingService
from ..schemas.bill import BillCreate, BillUpdate, BillResponse, BillPaymentRecord
from ..dependencies.permissions import require_household_member, require_household_admin
from ..utils.router_helpers import (
    handle_service_errors,
)
from ..models.user import User
from ..utils.constants import ResponseMessages
from ..schemas.common import (
    ResponseFactory,
    SuccessResponse,
    PaginationParams,
    ConfigResponse,
    ConfigOption,
)

router = APIRouter(tags=["bills"])


@router.post("/", response_model=SuccessResponse[BillResponse])
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

    return ResponseFactory.created(data=bill, message=ResponseMessages.BILL_CREATED)


@router.get("/", response_model=SuccessResponse[dict])
@handle_service_errors
async def get_household_bills(
    active_only: bool = Query(True, description="Show only active bills"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household's recurring bills"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    bills = billing_service.get_household_bills(household_id, active_only=active_only)

    return ResponseFactory.success(
        data={
            "bills": bills,
            "total_count": len(bills),
            "active_only": active_only,
        }
    )


@router.get("/upcoming", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(
        data={
            "upcoming_bills": upcoming,
            "days_ahead": days_ahead,
            "count": len(upcoming),
        }
    )


@router.get("/overdue", response_model=SuccessResponse[dict])
@handle_service_errors
async def get_overdue_bills(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get overdue bills for household"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    overdue = billing_service.get_overdue_bills(household_id=household_id)

    return ResponseFactory.success(
        data={
            "overdue_bills": overdue,
            "count": len(overdue),
            "total_overdue_amount": sum(
                bill.get("amount_remaining", 0) for bill in overdue
            ),
        }
    )


@router.get("/{bill_id}", response_model=SuccessResponse[dict])
@handle_service_errors
async def get_bill_details(
    bill_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed bill information"""
    billing_service = BillingService(db)

    details = billing_service.get_bill_details(bill_id)

    return ResponseFactory.success(
        data={
            "bill_id": bill_id,
            "details": details,
        }
    )


@router.put("/{bill_id}", response_model=SuccessResponse[BillResponse])
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

    return ResponseFactory.success(data=bill, message=ResponseMessages.BILL_UPDATED)


@router.delete("/{bill_id}", response_model=SuccessResponse[dict])
@handle_service_errors
async def deactivate_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Deactivate a recurring bill (admin only)"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    success = billing_service.deactivate_bill(bill_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
        )

    return ResponseFactory.success(
        data={"bill_id": bill_id, "deactivated": True},
        message="Bill deactivated successfully",
    )


# =============================================================================
# PAYMENT ENDPOINTS
# =============================================================================


@router.post("/{bill_id}/payments", response_model=SuccessResponse[dict])
@handle_service_errors
async def record_bill_payment(
    bill_id: int,
    payment_data: BillPaymentRecord,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Record a payment for a bill"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    payment = billing_service.record_bill_payment(
        bill_id=bill_id,
        paid_by=current_user.id,
        amount_paid=payment_data.amount_paid,
        payment_method=payment_data.payment_method,
        notes=payment_data.notes,
        for_month=payment_data.for_month,
    )

    return ResponseFactory.created(
        data={
            "payment": {
                "id": payment.id,
                "amount_paid": payment.amount_paid,
                "payment_date": payment.payment_date,
                "payment_method": payment.payment_method,
                "for_month": payment.for_month,
            }
        },
        message=ResponseMessages.BILL_PAYMENT_RECORDED,
    )


@router.get("/{bill_id}/payment-history", response_model=SuccessResponse[dict])
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

    return ResponseFactory.success(
        data={
            "payment_history": history,
            "bill_id": bill_id,
            "months_back": months_back,
        }
    )


# =============================================================================
# SUMMARY & ANALYTICS ENDPOINTS
# =============================================================================


@router.get("/summary", response_model=SuccessResponse[dict])
@handle_service_errors
async def get_billing_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive billing summary"""
    current_user, household_id = user_household
    billing_service = BillingService(db)

    summary = billing_service.get_household_billing_summary(household_id=household_id)

    return ResponseFactory.success(data={"billing_summary": summary})


# =============================================================================
# CONFIGURATION ENDPOINTS
# =============================================================================


@router.get("/config/categories", response_model=SuccessResponse[ConfigResponse])
async def get_bill_categories():
    """Get available bill categories"""
    from ..models.enums import ExpenseCategory

    # Filter to bill-relevant categories
    bill_categories = ["utilities", "rent", "internet", "maintenance"]

    options = [
        ConfigOption(
            value=cat.value,
            label=cat.value.replace("_", " ").title(),
            description=f"Bills related to {cat.value.replace('_', ' ')}",
        )
        for cat in ExpenseCategory
        if cat.value in bill_categories
    ]

    return ResponseFactory.success(
        data=ConfigResponse(
            options=options, total_count=len(options), category="Bill Categories"
        )
    )


@router.get("/config/split-methods", response_model=SuccessResponse[ConfigResponse])
async def get_split_methods():
    """Get available split methods for bills"""
    from ..models.enums import SplitMethod

    options = [
        ConfigOption(
            value=method.value,
            label=method.value.replace("_", " ").title(),
            description=f"Split bills using {method.value.replace('_', ' ')} method",
        )
        for method in SplitMethod
    ]

    return ResponseFactory.success(
        data=ConfigResponse(
            options=options, total_count=len(options), category="Split Methods"
        )
    )
