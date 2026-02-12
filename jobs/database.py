"""Database connection for job processor."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import config

# Create database engine
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models (if needed)
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, caller is responsible
