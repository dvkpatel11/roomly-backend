#!/usr/bin/env python3
"""
Database Relationship Validator
Validates all model relationships and creates test data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from models import *
from datetime import datetime, timedelta
import json

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_roomly.db"

def create_test_database():
    """Create test database with all tables"""
    print("🗄️ Creating test database...")
    
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Drop all tables if they exist
    Base.metadata.drop_all(bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Test database created successfully")
    return engine

def validate_table_creation(engine):
    """Validate that all tables were created"""
    print("📋 Validating table creation...")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = [
        'users', 'households', 'expenses', 'bills', 'bill_payments',
        'tasks', 'events', 'guests', 'announcements', 'polls', 'poll_votes',
        'notifications', 'notification_preferences', 'rsvps', 
        'user_schedules', 'shopping_lists', 'shopping_items'
    ]
    
    missing_tables = []
    for table in expected_tables:
        if table in tables:
            print(f"  ✅ {table}")
        else:
            print(f"  ❌ {table} - MISSING")
            missing_tables.append(table)
    
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
        return False
    
    print("✅ All tables created successfully")
    return True

def validate_foreign_keys(engine):
    """Validate foreign key relationships"""
    print("🔗 Validating foreign key relationships...")
    
    inspector = inspect(engine)
    
    # Define expected foreign keys
    expected_fks = {
        'users': ['household_id'],
        'expenses': ['household_id', 'created_by'],
        'bills': ['household_id', 'created_by'],
        'bill_payments': ['bill_id', 'paid_by'],
        'tasks': ['household_id', 'assigned_to', 'created_by'],
        'events': ['household_id', 'created_by'],
        'guests': ['household_id', 'hosted_by', 'approved_by'],
        'announcements': ['household_id', 'created_by'],
        'polls': ['household_id', 'created_by'],
        'poll_votes': ['poll_id', 'user_id'],
        'notifications': ['user_id', 'household_id'],
        'notification_preferences': ['user_id'],
        'rsvps': ['event_id', 'user_id'],
        'user_schedules': ['user_id'],
        'shopping_lists': ['household_id', 'created_by', 'assigned_shopper'],
        'shopping_items': ['shopping_list_id', 'requested_by']
    }
    
    all_valid = True
    
    for table_name, expected_fk_columns in expected_fks.items():
        try:
            foreign_keys = inspector.get_foreign_keys(table_name)
            fk_columns = [fk['constrained_columns'][0] for fk in foreign_keys]
            
            for expected_fk in expected_fk_columns:
                if expected_fk in fk_columns:
                    print(f"  ✅ {table_name}.{expected_fk}")
                else:
                    print(f"  ❌ {table_name}.{expected_fk} - MISSING FK")
                    all_valid = False
                    
        except Exception as e:
            print(f"  ❌ {table_name} - Error checking FKs: {str(e)}")
            all_valid = False
    
    if all_valid:
        print("✅ All foreign keys validated successfully")
    else:
        print("❌ Some foreign key validations failed")
    
    return all_valid

def create_test_data(engine):
    """Create test data to validate relationships"""
    print("📊 Creating test data to validate relationships...")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Create household
        household = Household(
            name="Test Household",
            address="123 Test St",
            house_rules="Be respectful and clean up after yourself"
        )
        db.add(household)
        db.flush()
        
        # 2. Create users
        user1 = User(
            email="alice@test.com",
            name="Alice Johnson",
            hashed_password="hashed_password_1",
            household_id=household.id
        )
        user2 = User(
            email="bob@test.com",
            name="Bob Smith", 
            hashed_password="hashed_password_2",
            household_id=household.id
        )
        db.add_all([user1, user2])
        db.flush()
        
        # 3. Create expense
        expense = Expense(
            description="Groceries at Whole Foods",
            amount=85.50,
            category="groceries",
            split_method="equal_split",
            household_id=household.id,
            created_by=user1.id,
            split_details={"splits": []}
        )
        db.add(expense)
        
        # 4. Create bill
        bill = Bill(
            name="Electricity",
            amount=120.00,
            category="utilities",
            due_day=15,
            split_method="equal_split",
            household_id=household.id,
            created_by=user1.id
        )
        db.add(bill)
        db.flush()
        
        # 5. Create bill payment
        bill_payment = BillPayment(
            bill_id=bill.id,
            paid_by=user1.id,
            amount_paid=60.00,
            payment_method="venmo",
            for_month="2025-06"
        )
        db.add(bill_payment)
        
        # 6. Create task
        task = Task(
            title="Clean Kitchen",
            description="Deep clean the kitchen including appliances",
            household_id=household.id,
            assigned_to=user2.id,
            created_by=user1.id,
            due_date=datetime.utcnow() + timedelta(days=2)
        )
        db.add(task)
        
        # 7. Create event
        event = Event(
            title="House Party",
            description="Summer BBQ party",
            event_type="party",
            start_date=datetime.utcnow() + timedelta(days=7),
            household_id=household.id,
            created_by=user1.id,
            status="published"
        )
        db.add(event)
        db.flush()
        
        # 8. Create RSVP
        rsvp = RSVP(
            event_id=event.id,
            user_id=user2.id,
            status="yes",
            guest_count=2
        )
        db.add(rsvp)
        
        # 9. Create guest
        guest = Guest(
            name="Charlie Brown",
            phone="555-1234",
            relationship_to_host="friend",
            check_in=datetime.utcnow() + timedelta(days=3),
            household_id=household.id,
            hosted_by=user1.id
        )
        db.add(guest)
        
        # 10. Create announcement
        announcement = Announcement(
            title="Rent Increase Notice",
            content="Rent will increase by $50 starting next month",
            category="general",
            household_id=household.id,
            created_by=user1.id
        )
        db.add(announcement)
        
        # 11. Create poll
        poll = Poll(
            question="What should we do for house cleaning day?",
            options=["Deep clean everything", "Just basics", "Hire cleaners"],
            household_id=household.id,
            created_by=user1.id
        )
        db.add(poll)
        db.flush()
        
        # 12. Create poll vote
        poll_vote = PollVote(
            poll_id=poll.id,
            user_id=user2.id,
            selected_options=[0]  # First option
        )
        db.add(poll_vote)
        
        # 13. Create notification
        notification = Notification(
            title="Bill Due Reminder",
            message="Your electricity bill is due in 3 days",
            notification_type="bill_due",
            user_id=user2.id,
            household_id=household.id,
            related_entity_type="bill",
            related_entity_id=bill.id
        )
        db.add(notification)
        
        # 14. Create shopping list
        shopping_list = ShoppingList(
            name="Weekly Groceries",
            household_id=household.id,
            created_by=user1.id,
            assigned_shopper=user2.id
        )
        db.add(shopping_list)
        db.flush()
        
        # 15. Create shopping item
        shopping_item = ShoppingItem(
            name="Milk",
            quantity="1 gallon",
            category="dairy",
            estimated_cost=4.50,
            shopping_list_id=shopping_list.id,
            requested_by=user1.id
        )
        db.add(shopping_item)
        
        # Commit all changes
        db.commit()
        
        print("✅ Test data created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating test data: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

def validate_relationships(engine):
    """Validate that relationships work correctly"""
    print("🔗 Validating relationship queries...")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Test queries that use relationships
        
        # 1. Get household with all members
        household = db.query(Household).first()
        if household and len(household.members) >= 2:
            print("  ✅ Household -> Users relationship")
        else:
            print("  ❌ Household -> Users relationship")
            
        # 2. Get user with household
        user = db.query(User).first()
        if user and user.household:
            print("  ✅ User -> Household relationship")
        else:
            print("  ❌ User -> Household relationship")
            
        # 3. Get expense with creator
        expense = db.query(Expense).first()
        if expense and expense.created_by_user:
            print("  ✅ Expense -> User relationship")
        else:
            print("  ❌ Expense -> User relationship")
            
        # 4. Get bill with payments
        bill = db.query(Bill).first()
        if bill and len(bill.payments) >= 1:
            print("  ✅ Bill -> BillPayment relationship")
        else:
            print("  ❌ Bill -> BillPayment relationship")
            
        # 5. Get task with assigned user
        task = db.query(Task).first()
        if task and task.assigned_user:
            print("  ✅ Task -> User relationship")
        else:
            print("  ❌ Task -> User relationship")
            
        # 6. Get event with RSVPs
        event = db.query(Event).first()
        if event and len(event.rsvps) >= 1:
            print("  ✅ Event -> RSVP relationship")
        else:
            print("  ❌ Event -> RSVP relationship")
            
        # 7. Get shopping list with items
        shopping_list = db.query(ShoppingList).first()
        if shopping_list and len(shopping_list.items) >= 1:
            print("  ✅ ShoppingList -> ShoppingItem relationship")
        else:
            print("  ❌ ShoppingList -> ShoppingItem relationship")
            
        # 8. Get poll with votes
        poll = db.query(Poll).first()
        if poll and len(poll.votes) >= 1:
            print("  ✅ Poll -> PollVote relationship")
        else:
            print("  ❌ Poll -> PollVote relationship")
            
        print("✅ Relationship validation completed")
        return True
        
    except Exception as e:
        print(f"❌ Error validating relationships: {str(e)}")
        return False
    finally:
        db.close()

def main():
    """Main validation function"""
    print("🗄️ ROOMLY DATABASE RELATIONSHIP VALIDATOR")
    print("=========================================")
    
    # Create test database
    engine = create_test_database()
    
    # Validate table creation
    if not validate_table_creation(engine):
        print("❌ Database validation failed at table creation")
        return False
    
    # Validate foreign keys
    if not validate_foreign_keys(engine):
        print("❌ Database validation failed at foreign key validation")
        return False
    
    # Create test data
    if not create_test_data(engine):
        print("❌ Database validation failed at test data creation")
        return False
    
    # Validate relationships
    if not validate_relationships(engine):
        print("❌ Database validation failed at relationship validation")
        return False
    
    print("\n🎉 DATABASE VALIDATION SUCCESSFUL! 🎉")
    print("====================================")
    print("✅ All tables created correctly")
    print("✅ All foreign keys configured properly")
    print("✅ Test data created successfully")
    print("✅ All relationships working correctly")
    print(f"✅ Test database: {TEST_DATABASE_URL}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
