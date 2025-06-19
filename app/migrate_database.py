#!/usr/bin/env python3
"""
Database Migration Script
Handles migration from old schema to new household membership structure
"""

from sqlalchemy import text, inspect
from sqlalchemy.orm import sessionmaker
from .database import engine, Base
from .models import User, Household, HouseholdMembership
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_migration_needed():
    """Check if migration is needed"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Check if we have the old structure (users.household_id) and new structure (household_memberships)
    has_old_structure = False
    has_new_structure = "household_memberships" in tables

    if "users" in tables:
        user_columns = [col["name"] for col in inspector.get_columns("users")]
        has_old_structure = "household_id" in user_columns

    return has_old_structure, has_new_structure


def migrate_user_household_relationships():
    """Migrate from direct household_id to membership table"""
    logger.info("🔄 Starting household membership migration...")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if migration is needed
        has_old, has_new = check_migration_needed()

        if not has_old:
            logger.info("✅ No migration needed - old structure not found")
            return True

        if not has_new:
            logger.info("📋 Creating household_memberships table...")
            Base.metadata.create_all(bind=engine)

        # Get users with household_id
        result = db.execute(
            text(
                """
            SELECT id, household_id, household_role 
            FROM users 
            WHERE household_id IS NOT NULL
        """
            )
        )

        users_to_migrate = result.fetchall()
        logger.info(f"📊 Found {len(users_to_migrate)} users to migrate")

        # Create membership records
        for user_id, household_id, role in users_to_migrate:
            # Check if membership already exists
            existing = db.execute(
                text(
                    """
                SELECT id FROM household_memberships 
                WHERE user_id = :user_id AND household_id = :household_id
            """
                ),
                {"user_id": user_id, "household_id": household_id},
            ).fetchone()

            if not existing:
                db.execute(
                    text(
                        """
                    INSERT INTO household_memberships (user_id, household_id, role, is_active)
                    VALUES (:user_id, :household_id, :role, true)
                """
                    ),
                    {
                        "user_id": user_id,
                        "household_id": household_id,
                        "role": role or "member",
                    },
                )
                logger.info(
                    f"✅ Created membership for user {user_id} in household {household_id}"
                )
            else:
                logger.info(f"⏭️  Membership already exists for user {user_id}")

        db.commit()
        logger.info("🎉 Migration completed successfully!")

        # Optionally remove old columns (commented out for safety)
        # logger.info("🗑️  Removing old household_id and household_role columns...")
        # db.execute(text("ALTER TABLE users DROP COLUMN household_id"))
        # db.execute(text("ALTER TABLE users DROP COLUMN household_role"))
        # db.commit()

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def validate_migration():
    """Validate that migration was successful"""
    logger.info("🔍 Validating migration...")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Count users and memberships
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        membership_count = db.execute(
            text("SELECT COUNT(*) FROM household_memberships WHERE is_active = true")
        ).scalar()

        logger.info(f"📊 Users: {user_count}, Active memberships: {membership_count}")

        # Check for orphaned data
        orphaned_users = db.execute(
            text(
                """
            SELECT COUNT(*) FROM users u
            WHERE u.household_id IS NOT NULL 
            AND NOT EXISTS (
                SELECT 1 FROM household_memberships hm 
                WHERE hm.user_id = u.id AND hm.is_active = true
            )
        """
            )
        ).scalar()

        if orphaned_users > 0:
            logger.warning(
                f"⚠️  Found {orphaned_users} users with household_id but no active membership"
            )
            return False

        logger.info("✅ Migration validation passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        return False
    finally:
        db.close()


def backup_database():
    """Create a backup before migration"""
    logger.info("💾 Creating database backup...")

    # For SQLite
    if "sqlite" in str(engine.url):
        import shutil
        from pathlib import Path

        db_path = str(engine.url).replace("sqlite:///", "")
        backup_path = f"{db_path}.backup"

        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None
    else:
        logger.warning("⚠️  Automatic backup not implemented for this database type")
        logger.warning("Please create a manual backup before proceeding")
        return None


def main():
    """Run the complete migration process"""
    logger.info("🚀 Starting database migration process...")

    try:
        # Create backup
        backup_path = backup_database()

        # Check if migration is needed
        has_old, has_new = check_migration_needed()

        if not has_old and has_new:
            logger.info("✅ Database is already migrated!")
            return

        # Run migration
        if migrate_user_household_relationships():
            if validate_migration():
                logger.info("🎉 Migration completed successfully!")
            else:
                logger.error("❌ Migration validation failed!")
                if backup_path:
                    logger.info(f"💡 Restore from backup: {backup_path}")
        else:
            logger.error("❌ Migration failed!")

    except Exception as e:
        logger.error(f"❌ Migration process failed: {e}")
        raise


if __name__ == "__main__":
    main()
