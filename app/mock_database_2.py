#!/usr/bin/env python3
"""
Enhanced Sample Data Initializer
Creates comprehensive sample data for testing ALL MVP features
"""

from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from .database import engine
from .models import (
    User,
    Household,
    HouseholdMembership,
    Expense,
    ExpensePayment,
    Bill,
    BillPayment,
    Task,
    Event,
    Guest,
    Announcement,
    Poll,
    PollVote,
    Notification,
    ShoppingList,
    ShoppingItem,
    RSVP,
)
from .utils.security import get_password_hash
from app.database import session_scope
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_comprehensive_household():
    """Create a complete household with ALL features for testing"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        logger.info("🏠 Creating comprehensive test household...")

        # Create household with proper settings
        household = Household(
            name="Roomly Test House",
            address="123 Demo St, Test City, TC 12345",
            house_rules="""
1. Clean up after yourself immediately
2. Respect quiet hours (10pm-8am on weekdays, 11pm-9am weekends)
3. Ask before having overnight guests
4. No smoking indoors
5. Shared food in fridge is fair game unless labeled
6. Take turns with chores - check the app!
            """.strip(),
            settings={
                "guest_policy": {
                    "max_overnight_guests": 2,
                    "max_consecutive_nights": 3,
                    "approval_required": True,
                    "quiet_hours_start": "22:00",
                    "quiet_hours_end": "08:00",
                },
                "task_settings": {
                    "rotation_enabled": True,
                    "point_system_enabled": True,
                    "photo_proof_required": False,
                },
                "notification_settings": {
                    "bill_reminder_days": 3,
                    "task_overdue_hours": 24,
                    "event_reminder_hours": 24,
                },
            },
        )
        db.add(household)
        db.flush()

        # Create users with proper password hashing
        users_data = [
            {
                "name": "Alice Johnson",
                "email": "alice@test.com",
                "role": "admin",
                "phone": "+1-555-0101",
            },
            {
                "name": "Bob Smith",
                "email": "bob@test.com",
                "role": "member",
                "phone": "+1-555-0102",
            },
            {
                "name": "Carol Davis",
                "email": "carol@test.com",
                "role": "member",
                "phone": "+1-555-0103",
            },
            {
                "name": "David Wilson",
                "email": "david@test.com",
                "role": "member",
                "phone": "+1-555-0104",
            },
        ]

        users = []
        for user_data in users_data:
            user = User(
                name=user_data["name"],
                email=user_data["email"],
                phone=user_data["phone"],
                hashed_password=get_password_hash(
                    "password123"
                ),  # All use same test password
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

        # Create comprehensive expenses with proper splits
        expenses_data = [
            {
                "description": "Costco grocery run - bulk shopping",
                "amount": 185.75,
                "category": "groceries",
                "split_method": "equal_split",
                "created_by": users[0].id,
                "notes": "Toilet paper, snacks, cleaning supplies",
            },
            {
                "description": "Pizza night for 8 people",
                "amount": 67.89,
                "category": "food",
                "split_method": "equal_split",
                "created_by": users[1].id,
                "notes": "3 large pizzas + drinks",
            },
            {
                "description": "Uber ride to airport",
                "amount": 45.50,
                "category": "transportation",
                "split_method": "specific",
                "created_by": users[2].id,
                "notes": "Split between Alice and Carol only",
            },
            {
                "description": "Netflix subscription",
                "amount": 15.99,
                "category": "entertainment",
                "split_method": "equal_split",
                "created_by": users[3].id,
                "notes": "Monthly subscription",
            },
        ]

        expenses = []
        for i, expense_data in enumerate(expenses_data):
            # Calculate proper splits
            if expense_data["split_method"] == "equal_split":
                amount_per_person = expense_data["amount"] / len(users)
                splits = [
                    {
                        "user_id": user.id,
                        "user_name": user.name,
                        "amount_owed": round(amount_per_person, 2),
                        "calculation_method": "equal",
                        "is_paid": i < 2,  # First 2 expenses are paid
                    }
                    for user in users
                ]
            elif expense_data["split_method"] == "specific":
                # Uber split between Alice and Carol only
                splits = [
                    {
                        "user_id": users[0].id,
                        "user_name": users[0].name,
                        "amount_owed": 22.75,
                        "calculation_method": "custom_amount",
                        "is_paid": False,
                    },
                    {
                        "user_id": users[2].id,
                        "user_name": users[2].name,
                        "amount_owed": 22.75,
                        "calculation_method": "custom_amount",
                        "is_paid": False,
                    },
                ]

            expense = Expense(
                household_id=household.id,
                description=expense_data["description"],
                amount=expense_data["amount"],
                category=expense_data["category"],
                split_method=expense_data["split_method"],
                notes=expense_data["notes"],
                created_by=expense_data["created_by"],
                split_details={
                    "splits": splits,
                    "total_amount": expense_data["amount"],
                    "split_method": expense_data["split_method"],
                    "calculated_at": datetime.utcnow().isoformat(),
                    "all_paid": i < 2,
                },
            )
            db.add(expense)
            db.flush()
            expenses.append(expense)

            # Add some expense payments for the first 2 expenses
            if i < 2:
                for split in splits:
                    payment = ExpensePayment(
                        expense_id=expense.id,
                        paid_by=split["user_id"],
                        amount_paid=split["amount_owed"],
                        payment_method="venmo" if i == 0 else "cash",
                        payment_date=datetime.utcnow() - timedelta(days=2 - i),
                    )
                    db.add(payment)

        logger.info("💰 Created comprehensive expenses with payments")

        # Create bills with payment history
        bills_data = [
            {"name": "Rent", "amount": 2800.00, "category": "rent", "due_day": 1},
            {
                "name": "Electric & Gas",
                "amount": 180.00,
                "category": "utilities",
                "due_day": 15,
            },
            {
                "name": "Internet/WiFi",
                "amount": 89.99,
                "category": "utilities",
                "due_day": 20,
            },
            {
                "name": "Water/Sewer",
                "amount": 95.00,
                "category": "utilities",
                "due_day": 25,
            },
        ]

        bills = []
        for bill_data in bills_data:
            bill = Bill(
                household_id=household.id,
                created_by=users[0].id,
                split_method="equal_split",
                is_active=True,
                **bill_data,
            )
            db.add(bill)
            db.flush()
            bills.append(bill)

            # Add payment history for last month
            last_month = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m")
            for user in users:
                payment = BillPayment(
                    bill_id=bill.id,
                    paid_by=user.id,
                    amount_paid=bill.amount / len(users),
                    payment_method="bank_transfer",
                    for_month=last_month,
                    payment_date=datetime.utcnow() - timedelta(days=25),
                )
                db.add(payment)

        logger.info("📋 Created bills with payment history")

        # Create tasks with various statuses
        tasks_data = [
            {
                "title": "Take out trash and recycling",
                "description": "Trash pickup is tomorrow morning",
                "assigned_to": users[0].id,
                "priority": "high",
                "points": 10,
                "due_date": datetime.now() + timedelta(hours=18),
                "status": "pending",
            },
            {
                "title": "Deep clean main bathroom",
                "description": "Scrub tub, clean mirrors, mop floor",
                "assigned_to": users[1].id,
                "priority": "normal",
                "points": 25,
                "due_date": datetime.now() + timedelta(days=2),
                "status": "in_progress",
            },
            {
                "title": "Vacuum living room and hallway",
                "description": "Use the Dyson, don't forget under furniture",
                "assigned_to": users[2].id,
                "priority": "normal",
                "points": 15,
                "due_date": datetime.now() - timedelta(days=1),  # Overdue
                "status": "overdue",
            },
            {
                "title": "Grocery shopping",
                "description": "Check shared shopping list in app",
                "assigned_to": users[3].id,
                "priority": "normal",
                "points": 20,
                "due_date": datetime.now() + timedelta(days=3),
                "status": "pending",
            },
            {
                "title": "Clean kitchen after dinner",
                "description": "Dishes, wipe counters, take out compost",
                "assigned_to": users[1].id,
                "priority": "normal",
                "points": 10,
                "due_date": datetime.now() - timedelta(days=3),
                "status": "completed",
                "completed_at": datetime.now() - timedelta(days=3, hours=2),
                "completion_notes": "All done! Cleaned extra thoroughly.",
            },
        ]

        for task_data in tasks_data:
            task = Task(household_id=household.id, created_by=users[0].id, **task_data)
            db.add(task)

        logger.info("✅ Created tasks with various statuses")

        # Create events and RSVPs
        events_data = [
            {
                "title": "Monthly House Meeting",
                "description": "Discuss bills, chores, and upcoming maintenance",
                "event_type": "meeting",
                "start_date": datetime.now() + timedelta(days=5, hours=19),
                "end_date": datetime.now() + timedelta(days=5, hours=20, minutes=30),
                "status": "published",
                "requires_approval": False,
                "max_attendees": None,
            },
            {
                "title": "Game Night & Pizza Party",
                "description": "Board games, video games, pizza, and good vibes!",
                "event_type": "party",
                "start_date": datetime.now() + timedelta(days=12, hours=18),
                "end_date": datetime.now() + timedelta(days=12, hours=23),
                "status": "published",
                "requires_approval": False,
                "max_attendees": 8,
            },
            {
                "title": "Professional Cleaner Visit",
                "description": "Deep cleaning service coming for move-out prep",
                "event_type": "maintenance",
                "start_date": datetime.now() + timedelta(days=20, hours=10),
                "end_date": datetime.now() + timedelta(days=20, hours=14),
                "status": "pending_approval",
                "requires_approval": True,
                "max_attendees": None,
            },
        ]

        events = []
        for event_data in events_data:
            event = Event(
                household_id=household.id, created_by=users[0].id, **event_data
            )
            db.add(event)
            db.flush()
            events.append(event)

            # Add RSVPs for published events
            if event.status == "published":
                for i, user in enumerate(users):
                    rsvp = RSVP(
                        event_id=event.id,
                        user_id=user.id,
                        status=["yes", "yes", "maybe", "no"][i],
                        guest_count=1 if i < 2 else 0,
                        dietary_restrictions="Vegetarian" if i == 2 else None,
                    )
                    db.add(rsvp)

        logger.info("🎉 Created events with RSVPs")

        # Create guest requests
        guests_data = [
            {
                "name": "Sarah Miller",
                "phone": "+1-555-0201",
                "email": "sarah.m@email.com",
                "relationship_to_host": "friend",
                "check_in": datetime.now() + timedelta(days=8, hours=16),
                "check_out": datetime.now() + timedelta(days=10, hours=11),
                "is_overnight": True,
                "hosted_by": users[1].id,
                "is_approved": True,
                "approved_by": users[0].id,
                "notes": "Visiting from out of town",
            },
            {
                "name": "Mike Johnson",
                "phone": "+1-555-0202",
                "relationship_to_host": "family",
                "check_in": datetime.now() + timedelta(days=15, hours=18),
                "check_out": datetime.now() + timedelta(days=16, hours=12),
                "is_overnight": True,
                "hosted_by": users[2].id,
                "is_approved": False,  # Pending approval
                "notes": "Carol's brother visiting for weekend",
            },
        ]

        for guest_data in guests_data:
            guest = Guest(household_id=household.id, **guest_data)
            db.add(guest)

        logger.info("👥 Created guest requests")

        # Create announcements
        announcements_data = [
            {
                "title": "Welcome to Roomly! 🏠",
                "content": "Welcome to our household management system! Please take a moment to review the house rules, check your assigned tasks, and RSVP for upcoming events. Remember to log expenses and update your availability.",
                "category": "general",
                "priority": "normal",
                "is_pinned": True,
            },
            {
                "title": "WiFi Password Updated 📶",
                "content": "New WiFi password: RoomlyRocks2024! Please update your devices. Old password expires this weekend.",
                "category": "maintenance",
                "priority": "high",
                "is_pinned": False,
            },
            {
                "title": "Landlord Inspection Next Month 🏠",
                "content": "Annual inspection scheduled for the 15th. Let's make sure everything is clean and in good condition. Deep cleaning checklist coming soon!",
                "category": "maintenance",
                "priority": "medium",
                "is_pinned": False,
            },
        ]

        for announcement_data in announcements_data:
            announcement = Announcement(
                household_id=household.id, created_by=users[0].id, **announcement_data
            )
            db.add(announcement)

        logger.info("📢 Created announcements")

        # Create polls
        polls_data = [
            {
                "question": "What should we do for our next house dinner?",
                "description": "Vote for your preferred option - we'll go with the majority!",
                "options": [
                    "Homemade tacos",
                    "Order Thai food",
                    "BBQ in backyard",
                    "Potluck style",
                ],
                "is_multiple_choice": False,
                "is_anonymous": False,
                "is_active": True,
            },
            {
                "question": "Which household rules should we add?",
                "description": "Select all that you think would be good additions",
                "options": [
                    "24hr advance notice for guests",
                    "No dishes in sink overnight",
                    "Mandatory house meetings",
                    "Shared meal once per week",
                ],
                "is_multiple_choice": True,
                "is_anonymous": True,
                "is_active": True,
            },
        ]

        polls = []
        for poll_data in polls_data:
            poll = Poll(household_id=household.id, created_by=users[0].id, **poll_data)
            db.add(poll)
            db.flush()
            polls.append(poll)

            # Add some votes
            if poll_data["question"].startswith("What should we do"):
                # Single choice poll
                votes = [0, 1, 0, 2]  # Users vote for options 0, 1, 0, 2
                for i, user in enumerate(users):
                    vote = PollVote(
                        poll_id=poll.id, user_id=user.id, selected_options=[votes[i]]
                    )
                    db.add(vote)

        logger.info("🗳️ Created polls with votes")

        # Create shopping lists
        shopping_data = [
            {
                "name": "Weekly Groceries",
                "description": "Regular weekly shopping trip",
                "store_name": "Whole Foods",
                "planned_date": datetime.now() + timedelta(days=2),
                "created_by": users[0].id,
                "assigned_shopper": users[3].id,
                "is_active": True,
                "items": [
                    {
                        "name": "Milk (2%)",
                        "quantity": "1 gallon",
                        "category": "dairy",
                        "estimated_cost": 4.99,
                        "is_urgent": False,
                    },
                    {
                        "name": "Bread (whole wheat)",
                        "quantity": "2 loaves",
                        "category": "bakery",
                        "estimated_cost": 6.98,
                        "is_urgent": False,
                    },
                    {
                        "name": "Bananas",
                        "quantity": "1 bunch",
                        "category": "produce",
                        "estimated_cost": 3.49,
                        "is_urgent": False,
                    },
                    {
                        "name": "Toilet paper",
                        "quantity": "12 pack",
                        "category": "household",
                        "estimated_cost": 15.99,
                        "is_urgent": True,
                    },
                    {
                        "name": "Chicken breast",
                        "quantity": "2 lbs",
                        "category": "meat",
                        "estimated_cost": 12.99,
                        "is_urgent": False,
                    },
                ],
            },
            {
                "name": "Party Supplies",
                "description": "For game night next week",
                "store_name": "Target",
                "planned_date": datetime.now() + timedelta(days=10),
                "created_by": users[1].id,
                "assigned_shopper": users[1].id,
                "is_active": True,
                "items": [
                    {
                        "name": "Chips & Salsa",
                        "quantity": "3 bags + dip",
                        "category": "snacks",
                        "estimated_cost": 12.99,
                        "is_urgent": False,
                    },
                    {
                        "name": "Soda variety pack",
                        "quantity": "24 pack",
                        "category": "beverages",
                        "estimated_cost": 8.99,
                        "is_urgent": False,
                    },
                    {
                        "name": "Paper plates",
                        "quantity": "50 count",
                        "category": "household",
                        "estimated_cost": 4.99,
                        "is_urgent": False,
                    },
                ],
            },
        ]

        for list_data in shopping_data:
            shopping_list = ShoppingList(
                household_id=household.id,
                name=list_data["name"],
                description=list_data["description"],
                store_name=list_data["store_name"],
                planned_date=list_data["planned_date"],
                created_by=list_data["created_by"],
                assigned_shopper=list_data["assigned_shopper"],
                is_active=list_data["is_active"],
                total_estimated_cost=sum(
                    item["estimated_cost"] for item in list_data["items"]
                ),
            )
            db.add(shopping_list)
            db.flush()

            # Add items to list
            for item_data in list_data["items"]:
                item = ShoppingItem(
                    shopping_list_id=shopping_list.id,
                    requested_by=list_data["created_by"],
                    **item_data,
                )
                db.add(item)

        logger.info("🛒 Created shopping lists with items")

        # Create some notifications
        notifications_data = [
            {
                "user_id": users[2].id,
                "title": "Task Overdue: Vacuum living room",
                "message": "Your task 'Vacuum living room and hallway' was due yesterday. Please complete it to earn 15 points!",
                "notification_type": "task_overdue",
                "priority": "high",
                "is_read": False,
                "related_entity_type": "task",
                "related_entity_id": 3,
            },
            {
                "user_id": users[1].id,
                "title": "Guest Request Needs Approval",
                "message": "Carol has requested approval for guest Mike Johnson (Dec 15-16). Please review and approve/deny.",
                "notification_type": "guest_request",
                "priority": "medium",
                "is_read": False,
                "related_entity_type": "guest",
                "related_entity_id": 2,
            },
        ]

        for notif_data in notifications_data:
            notification = Notification(**notif_data)
            db.add(notification)

        logger.info("🔔 Created sample notifications")

        # Commit all changes
        db.commit()

        logger.info("🎉 Comprehensive sample data created successfully!")
        logger.info(f"📊 Complete Summary:")
        logger.info(f"  - Household: {household.name}")
        logger.info(f"  - Users: {len(users)} (1 admin, 3 members)")
        logger.info(f"  - Expenses: {len(expenses)} (with payments)")
        logger.info(f"  - Bills: {len(bills)} (with payment history)")
        logger.info(f"  - Tasks: {len(tasks_data)} (various statuses)")
        logger.info(f"  - Events: {len(events)} (with RSVPs)")
        logger.info(f"  - Guests: {len(guests_data)} (1 approved, 1 pending)")
        logger.info(f"  - Announcements: {len(announcements_data)}")
        logger.info(f"  - Polls: {len(polls)} (with votes)")
        logger.info(f"  - Shopping Lists: {len(shopping_data)} (with items)")
        logger.info(f"  - Notifications: {len(notifications_data)}")

        return household, users

    except Exception as e:
        logger.error(f"❌ Failed to create comprehensive sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Initialize database with comprehensive sample data"""
    logger.info("🚀 Initializing comprehensive sample data for full MVP testing...")

    try:
        # household, users = create_comprehensive_household()

        logger.info("\n🔑 Test Login Credentials (all use password: password123):")

        with session_scope() as session:
            users = session.query(User).all()

            # Build the credentials info while session is active
            credentials = []
            for user in users:
                role_icon = (
                    "👑"
                    if user.household_memberships
                    and "admin" in str(user.household_memberships[0].role)
                    else "👤"
                )
                credentials.append(
                    {
                        "email": user.email,
                        "role_icon": role_icon,
                        "role": (
                            user.household_memberships[0].role
                            if user.household_memberships
                            else None
                        ),
                    }
                )
                logger.info(f"  {role_icon} {user.name}: {user.email}")

        # Use credentials list outside the session
        for cred in credentials:
            print(f"  {cred['role_icon']} {cred['email']}")

        logger.info("\n🧪 What you can test:")
        logger.info("  💰 Expense splitting & payments")
        logger.info("  📋 Bill management & payment tracking")
        logger.info("  ✅ Task assignment & completion")
        logger.info("  🎉 Event creation & RSVP system")
        logger.info("  👥 Guest approval workflow")
        logger.info("  📢 Announcements & polls")
        logger.info("  🛒 Shopping lists & trip completion")
        logger.info("  🔔 Notification system")
        logger.info("  📊 Dashboard with all data")

        logger.info("\n💡 Next steps:")
        logger.info("  1. python -m uvicorn app.main:app --reload")
        logger.info("  2. Open http://localhost:8000/docs")
        logger.info("  3. Login with alice@test.com / password123")
        logger.info("  4. Test GET /dashboard/ for the full experience!")

    except Exception as e:
        logger.error(f"❌ Comprehensive sample data initialization failed: {e}")
        raise


if __name__ == "__main__":
    main()
