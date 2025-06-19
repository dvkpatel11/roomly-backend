#!/usr/bin/env python3
"""
Sample Data Initializer
Creates sample data for testing the MVP features
"""

from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from .database import engine
from .models import (
    User,
    Household,
    HouseholdMembership,
    Expense,
    Bill,
    Task,
    Event,
    Announcement,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_household():
    """Create a sample household with users and basic data"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        logger.info("🏠 Creating sample household...")

        # Create household
        household = Household(
            name="The Awesome House",
            address="123 Main St, Anytown, USA",
            house_rules="1. Clean up after yourself\n2. Respect quiet hours (10pm-8am)\n3. Ask before having overnight guests",
            settings={
                "guest_policy": {"max_overnight_guests": 2, "approval_required": True},
                "task_settings": {
                    "rotation_enabled": True,
                    "point_system_enabled": True,
                },
            },
        )
        db.add(household)
        db.flush()

        # Create users
        users_data = [
            {"name": "Alice Johnson", "email": "alice@example.com", "role": "admin"},
            {"name": "Bob Smith", "email": "bob@example.com", "role": "member"},
            {"name": "Carol Davis", "email": "carol@example.com", "role": "member"},
        ]

        users = []
        for user_data in users_data:
            user = User(
                name=user_data["name"],
                email=user_data["email"],
                hashed_password="$2b$12$dummy_hash_for_testing",  # In real app, hash properly
                is_active=True,
            )
            db.add(user)
            db.flush()

            # Create household membership
            membership = HouseholdMembership(
                user_id=user.id,
                household_id=household.id,
                role=user_data["role"],
                is_active=True,
            )
            db.add(membership)
            users.append(user)

        logger.info(f"👥 Created {len(users)} users")

        # Create sample expenses
        expenses_data = [
            {
                "description": "Grocery shopping at Whole Foods",
                "amount": 127.50,
                "category": "groceries",
                "split_method": "equal_split",
                "created_by": users[0].id,
            },
            {
                "description": "Internet bill for March",
                "amount": 79.99,
                "category": "utilities",
                "split_method": "equal_split",
                "created_by": users[1].id,
            },
            {
                "description": "Cleaning supplies",
                "amount": 45.20,
                "category": "cleaning",
                "split_method": "equal_split",
                "created_by": users[2].id,
            },
        ]

        for expense_data in expenses_data:
            expense = Expense(
                household_id=household.id,
                **expense_data,
                split_details={
                    "method": expense_data["split_method"],
                    "participants": [u.id for u in users],
                    "amounts": {
                        str(u.id): expense_data["amount"] / len(users) for u in users
                    },
                },
            )
            db.add(expense)

        logger.info("💰 Created sample expenses")

        # Create sample bills
        bills_data = [
            {"name": "Rent", "amount": 2400.00, "category": "rent", "due_day": 1},
            {
                "name": "Electricity",
                "amount": 150.00,
                "category": "utilities",
                "due_day": 15,
            },
            {"name": "Gas", "amount": 80.00, "category": "utilities", "due_day": 20},
        ]

        for bill_data in bills_data:
            bill = Bill(
                household_id=household.id,
                created_by=users[0].id,
                split_method="equal_split",
                **bill_data,
            )
            db.add(bill)

        logger.info("📋 Created sample bills")

        # Create sample tasks
        tasks_data = [
            {
                "title": "Take out trash",
                "description": "Take trash and recycling to curb",
                "assigned_to": users[0].id,
                "priority": "normal",
                "due_date": datetime.now() + timedelta(days=1),
            },
            {
                "title": "Clean bathroom",
                "description": "Deep clean main bathroom",
                "assigned_to": users[1].id,
                "priority": "normal",
                "due_date": datetime.now() + timedelta(days=3),
            },
            {
                "title": "Vacuum living room",
                "description": "Vacuum and tidy living room",
                "assigned_to": users[2].id,
                "priority": "normal",
                "due_date": datetime.now() + timedelta(days=2),
            },
        ]

        for task_data in tasks_data:
            task = Task(household_id=household.id, created_by=users[0].id, **task_data)
            db.add(task)

        logger.info("✅ Created sample tasks")

        # Create sample events
        events_data = [
            {
                "title": "House Meeting",
                "description": "Monthly house meeting to discuss bills and chores",
                "event_type": "meeting",
                "start_date": datetime.now() + timedelta(days=7),
                "end_date": datetime.now() + timedelta(days=7, hours=1),
                "requires_approval": False,
            },
            {
                "title": "Game Night",
                "description": "Board games and pizza night!",
                "event_type": "game_night",
                "start_date": datetime.now() + timedelta(days=14),
                "end_date": datetime.now() + timedelta(days=14, hours=3),
                "requires_approval": False,
            },
        ]

        for event_data in events_data:
            event = Event(
                household_id=household.id, created_by=users[0].id, **event_data
            )
            db.add(event)

        logger.info("🎉 Created sample events")

        # Create sample announcements
        announcements_data = [
            {
                "title": "Welcome to Roomly!",
                "content": "Welcome to our household management system. Please take a moment to review the house rules and upcoming tasks.",
                "category": "general",
                "priority": "normal",
                "is_pinned": True,
            },
            {
                "title": "Wifi Password Updated",
                "content": "The wifi password has been changed to: HouseGuest2024!",
                "category": "maintenance",
                "priority": "high",
            },
        ]

        for announcement_data in announcements_data:
            announcement = Announcement(
                household_id=household.id, created_by=users[0].id, **announcement_data
            )
            db.add(announcement)

        logger.info("📢 Created sample announcements")

        # Commit all changes
        db.commit()

        logger.info("🎉 Sample data created successfully!")
        logger.info(f"📊 Summary:")
        logger.info(f"  - Household: {household.name}")
        logger.info(f"  - Users: {len(users)}")
        logger.info(f"  - Expenses: {len(expenses_data)}")
        logger.info(f"  - Bills: {len(bills_data)}")
        logger.info(f"  - Tasks: {len(tasks_data)}")
        logger.info(f"  - Events: {len(events_data)}")
        logger.info(f"  - Announcements: {len(announcements_data)}")

        return household, users

    except Exception as e:
        logger.error(f"❌ Failed to create sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Initialize database with sample data"""
    logger.info("🚀 Initializing sample data for MVP testing...")

    try:
        household, users = create_sample_household()

        logger.info("\n🔑 Test Login Credentials:")
        for user in users:
            logger.info(f"  - {user.name}: {user.email} / password123")

        logger.info("\n💡 Next steps:")
        logger.info("  1. Start your FastAPI server")
        logger.info("  2. Log in with any of the test accounts")
        logger.info(
            "  3. Test expense splitting, task management, and calendar features"
        )
        logger.info("  4. Check the dashboard for household activity")

    except Exception as e:
        logger.error(f"❌ Sample data initialization failed: {e}")
        raise


if __name__ == "__main__":
    main()
