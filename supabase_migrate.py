"""
Database Migration Script for Supabase
Run this after updating your models and before starting the application
"""

from sqlalchemy import text
from app.database import engine, SessionLocal, init_db
from ..models.user import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_user_table():
    """Add Supabase integration columns to existing users table"""

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            # Check if supabase_id column exists
            result = conn.execute(
                text(
                    """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'supabase_id'
            """
                )
            )

            if not result.fetchone():
                logger.info("Adding supabase_id column to users table...")

                # Add supabase_id column
                conn.execute(
                    text(
                        """
                    ALTER TABLE users 
                    ADD COLUMN supabase_id VARCHAR UNIQUE
                """
                    )
                )

                # Add index for supabase_id
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS ix_users_supabase_id 
                    ON users (supabase_id)
                """
                    )
                )

                # Make hashed_password nullable (for new Supabase users)
                conn.execute(
                    text(
                        """
                    ALTER TABLE users 
                    ALTER COLUMN hashed_password DROP NOT NULL
                """
                    )
                )

                logger.info("✅ User table migration completed")
            else:
                logger.info("✅ User table already migrated")

            # Remove SQLite-specific constraint if it exists (for PostgreSQL)
            try:
                conn.execute(
                    text(
                        """
                    ALTER TABLE users 
                    DROP CONSTRAINT IF EXISTS uq_user_phone
                """
                    )
                )

                # Add PostgreSQL-compatible constraint
                conn.execute(
                    text(
                        """
                    ALTER TABLE users 
                    ADD CONSTRAINT uq_user_phone UNIQUE (phone)
                """
                    )
                )

                logger.info("✅ Phone constraint updated for PostgreSQL")
            except Exception as e:
                logger.warning(
                    f"Constraint update failed (may already be correct): {e}"
                )

            # Commit transaction
            trans.commit()
            logger.info("✅ All migrations completed successfully")

        except Exception as e:
            trans.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise


def verify_migration():
    """Verify that migration was successful"""

    try:
        with engine.connect() as conn:
            # Check table structure
            result = conn.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """
                )
            )

            columns = result.fetchall()
            logger.info("Current users table structure:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")

            # Check for required columns
            column_names = [col[0] for col in columns]
            required_columns = ["id", "email", "supabase_id", "name", "hashed_password"]

            missing_columns = [
                col for col in required_columns if col not in column_names
            ]
            if missing_columns:
                logger.error(f"❌ Missing required columns: {missing_columns}")
                return False

            # Check constraints
            result = conn.execute(
                text(
                    """
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'users'
            """
                )
            )

            constraints = result.fetchall()
            logger.info("Table constraints:")
            for constraint in constraints:
                logger.info(f"  - {constraint[0]}: {constraint[1]}")

            logger.info("✅ Migration verification completed")
            return True

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


def create_test_data():
    """Create test data for development (optional)"""

    db = SessionLocal()
    try:
        # Check if we already have users
        user_count = db.query(User).count()
        if user_count > 0:
            logger.info(f"✅ Database already has {user_count} users")
            return

        # Create a test user (you can remove this in production)
        test_user = User(
            email="test@example.com",
            name="Test User",
            phone="+1234567890",
            is_active=True,
            # No supabase_id or hashed_password - will be set when they register via Supabase
        )

        db.add(test_user)
        db.commit()
        logger.info("✅ Test user created")

    except Exception as e:
        logger.error(f"❌ Test data creation failed: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Run the complete migration process"""
    init_db()
    logger.info("🚀 Starting Supabase migration...")

    try:
        # Step 1: Migrate user table
        migrate_user_table()

        # Step 2: Verify migration
        if not verify_migration():
            raise Exception("Migration verification failed")

        # Step 3: Create test data (optional, comment out for production)
        # create_test_data()

        logger.info("🎉 Migration completed successfully!")
        logger.info("Next steps:")
        logger.info("1. Update your DATABASE_URL to point to Supabase PostgreSQL")
        logger.info(
            "2. Set your SUPABASE_URL and SUPABASE_ANON_KEY environment variables"
        )
        logger.info("3. Replace your auth.py router with the new Supabase version")
        logger.info("4. Start your application")

    except Exception as e:
        logger.error(f"💥 Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
