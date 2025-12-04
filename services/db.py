from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# Database engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine."""
    global _engine
    
    if _engine is None:
        from config.settings import get_settings
        settings = get_settings()
        
        try:
            _engine = create_engine(
                settings.build_sqlalchemy_url(),
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=True,
                echo=settings.SQLALCHEMY_ECHO,
            )
            logger.info("Database engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    return _engine


def get_session_factory():
    """Get or create session factory."""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            )
        )
    
    return _SessionLocal


def init_db():
    """Initialize database connection (legacy support)."""
    get_engine()
    get_session_factory()


def get_db() -> Generator:
    """
    Get database session.
    
    Usage:
        db = next(get_db())
        try:
            # Use db
        finally:
            db.close()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = get_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


@contextmanager
def get_session():
    """
    Context manager for database sessions.
    
    Usage:
        with get_session() as session:
            # Use session
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_db():
    """Close database connections (useful for cleanup)."""
    global _engine, _SessionLocal
    
    if _SessionLocal is not None:
        _SessionLocal.remove()
        _SessionLocal = None
    
    if _engine is not None:
        _engine.dispose()
        _engine = None