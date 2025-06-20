from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..services.expense_service import ExpenseService, ExpenseServiceError
from ..services.household_service import HouseholdService
from ..schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseSplitCalculation,
    SplitMethod,
)
from .auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    custom_splits: Optional[Dict[int, float]] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new expense with automatic splitting"""
    try:
        # Get user's household using service
        household_service = HouseholdService(db)
        household_info = household_service.get_user_household_info(current_user.id)

        if not household_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be a member of a household to create expenses",
            )

        expense_service = ExpenseService(db)
        expense = expense_service.create_expense_with_split(
            expense_data=expense_data,
            household_id=household_info["household_id"],
            created_by=current_user.id,
            custom_splits=custom_splits or {},
        )
        return expense
    except ExpenseServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expense",
        )


@router.get("/", response_model=Dict[str, Any])
async def get_household_expenses(
    limit: int = Query(50, le=100, description="Number of expenses to return"),
    offset: int = Query(0, ge=0, description="Number of expenses to skip"),
    category: Optional[str] = Query(None, description="Filter by expense category"),
    created_by: Optional[int] = Query(None, description="Filter by creator"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get household expenses with filtering and pagination"""
    try:
        # Get user's household using service
        household_service = HouseholdService(db)
        household_info = household_service.get_user_household_info(current_user.id)

        if not household_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be a member of a household",
            )

        expense_service = ExpenseService(db)
        expenses = expense_service.get_household_expenses(
            household_id=household_info["household_id"],
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            category=category,
            created_by=created_by,
        )
        return expenses
    except ExpenseServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expenses",
        )


@router.get("/{expense_id}", response_model=Dict[str, Any])
async def get_expense_details(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed expense information with split status and payments"""
    try:
        expense_service = ExpenseService(db)
        expense_details = expense_service.get_expense_details(
            expense_id=expense_id, requested_by=current_user.id
        )
        return expense_details
    except ExpenseServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "cannot view" in str(e).lower() or "access denied" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expense details",
        )


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    expense_updates: ExpenseUpdate,
    custom_splits: Optional[Dict[int, float]] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update expense details and recalculate splits if needed"""
    try:
        expense_service = ExpenseService(db)
        expense = expense_service.update_expense(
            expense_id=expense_id,
            expense_updates=expense_updates,
            updated_by=current_user.id,
            custom_splits=custom_splits or {},
        )
        return expense
    except ExpenseServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "cannot edit" in str(e).lower() or "permission" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update expense",
        )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an expense (only if no payments have been made)"""
    try:
        expense_service = ExpenseService(db)
        success = expense_service.delete_expense(
            expense_id=expense_id, deleted_by=current_user.id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete expense",
            )
    except ExpenseServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "cannot delete" in str(e).lower() or "permission" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense",
        )


@router.post("/{expense_id}/payments", response_model=Dict[str, Any])
async def record_expense_payment(
    expense_id: int,
    amount_paid: float = Body(..., description="Amount being paid"),
    payment_method: Optional[str] = Body(None, description="Payment method used"),
    notes: Optional[str] = Body(None, description="Payment notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a payment towards an expense"""
    try:
        expense_service = ExpenseService(db)
        payment = expense_service.record_expense_payment(
            expense_id=expense_id,
            paid_by=current_user.id,
            amount_paid=amount_paid,
            payment_method=payment_method,
            notes=notes,
        )

        return {
            "message": "Payment recorded successfully",
            "payment_id": payment.id,
            "amount_paid": payment.amount_paid,
            "payment_date": payment.payment_date,
        }
    except ExpenseServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "cannot make payment" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record payment",
        )


@router.put("/{expense_id}/split/{user_id}/paid", response_model=Dict[str, Any])
async def mark_split_paid(
    expense_id: int,
    user_id: int,
    payment_method: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a user's portion of expense as paid (for cash/offline payments)"""
    try:
        expense_service = ExpenseService(db)
        success = expense_service.mark_split_paid(
            expense_id=expense_id, user_id=user_id, payment_method=payment_method
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update payment status",
            )

        return {"message": "Payment status updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment status",
        )


@router.get("/user/summary", response_model=Dict[str, Any])
async def get_user_expense_summary(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get user's expense summary (what they owe and what's owed to them)"""
    try:
        # Get user's household using service
        household_service = HouseholdService(db)
        household_info = household_service.get_user_household_info(current_user.id)

        if not household_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be a member of a household",
            )

        expense_service = ExpenseService(db)
        summary = expense_service.get_user_expense_summary(
            user_id=current_user.id, household_id=household_info["household_id"]
        )
        return summary
    except ExpenseServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expense summary",
        )


@router.get("/user/payment-history", response_model=Dict[str, Any])
async def get_user_payment_history(
    limit: int = Query(20, le=100, description="Number of payments to return"),
    offset: int = Query(0, ge=0, description="Number of payments to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's payment history"""
    try:
        # Get user's household using service
        household_service = HouseholdService(db)
        household_info = household_service.get_user_household_info(current_user.id)

        if not household_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be a member of a household",
            )

        expense_service = ExpenseService(db)
        payment_history = expense_service.get_payment_history(
            user_id=current_user.id,
            household_id=household_info["household_id"],
            limit=limit,
            offset=offset,
        )
        return payment_history
    except ExpenseServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment history",
        )


@router.get("/categories", response_model=List[Dict[str, str]])
async def get_expense_categories():
    """Get available expense categories"""
    from ..schemas.expense import ExpenseCategory

    categories = [
        {"value": category.value, "label": category.value.replace("_", " ").title()}
        for category in ExpenseCategory
    ]
    return categories


@router.get("/split-methods", response_model=List[Dict[str, str]])
async def get_split_methods():
    """Get available split methods"""
    from ..schemas.expense import SplitMethod

    methods = [
        {"value": method.value, "label": method.value.replace("_", " ").title()}
        for method in SplitMethod
    ]
    return methods


@router.post("/preview-split", response_model=Dict[str, Any])
async def preview_expense_split(
    amount: float = Body(..., description="Total expense amount"),
    split_method: SplitMethod = Body(..., description="Split method to use"),
    custom_splits: Optional[Dict[int, float]] = Body(
        None, description="Custom split amounts or percentages"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview how an expense would be split without creating it"""
    try:
        # Get user's household using service
        household_service = HouseholdService(db)
        household_info = household_service.get_user_household_info(current_user.id)

        if not household_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be a member of a household",
            )

        expense_service = ExpenseService(db)
        # Get household members for preview
        household_members = expense_service._get_household_members(
            household_info["household_id"]
        )

        # Calculate splits
        split_details = expense_service._calculate_splits(
            total_amount=amount,
            split_method=split_method,
            household_members=household_members,
            custom_splits=custom_splits or {},
        )

        return {
            "total_amount": amount,
            "split_method": split_method.value,
            "splits": split_details["splits"],
            "calculation_details": split_details,
        }
    except ExpenseServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview split",
        )
