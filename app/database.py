from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from contextlib import contextmanager
import asyncpg

load_dotenv()

# Database URLs
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./roomly.db")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Optional

# SQLAlchemy setup (for ORM approach)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,  # Good for PostgreSQL connections
    pool_recycle=300,  # Recycle connections every 5 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Supabase client setup (for direct API approach)
supabase: Client = None
supabase_admin: Client = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    # Optional admin client for administrative operations
    if SUPABASE_SERVICE_ROLE_KEY:
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# SQLAlchemy dependency (existing approach)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Supabase dependency (new approach)
def get_supabase() -> Client:
    """Get Supabase client for regular operations"""
    if not supabase:
        raise RuntimeError(
            "Supabase client not initialized. Check your environment variables."
        )
    return supabase


def get_supabase_admin() -> Client:
    """Get Supabase admin client for administrative operations"""
    if not supabase_admin:
        raise RuntimeError(
            "Supabase admin client not initialized. Check SUPABASE_SERVICE_ROLE_KEY."
        )
    return supabase_admin


# Async PostgreSQL connection (for direct async database operations)
async def get_async_db_connection():
    """Get direct async PostgreSQL connection"""
    if not DATABASE_URL or "postgresql" not in DATABASE_URL:
        raise RuntimeError("PostgreSQL DATABASE_URL required for async operations")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            yield conn
        finally:
            await conn.close()
    except Exception as e:
        raise RuntimeError(f"Failed to connect to database: {e}")


# Database initialization
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


# Health check function
def check_db_connection() -> dict:
    """Check database connectivity"""
    status = {"sqlalchemy": False, "supabase": False, "supabase_admin": False}

    # Check SQLAlchemy connection
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        status["sqlalchemy"] = True
    except Exception:
        pass

    # Check Supabase connection
    try:
        if supabase:
            # Try a simple query to test connection
            result = supabase.table("dummy").select("*").limit(1).execute()
            status["supabase"] = True
    except Exception:
        pass

    # Check Supabase admin connection
    try:
        if supabase_admin:
            result = supabase_admin.table("dummy").select("*").limit(1).execute()
            status["supabase_admin"] = True
    except Exception:
        pass

    return status
