
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker, Session
# from sqlalchemy.pool import QueuePool
# from typing import Generator
# import os
# from dotenv import load_dotenv
# from services.cache import cache_resource_singleton

# # Load environment variables
# load_dotenv()

# # Database configuration
# DB_USER = os.getenv("POSTGRES_USER", "airflow")
# DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
# DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
# DB_PORT = os.getenv("POSTGRES_PORT", "5432")
# DB_NAME = os.getenv("POSTGRES_DB", "dwh")

# # Connection pool settings
# POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
# MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
# POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

# # Build connection string
# DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# @cache_resource_singleton()
# def get_engine():
#     """
#     Create and cache SQLAlchemy engine with connection pooling.
    
#     This function is cached as a resource, meaning the engine is created
#     once and reused across all sessions.
    
#     Returns:
#         SQLAlchemy Engine instance
#     """
#     engine = create_engine(
#         DATABASE_URL,
#         poolclass=QueuePool,
#         pool_size=POOL_SIZE,
#         max_overflow=MAX_OVERFLOW,
#         pool_recycle=POOL_RECYCLE,
#         pool_pre_ping=True,  # Verify connections before using
#         echo=os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
#     )
#     return engine


# def get_session_maker():
#     """
#     Create session maker bound to the cached engine.
    
#     Returns:
#         SQLAlchemy SessionMaker
#     """
#     engine = get_engine()
#     return sessionmaker(bind=engine)


# def get_db() -> Generator[Session, None, None]:
#     """
#     Dependency function to get database session.
    
#     Yields:
#         SQLAlchemy Session
        
#     Usage:
#         db = next(get_db())
#         try:
#             # Use db
#             pass
#         finally:
#             db.close()
#     """
#     SessionLocal = get_session_maker()
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# def test_connection() -> bool:
#     """
#     Test database connection.
    
#     Returns:
#         True if connection successful, False otherwise
#     """
#     try:
#         engine = get_engine()
#         with engine.connect() as conn:
#             conn.execute(text("SELECT 1"))
#         return True
#     except Exception as e:
#         print(f"Database connection failed: {e}")
#         return False

# AWS connection settings

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator, Optional
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_engine = None
_settings = None

def get_db_settings():
    """Get database settings (cached)."""
    global _settings
    if _settings is None:
        from config.settings import get_db_settings as load_settings
        _settings = load_settings()
    return _settings

def get_engine():
    """Create SQLAlchemy engine once and reuse."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_db_settings()
    
    try:
        database_url = settings.build_sqlalchemy_url()
        
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,  # Critical for AWS connections
            echo=settings.SQLALCHEMY_ECHO,
            connect_args={
                "connect_timeout": 10,  # Prevent hanging
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            }
        )
        logger.info("Database engine created successfully")
        return _engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise RuntimeError(f"Database connection failed: {e}")

def get_session_maker():
    """Create session maker bound to the cached engine."""
    engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)

def get_db() -> Generator[Session, None, None]:
    """Dependency function to get database session."""
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def test_connection() -> bool:
    """Test database connection."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False