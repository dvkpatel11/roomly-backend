import schedule, asyncio
import time
import logging
import threading
from datetime import datetime, timezone
from ..database import SessionLocal
from ..services.notification_service import NotificationService

# Configure logging for background tasks
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackgroundTaskScheduler:
    def __init__(self):
        self.running = False
        self._shutdown_event = asyncio.Event()

    def schedule_notification_checks(self):
        """Schedule notification checks to run every hour"""

        # Run notification checks every hour
        schedule.every().hour.do(self._run_notification_checks)

        # Also run every 30 minutes during business hours (9 AM - 9 PM)
        for hour in range(9, 22):
            schedule.every().day.at(f"{hour:02d}:30").do(self._run_notification_checks)

        logger.info(
            "📅 Notification checks scheduled every hour and half-hour during business hours"
        )

    def _run_notification_checks(self):
        """Run all notification checks with proper error handling"""
        self.last_check_time = datetime.now(timezone.utc)

        with self.get_db_session() as db:
            try:
                notification_service = NotificationService(db)
                notification_service.run_all_notification_checks()
                self.last_check_status = "Success"
            except Exception as e:
                logger.error(f"Notification check failed: {str(e)}", exc_info=True)
                self.last_check_status = f"Error: {str(e)}"

    async def start_scheduler(self):
        """Async scheduler with proper shutdown"""
        self.running = True

        while self.running and not self._shutdown_event.is_set():
            try:
                schedule.run_pending()
                await asyncio.sleep(300)  # Check every 5 minutes instead
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                await asyncio.sleep(60)

    def stop_scheduler(self):
        """Graceful shutdown"""
        self.running = False
        self._shutdown_event.set()

    def run_immediate_check(self):
        """Run notification checks immediately (for testing)"""

        logger.info("🔔 Running immediate notification check...")
        self._run_notification_checks()

    def get_status(self):
        """Get current scheduler status"""
        return {
            "running": self.running,
            "scheduled_jobs_count": len(schedule.jobs),
            "last_check_time": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
            "last_check_status": self.last_check_status,
            "job_details": [
                {
                    "job": str(job.job_func.__name__),
                    "next_run": job.next_run.isoformat() if job.next_run else None,
                    "interval": str(job.interval),
                    "unit": job.unit,
                }
                for job in schedule.jobs
            ],
        }


scheduler = BackgroundTaskScheduler()


def start_background_tasks():
    """Start background tasks (call this when starting the app)"""

    def run_scheduler():
        try:
            scheduler.start_scheduler()
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")

    # Run scheduler in separate thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    logger.info("✅ Background tasks started in separate thread")


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
        logger.info("✅ Bill reminders triggered")
    except Exception as e:
        logger.error(f"❌ Bill reminders failed: {str(e)}")
    finally:
        db.close()


def trigger_task_reminders():
    """Manually trigger task reminders (for testing)"""
    db = SessionLocal()
    try:
        notification_service = NotificationService(db)
        notification_service.check_and_send_task_reminders()
        logger.info("✅ Task reminders triggered")
    except Exception as e:
        logger.error(f"❌ Task reminders failed: {str(e)}")
    finally:
        db.close()


def trigger_event_reminders():
    """Manually trigger event reminders (for testing)"""
    db = SessionLocal()
    try:
        notification_service = NotificationService(db)
        notification_service.check_and_send_event_reminders()
        logger.info("✅ Event reminders triggered")
    except Exception as e:
        logger.error(f"❌ Event reminders failed: {str(e)}")
    finally:
        db.close()
