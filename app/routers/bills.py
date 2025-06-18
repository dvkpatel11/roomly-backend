from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..database import get_db
from ..services.billing_service import BillingService
from ..schemas.bill import BillCreate, BillUpdate, BillResponse
from .auth import get_current_user
from ..models.user import User

router = APIRouter()

@router.post("/", response_model=BillResponse)
async def create_recurring_bill(
    bill_data: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new recurring bill"""
    try:
        billing_service = BillingService(db)
        bill = billing_service.create_recurring_bill(
            bill_data=bill_data,
            household_id=current_user.household_id,
            created_by=current_user.id
        )
        return bill
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=Dict[str, List[Dict[str, Any]]])
async def get_household_bills(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household's recurring bills"""
    billing_service = BillingService(db)
    
    # Add method to get all bills
    bills = []  # billing_service.get_household_bills(current_user.household_id, active_only)
    
    return {"bills": bills}

@router.get("/upcoming")
async def get_upcoming_bills(
    days_ahead: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get bills due in the next N days"""
    billing_service = BillingService(db)
    
    upcoming = billing_service.get_upcoming_bills(
        household_id=current_user.household_id,
        days_ahead=days_ahead
    )
    
    return {"upcoming_bills": upcoming}

@router.get("/overdue")
async def get_overdue_bills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overdue bills for household"""
    billing_service = BillingService(db)
    
    overdue = billing_service.get_overdue_bills(
        household_id=current_user.household_id
    )
    
    return {"overdue_bills": overdue}

@router.post("/{bill_id}/payments")
async def record_bill_payment(
    bill_id: int,
    amount_paid: float,
    payment_method: str,
    for_month: str,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record a bill payment"""
    try:
        billing_service = BillingService(db)
        payment = billing_service.record_bill_payment(
            bill_id=bill_id,
            paid_by=current_user.id,
            amount_paid=amount_paid,
            payment_method=payment_method,
            for_month=for_month,
            notes=notes
        )
        return {"message": "Payment recorded successfully", "payment_id": payment.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{bill_id}/payment-history")
async def get_bill_payment_history(
    bill_id: int,
    months_back: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get payment history for a bill"""
    billing_service = BillingService(db)
    
    history = billing_service.get_bill_payment_history(
        bill_id=bill_id,
        months_back=months_back
    )
    
    return {"payment_history": history}

@router.put("/{bill_id}")
async def update_bill(
    bill_id: int,
    bill_update: BillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update recurring bill"""
    try:
        billing_service = BillingService(db)
        bill = billing_service.update_bill(bill_id, bill_update)
        return bill
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{bill_id}")
async def deactivate_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a recurring bill"""
    billing_service = BillingService(db)
    
    success = billing_service.deactivate_bill(bill_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    return {"message": "Bill deactivated successfully"}

@router.get("/summary")
async def get_billing_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive billing summary"""
    billing_service = BillingService(db)
    
    summary = billing_service.get_household_billing_summary(
        household_id=current_user.household_id
    )
    
    return summary
