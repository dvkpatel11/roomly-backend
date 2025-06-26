from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..models.notification import Notification, NotificationPreference
from ..models.bill import Bill
from ..models.task import Task
from ..models.event import Event
from ..models.user import User
from ..utils.email import EmailService
from ..utils.date_helpers import DateHelpers
from ..schemas.enums import NotificationType
from dataclasses import dataclass
from ..utils.service_helpers import ServiceHelpers


@dataclass
class HouseholdMember:
    """Communication service household member representation"""

    id: int
    name: str
    email: str
    role: str


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()

    def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: str = "normal",
        related_entity_type: str = None,
        related_entity_id: int = None,
        action_url: str = None,
    ) -> Notification:
        """Create a notification for a user"""

        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type.value,
            priority=priority,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            action_url=action_url,
            is_read=False,
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        # Send notification based on user preferences
        self._deliver_notification(notification)

        return notification

    def _deliver_notification(self, notification: Notification):
        """Deliver notification via user's preferred methods"""

        preferences = self.get_user_preferences(notification.user_id)
        user = self.db.query(User).filter(User.id == notification.user_id).first()

        if not user:
            return

        notification_type = notification.notification_type

        # Check if user wants email notifications for this type
        email_enabled = self._should_send_email(notification_type, preferences)
        if email_enabled and user.email:
            self._send_email_notification(user, notification)
            notification.sent_email = True

        # Check if user wants push notifications for this type
        push_enabled = self._should_send_push(notification_type, preferences)
        if push_enabled:
            self._send_push_notification(user, notification)
            notification.sent_push = True

        # In-app notification is always sent
        notification.sent_in_app = True

        self.db.commit()

    def _should_send_email(self, notification_type: str, preferences: Dict) -> bool:
        """Check if email should be sent for this notification type"""

        email_map = {
            NotificationType.BILL_DUE.value: preferences.get(
                "bill_reminders_email", True
            ),
            NotificationType.BILL_OVERDUE.value: preferences.get(
                "bill_reminders_email", True
            ),
            NotificationType.TASK_OVERDUE.value: preferences.get(
                "task_reminders_email", True
            ),
            NotificationType.EVENT_REMINDER.value: preferences.get(
                "event_reminders_email", True
            ),
            NotificationType.GUEST_REQUEST.value: preferences.get(
                "guest_requests_email", True
            ),
            NotificationType.ANNOUNCEMENT.value: preferences.get(
                "announcements_email", True
            ),
        }

        return email_map.get(notification_type, False)

    def _should_send_push(self, notification_type: str, preferences: Dict) -> bool:
        """Check if push notification should be sent for this notification type"""

        push_map = {
            NotificationType.BILL_DUE.value: preferences.get(
                "bill_reminders_push", True
            ),
            NotificationType.BILL_OVERDUE.value: preferences.get(
                "bill_reminders_push", True
            ),
            NotificationType.TASK_OVERDUE.value: preferences.get(
                "task_reminders_push", True
            ),
            NotificationType.EVENT_REMINDER.value: preferences.get(
                "event_reminders_push", True
            ),
            NotificationType.GUEST_REQUEST.value: preferences.get(
                "guest_requests_push", True
            ),
            NotificationType.EXPENSE_ADDED.value: preferences.get(
                "expense_updates_push", True
            ),
        }

        return push_map.get(notification_type, False)

    def _send_email_notification(self, user: User, notification: Notification):
        """Send email notification"""

        subject = f"Roomly: {notification.title}"
        body = f"""
        Hi {user.name},
        
        {notification.message}
        
        {f'Take action: {notification.action_url}' if notification.action_url else ''}
        
        Best regards,
        Your Roomly Team
        """

        self.email_service.send_email(user.email, subject, body)

    def _send_push_notification(self, user: User, notification: Notification):
        """Send push notification (placeholder for future implementation)"""
        # This would integrate with Firebase, Apple Push, etc.
        print(f"PUSH: {user.name} - {notification.title}")

    # BILL REMINDER SYSTEM - Exact timing rules
    def check_and_send_bill_reminders(self):
        """Check for bills that need reminders and send them"""

        now = datetime.utcnow()

        # Get all active bills
        bills = self.db.query(Bill).filter(Bill.is_active == True).all()

        for bill in bills:
            household_members = ServiceHelpers.get_household_members(bill.household_id)

            # Calculate current and next month due dates
            current_month_due = self._get_current_month_due_date(bill, now)
            next_month_due = self._get_next_month_due_date(bill, now)

            for due_date in [current_month_due, next_month_due]:
                if not due_date:
                    continue

                # 3 days before reminder
                three_days_before = due_date - timedelta(days=3)
                if self._is_time_for_reminder(
                    now, three_days_before, tolerance_hours=1
                ):
                    self._send_bill_reminder(
                        bill, due_date, household_members, "3 days"
                    )

                # Day of reminder
                day_of = due_date.replace(hour=9, minute=0, second=0, microsecond=0)
                if self._is_time_for_reminder(now, day_of, tolerance_hours=1):
                    self._send_bill_reminder(bill, due_date, household_members, "today")

                # Daily overdue reminders
                if due_date < now:
                    days_overdue = (now - due_date).days
                    if days_overdue > 0:
                        # Send daily reminders at 10 AM
                        daily_reminder_time = now.replace(
                            hour=10, minute=0, second=0, microsecond=0
                        )
                        if self._is_time_for_reminder(
                            now, daily_reminder_time, tolerance_hours=1
                        ):
                            self._send_bill_overdue_reminder(
                                bill, due_date, household_members, days_overdue
                            )

    def _send_bill_reminder(
        self, bill: Bill, due_date: datetime, members: List[User], timing: str
    ):
        """Send bill due reminder"""

        for member in members:
            # Check if we already sent this reminder recently
            if self._was_reminder_sent_recently(
                member.id,
                NotificationType.BILL_DUE,
                bill.id,
                hours=23,  # Don't send same reminder within 23 hours
            ):
                continue

            due_date_str = due_date.strftime("%B %d, %Y")

            if timing == "3 days":
                title = f"Bill Due in 3 Days: {bill.name}"
                message = f"Your {bill.name} bill (${bill.amount}) is due on {due_date_str}. Don't forget to pay your share!"
            elif timing == "today":
                title = f"Bill Due Today: {bill.name}"
                message = f"Your {bill.name} bill (${bill.amount}) is due today. Please pay your share as soon as possible."

            self.create_notification(
                user_id=member.id,
                title=title,
                message=message,
                notification_type=NotificationType.BILL_DUE,
                priority="high" if timing == "today" else "normal",
                related_entity_type="bill",
                related_entity_id=bill.id,
                action_url=f"/bills/{bill.id}",
            )

    def _send_bill_overdue_reminder(
        self, bill: Bill, due_date: datetime, members: List[User], days_overdue: int
    ):
        """Send bill overdue reminder"""

        for member in members:
            # Check if we already sent overdue reminder today
            if self._was_reminder_sent_recently(
                member.id, NotificationType.BILL_OVERDUE, bill.id, hours=23
            ):
                continue

            title = f"OVERDUE: {bill.name} ({days_overdue} days)"
            message = f"Your {bill.name} bill (${bill.amount}) was due {days_overdue} days ago. Please pay immediately to avoid late fees."

            self.create_notification(
                user_id=member.id,
                title=title,
                message=message,
                notification_type=NotificationType.BILL_OVERDUE,
                priority="urgent",
                related_entity_type="bill",
                related_entity_id=bill.id,
                action_url=f"/bills/{bill.id}/pay",
            )

    # TASK REMINDER SYSTEM - Twice daily when overdue
    def check_and_send_task_reminders(self):
        """Check for overdue tasks and send twice daily reminders"""

        now = datetime.utcnow()

        # Get all overdue tasks
        overdue_tasks = (
            self.db.query(Task)
            .filter(and_(Task.status != "completed", Task.due_date < now))
            .all()
        )

        for task in overdue_tasks:
            # Send twice daily: 9 AM and 6 PM
            morning_reminder = now.replace(hour=9, minute=0, second=0, microsecond=0)
            evening_reminder = now.replace(hour=18, minute=0, second=0, microsecond=0)

            for reminder_time in [morning_reminder, evening_reminder]:
                if self._is_time_for_reminder(now, reminder_time, tolerance_hours=1):
                    self._send_task_overdue_reminder(task, now)

    def _send_task_overdue_reminder(self, task: Task, now: datetime):
        """Send task overdue reminder"""

        # Check if we already sent this reminder recently (within 5 hours)
        if self._was_reminder_sent_recently(
            task.assigned_to, NotificationType.TASK_OVERDUE, task.id, hours=5
        ):
            return

        hours_overdue = (now - task.due_date).total_seconds() / 3600
        days_overdue = int(hours_overdue / 24)

        if days_overdue > 0:
            overdue_text = f"{days_overdue} day{'s' if days_overdue > 1 else ''}"
        else:
            overdue_text = (
                f"{int(hours_overdue)} hour{'s' if int(hours_overdue) > 1 else ''}"
            )

        title = f"Overdue Task: {task.title}"
        message = f"Your task '{task.title}' was due {overdue_text} ago!"

        self.create_notification(
            user_id=task.assigned_to,
            title=title,
            message=message,
            notification_type=NotificationType.TASK_OVERDUE,
            priority="high",
            related_entity_type="task",
            related_entity_id=task.id,
            action_url=f"/tasks/{task.id}",
        )

    # EVENT REMINDER SYSTEM - 24 hours before + day of
    def check_and_send_event_reminders(self):
        """Check for upcoming events and send reminders"""

        now = datetime.utcnow()

        # Get upcoming events in next 2 days
        upcoming_events = (
            self.db.query(Event)
            .filter(
                and_(
                    Event.status == "published",
                    Event.start_date >= now,
                    Event.start_date <= now + timedelta(days=2),
                )
            )
            .all()
        )

        for event in upcoming_events:
            household_members = ServiceHelpers.get_household_members(event.household_id)

            # 24 hours before reminder
            twenty_four_hours_before = event.start_date - timedelta(hours=24)
            if self._is_time_for_reminder(
                now, twenty_four_hours_before, tolerance_hours=1
            ):
                self._send_event_reminder(event, household_members, "24 hours")

            # Day of reminder (2 hours before)
            day_of_reminder = event.start_date - timedelta(hours=2)
            if self._is_time_for_reminder(now, day_of_reminder, tolerance_hours=1):
                self._send_event_reminder(event, household_members, "2 hours")

    def _send_event_reminder(self, event: Event, members: List[User], timing: str):
        """Send event reminder"""

        for member in members:
            # Check if we already sent this reminder
            reminder_type = f"event_{timing.replace(' ', '_')}"
            if self._was_reminder_sent_recently(
                member.id, NotificationType.EVENT_REMINDER, event.id, hours=23
            ):
                continue

            event_time = event.start_date.strftime("%B %d at %I:%M %p")

            if timing == "24 hours":
                title = f"Event Tomorrow: {event.title}"
                message = f"Don't forget: '{event.title}' is tomorrow ({event_time}). Make sure to RSVP!"
            elif timing == "2 hours":
                title = f"Event Starting Soon: {event.title}"
                message = (
                    f"'{event.title}' starts in 2 hours ({event_time}). See you there!"
                )

            self.create_notification(
                user_id=member.id,
                title=title,
                message=message,
                notification_type=NotificationType.EVENT_REMINDER,
                priority="normal",
                related_entity_type="event",
                related_entity_id=event.id,
                action_url=f"/events/{event.id}",
            )

    # UTILITY METHODS
    def _is_time_for_reminder(
        self, now: datetime, target_time: datetime, tolerance_hours: int = 1
    ) -> bool:
        """Check if now is within tolerance of target time"""

        time_diff = abs((now - target_time).total_seconds() / 3600)
        return time_diff <= tolerance_hours

    def _was_reminder_sent_recently(
        self,
        user_id: int,
        notification_type: NotificationType,
        entity_id: int,
        hours: int = 24,
    ) -> bool:
        """Check if similar reminder was sent recently"""

        since_time = datetime.utcnow() - timedelta(hours=hours)

        recent_notification = (
            self.db.query(Notification)
            .filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.notification_type == notification_type.value,
                    Notification.related_entity_id == entity_id,
                    Notification.created_at >= since_time,
                )
            )
            .first()
        )

        return recent_notification is not None

    def _get_current_month_due_date(
        self, bill: Bill, now: datetime
    ) -> Optional[datetime]:
        """Get due date for current month"""
        return DateHelpers.get_bill_due_date(now.year, now.month, bill.due_day)

    def _get_next_month_due_date(self, bill: Bill, now: datetime) -> Optional[datetime]:
        """Get due date for next month"""
        if now.month == 12:
            return DateHelpers.get_bill_due_date(now.year + 1, 1, bill.due_day)
        else:
            return DateHelpers.get_bill_due_date(now.year, now.month + 1, bill.due_day)

    # USER PREFERENCE METHODS
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user notification preferences"""

        preferences = (
            self.db.query(NotificationPreference)
            .filter(NotificationPreference.user_id == user_id)
            .all()
        )

        # Convert to dictionary with defaults
        pref_dict = {
            "bill_reminders_email": True,
            "bill_reminders_push": True,
            "task_reminders_email": True,
            "task_reminders_push": True,
            "event_reminders_email": True,
            "event_reminders_push": True,
            "announcements_email": True,
            "announcements_push": False,
            "guest_requests_email": True,
            "guest_requests_push": True,
            "expense_updates_email": False,
            "expense_updates_push": True,
        }

        # Override with user's actual preferences
        for pref in preferences:
            pref_dict[f"{pref.notification_type}_email"] = pref.email_enabled
            pref_dict[f"{pref.notification_type}_push"] = pref.push_enabled

        return pref_dict

    def update_user_preferences(
        self, user_id: int, preferences: Dict[str, bool]
    ) -> bool:
        """Update user notification preferences"""

        try:
            # Delete existing preferences
            self.db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).delete()

            # Create new preferences
            for key, value in preferences.items():
                if "_email" in key:
                    notification_type = key.replace("_email", "")
                    pref = NotificationPreference(
                        user_id=user_id,
                        notification_type=notification_type,
                        email_enabled=value,
                        push_enabled=preferences.get(f"{notification_type}_push", True),
                    )
                    self.db.add(pref)

            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    # SYSTEM METHODS FOR BACKGROUND TASKS
    def run_all_notification_checks(self):
        """Run all notification checks (called by background task)"""

        print(f"🔔 Running notification checks at {datetime.utcnow()}")

        try:
            self.check_and_send_bill_reminders()
            self.check_and_send_task_reminders()
            self.check_and_send_event_reminders()

            print("✅ All notification checks completed")
        except Exception as e:
            print(f"❌ Notification check failed: {str(e)}")

    def get_notification_summary(self, user_id: int) -> Dict[str, Any]:
        """Get notification summary for user"""

        unread_count = (
            self.db.query(Notification)
            .filter(
                and_(Notification.user_id == user_id, Notification.is_read == False)
            )
            .count()
        )

        high_priority_count = (
            self.db.query(Notification)
            .filter(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.priority.in_(["high", "urgent"]),
                )
            )
            .count()
        )

        recent_notifications = (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(5)
            .all()
        )

        return {
            "unread_count": unread_count,
            "high_priority_count": high_priority_count,
            "recent_notifications": [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "type": n.notification_type,
                    "priority": n.priority,
                    "created_at": n.created_at,
                    "is_read": n.is_read,
                }
                for n in recent_notifications
            ],
        }

    def get_notification_by_id(
        self, notification_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single notification if the user is authorized"""

        notification = (
            self.db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )

        if not notification:
            return None

        return {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.notification_type,
            "priority": notification.priority,
            "created_at": notification.created_at,
            "is_read": notification.is_read,
            "related_entity_type": notification.related_entity_type,
            "related_entity_id": notification.related_entity_id,
            "action_url": notification.action_url,
        }

    def get_user_notifications(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> Dict[str, Any]:
        """Paginated retrieval of user's notifications"""

        query = self.db.query(Notification).filter(Notification.user_id == user_id)

        if unread_only:
            query = query.filter(Notification.is_read == False)

        total = query.count()

        notifications = (
            query.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "total_count": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
            "notifications": [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "type": n.notification_type,
                    "priority": n.priority,
                    "created_at": n.created_at,
                    "is_read": n.is_read,
                    "related_entity_type": n.related_entity_type,
                    "related_entity_id": n.related_entity_id,
                    "action_url": n.action_url,
                }
                for n in notifications
            ],
        }
