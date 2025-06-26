import schedule
import time
from ..database import SessionLocal
from ..services.notification_service import NotificationService


class BackgroundTaskScheduler:
    def __init__(self):
        self.running = False
        self.tasks = []

    def schedule_notification_checks(self):
        """Schedule notification checks to run every hour"""

        # Run notification checks every hour
        schedule.every().hour.do(self._run_notification_checks)

        # Also run every 30 minutes during business hours (9 AM - 9 PM)
        for hour in range(9, 22):
            schedule.every().day.at(f"{hour:02d}:30").do(self._run_notification_checks)

        print(
            "📅 Notification checks scheduled every hour and half-hour during business hours"
        )

    def _run_notification_checks(self):
        """Run all notification checks"""

        db = SessionLocal()
        try:
            notification_service = NotificationService(db)
            notification_service.run_all_notification_checks()
        except Exception as e:
            print(f"❌ Background notification check failed: {str(e)}")
        finally:
            db.close()

    def start_scheduler(self):
        """Start the background task scheduler"""

        self.running = True
        print("🚀 Starting background task scheduler...")

        self.schedule_notification_checks()

        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def stop_scheduler(self):
        """Stop the background task scheduler"""

        self.running = False
        print("⏹️ Background task scheduler stopped")

    def run_immediate_check(self):
        """Run notification checks immediately (for testing)"""

        print("🔔 Running immediate notification check...")
        self._run_notification_checks()


scheduler = BackgroundTaskScheduler()


def start_background_tasks():
    """Start background tasks (call this when starting the app)"""

    import threading

    def run_scheduler():
        scheduler.start_scheduler()

    # Run scheduler in separate thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    print("✅ Background tasks started in separate thread")


def stop_background_tasks():
    """Stop background tasks"""
    scheduler.stop_scheduler()


# Manual trigger functions for testing
def trigger_bill_reminders():
    """Manually trigger bill reminders (for testing)"""
    db = SessionLocal()
    try:
        notification_service = NotificationService(db)
        notification_service.check_and_send_bill_reminders()
        print("✅ Bill reminders triggered")
    finally:
        db.close()


def trigger_task_reminders():
    """Manually trigger task reminders (for testing)"""
    db = SessionLocal()
    try:
        notification_service = NotificationService(db)
        notification_service.check_and_send_task_reminders()
        print("✅ Task reminders triggered")
    finally:
        db.close()


def trigger_event_reminders():
    """Manually trigger event reminders (for testing)"""
    db = SessionLocal()
    try:
        notification_service = NotificationService(db)
        notification_service.check_and_send_event_reminders()
        print("✅ Event reminders triggered")
    finally:
        db.close()
