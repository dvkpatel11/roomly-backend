import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from .constants import AppConstants
from datetime import timedelta


class ValidationHelpers:
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format (flexible)"""
        if not phone:
            return True  # Optional field

        # Remove all non-numeric characters
        digits_only = re.sub(r"\D", "", phone)

        # Check if it's a reasonable length (7-15 digits)
        return 7 <= len(digits_only) <= 15

    @staticmethod
    def validate_amount(
        amount: float, max_amount: float = AppConstants.MAX_EXPENSE_AMOUNT
    ) -> bool:
        """Validate monetary amount"""
        return 0 < amount <= max_amount

    @staticmethod
    def validate_percentage(percentage: float) -> bool:
        """Validate percentage (0-100)"""
        return 0 <= percentage <= 100

    @staticmethod
    def validate_split_ratios(
        ratios: Dict[int, float], total_amount: float
    ) -> Dict[str, Any]:
        """
        Validate expense split ratios.

        Returns:
            dict: {
                "valid": bool,         # Whether the split ratios are valid
                "errors": list,        # List of error messages (if any)
                "total_ratio": float   # The sum of all split ratios
            }
        """
        errors = []

        if not ratios:
            return {"valid": False, "errors": ["No split ratios provided"]}

        # Check individual ratios
        for user_id, ratio in ratios.items():
            if not isinstance(user_id, int) or user_id <= 0:
                errors.append(f"Invalid user ID: {user_id}")

            if not isinstance(ratio, (int, float)) or ratio < 0:
                errors.append(f"Invalid ratio for user {user_id}: {ratio}")

        # Check total doesn't exceed 100% for percentages
        total_ratio = sum(ratios.values())
        if all(0 <= ratio <= 100 for ratio in ratios.values()):
            # Assume percentages
            if total_ratio > 100:
                errors.append(f"Total percentage exceeds 100%: {total_ratio}%")
        else:
            # Assume fixed amounts
            if total_ratio > total_amount:
                errors.append(
                    f"Total split amount exceeds expense amount: ${total_ratio} > ${total_amount}"
                )

        return {"valid": len(errors) == 0, "errors": errors, "total_ratio": total_ratio}

    @staticmethod
    def validate_date_range(
        start_date: datetime, end_date: Optional[datetime] = None
    ) -> bool:
        """Validate date range"""
        if not start_date:
            return False

        if end_date and end_date <= start_date:
            return False

        # Check if start date is not too far in the past (e.g., more than 1 year)
        one_year_ago = datetime.utcnow().replace(year=datetime.utcnow().year - 1)
        if start_date < one_year_ago:
            return False

        # Check if start date is not too far in the future (e.g., more than 2 years)
        two_years_future = datetime.utcnow().replace(year=datetime.utcnow().year + 2)
        if start_date > two_years_future:
            return False

        return True

    @staticmethod
    def validate_household_size(member_count: int) -> bool:
        """Validate household member count"""
        return 1 <= member_count <= AppConstants.MAX_HOUSEHOLD_MEMBERS

    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitize and truncate text input"""
        if not text:
            return ""

        # Strip whitespace and limit length
        sanitized = text.strip()[:max_length]

        # Remove any potentially harmful characters (basic sanitization)
        # In production, you might want more sophisticated sanitization
        sanitized = re.sub(r"[<>\"\'&]", "", sanitized)

        return sanitized

    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
        """Validate file extension"""
        if not filename:
            return False

        file_extension = filename.lower().split(".")[-1]
        return f".{file_extension}" in [ext.lower() for ext in allowed_extensions]

    @staticmethod
    def validate_recurring_pattern(
        pattern: str, start_date: datetime
    ) -> Dict[str, Any]:
        """Validate recurring pattern configuration"""
        valid_patterns = ["daily", "weekly", "biweekly", "monthly", "yearly"]

        if pattern not in valid_patterns:
            return {
                "valid": False,
                "error": f"Invalid pattern. Must be one of: {', '.join(valid_patterns)}",
            }

        # Additional pattern-specific validation could go here
        return {"valid": True}

    @staticmethod
    def validate_guest_stay_duration(
        check_in: datetime, check_out: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Validate guest stay duration"""
        if not check_in:
            return {"valid": False, "error": "Check-in date required"}

        now = datetime.utcnow()

        # Check-in can't be too far in the past
        if check_in < now - timedelta(days=1):
            return {"valid": False, "error": "Check-in date cannot be in the past"}

        if check_out:
            if check_out <= check_in:
                return {"valid": False, "error": "Check-out must be after check-in"}

            stay_duration = (check_out - check_in).days
            if stay_duration > AppConstants.MAX_GUEST_DAYS:
                return {
                    "valid": False,
                    "error": f"Stay duration cannot exceed {AppConstants.MAX_GUEST_DAYS} days",
                }

        return {"valid": True}
