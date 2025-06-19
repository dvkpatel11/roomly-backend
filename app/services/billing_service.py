from app.models.household_membership import HouseholdMembership
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.bill import Bill, BillPayment
from ..models.user import User
from ..models.expense import Expense
from ..schemas.bill import BillCreate, BillUpdate
from ..utils.date_helpers import DateHelpers
from ..utils.constants import AppConstants
from .expense_service import ExpenseService
from dataclasses import dataclass


@dataclass
class HouseholdMember:
    """Communication service household member representation"""

    id: int
    name: str
    email: str
    role: str


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.expense_service = ExpenseService(db)

    def create_recurring_bill(
        self, bill_data: BillCreate, household_id: int, created_by: int
    ) -> Bill:
        """Create a new recurring bill"""

        bill = Bill(
            name=bill_data.name,
            amount=bill_data.amount,
            category=bill_data.category,
            due_day=bill_data.due_day,
            split_method=bill_data.split_method,
            notes=bill_data.notes,
            household_id=household_id,
            created_by=created_by,
            is_active=True,
        )

        self.db.add(bill)
        self.db.commit()
        self.db.refresh(bill)

        # Generate upcoming bill instances
        self._generate_bill_instances(bill)

        return bill

    def _generate_bill_instances(self, bill: Bill, months_ahead: int = 3):
        """Generate bill payment instances for upcoming months"""

        # Get next N months of due dates
        due_dates = DateHelpers.generate_bill_schedule(
            datetime.utcnow(), bill.due_day, months_ahead
        )

        for due_date in due_dates:
            # Check if bill instance already exists for this month
            month_key = due_date.strftime("%Y-%m")
            existing_payment = (
                self.db.query(BillPayment)
                .filter(
                    and_(
                        BillPayment.bill_id == bill.id,
                        BillPayment.for_month == month_key,
                    )
                )
                .first()
            )

            if not existing_payment:
                # Create expense for this bill instance
                expense = Expense(
                    description=f"{bill.name} - {due_date.strftime('%B %Y')}",
                    amount=bill.amount,
                    category=bill.category,
                    split_method=bill.split_method,
                    household_id=bill.household_id,
                    created_by=bill.created_by,
                    # Link to bill
                    notes=f"Auto-generated from bill: {bill.name}",
                )

                self.db.add(expense)
                self.db.flush()  # Get expense ID

                # Calculate splits for the expense
                household_members = self._get_household_members(bill.household_id)
                split_details = self.expense_service._calculate_splits(
                    bill.amount,
                    bill.split_method,
                    household_members,
                    {},  # No custom splits for recurring bills
                )

                expense.split_details = split_details

        self.db.commit()

    def record_bill_payment(
        self,
        bill_id: int,
        paid_by: int,
        amount_paid: float,
        payment_method: str,
        for_month: str,
        notes: str = "",
    ) -> BillPayment:
        """Record a bill payment"""

        bill = self.db.query(Bill).filter(Bill.id == bill_id).first()
        if not bill:
            raise ValueError("Bill not found")

        # Check if payment already exists for this month
        existing_payment = (
            self.db.query(BillPayment)
            .filter(
                and_(
                    BillPayment.bill_id == bill_id,
                    BillPayment.for_month == for_month,
                    BillPayment.paid_by == paid_by,
                )
            )
            .first()
        )

        if existing_payment:
            raise ValueError("Payment already recorded for this month")

        payment = BillPayment(
            bill_id=bill_id,
            paid_by=paid_by,
            amount_paid=amount_paid,
            payment_method=payment_method,
            for_month=for_month,
            notes=notes,
            payment_date=datetime.utcnow(),
        )

        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        return payment

    def get_upcoming_bills(
        self, household_id: int, days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Get bills due in the next N days"""

        now = datetime.utcnow()
        cutoff_date = now + timedelta(days=days_ahead)

        active_bills = (
            self.db.query(Bill)
            .filter(and_(Bill.household_id == household_id, Bill.is_active == True))
            .all()
        )

        upcoming = []

        for bill in active_bills:
            # Calculate next due date
            current_month = now.month
            current_year = now.year

            # Check current month
            current_due_date = DateHelpers.get_bill_due_date(
                current_year, current_month, bill.due_day
            )

            if current_due_date >= now and current_due_date <= cutoff_date:
                payment_status = self._get_bill_payment_status(
                    bill.id, f"{current_year}-{current_month:02d}"
                )

                upcoming.append(
                    {
                        "bill_id": bill.id,
                        "name": bill.name,
                        "amount": bill.amount,
                        "due_date": current_due_date,
                        "days_until_due": (current_due_date - now).days,
                        "payment_status": payment_status,
                        "category": bill.category,
                    }
                )

            # Check next month if current month's bill is past due
            elif current_due_date < now:
                next_month = current_month + 1 if current_month < 12 else 1
                next_year = current_year + 1 if current_month == 12 else current_year

                next_due_date = DateHelpers.get_bill_due_date(
                    next_year, next_month, bill.due_day
                )

                if next_due_date <= cutoff_date:
                    payment_status = self._get_bill_payment_status(
                        bill.id, f"{next_year}-{next_month:02d}"
                    )

                    upcoming.append(
                        {
                            "bill_id": bill.id,
                            "name": bill.name,
                            "amount": bill.amount,
                            "due_date": next_due_date,
                            "days_until_due": (next_due_date - now).days,
                            "payment_status": payment_status,
                            "category": bill.category,
                        }
                    )

        return sorted(upcoming, key=lambda x: x["due_date"])

    def get_overdue_bills(self, household_id: int) -> List[Dict[str, Any]]:
        """Get overdue bills for household"""

        now = datetime.utcnow()
        active_bills = (
            self.db.query(Bill)
            .filter(and_(Bill.household_id == household_id, Bill.is_active == True))
            .all()
        )

        overdue = []

        for bill in active_bills:
            # Check last few months for unpaid bills
            for months_back in range(0, 3):  # Check current month and 2 months back
                check_date = now - timedelta(days=months_back * 30)
                month_key = check_date.strftime("%Y-%m")

                due_date = DateHelpers.get_bill_due_date(
                    check_date.year, check_date.month, bill.due_day
                )

                if due_date < now:  # Past due
                    payment_status = self._get_bill_payment_status(bill.id, month_key)

                    if payment_status["total_paid"] < bill.amount:
                        overdue.append(
                            {
                                "bill_id": bill.id,
                                "name": bill.name,
                                "amount": bill.amount,
                                "amount_paid": payment_status["total_paid"],
                                "amount_remaining": bill.amount
                                - payment_status["total_paid"],
                                "due_date": due_date,
                                "days_overdue": (now - due_date).days,
                                "month": month_key,
                                "category": bill.category,
                            }
                        )

        return sorted(overdue, key=lambda x: x["days_overdue"], reverse=True)

    def _get_bill_payment_status(self, bill_id: int, month: str) -> Dict[str, Any]:
        """Get payment status for a bill in a specific month"""

        payments = (
            self.db.query(BillPayment)
            .filter(
                and_(BillPayment.bill_id == bill_id, BillPayment.for_month == month)
            )
            .all()
        )

        total_paid = sum(payment.amount_paid for payment in payments)
        payment_count = len(payments)

        return {
            "total_paid": total_paid,
            "payment_count": payment_count,
            "payments": [
                {
                    "amount": p.amount_paid,
                    "paid_by": p.paid_by,
                    "payment_date": p.payment_date,
                    "payment_method": p.payment_method,
                }
                for p in payments
            ],
        }

    def _get_household_members(self, household_id: int) -> List[HouseholdMember]:
        """Get all active members using HouseholdMembership"""

        members_query = (
            self.db.query(User, HouseholdMembership)
            .join(HouseholdMembership, User.id == HouseholdMembership.user_id)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                    User.is_active == True,
                )
            )
            .all()
        )

        return [
            HouseholdMember(
                id=user.id,
                name=user.name,
                email=user.email,
                role=membership.role,
            )
            for user, membership in members_query
        ]

    def get_bill_payment_history(
        self, bill_id: int, months_back: int = 12
    ) -> List[Dict[str, Any]]:
        """Get payment history for a bill"""

        payments = (
            self.db.query(BillPayment)
            .filter(BillPayment.bill_id == bill_id)
            .order_by(BillPayment.payment_date.desc())
            .limit(months_back)
            .all()
        )

        history = []
        for payment in payments:
            user = self.db.query(User).filter(User.id == payment.paid_by).first()

            history.append(
                {
                    "payment_id": payment.id,
                    "amount": payment.amount_paid,
                    "month": payment.for_month,
                    "paid_by": user.name if user else "Unknown",
                    "payment_date": payment.payment_date,
                    "payment_method": payment.payment_method,
                    "notes": payment.notes,
                }
            )

        return history

    def update_bill(self, bill_id: int, bill_update: BillUpdate) -> Bill:
        """Update recurring bill"""

        bill = self.db.query(Bill).filter(Bill.id == bill_id).first()
        if not bill:
            raise ValueError("Bill not found")

        # Update fields
        for field, value in bill_update.dict(exclude_unset=True).items():
            setattr(bill, field, value)

        self.db.commit()
        self.db.refresh(bill)

        return bill

    def deactivate_bill(self, bill_id: int) -> bool:
        """Deactivate a recurring bill"""

        bill = self.db.query(Bill).filter(Bill.id == bill_id).first()
        if not bill:
            return False

        bill.is_active = False
        self.db.commit()

        return True

    def get_household_billing_summary(self, household_id: int) -> Dict[str, Any]:
        """Get comprehensive billing summary for household"""

        active_bills = (
            self.db.query(Bill)
            .filter(and_(Bill.household_id == household_id, Bill.is_active == True))
            .all()
        )

        total_monthly_bills = sum(bill.amount for bill in active_bills)
        upcoming_bills = self.get_upcoming_bills(household_id, 30)
        overdue_bills = self.get_overdue_bills(household_id)

        return {
            "total_monthly_bills": total_monthly_bills,
            "active_bill_count": len(active_bills),
            "upcoming_bills": upcoming_bills,
            "overdue_bills": overdue_bills,
            "total_overdue_amount": sum(
                bill["amount_remaining"] for bill in overdue_bills
            ),
        }
