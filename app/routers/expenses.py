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


@router.post("/{expense_id}/payments")
@handle_service_errors
async def record_expense_payment(
    expense_id: int,
    payment_data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    expense_service = ExpenseService(db)
    payment = expense_service.record_expense_payment(
        expense_id=expense_id, **payment_data
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
