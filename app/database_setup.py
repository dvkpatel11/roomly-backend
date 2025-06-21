#!/usr/bin/env python3
"""
Database Setup Module
Creates database tables using proper module imports
"""

try:
    from .database import engine, Base

    # Import all models to ensure they're registered with SQLAlchemy
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
        EventApproval,
        Guest,
        GuestApproval,
        Announcement,
        Poll,
        PollVote,
        Notification,
        NotificationPreference,
        RSVP,
        ShoppingList,
        ShoppingItem,
    )

    print("📋 Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database setup complete!")

    # Print table summary
    tables = Base.metadata.tables.keys()
    print(f"📊 Created {len(tables)} tables:")
    for table in sorted(tables):
        print(f"  - {table}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you are running from the correct directory")
    print("💡 Try running: python -m app.database_setup")
    raise
except Exception as e:
    print(f"❌ Database setup failed: {e}")
    raise

if __name__ == "__main__":
    print("Database setup completed!")
