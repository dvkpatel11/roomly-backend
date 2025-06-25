from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import Dict, List, Any, Union, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from ..models.expense import Expense, ExpensePayment
from ..models.user import User
from ..models.household_membership import HouseholdMembership
from ..schemas.expense import ExpenseCreate, ExpenseUpdate, SplitMethod
from dataclasses import dataclass
from ..utils.service_helpers import calculate_splits
from ..utils.service_helpers import ServiceHelpers


# Custom Exceptions
class ExpenseServiceError(Exception):
    """Base exception for expense service errors"""

    pass


class ExpenseNotFoundError(ExpenseServiceError):
    """Expense not found"""

    pass


class PermissionDeniedError(ExpenseServiceError):
    """Permission denied for operation"""

    pass


class BusinessRuleViolationError(ExpenseServiceError):
    """Business rule violation (e.g., invalid splits)"""

    pass


class PaymentValidationError(ExpenseServiceError):
    """Payment validation error"""

    pass


# Remove the schema import, add this at top of file:
@dataclass
class HouseholdMember:
    id: int
    name: str
    email: str
    role: str


class ExpenseService:
    def __init__(self, db: Session):
        self.db = db

    def create_expense_with_split(
        self,
        expense_data: ExpenseCreate,
        household_id: int,
        created_by: int,
        custom_splits: Dict[int, Union[float, str]] = None,
    ) -> Expense:
        """
        Create expense and calculate splits based on method.
        custom_splits: {user_id: amount_or_percentage}
        """

        # Validate permissions
        if not self._user_can_create_expense(created_by, household_id):
            raise PermissionDeniedError("User is not a member of this household")

        # Get household members for split calculation
        household_members = ServiceHelpers.get_household_members(household_id)
        if not household_members:
            raise BusinessRuleViolationError("Household has no active members")

        # Validate custom splits if provided
        if custom_splits:
            self._validate_custom_splits(
                expense_data.amount,
                expense_data.split_method,
                household_members,
                custom_splits,
            )

        try:
            # Create the expense
            expense = Expense(
                description=expense_data.description,
                amount=expense_data.amount,
                category=expense_data.category.value,
                split_method=expense_data.split_method.value,
                receipt_url=expense_data.receipt_url,
                notes=expense_data.notes,
                household_id=household_id,
                created_by=created_by,
            )

            # Calculate splits
            split_details = calculate_splits(
                expense_data.amount,
                expense_data.split_method,
                household_members,
                custom_splits or {},
            )

            expense.split_details = split_details

            self.db.add(expense)
            self.db.commit()
            self.db.refresh(expense)

            return expense

        except Exception as e:
            self.db.rollback()
            raise ExpenseServiceError(f"Failed to create expense: {str(e)}")

    def get_household_expenses(
        self,
        household_id: int,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        category: str = None,
        created_by: int = None,
    ) -> Dict[str, Any]:
        """Get household expenses with filtering and pagination"""

        if not self._user_can_view_household_expenses(user_id, household_id):
            raise PermissionDeniedError("User cannot view household expenses")

        # Build query with filters
        query = self.db.query(Expense).filter(Expense.household_id == household_id)

        if category:
            query = query.filter(Expense.category == category)

        if created_by:
            query = query.filter(Expense.created_by == created_by)

        # Get total count for pagination
        total_count = query.count()

        # Get expenses with pagination
        expenses = (
            query.order_by(desc(Expense.created_at)).offset(offset).limit(limit).all()
        )

        # Enrich with creator names and payment status
        expense_list = []
        for expense in expenses:
            creator = self.db.query(User).filter(User.id == expense.created_by).first()

            # Calculate payment status
            total_payments = (
                self.db.query(func.sum(ExpensePayment.amount_paid))
                .filter(ExpensePayment.expense_id == expense.id)
                .scalar()
                or 0
            )

            is_fully_paid = total_payments >= expense.amount - 0.01

            expense_list.append(
                {
                    "id": expense.id,
                    "description": expense.description,
                    "amount": expense.amount,
                    "category": expense.category,
                    "created_by": expense.created_by,
                    "created_by_name": creator.name if creator else "Unknown",
                    "created_at": expense.created_at,
                    "total_paid": float(total_payments),
                    "is_fully_paid": is_fully_paid,
                    "split_method": expense.split_method,
                }
            )

        return {
            "expenses": expense_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    def update_expense(
        self,
        expense_id: int,
        expense_updates: ExpenseUpdate,
        updated_by: int,
        custom_splits: Dict[int, Union[float, str]] = None,
    ) -> Expense:
        """Update expense with permission validation"""

        expense = self._get_expense_or_raise(expense_id)

        # Check permissions (creator or household admin can edit)
        if not self._user_can_edit_expense(updated_by, expense):
            raise PermissionDeniedError(
                "Only expense creator or household admin can edit"
            )

        # Check if expense has payments (restrict editing)
        if self._expense_has_payments(expense_id):
            raise BusinessRuleViolationError("Cannot edit expense that has payments")

        try:
            # Update basic fields
            update_data = expense_updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field != "split_method":  # Handle split_method separately
                    setattr(
                        expense,
                        field,
                        value.value if hasattr(value, "value") else value,
                    )

            # Recalculate splits if amount or split method changed
            if "amount" in update_data or "split_method" in update_data:
                household_members = ServiceHelpers.get_household_members(
                    expense.household_id
                )

                split_method = expense_updates.split_method or SplitMethod(
                    expense.split_method
                )
                amount = expense_updates.amount or expense.amount

                expense.split_details = calculate_splits(
                    amount, split_method, household_members, custom_splits or {}
                )

            expense.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(expense)
            return expense

        except Exception as e:
            self.db.rollback()
            raise ExpenseServiceError(f"Failed to update expense: {str(e)}")

    def delete_expense(self, expense_id: int, deleted_by: int) -> bool:
        """Delete expense with proper validation"""

        expense = self._get_expense_or_raise(expense_id)

        if not self._user_can_edit_expense(deleted_by, expense):
            raise PermissionDeniedError(
                "Only expense creator or household admin can delete"
            )

        if self._expense_has_payments(expense_id):
            raise BusinessRuleViolationError("Cannot delete expense that has payments")

        try:
            self.db.delete(expense)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise ExpenseServiceError(f"Failed to delete expense: {str(e)}")

    def _round_currency(self, amount: float) -> float:
        """Round to 2 decimal places using proper currency rounding"""
        return float(
            Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

    def get_user_expense_summary(
        self, user_id: int, household_id: int
    ) -> Dict[str, Any]:
        """Get comprehensive summary of user's expense obligations"""

        if not self._user_can_view_household_expenses(user_id, household_id):
            raise PermissionDeniedError("User cannot view household expenses")

        # Get all household expenses
        expenses = (
            self.db.query(Expense)
            .filter(Expense.household_id == household_id)
            .order_by(desc(Expense.created_at))
            .all()
        )

        total_owed = 0
        total_owed_to_user = 0
        unpaid_expenses = []
        expenses_created = []

        for expense in expenses:
            if not expense.split_details:
                continue

            # Check what user owes
            user_split = self._get_user_split_amount(expense, user_id)
            if user_split:
                user_payments = self._get_user_payments_total(expense.id, user_id)
                remaining = user_split - user_payments

                if remaining > 0.01:  # Has unpaid amount
                    total_owed += remaining
                    unpaid_expenses.append(
                        {
                            "expense_id": expense.id,
                            "description": expense.description,
                            "amount_owed": user_split,
                            "amount_paid": user_payments,
                            "remaining": self._round_currency(remaining),
                            "created_at": expense.created_at,
                            "category": expense.category,
                        }
                    )

            # Check what others owe to user (for expenses they created)
            if expense.created_by == user_id:
                for split in expense.split_details["splits"]:
                    if split["user_id"] != user_id:  # Others' shares
                        other_user_payments = self._get_user_payments_total(
                            expense.id, split["user_id"]
                        )
                        remaining = split["amount_owed"] - other_user_payments
                        if remaining > 0.01:
                            total_owed_to_user += remaining

                expenses_created.append(
                    {
                        "expense_id": expense.id,
                        "description": expense.description,
                        "total_amount": expense.amount,
                        "created_at": expense.created_at,
                        "category": expense.category,
                    }
                )

        return {
            "user_id": user_id,
            "household_id": household_id,
            "total_owed": self._round_currency(total_owed),
            "total_owed_to_user": self._round_currency(total_owed_to_user),
            "net_balance": self._round_currency(total_owed_to_user - total_owed),
            "unpaid_expenses_count": len(unpaid_expenses),
            "unpaid_expenses": unpaid_expenses,
            "expenses_created_count": len(expenses_created),
            "expenses_created": expenses_created,
            "summary_generated_at": datetime.utcnow(),
        }

    def get_payment_history(
        self,
        user_id: int,
        household_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get user's payment history for household"""

        if not self._user_can_view_household_expenses(user_id, household_id):
            raise PermissionDeniedError("User cannot view household expenses")

        # Get payments with expense details
        payments_query = (
            self.db.query(ExpensePayment, Expense)
            .join(Expense, ExpensePayment.expense_id == Expense.id)
            .filter(
                and_(
                    ExpensePayment.paid_by == user_id,
                    Expense.household_id == household_id,
                )
            )
            .order_by(desc(ExpensePayment.payment_date))
        )

        total_count = payments_query.count()
        payments = payments_query.offset(offset).limit(limit).all()

        payment_history = []
        for payment, expense in payments:
            payment_history.append(
                {
                    "payment_id": payment.id,
                    "amount_paid": payment.amount_paid,
                    "payment_method": payment.payment_method,
                    "payment_date": payment.payment_date,
                    "expense": {
                        "id": expense.id,
                        "description": expense.description,
                        "total_amount": expense.amount,
                        "category": expense.category,
                        "created_at": expense.created_at,
                    },
                }
            )

        total_paid = sum(payment.amount_paid for payment, _ in payments)

        return {
            "payments": payment_history,
            "total_count": total_count,
            "total_paid_shown": float(total_paid),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
        }

    def record_expense_payment(
        self,
        expense_id: int,
        paid_by: int,
        amount_paid: float,
        payment_method: str = None,
        notes: str = None,
    ) -> ExpensePayment:
        """Record actual payment with comprehensive validation"""

        expense = self._get_expense_or_raise(expense_id)

        # Validate payment permissions
        if not self._user_can_make_payment(paid_by, expense):
            raise PermissionDeniedError("User cannot make payments for this expense")

        # Validate payment amount
        user_split = self._get_user_split_amount(expense, paid_by)
        if user_split is None:
            raise PaymentValidationError(
                f"User {paid_by} is not part of expense {expense_id} split"
            )
        already_paid = self._get_user_payments_total(expense_id, paid_by)
        remaining_owed = user_split - already_paid

        if amount_paid > remaining_owed + 0.01:  # Small tolerance for rounding
            raise PaymentValidationError(
                f"Payment amount ${amount_paid:.2f} exceeds remaining owed ${remaining_owed:.2f}"
            )

        try:
            # Create payment record
            payment = ExpensePayment(
                expense_id=expense_id,
                paid_by=paid_by,
                amount_paid=self._round_currency(amount_paid),
                payment_method=payment_method,
                payment_date=datetime.utcnow(),
            )

            self.db.add(payment)

            # Update split details for UI consistency
            self._update_split_payment_status(
                expense, paid_by, amount_paid, payment_method
            )

            self.db.commit()
            self.db.refresh(payment)
            return payment

        except Exception as e:
            self.db.rollback()
            raise ExpenseServiceError(f"Failed to record payment: {str(e)}")

    def get_expense_details(self, expense_id: int, requested_by: int) -> Dict[str, Any]:
        """Get comprehensive expense details with permissions check"""

        expense = self._get_expense_or_raise(expense_id)

        if not self._user_can_view_expense(requested_by, expense):
            raise PermissionDeniedError("User cannot view this expense")

        # Get payment records
        payments = (
            self.db.query(ExpensePayment, User.name)
            .join(User, ExpensePayment.paid_by == User.id)
            .filter(ExpensePayment.expense_id == expense_id)
            .order_by(desc(ExpensePayment.payment_date))
            .all()
        )

        payment_details = []
        for payment, user_name in payments:
            payment_details.append(
                {
                    "id": payment.id,
                    "paid_by": payment.paid_by,
                    "paid_by_name": user_name,
                    "amount_paid": payment.amount_paid,
                    "payment_method": payment.payment_method,
                    "payment_date": payment.payment_date,
                }
            )

        # Calculate payment status for each user
        split_status = []
        if expense.split_details:
            for split in expense.split_details["splits"]:
                user_payments = self._get_user_payments_total(
                    expense_id, split["user_id"]
                )
                remaining = split["amount_owed"] - user_payments

                split_status.append(
                    {
                        "user_id": split["user_id"],
                        "user_name": split["user_name"],
                        "amount_owed": split["amount_owed"],
                        "amount_paid": user_payments,
                        "remaining_owed": self._round_currency(remaining),
                        "is_fully_paid": remaining <= 0.01,  # Tolerance for rounding
                        "calculation_method": split.get(
                            "calculation_method", "unknown"
                        ),
                    }
                )

        return {
            "expense": {
                "id": expense.id,
                "description": expense.description,
                "amount": expense.amount,
                "category": expense.category,
                "split_method": expense.split_method,
                "receipt_url": expense.receipt_url,
                "notes": expense.notes,
                "created_by": expense.created_by,
                "created_at": expense.created_at,
                "updated_at": expense.updated_at,
            },
            "split_details": expense.split_details,
            "split_status": split_status,
            "payments": payment_details,
            "total_paid": sum(p.amount_paid for p, _ in payments),
            "is_fully_paid": all(s["is_fully_paid"] for s in split_status),
        }

    def mark_split_paid(
        self, expense_id: int, user_id: int, payment_method: str = None
    ) -> bool:
        """Mark a user's portion of an expense as paid"""

        expense = self.db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense or not expense.split_details:
            return False

        split_details = expense.split_details.copy()

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

        from sqlalchemy.orm.attributes import flag_modified

        expense.split_details = split_details
        flag_modified(expense, "split_details")

        self.db.commit()
        return True

    def _validate_custom_splits(
        self,
        total_amount: float,
        split_method: SplitMethod,
        household_members: List[HouseholdMember],
        custom_splits: Dict[int, Union[float, str]],
    ) -> None:
        """Validate custom splits before processing"""

        member_ids = {m.id for m in household_members}

        # Check all specified users are household members
        for user_id in custom_splits.keys():
            if user_id not in member_ids:
                raise BusinessRuleViolationError(
                    f"User {user_id} is not a household member"
                )

        if split_method == SplitMethod.SPECIFIC:
            # For specific amounts, check they don't exceed total
            specified_total = sum(float(amount) for amount in custom_splits.values())
            if specified_total > total_amount + 0.01:
                raise BusinessRuleViolationError(
                    "Custom amounts exceed total expense amount"
                )

        elif split_method == SplitMethod.PERCENTAGE:
            # For percentages, check they don't exceed 100%
            total_percentage = sum(float(pct) for pct in custom_splits.values())
            if total_percentage > 100:
                raise BusinessRuleViolationError("Total percentages cannot exceed 100%")

    def _get_expense_or_raise(self, expense_id: int) -> Expense:
        """Get expense or raise exception"""
        expense = self.db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise ExpenseNotFoundError(f"Expense {expense_id} not found")
        return expense

    def _user_can_create_expense(self, user_id: int, household_id: int) -> bool:
        """Check if user can create expenses for household"""
        return (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        ) is not None

    def _user_can_edit_expense(self, user_id: int, expense: Expense) -> bool:
        """Check if user can edit expense (creator or admin)"""
        if expense.created_by == user_id:
            return True

        # Check if user is household admin
        admin_membership = (
            self.db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == expense.household_id,
                    HouseholdMembership.role == "admin",
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
        )
        return admin_membership is not None

    def _user_can_view_expense(self, user_id: int, expense: Expense) -> bool:
        """Check if user can view expense details"""
        return self._user_can_create_expense(user_id, expense.household_id)

    def _user_can_view_household_expenses(
        self, user_id: int, household_id: int
    ) -> bool:
        """Check if user can view household expenses"""
        return self._user_can_create_expense(user_id, household_id)

    def _user_can_make_payment(self, user_id: int, expense: Expense) -> bool:
        """Check if user can make payments for expense"""
        return self._user_can_create_expense(user_id, expense.household_id)

    def _expense_has_payments(self, expense_id: int) -> bool:
        """Check if expense has any payment records"""
        return (
            self.db.query(ExpensePayment)
            .filter(ExpensePayment.expense_id == expense_id)
            .first()
        ) is not None

    def _get_user_split_amount(self, expense: Expense, user_id: int) -> Optional[float]:
        """Get the amount a user owes for an expense"""
        if not expense.split_details:
            return None

        for split in expense.split_details["splits"]:
            if split["user_id"] == user_id:
                return split["amount_owed"]
        return None

    def _get_user_payments_total(self, expense_id: int, user_id: int) -> float:
        """Get total amount user has paid for expense"""
        total = (
            self.db.query(func.sum(ExpensePayment.amount_paid))
            .filter(
                and_(
                    ExpensePayment.expense_id == expense_id,
                    ExpensePayment.paid_by == user_id,
                )
            )
            .scalar()
        )
        return float(total or 0)

    def _update_split_payment_status(
        self, expense: Expense, user_id: int, amount_paid: float, payment_method: str
    ) -> None:
        """Update split_details JSON for UI consistency"""
        if not expense.split_details:
            return

        split_details = expense.split_details.copy()

        # Find and update user's split status
        for split in split_details["splits"]:
            if split["user_id"] == user_id:
                total_paid = (
                    self._get_user_payments_total(expense.id, user_id) + amount_paid
                )
                split["amount_paid"] = total_paid
                split["is_paid"] = total_paid >= split["amount_owed"] - 0.01
                if split["is_paid"]:
                    split["paid_at"] = datetime.utcnow().isoformat()
                if payment_method:
                    split["payment_method"] = payment_method
                break

        # Check if all splits are paid
        all_paid = all(split["is_paid"] for split in split_details["splits"])
        split_details["all_paid"] = all_paid

        # Update expense
        from sqlalchemy.orm.attributes import flag_modified

        expense.split_details = split_details
        flag_modified(expense, "split_details")
