"""
Mock Data Generator for Roomly Application
Run this script to populate your development database with realistic test data.

Usage:
    python create_mock_data.py

Requirements:
    pip install faker passlib[bcrypt]
"""

import random
import uuid
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session

# Import your models and database
from app.database import SessionLocal, init_db
from ..models import (
    User,
    Household,
    HouseholdMembership,
    Expense,
    ExpensePayment,
    Bill,
    BillPayment,
    Task,
    Event,
    RSVP,
    Guest,
    GuestApproval,
    Announcement,
    Poll,
    PollVote,
    Notification,
    NotificationPreference,
    ShoppingList,
    ShoppingItem,
)
from ..schemas.enums import HouseholdRole, EventStatus, TaskStatus

# Initialize Faker
fake = Faker()


class MockDataGenerator:
    def __init__(self, db: Session):
        self.db = db
        self.users = []
        self.households = []
        self.memberships = []

    def clear_existing_data(self):
        """Clear existing data (use with caution!)"""
        print("🗑️  Clearing existing data...")

        # Delete in reverse dependency order
        self.db.query(ShoppingItem).delete()
        self.db.query(ShoppingList).delete()
        self.db.query(NotificationPreference).delete()
        self.db.query(Notification).delete()
        self.db.query(PollVote).delete()
        self.db.query(Poll).delete()
        self.db.query(Announcement).delete()
        self.db.query(GuestApproval).delete()
        self.db.query(Guest).delete()
        self.db.query(RSVP).delete()
        self.db.query(Event).delete()
        self.db.query(Task).delete()
        self.db.query(BillPayment).delete()
        self.db.query(Bill).delete()
        self.db.query(ExpensePayment).delete()
        self.db.query(Expense).delete()
        self.db.query(HouseholdMembership).delete()
        self.db.query(Household).delete()
        self.db.query(User).delete()

        self.db.commit()
        print("✅ Existing data cleared")

    def create_users(self, count=20):
        """Create mock users"""
        print(f"👥 Creating {count} users...")

        # Import password hashing
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Create known dev users first
        dev_users = [
            {"email": "admin@test.com", "name": "Admin User", "password": "admin123"},
            {"email": "dev@test.com", "name": "Dev User", "password": "dev123"},
            {"email": "user@test.com", "name": "Test User", "password": "user123"},
        ]

        for dev_user in dev_users:
            user = User(
                email=dev_user["email"],
                name=dev_user["name"],
                phone=fake.phone_number()[:15],
                supabase_id=str(uuid.uuid4()) if random.choice([True, False]) else None,
                hashed_password=pwd_context.hash(dev_user["password"]),
                is_active=True,
                created_at=fake.date_time_between(start_date="-2y", end_date="now"),
            )
            self.db.add(user)
            self.users.append(user)
            print(f"✅ Created dev user: {dev_user['email']} / {dev_user['password']}")

        # Create remaining random users
        for i in range(count - len(dev_users)):
            # Use a known password for easier testing
            common_password = "password123"

            user = User(
                email=fake.unique.email(),
                name=fake.name(),
                phone=fake.phone_number()[:15],
                supabase_id=str(uuid.uuid4()) if random.choice([True, False]) else None,
                hashed_password=pwd_context.hash(common_password),
                is_active=True,
                created_at=fake.date_time_between(start_date="-2y", end_date="now"),
            )
            self.db.add(user)
            self.users.append(user)

        self.db.commit()
        print(f"✅ Created {len(self.users)} users")
        print("📋 Dev user credentials:")
        print("   admin@test.com / admin123")
        print("   dev@test.com / dev123")
        print("   user@test.com / user123")
        print(f"   All other users: password123")

    def create_households(self, count=5):
        """Create mock households"""
        print(f"🏠 Creating {count} households...")

        house_types = ["House", "Apartment", "Condo", "Townhouse"]
        street_names = ["Oak", "Maple", "Pine", "Cedar", "Elm", "Birch"]

        for i in range(count):
            household = Household(
                name=f"{random.choice(street_names)} {random.choice(house_types)}",
                address=fake.address(),
                house_rules=fake.text(max_nb_chars=500),
                settings={
                    "guest_approval_required": random.choice([True, False]),
                    "quiet_hours": {"start": "22:00", "end": "08:00"},
                    "max_guests_per_event": random.randint(5, 20),
                    "expense_split_default": random.choice(["equal", "custom"]),
                    "notifications_enabled": True,
                },
                created_at=fake.date_time_between(start_date="-1y", end_date="now"),
            )
            self.db.add(household)
            self.households.append(household)

        self.db.commit()
        print(f"✅ Created {len(self.households)} households")

    def create_household_memberships(self):
        """Create household memberships"""
        print("🔗 Creating household memberships...")

        # Ensure each household has at least one admin
        for household in self.households:
            admin_user = random.choice(self.users)
            membership = HouseholdMembership(
                user_id=admin_user.id,
                household_id=household.id,
                role=HouseholdRole.ADMIN.value,
                joined_at=household.created_at + timedelta(days=random.randint(0, 30)),
                is_active=True,
            )
            self.db.add(membership)
            self.memberships.append(membership)

            # Add 2-4 more members to each household
            available_users = [u for u in self.users if u.id != admin_user.id]
            member_count = random.randint(2, 4)

            for _ in range(min(member_count, len(available_users))):
                user = available_users.pop(random.randint(0, len(available_users) - 1))
                membership = HouseholdMembership(
                    user_id=user.id,
                    household_id=household.id,
                    role=random.choice(
                        [HouseholdRole.MEMBER.value, HouseholdRole.ADMIN.value]
                    ),
                    joined_at=household.created_at
                    + timedelta(days=random.randint(0, 60)),
                    is_active=random.choice([True, True, True, False]),  # 75% active
                )
                self.db.add(membership)
                self.memberships.append(membership)

        self.db.commit()
        print(f"✅ Created {len(self.memberships)} memberships")

    def create_expenses(self, count_per_household=15):
        """Create mock expenses"""
        print(f"💰 Creating expenses ({count_per_household} per household)...")

        expense_categories = [
            "groceries",
            "utilities",
            "household_supplies",
            "entertainment",
            "maintenance",
        ]
        split_methods = ["equal", "custom", "by_income", "manual"]

        # First create all expenses
        expenses_to_process = []
        total_expenses = 0

        for household in self.households:
            members = [
                m
                for m in self.memberships
                if m.household_id == household.id and m.is_active
            ]

            for _ in range(count_per_household):
                creator = random.choice(members)
                amount = round(random.uniform(10.0, 500.0), 2)

                expense = Expense(
                    description=fake.sentence(nb_words=4),
                    amount=amount,
                    category=random.choice(expense_categories),
                    split_method=random.choice(split_methods),
                    receipt_url=fake.url() if random.choice([True, False]) else None,
                    notes=(
                        fake.text(max_nb_chars=200)
                        if random.choice([True, False])
                        else None
                    ),
                    split_details=self._generate_split_details(members, amount),
                    household_id=household.id,
                    created_by=creator.user_id,
                    created_at=fake.date_time_between(start_date="-6m", end_date="now"),
                )
                self.db.add(expense)
                expenses_to_process.append((expense, members))
                total_expenses += 1

        # Commit expenses first to get IDs
        self.db.commit()

        # Now create payments with valid expense IDs
        total_payments = 0
        for expense, members in expenses_to_process:
            if random.choice([True, False, False]):  # 33% chance of payment
                payer = random.choice(members)
                payment_amount = round(
                    random.uniform(expense.amount * 0.1, expense.amount), 2
                )
                payment = ExpensePayment(
                    expense_id=expense.id,  # Now expense.id exists
                    paid_by=payer.user_id,
                    amount_paid=payment_amount,
                    payment_date=expense.created_at
                    + timedelta(days=random.randint(1, 30)),
                    payment_method=random.choice(["venmo", "cash", "check", "zelle"]),
                )
                self.db.add(payment)
                total_payments += 1

        self.db.commit()
        print(f"✅ Created {total_expenses} expenses with {total_payments} payments")

    def create_bills(self, count_per_household=8):
        """Create mock bills"""
        print(f"📄 Creating bills ({count_per_household} per household)...")

        bill_categories = [
            "rent",
            "utilities",
            "internet",
            "electricity",
            "gas",
            "water",
            "insurance",
        ]
        split_methods = ["equal", "by_room", "custom"]

        # First create all bills
        bills_to_process = []
        total_bills = 0

        for household in self.households:
            members = [
                m
                for m in self.memberships
                if m.household_id == household.id and m.is_active
            ]

            for category in bill_categories[:count_per_household]:
                creator = random.choice(members)
                amount = round(random.uniform(50.0, 1500.0), 2)

                bill = Bill(
                    name=f"{category.title()} Bill",
                    amount=amount,
                    category=category,
                    due_day=random.randint(1, 28),
                    split_method=random.choice(split_methods),
                    is_active=random.choice([True, True, True, False]),  # 75% active
                    notes=(
                        fake.text(max_nb_chars=200)
                        if random.choice([True, False])
                        else None
                    ),
                    split_details=self._generate_split_details(members, amount),
                    household_id=household.id,
                    created_by=creator.user_id,
                    created_at=fake.date_time_between(start_date="-1y", end_date="-1m"),
                )
                self.db.add(bill)
                bills_to_process.append((bill, members))
                total_bills += 1

        # Commit bills first to get IDs
        self.db.commit()

        # Now create bill payments with valid bill IDs
        total_payments = 0
        for bill, members in bills_to_process:
            # Create bill payments for the last few months
            for month_offset in range(1, 6):  # Last 5 months
                if random.choice([True, True, False]):  # 66% chance
                    payer = random.choice(members)
                    payment_date = datetime.now() - timedelta(days=30 * month_offset)
                    for_month = payment_date.strftime("%Y-%m")

                    payment = BillPayment(
                        bill_id=bill.id,  # Now bill.id exists
                        paid_by=payer.user_id,
                        amount_paid=bill.amount
                        + random.uniform(-50, 50),  # Some variation
                        payment_date=payment_date,
                        payment_method=random.choice(
                            ["auto_pay", "online", "check", "cash"]
                        ),
                        for_month=for_month,
                        notes=fake.sentence() if random.choice([True, False]) else None,
                    )
                    self.db.add(payment)
                    total_payments += 1

        self.db.commit()
        print(f"✅ Created {total_bills} bills with {total_payments} payment records")

    def create_tasks(self, count_per_household=20):
        """Create mock tasks"""
        print(f"✅ Creating tasks ({count_per_household} per household)...")

        task_titles = [
            "Take out trash",
            "Clean bathroom",
            "Vacuum living room",
            "Do dishes",
            "Clean kitchen",
            "Mow lawn",
            "Water plants",
            "Clean windows",
            "Organize pantry",
            "Deep clean refrigerator",
            "Dust furniture",
            "Clean mirrors",
            "Sweep porch",
            "Wipe down surfaces",
        ]

        priorities = ["low", "normal", "high", "urgent"]
        statuses = [
            TaskStatus.PENDING.value,
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.COMPLETED.value,
            TaskStatus.OVERDUE.value,
        ]

        total_tasks = 0
        for household in self.households:
            members = [
                m
                for m in self.memberships
                if m.household_id == household.id and m.is_active
            ]

            for _ in range(count_per_household):
                creator = random.choice(members)
                assignee = random.choice(members)

                task = Task(
                    title=random.choice(task_titles),
                    description=(
                        fake.text(max_nb_chars=300)
                        if random.choice([True, False])
                        else None
                    ),
                    priority=random.choice(priorities),
                    estimated_duration=random.randint(15, 240),  # 15 min to 4 hours
                    recurring=random.choice([True, False]),
                    recurrence_pattern=(
                        random.choice(["daily", "weekly", "monthly"])
                        if random.choice([True, False])
                        else None
                    ),
                    status=random.choice(statuses),
                    household_id=household.id,
                    assigned_to=assignee.user_id,
                    created_by=creator.user_id,
                    due_date=fake.date_time_between(start_date="-1m", end_date="+1m"),
                    created_at=fake.date_time_between(start_date="-2m", end_date="now"),
                )

                # Add completion details if completed
                if task.status == TaskStatus.COMPLETED.value:
                    task.completed_at = task.due_date - timedelta(
                        days=random.randint(0, 5)
                    )
                    task.completion_notes = (
                        fake.sentence() if random.choice([True, False]) else None
                    )
                    task.photo_proof_url = (
                        fake.url() if random.choice([True, False]) else None
                    )

                self.db.add(task)
                total_tasks += 1

        self.db.commit()
        print(f"✅ Created {total_tasks} tasks")

    def create_events(self, count_per_household=8):
        """Create mock events"""
        print(f"🎉 Creating events ({count_per_household} per household)...")

        event_types = [
            "party",
            "game_night",
            "movie_night",
            "BBQ",
            "cleaning",
            "maintenance",
            "meeting",
        ]
        event_titles = {
            "party": ["House Party", "Birthday Party", "Graduation Party"],
            "game_night": ["Board Game Night", "Video Game Tournament", "Poker Night"],
            "movie_night": [
                "Movie Marathon",
                "Documentary Night",
                "Horror Movie Night",
            ],
            "BBQ": ["Summer BBQ", "Backyard Grill", "Pool Party BBQ"],
            "cleaning": ["Spring Cleaning", "Deep Clean Day", "Declutter Day"],
            "maintenance": ["Maintenance Day", "Repair Session", "Home Improvement"],
            "meeting": ["House Meeting", "Monthly Check-in", "Rules Discussion"],
        }

        # First create all events
        events_to_process = []
        total_events = 0

        for household in self.households:
            members = [
                m
                for m in self.memberships
                if m.household_id == household.id and m.is_active
            ]

            for _ in range(count_per_household):
                creator = random.choice(members)
                event_type = random.choice(event_types)

                start_date = fake.date_time_between(start_date="-2m", end_date="+2m")
                end_date = start_date + timedelta(hours=random.randint(2, 8))

                event = Event(
                    title=random.choice(event_titles[event_type]),
                    description=fake.text(max_nb_chars=400),
                    event_type=event_type,
                    start_date=start_date,
                    end_date=end_date,
                    location=random.choice(
                        ["Living Room", "Backyard", "Kitchen", "Whole House"]
                    ),
                    max_attendees=(
                        random.randint(5, 20) if random.choice([True, False]) else None
                    ),
                    is_public=random.choice([True, False]),
                    requires_approval=random.choice([True, False]),
                    status=random.choice(
                        [
                            EventStatus.PENDING.value,
                            EventStatus.PUBLISHED.value,
                            EventStatus.COMPLETED.value,
                        ]
                    ),
                    household_id=household.id,
                    created_by=creator.user_id,
                    created_at=start_date - timedelta(days=random.randint(1, 30)),
                )
                self.db.add(event)
                events_to_process.append((event, members))
                total_events += 1

        # Commit events first to get IDs
        self.db.commit()

        # Now create RSVPs with valid event IDs
        total_rsvps = 0
        for event, members in events_to_process:
            # Create RSVPs for published events
            if event.status == EventStatus.PUBLISHED.value:
                for member in random.sample(members, random.randint(1, len(members))):
                    rsvp = RSVP(
                        event_id=event.id,  # Now event.id exists
                        user_id=member.user_id,
                        status=random.choice(["yes", "no", "maybe"]),
                        guest_count=random.randint(1, 3),
                        response_notes=(
                            fake.sentence() if random.choice([True, False]) else None
                        ),
                        created_at=event.created_at
                        + timedelta(days=random.randint(1, 5)),
                    )
                    self.db.add(rsvp)
                    total_rsvps += 1

        self.db.commit()
        print(f"✅ Created {total_events} events with {total_rsvps} RSVPs")

    def create_guests(self, count_per_household=6):
        """Create mock guests"""
        print(f"👤 Creating guests ({count_per_household} per household)...")

        relationships = ["friend", "family", "partner", "colleague", "neighbor"]

        total_guests = 0
        for household in self.households:
            members = [
                m
                for m in self.memberships
                if m.household_id == household.id and m.is_active
            ]

            for _ in range(count_per_household):
                host = random.choice(members)

                check_in = fake.date_time_between(start_date="-1m", end_date="+2m")
                is_overnight = random.choice([True, False])
                check_out = (
                    check_in + timedelta(hours=random.randint(2, 24))
                    if is_overnight
                    else check_in + timedelta(hours=random.randint(2, 8))
                )

                guest = Guest(
                    name=fake.name(),
                    phone=(
                        fake.phone_number()[:15]
                        if random.choice([True, False])
                        else None
                    ),
                    email=fake.email() if random.choice([True, False]) else None,
                    relationship_to_host=random.choice(relationships),
                    check_in=check_in,
                    check_out=check_out,
                    is_overnight=is_overnight,
                    is_approved=random.choice([True, True, False]),  # 66% approved
                    notes=(
                        fake.text(max_nb_chars=200)
                        if random.choice([True, False])
                        else None
                    ),
                    special_requests=(
                        fake.sentence() if random.choice([True, False]) else None
                    ),
                    household_id=household.id,
                    hosted_by=host.user_id,
                    approved_by=(
                        random.choice(members).user_id
                        if random.choice([True, False])
                        else None
                    ),
                    created_at=check_in - timedelta(days=random.randint(1, 7)),
                )
                self.db.add(guest)
                total_guests += 1

        self.db.commit()
        print(f"✅ Created {total_guests} guests")

    def create_announcements(self, count_per_household=5):
        """Create mock announcements"""
        print(f"📢 Creating announcements ({count_per_household} per household)...")

        categories = ["general", "maintenance", "event", "rule"]
        priorities = ["low", "normal", "high", "urgent"]

        announcement_templates = {
            "general": [
                "Important house update",
                "Reminder for everyone",
                "General announcement",
            ],
            "maintenance": [
                "Maintenance scheduled",
                "Repair notice",
                "Utility work planned",
            ],
            "event": ["Upcoming event", "Event reminder", "Special occasion"],
            "rule": ["Rule update", "New house policy", "Behavior reminder"],
        }

        total_announcements = 0
        for household in self.households:
            members = [
                m
                for m in self.memberships
                if m.household_id == household.id and m.is_active
            ]

            for _ in range(count_per_household):
                creator = random.choice(members)
                category = random.choice(categories)

                announcement = Announcement(
                    title=random.choice(announcement_templates[category]),
                    content=fake.text(max_nb_chars=600),
                    category=category,
                    priority=random.choice(priorities),
                    is_pinned=random.choice([True, False, False, False]),  # 25% pinned
                    expires_at=(
                        fake.date_time_between(start_date="+1d", end_date="+1m")
                        if random.choice([True, False])
                        else None
                    ),
                    household_id=household.id,
                    created_by=creator.user_id,
                    created_at=fake.date_time_between(start_date="-1m", end_date="now"),
                )
                self.db.add(announcement)
                total_announcements += 1

        self.db.commit()
        print(f"✅ Created {total_announcements} announcements")

    def create_polls(self, count_per_household=3):
        """Create mock polls"""
        print(f"🗳️ Creating polls ({count_per_household} per household)...")

        poll_questions = [
            "What should we order for the house party?",
            "When should we schedule the next house meeting?",
            "Which streaming service should we get?",
            "What color should we paint the living room?",
            "Which cleaning schedule works best?",
            "Where should we go for our house trip?",
        ]

        total_polls = 0
        for household in self.households:
            members = [
                m
                for m in self.memberships
                if m.household_id == household.id and m.is_active
            ]

            for _ in range(count_per_household):
                creator = random.choice(members)

                # Generate options based on question type
                options = self._generate_poll_options()

                poll = Poll(
                    question=random.choice(poll_questions),
                    description=(
                        fake.text(max_nb_chars=300)
                        if random.choice([True, False])
                        else None
                    ),
                    options=options,
                    is_multiple_choice=random.choice([True, False]),
                    is_anonymous=random.choice([True, False]),
                    is_active=random.choice([True, True, False]),  # 66% active
                    closes_at=(
                        fake.date_time_between(start_date="+1d", end_date="+1m")
                        if random.choice([True, False])
                        else None
                    ),
                    household_id=household.id,
                    created_by=creator.user_id,
                    created_at=fake.date_time_between(start_date="-2w", end_date="now"),
                )
                self.db.add(poll)
                total_polls += 1

                # Create votes for this poll
                voting_members = random.sample(members, random.randint(1, len(members)))
                for voter in voting_members:
                    selected_count = random.randint(
                        1, 2 if poll.is_multiple_choice else 1
                    )
                    selected_options = random.sample(
                        range(len(options)), selected_count
                    )

                    vote = PollVote(
                        poll_id=poll.id,
                        user_id=voter.user_id,
                        selected_options=selected_options,
                        created_at=poll.created_at
                        + timedelta(days=random.randint(0, 7)),
                    )
                    self.db.add(vote)

        self.db.commit()
        print(f"✅ Created {total_polls} polls with votes")

    def create_shopping_lists(self, count_per_household=3):
        """Create mock shopping lists"""
        print(f"🛒 Creating shopping lists ({count_per_household} per household)...")

        list_names = [
            "Weekly Groceries",
            "Party Supplies",
            "Household Items",
            "Emergency Supplies",
        ]
        stores = ["Walmart", "Target", "Whole Foods", "Costco", "Local Market"]

        item_names = {
            "produce": [
                "Bananas",
                "Apples",
                "Spinach",
                "Tomatoes",
                "Onions",
                "Carrots",
            ],
            "dairy": ["Milk", "Cheese", "Yogurt", "Eggs", "Butter"],
            "meat": ["Chicken Breast", "Ground Beef", "Salmon", "Turkey"],
            "pantry": ["Rice", "Pasta", "Bread", "Cereal", "Canned Beans"],
            "household": [
                "Toilet Paper",
                "Paper Towels",
                "Dish Soap",
                "Laundry Detergent",
            ],
        }

        total_lists = 0
        for household in self.households:
            members = [
                m
                for m in self.memberships
                if m.household_id == household.id and m.is_active
            ]

            for _ in range(count_per_household):
                creator = random.choice(members)
                shopper = (
                    random.choice(members) if random.choice([True, False]) else None
                )

                shopping_list = ShoppingList(
                    name=random.choice(list_names),
                    description=(
                        fake.text(max_nb_chars=200)
                        if random.choice([True, False])
                        else None
                    ),
                    is_active=random.choice([True, True, False]),  # 66% active
                    store_name=(
                        random.choice(stores) if random.choice([True, False]) else None
                    ),
                    planned_date=(
                        fake.date_time_between(start_date="now", end_date="+1w")
                        if random.choice([True, False])
                        else None
                    ),
                    total_estimated_cost=round(random.uniform(50.0, 300.0), 2),
                    total_actual_cost=(
                        round(random.uniform(45.0, 320.0), 2)
                        if random.choice([True, False])
                        else None
                    ),
                    household_id=household.id,
                    created_by=creator.user_id,
                    assigned_shopper=shopper.user_id if shopper else None,
                    created_at=fake.date_time_between(start_date="-1w", end_date="now"),
                    completed_at=(
                        fake.date_time_between(start_date="now", end_date="+3d")
                        if random.choice([True, False])
                        else None
                    ),
                )
                self.db.add(shopping_list)
                total_lists += 1

                # Add items to this shopping list
                item_count = random.randint(5, 15)
                for _ in range(item_count):
                    category = random.choice(list(item_names.keys()))
                    item_name = random.choice(item_names[category])
                    requester = random.choice(members)

                    item = ShoppingItem(
                        name=item_name,
                        quantity=f"{random.randint(1, 5)} {random.choice(['items', 'lbs', 'packages', 'bottles'])}",
                        category=category,
                        estimated_cost=round(random.uniform(1.0, 25.0), 2),
                        actual_cost=(
                            round(random.uniform(0.8, 28.0), 2)
                            if random.choice([True, False])
                            else None
                        ),
                        notes=fake.sentence() if random.choice([True, False]) else None,
                        is_purchased=random.choice([True, False]),
                        is_urgent=random.choice(
                            [True, False, False, False]
                        ),  # 25% urgent
                        shopping_list_id=shopping_list.id,
                        requested_by=requester.user_id,
                        created_at=shopping_list.created_at
                        + timedelta(hours=random.randint(0, 24)),
                        purchased_at=(
                            fake.date_time_between(start_date="now", end_date="+3d")
                            if random.choice([True, False])
                            else None
                        ),
                    )
                    self.db.add(item)

        self.db.commit()
        print(f"✅ Created {total_lists} shopping lists with items")

    def create_notifications(self, count_per_user=8):
        """Create mock notifications"""
        print(f"🔔 Creating notifications ({count_per_user} per user)...")

        notification_types = [
            "bill_due",
            "task_overdue",
            "event_reminder",
            "guest_approval_needed",
            "expense_added",
            "announcement_posted",
            "poll_created",
            "task_assigned",
        ]

        priorities = ["low", "normal", "high", "urgent"]

        total_notifications = 0
        for user in self.users:
            user_memberships = [
                m for m in self.memberships if m.user_id == user.id and m.is_active
            ]

            for _ in range(count_per_user):
                if not user_memberships:
                    continue

                membership = random.choice(user_memberships)
                notification_type = random.choice(notification_types)

                notification = Notification(
                    title=self._generate_notification_title(notification_type),
                    message=fake.text(max_nb_chars=300),
                    notification_type=notification_type,
                    priority=random.choice(priorities),
                    is_read=random.choice([True, True, False]),  # 66% read
                    sent_in_app=True,
                    sent_email=random.choice([True, False]),
                    sent_push=random.choice([True, False]),
                    related_entity_type=(
                        random.choice(["bill", "task", "event", "expense"])
                        if random.choice([True, False])
                        else None
                    ),
                    related_entity_id=(
                        random.randint(1, 100) if random.choice([True, False]) else None
                    ),
                    action_url=(
                        f"/app/{random.choice(['bills', 'tasks', 'events'])}/{random.randint(1, 100)}"
                        if random.choice([True, False])
                        else None
                    ),
                    user_id=user.id,
                    household_id=membership.household_id,
                    created_at=fake.date_time_between(start_date="-1m", end_date="now"),
                    read_at=(
                        fake.date_time_between(start_date="-1m", end_date="now")
                        if random.choice([True, False])
                        else None
                    ),
                )
                self.db.add(notification)
                total_notifications += 1

        self.db.commit()
        print(f"✅ Created {total_notifications} notifications")

    def create_notification_preferences(self):
        """Create notification preferences for all users"""
        print("⚙️ Creating notification preferences...")

        notification_types = [
            "bill_due",
            "task_overdue",
            "event_reminder",
            "guest_approval_needed",
            "expense_added",
            "announcement_posted",
            "poll_created",
            "task_assigned",
        ]

        total_prefs = 0
        for user in self.users:
            for notification_type in notification_types:
                pref = NotificationPreference(
                    notification_type=notification_type,
                    in_app_enabled=True,
                    email_enabled=random.choice([True, False]),
                    push_enabled=random.choice([True, False]),
                    user_id=user.id,
                    created_at=user.created_at + timedelta(days=random.randint(0, 30)),
                )
                self.db.add(pref)
                total_prefs += 1

        self.db.commit()
        print(f"✅ Created {total_prefs} notification preferences")

    def _generate_split_details(self, members, amount):
        """Generate realistic split details"""
        if len(members) == 0:
            return {}

        per_person = round(amount / len(members), 2)
        split_details = {}

        for member in members:
            split_details[str(member.user_id)] = {
                "amount": per_person,
                "percentage": round(100 / len(members), 2),
            }

        return split_details

    def _generate_poll_options(self):
        """Generate realistic poll options"""
        option_sets = [
            ["Pizza", "Chinese", "Mexican", "Burgers"],
            ["Monday", "Tuesday", "Wednesday", "Thursday"],
            ["Netflix", "Hulu", "Disney+", "HBO Max"],
            ["Blue", "Green", "Gray", "White"],
            ["Morning", "Afternoon", "Evening"],
            ["Beach", "Mountains", "City", "Camping"],
        ]

        return random.choice(option_sets)

    def _generate_notification_title(self, notification_type):
        """Generate realistic notification titles"""
        titles = {
            "bill_due": "Bill Due Soon",
            "task_overdue": "Task Overdue",
            "event_reminder": "Event Reminder",
            "guest_approval_needed": "Guest Approval Needed",
            "expense_added": "New Expense Added",
            "announcement_posted": "New Announcement",
            "poll_created": "New Poll Created",
            "task_assigned": "Task Assigned to You",
        }

        return titles.get(notification_type, "Notification")

    def generate_all_data(self, clear_existing=False):
        """Generate all mock data"""
        print("🚀 Starting mock data generation...")

        if clear_existing:
            self.clear_existing_data()

        # Create data in dependency order
        self.create_users(count=20)
        self.create_households(count=5)
        self.create_household_memberships()
        self.create_expenses(count_per_household=15)
        self.create_bills(count_per_household=8)
        self.create_tasks(count_per_household=20)
        self.create_events(count_per_household=8)
        self.create_guests(count_per_household=6)
        self.create_announcements(count_per_household=5)
        self.create_polls(count_per_household=3)
        self.create_shopping_lists(count_per_household=3)
        self.create_notifications(count_per_user=8)
        self.create_notification_preferences()

        print("🎉 Mock data generation completed!")
        print(f"📊 Summary:")
        print(f"   - Users: {len(self.users)}")
        print(f"   - Households: {len(self.households)}")
        print(f"   - Memberships: {len(self.memberships)}")
        print("   - Plus expenses, bills, tasks, events, and more!")


def main():
    """Main function to run the mock data generator"""
    print("🏠 Roomly Mock Data Generator")
    print("=" * 40)

    # Initialize database
    init_db()

    # Create database session
    db = SessionLocal()

    try:
        # Create generator
        generator = MockDataGenerator(db)

        # Ask user if they want to clear existing data
        clear_existing = input("Clear existing data? (y/N): ").lower().startswith("y")

        # Generate all data
        generator.generate_all_data(clear_existing=clear_existing)

        print("\n✅ Mock data generation successful!")
        print("You can now use your application with realistic test data.")

    except Exception as e:
        print(f"\n❌ Error generating mock data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
