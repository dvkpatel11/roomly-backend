from datetime import datetime, timedelta, date
from typing import List, Tuple
from dateutil.relativedelta import relativedelta
import calendar
from enum import Enum


class RecurrenceType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class DateHelpers:
    @staticmethod
    def get_next_occurrence(
        start_date: datetime, recurrence_type: RecurrenceType, occurrences: int = 1
    ) -> datetime:
        """Calculate next occurrence(s) of a recurring date"""

        if recurrence_type == RecurrenceType.DAILY:
            return start_date + timedelta(days=occurrences)
        elif recurrence_type == RecurrenceType.WEEKLY:
            return start_date + timedelta(weeks=occurrences)
        elif recurrence_type == RecurrenceType.BIWEEKLY:
            return start_date + timedelta(weeks=2 * occurrences)
        elif recurrence_type == RecurrenceType.MONTHLY:
            return start_date + relativedelta(months=occurrences)
        elif recurrence_type == RecurrenceType.YEARLY:
            return start_date + relativedelta(years=occurrences)
        else:
            raise ValueError(f"Unsupported recurrence type: {recurrence_type}")

    @staticmethod
    def get_month_boundaries(year: int, month: int) -> Tuple[datetime, datetime]:
        """Get start and end datetime for a given month"""
        start_date = datetime(year, month, 1)

        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        return start_date, end_date

    @staticmethod
    def get_week_boundaries(target_date: datetime) -> Tuple[datetime, datetime]:
        """Get start (Monday) and end (Sunday) of week containing target_date"""
        days_since_monday = target_date.weekday()
        start_of_week = target_date - timedelta(days=days_since_monday)
        end_of_week = start_of_week + timedelta(days=6)

        # Set to start/end of day
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = end_of_week.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        return start_of_week, end_of_week

    @staticmethod
    def get_bill_due_date(year: int, month: int, due_day: int) -> datetime:
        """Calculate bill due date, handling month-end edge cases"""

        # Handle months with fewer days
        last_day_of_month = calendar.monthrange(year, month)[1]
        actual_due_day = min(due_day, last_day_of_month)

        return datetime(year, month, actual_due_day, 23, 59, 59)

    @staticmethod
    def generate_bill_schedule(
        start_date: datetime, due_day: int, months_ahead: int = 12
    ) -> List[datetime]:
        """Generate bill due dates for next N months"""

        schedule = []
        current_date = start_date

        for _ in range(months_ahead):
            # Move to next month
            if current_date.month == 12:
                next_month = datetime(current_date.year + 1, 1, 1)
            else:
                next_month = datetime(current_date.year, current_date.month + 1, 1)

            # Calculate due date for this month
            due_date = DateHelpers.get_bill_due_date(
                next_month.year, next_month.month, due_day
            )
            schedule.append(due_date)
            current_date = next_month

        return schedule

    @staticmethod
    def is_overdue(due_date: datetime, grace_hours: int = 0) -> bool:
        """Check if a due date has passed (with optional grace period)"""
        if not due_date:
            return False

        cutoff = datetime.utcnow() - timedelta(hours=grace_hours)
        return due_date < cutoff

    @staticmethod
    def get_relative_time_description(target_date: datetime) -> str:
        """Get human-readable relative time description"""
        now = datetime.utcnow()
        diff = target_date - now

        if diff.total_seconds() < 0:
            # Past
            diff = abs(diff)
            if diff.days > 7:
                return f"{diff.days} days ago"
            elif diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                return "Recently"
        else:
            # Future
            if diff.days > 7:
                return f"In {diff.days} days"
            elif diff.days > 0:
                return f"In {diff.days} day{'s' if diff.days > 1 else ''}"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"In {hours} hour{'s' if hours > 1 else ''}"
            else:
                return "Soon"

    @staticmethod
    def get_business_days_between(start_date: date, end_date: date) -> int:
        """Calculate business days between two dates"""
        business_days = 0
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                business_days += 1
            current_date += timedelta(days=1)

        return business_days

    @staticmethod
    def format_duration(minutes: int) -> str:
        """Format duration in minutes to human readable string"""
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"

        hours = minutes // 60
        remaining_minutes = minutes % 60

        if remaining_minutes == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            return f"{hours}h {remaining_minutes}m"

    @staticmethod
    def get_notification_timing(
        target_date: datetime, advance_hours: List[int] = [24, 2]
    ) -> List[datetime]:
        """Calculate when to send notifications before an event"""

        notification_times = []

        for hours in advance_hours:
            notification_time = target_date - timedelta(hours=hours)

            # Only include future notification times
            if notification_time > datetime.utcnow():
                notification_times.append(notification_time)

        return sorted(notification_times)
