# Mock Email Service for Testing
# Replace the real email service temporarily

import os
from typing import Optional

class MockEmailService:
    """Mock email service that logs instead of sending real emails"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "mock.smtp.com")
        self.sent_emails = []  # Store sent emails for testing
        
    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Mock send email - just log the email"""
        
        email_data = {
            "to": to_email,
            "subject": subject, 
            "body": body,
            "is_html": is_html,
            "timestamp": "2025-06-17T10:00:00Z"
        }
        
        self.sent_emails.append(email_data)
        
        print(f"📧 MOCK EMAIL SENT:")
        print(f"   To: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Body: {body[:100]}...")
        print("")
        
        return True
    
    def send_bill_reminder_email(self, user_email: str, bill_name: str, amount: float, due_date: str):
        """Send bill reminder email"""
        subject = f"💰 Bill Reminder: {bill_name} due {due_date}"
        body = f"Your {bill_name} bill of ${amount} is due on {due_date}."
        return self.send_email(user_email, subject, body)
    
    def send_task_reminder_email(self, user_email: str, task_title: str, due_date: str):
        """Send task reminder email"""
        subject = f"📋 Task Reminder: {task_title}"
        body = f"Your task '{task_title}' is due {due_date}."
        return self.send_email(user_email, subject, body)
    
    def get_sent_emails(self):
        """Get all sent emails for testing"""
        return self.sent_emails
    
    def clear_sent_emails(self):
        """Clear sent emails list"""
        self.sent_emails = []
