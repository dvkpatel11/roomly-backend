#!/usr/bin/env python3
"""
Database Migration Script
Handles database creation and updates
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from database import Base, DATABASE_URL
from models import *

def create_production_database():
    """Create production database with all tables"""
    print("🗄️ Creating production database...")
    
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Production database created successfully")
    print(f"📍 Database URL: {DATABASE_URL}")
    
    return engine

def main():
    """Main migration function"""
    print("🗄️ ROOMLY DATABASE MIGRATION")
    print("============================")
    
    try:
        engine = create_production_database()
        print("🎉 Database migration completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
