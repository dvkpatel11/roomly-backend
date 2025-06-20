# Additional methods to add to your HouseholdService class

from datetime import datetime, timedelta
from typing import List, Dict, Any
from ..models.expense import Expense
from ..models.task import Task
from ..models.security_deposit import SecurityDeposit
from ..models.damage_report import DamageReport


class MoveOutService:
    """Extended functionality for move-out/move-in processes"""

    def initiate_move_out_process(
        self,
        household_id: int,
        user_id: int,
        move_out_date: datetime,
        initiated_by: int = None,
    ) -> Dict[str, Any]:
        """Initiate comprehensive move-out process"""

        # Validate permissions
        if initiated_by and initiated_by != user_id:
            if not self.check_admin_permissions(initiated_by, household_id):
                raise PermissionDeniedError("Only admin or user can initiate move-out")

        membership = self._get_active_membership(user_id, household_id)
        if not membership:
            raise BusinessRuleViolationError("User is not a member of this household")

        # Check if move-out date is reasonable (not in past, not too far future)
        if move_out_date < datetime.utcnow():
            raise BusinessRuleViolationError("Move-out date cannot be in the past")

        if move_out_date > datetime.utcnow() + timedelta(days=90):
            raise BusinessRuleViolationError(
                "Move-out date cannot be more than 90 days in future"
            )

        try:
            # Create move-out record
            move_out_record = MoveOutRecord(
                household_id=household_id,
                user_id=user_id,
                planned_move_out_date=move_out_date,
                status="initiated",
                initiated_at=datetime.utcnow(),
                initiated_by=initiated_by or user_id,
            )
            self.db.add(move_out_record)
            self.db.flush()

            # Generate comprehensive move-out checklist
            checklist = self._generate_move_out_checklist(
                household_id, user_id, move_out_date
            )

            # Calculate financial obligations
            financial_summary = self._calculate_move_out_financials(
                household_id, user_id, move_out_date
            )

            # Get pending responsibilities
            responsibilities = self._get_detailed_pending_responsibilities(
                user_id, move_out_date
            )

            self.db.commit()

            return {
                "move_out_id": move_out_record.id,
                "status": "initiated",
                "planned_date": move_out_date,
                "checklist": checklist,
                "financial_summary": financial_summary,
                "pending_responsibilities": responsibilities,
                "estimated_completion_time": "7-14 days",
                "next_steps": [
                    "Complete financial settlement",
                    "Transfer or complete assigned tasks",
                    "Schedule move-out inspection",
                    "Update utilities and services",
                ],
            }

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to initiate move-out: {str(e)}")

    def _generate_move_out_checklist(
        self, household_id: int, user_id: int, move_out_date: datetime
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate comprehensive move-out checklist"""

        checklist = {
            "financial_tasks": [
                {
                    "id": "settle_expenses",
                    "title": "Settle all outstanding expenses",
                    "description": "Pay any pending shared expenses and bills",
                    "deadline": move_out_date - timedelta(days=7),
                    "status": "pending",
                    "priority": "high",
                },
                {
                    "id": "final_bills",
                    "title": "Handle final utility bills",
                    "description": "Coordinate final readings and bill settlements",
                    "deadline": move_out_date - timedelta(days=3),
                    "status": "pending",
                    "priority": "high",
                },
                {
                    "id": "security_deposit",
                    "title": "Coordinate security deposit return",
                    "description": "Complete damage assessment and deposit calculation",
                    "deadline": move_out_date + timedelta(days=30),
                    "status": "pending",
                    "priority": "medium",
                },
            ],
            "household_tasks": [
                {
                    "id": "transfer_tasks",
                    "title": "Transfer assigned household tasks",
                    "description": "Reassign or complete all pending household responsibilities",
                    "deadline": move_out_date - timedelta(days=5),
                    "status": "pending",
                    "priority": "medium",
                },
                {
                    "id": "deep_clean",
                    "title": "Deep clean assigned areas",
                    "description": "Thoroughly clean bedroom and shared areas as per agreement",
                    "deadline": move_out_date,
                    "status": "pending",
                    "priority": "high",
                },
            ],
            "administrative_tasks": [
                {
                    "id": "address_change",
                    "title": "Update address with services",
                    "description": "Bank, insurance, subscriptions, employer, etc.",
                    "deadline": move_out_date + timedelta(days=14),
                    "status": "pending",
                    "priority": "medium",
                },
                {
                    "id": "key_return",
                    "title": "Return all keys and access cards",
                    "description": "House keys, mailbox keys, garage remotes, etc.",
                    "deadline": move_out_date,
                    "status": "pending",
                    "priority": "high",
                },
            ],
            "inspection_tasks": [
                {
                    "id": "pre_inspection",
                    "title": "Schedule pre-move-out inspection",
                    "description": "Walk-through with roommates/landlord to identify issues",
                    "deadline": move_out_date - timedelta(days=7),
                    "status": "pending",
                    "priority": "high",
                },
                {
                    "id": "final_inspection",
                    "title": "Final move-out inspection",
                    "description": "Document room condition and complete damage assessment",
                    "deadline": move_out_date,
                    "status": "pending",
                    "priority": "high",
                },
            ],
        }

        return checklist

    def _calculate_move_out_financials(
        self, household_id: int, user_id: int, move_out_date: datetime
    ) -> Dict[str, Any]:
        """Calculate comprehensive financial obligations for move-out"""

        # Outstanding expenses owed BY user
        outstanding_expenses = (
            self.db.query(Expense)
            .join(ExpensePayment, Expense.id == ExpensePayment.expense_id)
            .filter(
                and_(
                    Expense.household_id == household_id,
                    ExpensePayment.user_id == user_id,
                    ExpensePayment.status == "pending",
                )
            )
            .all()
        )

        total_owed_by_user = sum(
            ep.amount_owed
            for expense in outstanding_expenses
            for ep in expense.payments
            if ep.user_id == user_id and ep.status == "pending"
        )

        # Outstanding expenses owed TO user
        expenses_owed_to_user = (
            self.db.query(Expense)
            .filter(
                and_(
                    Expense.household_id == household_id,
                    Expense.created_by == user_id,
                    Expense.status == "pending",
                )
            )
            .all()
        )

        total_owed_to_user = sum(
            ep.amount_owed
            for expense in expenses_owed_to_user
            for ep in expense.payments
            if ep.user_id != user_id and ep.status == "pending"
        )

        # Prorated rent calculation
        days_in_month = 30  # Simplified
        days_remaining = (move_out_date.replace(day=1) + timedelta(days=32)).replace(
            day=1
        ) - move_out_date
        rent_refund = 0  # Would need rent amount from household settings

        # Security deposit calculation
        security_deposit_info = self._get_security_deposit_info(household_id, user_id)

        return {
            "total_owed_by_user": float(total_owed_by_user),
            "total_owed_to_user": float(total_owed_to_user),
            "net_balance": float(total_owed_to_user - total_owed_by_user),
            "prorated_rent_adjustment": float(rent_refund),
            "security_deposit": security_deposit_info,
            "outstanding_expenses": [
                {
                    "id": exp.id,
                    "description": exp.description,
                    "amount": float(exp.amount),
                    "date": exp.created_at,
                    "status": exp.status,
                }
                for exp in outstanding_expenses
            ],
            "final_settlement_due": move_out_date + timedelta(days=7),
        }

    def _get_detailed_pending_responsibilities(
        self, user_id: int, move_out_date: datetime
    ) -> Dict[str, Any]:
        """Get detailed pending responsibilities that need handling"""

        # Pending tasks
        pending_tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.status.in_(["pending", "in_progress"]),
                    or_(Task.due_date.is_(None), Task.due_date >= datetime.utcnow()),
                )
            )
            .all()
        )

        # Recurring tasks that need reassignment
        recurring_tasks = (
            self.db.query(Task)
            .filter(
                and_(
                    Task.assigned_to == user_id,
                    Task.is_recurring == True,
                    Task.status == "active",
                )
            )
            .all()
        )

        # Shared purchases/subscriptions
        shared_subscriptions = (
            self.db.query(Expense)
            .filter(
                and_(
                    Expense.created_by == user_id,
                    Expense.is_recurring == True,
                    Expense.status == "active",
                )
            )
            .all()
        )

        return {
            "pending_one_time_tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "due_date": task.due_date,
                    "priority": task.priority,
                    "estimated_hours": task.estimated_hours,
                }
                for task in pending_tasks
            ],
            "recurring_tasks_to_reassign": [
                {
                    "id": task.id,
                    "title": task.title,
                    "frequency": task.recurrence_pattern,
                    "next_due": task.next_due_date,
                }
                for task in recurring_tasks
            ],
            "shared_subscriptions_to_transfer": [
                {
                    "id": exp.id,
                    "service": exp.description,
                    "amount": float(exp.amount),
                    "billing_cycle": exp.recurrence_pattern,
                }
                for exp in shared_subscriptions
            ],
            "total_items_requiring_action": len(pending_tasks)
            + len(recurring_tasks)
            + len(shared_subscriptions),
        }

    def complete_move_out_inspection(
        self,
        household_id: int,
        user_id: int,
        inspection_data: Dict[str, Any],
        inspector_id: int,
    ) -> Dict[str, Any]:
        """Complete move-out inspection with damage assessment"""

        # Validate inspector permissions
        if not (
            self.check_admin_permissions(inspector_id, household_id)
            or self.check_member_permissions(inspector_id, household_id)
        ):
            raise PermissionDeniedError("Inspector must be household member")

        try:
            # Create damage report
            damage_report = DamageReport(
                household_id=household_id,
                user_id=user_id,
                inspector_id=inspector_id,
                room_condition=inspection_data.get("room_condition", {}),
                damages_found=inspection_data.get("damages", []),
                cleaning_issues=inspection_data.get("cleaning_issues", []),
                estimated_repair_cost=inspection_data.get("estimated_repair_cost", 0),
                photos=inspection_data.get("photos", []),
                inspection_date=datetime.utcnow(),
                status="completed",
            )

            self.db.add(damage_report)
            self.db.flush()

            # Calculate security deposit deductions
            deposit_calculation = self._calculate_security_deposit_return(
                household_id, user_id, damage_report
            )

            self.db.commit()

            return {
                "inspection_id": damage_report.id,
                "damages_found": len(inspection_data.get("damages", [])),
                "estimated_repair_cost": float(
                    inspection_data.get("estimated_repair_cost", 0)
                ),
                "deposit_calculation": deposit_calculation,
                "inspection_photos": len(inspection_data.get("photos", [])),
                "next_steps": [
                    "Review damage assessment with all parties",
                    "Process security deposit return",
                    "Complete final financial settlement",
                ],
            }

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to complete inspection: {str(e)}")

    def finalize_move_out(
        self,
        household_id: int,
        user_id: int,
        final_settlement: Dict[str, Any],
        finalized_by: int,
    ) -> Dict[str, Any]:
        """Finalize move-out process with all settlements"""

        # Validate permissions
        if not self.check_admin_permissions(finalized_by, household_id):
            raise PermissionDeniedError("Only admin can finalize move-out")

        membership = self._get_active_membership(user_id, household_id)
        if not membership:
            raise BusinessRuleViolationError("User is not a member of this household")

        try:
            # Update membership status
            membership.is_active = False
            membership.moved_out_at = datetime.utcnow()
            membership.final_settlement = final_settlement

            # Create final settlement record
            settlement_record = FinalSettlement(
                household_id=household_id,
                user_id=user_id,
                final_balance=final_settlement.get("final_balance", 0),
                security_deposit_returned=final_settlement.get(
                    "security_deposit_returned", 0
                ),
                damage_deductions=final_settlement.get("damage_deductions", 0),
                settlement_date=datetime.utcnow(),
                processed_by=finalized_by,
                payment_method=final_settlement.get("payment_method", "pending"),
                notes=final_settlement.get("notes", ""),
            )

            self.db.add(settlement_record)

            # Archive user's data but preserve for audit trail
            self._archive_user_household_data(household_id, user_id)

            self.db.commit()

            return {
                "move_out_completed": True,
                "final_settlement_amount": float(
                    final_settlement.get("final_balance", 0)
                ),
                "security_deposit_returned": float(
                    final_settlement.get("security_deposit_returned", 0)
                ),
                "settlement_id": settlement_record.id,
                "completion_date": datetime.utcnow(),
                "status": "completed",
                "next_steps": [
                    "Process final payment within 7 business days",
                    "User access to household will be revoked",
                    "Audit trail preserved for records",
                ],
            }

        except Exception as e:
            self.db.rollback()
            raise HouseholdServiceError(f"Failed to finalize move-out: {str(e)}")

    def _get_security_deposit_info(
        self, household_id: int, user_id: int
    ) -> Dict[str, Any]:
        """Get security deposit information for user"""

        deposit_record = (
            self.db.query(SecurityDeposit)
            .filter(
                and_(
                    SecurityDeposit.household_id == household_id,
                    SecurityDeposit.user_id == user_id,
                    SecurityDeposit.status == "active",
                )
            )
            .first()
        )

        if not deposit_record:
            return {"amount": 0, "status": "not_found", "refundable": 0}

        return {
            "amount": float(deposit_record.amount),
            "paid_date": deposit_record.paid_date,
            "status": deposit_record.status,
            "refundable": float(
                deposit_record.amount
            ),  # Will be adjusted after inspection
            "conditions": deposit_record.conditions or [],
        }

    def _calculate_security_deposit_return(
        self, household_id: int, user_id: int, damage_report: DamageReport
    ) -> Dict[str, Any]:
        """Calculate security deposit return after inspection"""

        deposit_info = self._get_security_deposit_info(household_id, user_id)
        original_amount = deposit_info.get("amount", 0)

        # Calculate deductions
        damage_cost = float(damage_report.estimated_repair_cost or 0)
        cleaning_cost = self._calculate_cleaning_costs(damage_report.cleaning_issues)

        total_deductions = damage_cost + cleaning_cost
        refund_amount = max(0, original_amount - total_deductions)

        return {
            "original_deposit": original_amount,
            "damage_deductions": damage_cost,
            "cleaning_deductions": cleaning_cost,
            "total_deductions": total_deductions,
            "refund_amount": refund_amount,
            "refund_percentage": (
                round((refund_amount / original_amount) * 100, 1)
                if original_amount > 0
                else 0
            ),
            "deduction_breakdown": {
                "damages": damage_report.damages_found,
                "cleaning": damage_report.cleaning_issues,
            },
        }

    def _calculate_cleaning_costs(self, cleaning_issues: List[str]) -> float:
        """Calculate cleaning costs based on issues found"""

        cleaning_rates = {
            "deep_carpet_clean": 100.0,
            "wall_cleaning": 50.0,
            "bathroom_deep_clean": 75.0,
            "kitchen_deep_clean": 100.0,
            "window_cleaning": 30.0,
            "general_deep_clean": 200.0,
        }

        total_cost = 0
        for issue in cleaning_issues:
            issue_type = issue.get("type", "general_deep_clean")
            severity = issue.get("severity", "moderate")

            base_cost = cleaning_rates.get(issue_type, 50.0)

            # Adjust based on severity
            if severity == "minor":
                base_cost *= 0.5
            elif severity == "major":
                base_cost *= 1.5

            total_cost += base_cost

        return total_cost

    def _archive_user_household_data(self, household_id: int, user_id: int) -> None:
        """Archive user data while preserving audit trail"""

        # Mark tasks as archived instead of deleting
        self.db.query(Task).filter(
            and_(Task.household_id == household_id, Task.assigned_to == user_id)
        ).update({"status": "archived"})

        # Expenses remain for audit trail but are marked
        self.db.query(Expense).filter(
            and_(Expense.household_id == household_id, Expense.created_by == user_id)
        ).update({"archived": True})


# Additional models you'll need to create:

"""
class MoveOutRecord(Base):
    __tablename__ = "move_out_records"
    
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    planned_move_out_date = Column(DateTime)
    actual_move_out_date = Column(DateTime, nullable=True)
    status = Column(String(50))  # initiated, in_progress, completed, cancelled
    initiated_at = Column(DateTime, default=datetime.utcnow)
    initiated_by = Column(Integer, ForeignKey("users.id"))

class DamageReport(Base):
    __tablename__ = "damage_reports"
    
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    inspector_id = Column(Integer, ForeignKey("users.id"))
    room_condition = Column(JSON)
    damages_found = Column(JSON)
    cleaning_issues = Column(JSON)
    estimated_repair_cost = Column(Numeric(10, 2))
    photos = Column(JSON)
    inspection_date = Column(DateTime)
    status = Column(String(50))

class SecurityDeposit(Base):
    __tablename__ = "security_deposits"
    
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Numeric(10, 2))
    paid_date = Column(DateTime)
    status = Column(String(50))  # active, returned, forfeited
    conditions = Column(JSON)

class FinalSettlement(Base):
    __tablename__ = "final_settlements"
    
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    final_balance = Column(Numeric(10, 2))
    security_deposit_returned = Column(Numeric(10, 2))
    damage_deductions = Column(Numeric(10, 2))
    settlement_date = Column(DateTime)
    processed_by = Column(Integer, ForeignKey("users.id"))
    payment_method = Column(String(100))
    notes = Column(Text)
"""
