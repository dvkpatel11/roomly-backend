#!/usr/bin/env python3
"""
Database Setup Module
Creates database tables using proper module imports
"""

import os
import sys

# Add the parent directory to Python path to fix imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import engine, Base
    
    # Import all models to ensure they're registered
    from models.user import User
    from models.household import Household
    from models.expense import Expense
    from models.bill import Bill, BillPayment
    from models.task import Task
    from models.event import Event
    from models.guest import Guest
    from models.announcement import Announcement
    from models.poll import Poll, PollVote
    from models.notification import Notification, NotificationPreference
    from models.rsvp import RSVP
    from models.user_schedule import UserSchedule
    from models.shopping_list import ShoppingList, ShoppingItem
    
    print('📋 Creating all database tables...')
    Base.metadata.create_all(bind=engine)
    print('✅ Database setup complete!')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
    print('💡 Make sure you are running from the correct directory')
    sys.exit(1)
except Exception as e:
    print(f'❌ Database setup failed: {e}')
    sys.exit(1)
