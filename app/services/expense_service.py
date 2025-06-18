from sqlalchemy.orm import Session
from typing import Dict, List, Any, Union
from decimal import Decimal, ROUND_HALF_UP
from ..models.expense import Expense
from ..models.user import User
from ..schemas.expense import ExpenseCreate, ExpenseUpdate, SplitMethod
import json

class ExpenseService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_expense_with_split(
        self, 
        expense_data: ExpenseCreate, 
        household_id: int, 
        created_by: int,
        custom_splits: Dict[int, Union[float, str]] = None
    ) -> Expense:
        """
        Create expense and calculate splits based on method.
        custom_splits: {user_id: amount_or_percentage}
        """
        
        # Create the expense
        expense = Expense(
            description=expense_data.description,
            amount=expense_data.amount,
            category=expense_data.category.value,
            split_method=expense_data.split_method.value,
            receipt_url=expense_data.receipt_url,
            notes=expense_data.notes,
            household_id=household_id,
            created_by=created_by
        )
        
        # Calculate splits
        household_members = self._get_household_members(household_id)
        split_details = self._calculate_splits(
            expense_data.amount,
            expense_data.split_method,
            household_members,
            custom_splits or {}
        )
        
        expense.split_details = split_details
        
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        
        return expense
    
    def _calculate_splits(
        self,
        total_amount: float,
        split_method: SplitMethod,
        household_members: List[User],
        custom_splits: Dict[int, Union[float, str]] = None
    ) -> Dict[str, Any]:
        """Calculate how expense should be split among members"""
        
        splits = []
        
        if split_method == SplitMethod.EQUAL:
            # Equal split among all members
            per_person = self._round_currency(total_amount / len(household_members))
            
            for member in household_members:
                splits.append({
                    "user_id": member.id,
                    "user_name": member.name,
                    "amount_owed": per_person,
                    "calculation_method": "equal",
                    "is_paid": False
                })
                
        elif split_method == SplitMethod.SPECIFIC:
            # Custom amounts or percentages specified
            splits = self._calculate_custom_splits(
                total_amount, 
                household_members, 
                custom_splits
            )
            
        elif split_method == SplitMethod.BY_USAGE:
            # Usage-based (same as custom for now)
            splits = self._calculate_custom_splits(
                total_amount, 
                household_members, 
                custom_splits
            )
            
        elif split_method == SplitMethod.PERCENTAGE:
            # Percentage-based
            splits = self._calculate_percentage_splits(
                total_amount, 
                household_members, 
                custom_splits
            )
        
        # Ensure total adds up exactly (handle rounding differences)
        splits = self._adjust_for_rounding(splits, total_amount)
        
        return {
            "splits": splits,
            "total_amount": total_amount,
            "split_method": split_method.value,
            "calculated_at": str(datetime.utcnow()),
            "all_paid": False
        }
    
    def _calculate_custom_splits(
        self,
        total_amount: float,
        household_members: List[User],
        custom_splits: Dict[int, Union[float, str]]
    ) -> List[Dict[str, Any]]:
        """Handle custom fixed amounts"""
        
        splits = []
        remaining_amount = total_amount
        remaining_members = []
        
        # First, handle members with specified amounts
        for member in household_members:
            if member.id in custom_splits:
                amount = float(custom_splits[member.id])
                amount = self._round_currency(amount)
                
                splits.append({
                    "user_id": member.id,
                    "user_name": member.name,
                    "amount_owed": amount,
                    "calculation_method": "custom_amount",
                    "is_paid": False
                })
                
                remaining_amount -= amount
            else:
                remaining_members.append(member)
        
        # Split remaining amount equally among remaining members
        if remaining_members and remaining_amount > 0:
            per_person = self._round_currency(remaining_amount / len(remaining_members))
            
            for member in remaining_members:
                splits.append({
                    "user_id": member.id,
                    "user_name": member.name,
                    "amount_owed": per_person,
                    "calculation_method": "equal_remaining",
                    "is_paid": False
                })
        
        return splits
    
    def _calculate_percentage_splits(
        self,
        total_amount: float,
        household_members: List[User],
        custom_splits: Dict[int, Union[float, str]]
    ) -> List[Dict[str, Any]]:
        """Handle percentage-based splits"""
        
        splits = []
        total_percentage = 0
        
        # Calculate amounts for specified percentages
        for member in household_members:
            if member.id in custom_splits:
                percentage = float(custom_splits[member.id])
                if percentage > 100:
                    raise ValueError(f"Percentage cannot exceed 100% for {member.name}")
                
                amount = self._round_currency(total_amount * (percentage / 100))
                total_percentage += percentage
                
                splits.append({
                    "user_id": member.id,
                    "user_name": member.name,
                    "amount_owed": amount,
                    "calculation_method": f"{percentage}%",
                    "is_paid": False
                })
        
        if total_percentage > 100:
            raise ValueError("Total percentages cannot exceed 100%")
        
        # Handle remaining percentage equally if not 100%
        if total_percentage < 100:
            remaining_percentage = 100 - total_percentage
            unspecified_members = [m for m in household_members if m.id not in custom_splits]
            
            if unspecified_members:
                per_person_percentage = remaining_percentage / len(unspecified_members)
                
                for member in unspecified_members:
                    amount = self._round_currency(total_amount * (per_person_percentage / 100))
                    
                    splits.append({
                        "user_id": member.id,
                        "user_name": member.name,
                        "amount_owed": amount,
                        "calculation_method": f"{per_person_percentage:.1f}%",
                        "is_paid": False
                    })
        
        return splits
    
    def _adjust_for_rounding(self, splits: List[Dict[str, Any]], target_total: float) -> List[Dict[str, Any]]:
        """Adjust splits to ensure total equals target amount exactly"""
        
        current_total = sum(split["amount_owed"] for split in splits)
        difference = self._round_currency(target_total - current_total)
        
        if difference != 0 and splits:
            # Add difference to the first split (arbitrary but consistent)
            splits[0]["amount_owed"] = self._round_currency(splits[0]["amount_owed"] + difference)
            splits[0]["rounding_adjustment"] = difference
        
        return splits
    
    def _round_currency(self, amount: float) -> float:
        """Round to 2 decimal places using proper currency rounding"""
        return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def _get_household_members(self, household_id: int) -> List[User]:
        """Get all active members of the household"""
        return self.db.query(User).filter(
            User.household_id == household_id,
            User.is_active == True
        ).all()
    
    def mark_split_paid(self, expense_id: int, user_id: int, payment_method: str = None) -> bool:
        """Mark a user's portion of an expense as paid"""
        
        expense = self.db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense or not expense.split_details:
            return False
        
        split_details = expense.split_details
        
        # Find and update the user's split
        for split in split_details["splits"]:
            if split["user_id"] == user_id:
                split["is_paid"] = True
                split["paid_at"] = str(datetime.utcnow())
                if payment_method:
                    split["payment_method"] = payment_method
                break
        
        # Check if all splits are paid
        all_paid = all(split["is_paid"] for split in split_details["splits"])
        split_details["all_paid"] = all_paid
        
        expense.split_details = split_details
        self.db.commit()
        
        return True
    
    def get_user_expense_summary(self, user_id: int, household_id: int) -> Dict[str, Any]:
        """Get summary of user's expense obligations"""
        
        expenses = self.db.query(Expense).filter(
            Expense.household_id == household_id
        ).all()
        
        total_owed = 0
        total_owed_to_user = 0
        unpaid_expenses = []
        
        for expense in expenses:
            if not expense.split_details:
                continue
                
            for split in expense.split_details["splits"]:
                if split["user_id"] == user_id and not split["is_paid"]:
                    total_owed += split["amount_owed"]
                    unpaid_expenses.append({
                        "expense_id": expense.id,
                        "description": expense.description,
                        "amount_owed": split["amount_owed"],
                        "created_at": expense.created_at
                    })
                elif expense.created_by == user_id and not split["is_paid"]:
                    total_owed_to_user += split["amount_owed"]
        
        return {
            "total_owed": self._round_currency(total_owed),
            "total_owed_to_user": self._round_currency(total_owed_to_user),
            "unpaid_expenses": unpaid_expenses,
            "net_balance": self._round_currency(total_owed_to_user - total_owed)
        }

from datetime import datetime
