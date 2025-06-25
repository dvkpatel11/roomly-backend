from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models.user import User
from ..models.household_membership import HouseholdMembership
from typing import List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from ..schemas.expense import SplitMethod
from ..schemas.household import HouseholdMember


class ServiceHelpers:
    @staticmethod
    def get_household_members(db: Session, household_id: int):
        """Shared function for getting household members"""
        return (
            db.query(User, HouseholdMembership)
            .join(HouseholdMembership, User.id == HouseholdMembership.user_id)
            .filter(
                and_(
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .all()
        )

    @staticmethod
    def check_household_membership(
        db: Session, user_id: int, household_id: int
    ) -> bool:
        """Shared permission check"""
        return (
            db.query(HouseholdMembership)
            .filter(
                and_(
                    HouseholdMembership.user_id == user_id,
                    HouseholdMembership.household_id == household_id,
                    HouseholdMembership.is_active == True,
                )
            )
            .first()
            is not None
        )


def round_currency(amount: float) -> float:
    return float(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_splits(
    total_amount: float,
    split_method: SplitMethod,
    household_members: List[HouseholdMember],
    custom_splits: Dict[int, Union[float, str]],
) -> Dict[str, Any]:
    """Calculate how an expense should be split among members"""

    if not household_members:
        raise Exception("No household members to split expense among")

    if split_method == SplitMethod.EQUAL:
        splits = _calculate_equal_splits(total_amount, household_members)

    elif split_method in [SplitMethod.SPECIFIC, SplitMethod.BY_USAGE]:
        splits = _calculate_custom_splits(
            total_amount, household_members, custom_splits
        )

    elif split_method == SplitMethod.PERCENTAGE:
        splits = _calculate_percentage_splits(
            total_amount, household_members, custom_splits
        )

    splits = _adjust_for_rounding(splits, total_amount)

    return {
        "splits": splits,
        "total_amount": total_amount,
        "split_method": split_method.value,
        "calculated_at": datetime.utcnow().isoformat(),
        "all_paid": False,
    }


def _calculate_equal_splits(
    self, total_amount: float, household_members: List[HouseholdMember]
) -> List[Dict[str, Any]]:
    """Equal split among all members"""
    per_person = self._round_currency(total_amount / len(household_members))

    splits = []
    for member in household_members:
        splits.append(
            {
                "user_id": member.id,
                "user_name": member.name,
                "amount_owed": per_person,
                "calculation_method": "equal",
                "is_paid": False,
            }
        )

    return splits


def _calculate_custom_splits(
    self,
    total_amount: float,
    household_members: List[HouseholdMember],
    custom_splits: Dict[int, Union[float, str]],
) -> List[Dict[str, Any]]:
    """Handle custom fixed amounts"""

    splits = []
    remaining_amount = total_amount
    specified_members = set()

    # First, handle members with specified amounts
    for member in household_members:
        if member.id in custom_splits:
            amount = float(custom_splits[member.id])
            if amount < 0:
                raise Exception(f"Negative amount not allowed for {member.name}")

            amount = self._round_currency(amount)
            specified_members.add(member.id)

            splits.append(
                {
                    "user_id": member.id,
                    "user_name": member.name,
                    "amount_owed": amount,
                    "calculation_method": "custom_amount",
                    "is_paid": False,
                }
            )

            remaining_amount -= amount

    # Split remaining amount equally among unspecified members
    unspecified_members = [
        m for m in household_members if m.id not in specified_members
    ]

    if unspecified_members and remaining_amount > 0:
        per_person = self._round_currency(remaining_amount / len(unspecified_members))

        for member in unspecified_members:
            splits.append(
                {
                    "user_id": member.id,
                    "user_name": member.name,
                    "amount_owed": per_person,
                    "calculation_method": "equal_remaining",
                    "is_paid": False,
                }
            )
    elif remaining_amount < -0.01:  # Negative remaining (over-specified)
        raise Exception("Custom amounts exceed total expense amount")

    return splits


def _calculate_percentage_splits(
    self,
    total_amount: float,
    household_members: List[HouseholdMember],
    custom_splits: Dict[int, Union[float, str]],
) -> List[Dict[str, Any]]:
    """Handle percentage-based splits"""

    splits = []
    total_percentage = 0
    specified_members = set()

    # Calculate amounts for specified percentages
    for member in household_members:
        if member.id in custom_splits:
            percentage = float(custom_splits[member.id])
            if percentage < 0 or percentage > 100:
                raise Exception(f"Percentage must be between 0-100% for {member.name}")

            amount = self._round_currency(total_amount * (percentage / 100))
            total_percentage += percentage
            specified_members.add(member.id)

            splits.append(
                {
                    "user_id": member.id,
                    "user_name": member.name,
                    "amount_owed": amount,
                    "calculation_method": f"{percentage}%",
                    "is_paid": False,
                }
            )

    if total_percentage > 100:
        raise Exception("Total percentages cannot exceed 100%")

    # Handle remaining percentage equally if not 100%
    if total_percentage < 100:
        remaining_percentage = 100 - total_percentage
        unspecified_members = [
            m for m in household_members if m.id not in specified_members
        ]

        if unspecified_members:
            per_person_percentage = remaining_percentage / len(unspecified_members)

            for member in unspecified_members:
                amount = self._round_currency(
                    total_amount * (per_person_percentage / 100)
                )

                splits.append(
                    {
                        "user_id": member.id,
                        "user_name": member.name,
                        "amount_owed": amount,
                        "calculation_method": f"{per_person_percentage:.1f}%",
                        "is_paid": False,
                    }
                )

    return splits


def _adjust_for_rounding(
    self, splits: List[Dict[str, Any]], target_total: float
) -> List[Dict[str, Any]]:
    """Adjust splits to ensure total equals target amount exactly"""

    current_total = sum(split["amount_owed"] for split in splits)
    difference = self._round_currency(target_total - current_total)

    if abs(difference) > 0.01:  # Significant difference
        raise Exception(f"Split calculation error: total mismatch of ${difference:.2f}")

    if difference != 0 and splits:
        # Add difference to the largest split (most fair)
        largest_split = max(splits, key=lambda s: s["amount_owed"])
        largest_split["amount_owed"] = self._round_currency(
            largest_split["amount_owed"] + difference
        )
        if abs(difference) > 0.005:  # Only note significant adjustments
            largest_split["rounding_adjustment"] = difference

    return splits
