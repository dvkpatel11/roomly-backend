import os


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False):
        """Send email notification"""
        # TODO: Implement email sending
        print(f"EMAIL: {to_email} - {subject}")

    def send_bill_reminder_email(
        self, user_email: str, bill_name: str, amount: float, due_date: str
    ):
        """Send bill reminder email"""
        subject = f"Bill Reminder: {bill_name} due {due_date}"
        body = f"Your {bill_name} bill of ${amount} is due on {due_date}."
        self.send_email(user_email, subject, body)

    def send_task_reminder_email(self, user_email: str, task_title: str, due_date: str):
        """Send task reminder email"""
        subject = f"Task Reminder: {task_title}"
        body = f"Your task '{task_title}' is due {due_date}."
        self.send_email(user_email, subject, body)
