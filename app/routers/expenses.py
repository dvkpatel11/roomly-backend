from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from ..database import get_db
from ..services.expense_service import ExpenseService
from ..schemas.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse, 
    ExpenseSplitCalculation, SplitMethod
)
from .auth import get_current_user
from ..models.user import User

router = APIRouter()

@router.post("/", response_model=ExpenseResponse)
async def create_expense(
    expense_data: ExpenseCreate,
    custom_splits: Optional[Dict[int, float]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new expense with automatic splitting"""
    try:
        expense_service = ExpenseService(db)
        expense = expense_service.create_expense_with_split(
            expense_data=expense_data,
            household_id=current_user.household_id,
            created_by=current_user.id,
            custom_splits=custom_splits or {}
        )
        return expense
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create expense")

@router.get("/", response_model=Dict[str, List[ExpenseResponse]])
async def get_expenses(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get household expenses with optional filtering"""
    expense_service = ExpenseService(db)
    
    # This would be implemented in ExpenseService
    expenses = []  # expense_service.get_household_expenses(current_user.household_id, skip, limit, category)
    
    return {"expenses": expenses}

@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific expense details"""
    expense_service = ExpenseService(db)
    
    # Add method to ExpenseService
    expense = None  # expense_service.get_expense_by_id(expense_id)
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Check if user has access to this expense
    if expense.household_id != current_user.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return expense

@router.put("/{expense_id}/split/{user_id}/paid")
async def mark_split_paid(
    expense_id: int,
    user_id: int,
    payment_method: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a user's portion of expense as paid"""
    expense_service = ExpenseService(db)
    
    success = expense_service.mark_split_paid(
        expense_id=expense_id,
        user_id=user_id,
        payment_method=payment_method
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update payment status")
    
    return {"message": "Payment marked as received"}

@router.get("/user/summary")
async def get_user_expense_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's expense summary (what they owe and what's owed to them)"""
    expense_service = ExpenseService(db)
    
    summary = expense_service.get_user_expense_summary(
        user_id=current_user.id,
        household_id=current_user.household_id
    )
    
    return summary

@router.post("/{expense_id}/split/calculate", response_model=ExpenseSplitCalculation)
async def calculate_expense_split(
    expense_id: int,
    split_method: SplitMethod,
    custom_splits: Optional[Dict[int, float]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Recalculate expense split with new method or custom ratios"""
    expense_service = ExpenseService(db)
    
    # This would be a new method in ExpenseService
    calculation = None  # expense_service.recalculate_split(expense_id, split_method, custom_splits)
    
    if not calculation:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return calculation
