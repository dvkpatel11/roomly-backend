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
        Expense,
        Bill,
        BillPayment,
        Task,
        Event,
        Guest,
        Announcement,
        Poll,
        PollVote,
        Notification,
        NotificationPreference,
        RSVP,
        UserSchedule,
        ShoppingList,
        ShoppingItem,
        HouseholdMembership,  # MISSING
        ExpensePayment,  # MISSING
        GuestApproval,  # MISSING
        EventApproval,
    )

    print("📋 Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database setup complete!")

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
