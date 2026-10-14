"""
Database Connection & Session Management

This module handles:
  1. PostgreSQL connection configuration
  2. SQLAlchemy engine setup
  3. Database session factory
  4. Dependency injection for FastAPI endpoints

Why this pattern?
  - FastAPI endpoints need database access
  - Each request gets its own session (thread-safe)
  - Sessions auto-cleanup after request (no leaks)
  - Easy to test (inject mock session)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
import os
from typing import Generator

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Support for both PostgreSQL (production) and SQLite (development)
#
# Environment variable: DATABASE_URL
#   - If set: Use this connection string (e.g., postgresql://...)
#   - If not set: Auto-detect based on available services
#
# Development fallback:
#   - If PostgreSQL unavailable: Use SQLite (dev.db)
#   - Allows development without Docker

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DATABASE_URL = os.getenv("DATABASE_URL", None)

if not DATABASE_URL:
    if ENVIRONMENT == "production":
        # Production: PostgreSQL required
        DB_USER = os.getenv("DB_USER", "postgres")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = os.getenv("DB_PORT", "5432")
        DB_NAME = os.getenv("DB_NAME", "satellite_diagnosis")
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        # Development: Try PostgreSQL first, fall back to SQLite
        DB_USER = os.getenv("DB_USER", "postgres")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = os.getenv("DB_PORT", "5432")
        DB_NAME = os.getenv("DB_NAME", "satellite_diagnosis")
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# For backward compatibility
SQLALCHEMY_DATABASE_URL = DATABASE_URL

# ============================================================================
# ENGINE CONFIGURATION
# ============================================================================
# 
# Engine = Connection pool to database
#
# Why pooling?
#   - Creating new connection per request is slow (handshake with DB)
#   - Pool maintains N connections, reuses them
#   - Fast: get from pool instead of creating new
#   - Efficient: closes idle connections after timeout
#
# pool_size=5: Keep 5 connections in pool
# max_overflow=10: Allow 10 additional connections if pool exhausted
# pool_pre_ping=True: Test connection before using (detects dead connections)
# echo=False: Don't log SQL queries (set True for debugging)
# ============================================================================

# Try to create engine with PostgreSQL first, fall back to SQLite if needed
def create_database_engine():
    """Create database engine with fallback from PostgreSQL to SQLite"""
    try:
        print(f"[DB] Attempting to connect to PostgreSQL...")
        engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
            connect_args={"connect_timeout": 5}  # Increased timeout for container startup
        )
        # Test connection (with quick timeout)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[OK] Connected to PostgreSQL")
        return engine, "postgresql"
    except Exception as e:
        print(f"[WARN] PostgreSQL unavailable: {str(e)[:50]}...")
        print(f"[DB] Falling back to SQLite for development...")
        
        # Fall back to SQLite
        db_path = os.path.join(os.path.dirname(__file__), '../../dev.db')
        sqlite_url = f"sqlite:///{db_path}"
        
        engine = create_engine(
            sqlite_url,
            echo=False,
            connect_args={"check_same_thread": False}  # SQLite requirement
        )
        print(f"[OK] Using SQLite: {db_path}")
        return engine, "sqlite"

engine, DB_TYPE = create_database_engine()


# ============================================================================
# SESSION FACTORY
# ============================================================================
#
# SessionLocal = Factory that creates new sessions
#
# What's a session?
#   - Represents a database connection
#   - Tracks changes to objects (identity map)
#   - Commits transactions
#   - Auto-closes connections when done
#
# Pattern (inside FastAPI endpoint):
#   db = SessionLocal()
#   try:
#       user = db.query(User).filter(User.username == "alice").first()
#       # ... do stuff ...
#   finally:
#       db.close()
#
# Better: Use dependency injection (see get_db function below)
# ============================================================================

SessionLocal = sessionmaker(
    autocommit=False,  # Require explicit commit (safer)
    autoflush=False,   # Don't auto-flush changes (explicit control)
    bind=engine        # Use the engine we created above
)


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================
#
# create_all_tables()
#   - Creates all tables in database (if they don't exist)
#   - Uses models defined in models.py
#   - Called on application startup
#
# drop_all_tables()
#   - Drops all tables (DANGEROUS - only for testing!)
#   - Used to reset database
#
# ============================================================================

from .models import Base

def create_all_tables():
    """Create all database tables from models."""
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created/verified")


def drop_all_tables():
    """Drop all tables (DANGEROUS - use only for testing)."""
    Base.metadata.drop_all(bind=engine)
    print("[OK] Database tables dropped (WARNING: data lost)")


# ============================================================================
# DEPENDENCY INJECTION FOR FASTAPI
# ============================================================================
#
# FastAPI Pattern for database sessions:
#
# Without dependency injection (WRONG):
#   @app.post("/users/")
#   async def create_user(data):
#       db = SessionLocal()
#       user = User(**data)
#       db.add(user)
#       db.commit()
#       db.close()  # Easy to forget!
#       return user
#
# With dependency injection (CORRECT):
#   @app.post("/users/")
#   async def create_user(data, db: Session = Depends(get_db)):
#       user = User(**data)
#       db.add(user)
#       db.commit()
#       db.refresh(user)
#       return user
#
# FastAPI handles:
#   1. Creating session (calls get_db)
#   2. Running endpoint
#   3. Closing session (finally block)
#
# Benefits:
#   - Auto cleanup (no forgotten db.close())
#   - Easy to test (mock get_db)
#   - Sessions isolated per request (thread-safe)
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency: provides database session for each request.
    
    Usage:
        @app.get("/users/")
        async def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    
    FastAPI automatically:
        1. Calls get_db() to create session
        2. Passes session to endpoint
        3. Runs finally block to close session
        4. Cleans up after request completes
    """
    db = SessionLocal()
    try:
        yield db  # Yield = return session to endpoint, but wait for it to finish
    finally:
        db.close()  # Always close, even if endpoint raises exception


# ============================================================================
# HEALTH CHECK
# ============================================================================
#
# health_check()
#   - Tests if database connection works
#   - Used in /health endpoint
#   - If returns True: database is up
#   - If raises exception: database is down
#
# ============================================================================

def health_check() -> bool:
    """
    Check if database is accessible.
    
    Returns:
        True if healthy, raises exception if not.
    
    Usage:
        if health_check():
            print("Database is up")
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")  # Simple query that just returns 1
        db.close()
        return True
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False
