# services/db.py - FIXED for special characters + psycopg2
import os
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Import your cache decorator
from services.cache import cache_resource_singleton

def load_database_config():
    """Smart config loader."""
    if hasattr(st, 'secrets') and st.secrets:
        print("🔄 Loading from Streamlit secrets")
        return {
            'user': st.secrets.POSTGRES_USER,
            'password': st.secrets.POSTGRES_PASSWORD,
            'host': st.secrets.POSTGRES_HOST,
            'port': st.secrets.POSTGRES_PORT or '5432',
            'database': st.secrets.POSTGRES_DB,
            'ssl_mode': getattr(st.secrets, 'DB_SSL_MODE', 'require'),
            'source': 'streamlit_secrets'
        }
    elif os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
        return {
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD'),
            'host': os.getenv('POSTGRES_HOST'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB'),
            'ssl_mode': os.getenv('DB_SSL_MODE', 'prefer'),
            'source': '.env_file'
        }
    else:
        return {
            'user': 'airflow', 'password': 'airflow',
            'host': 'localhost', 'port': '5432', 'database': 'dwh',
            'ssl_mode': 'prefer', 'source': 'local_defaults'
        }

def build_connection_string(config):
    """Build psycopg2-compatible connection string."""
    # Use psycopg2 format - handles special chars automatically
    return (
        f"host={config['host']} "
        f"port={config['port']} "
        f"dbname={config['database']} "
        f"user={config['user']} "
        f"password={config['password']} "
        f"sslmode={config['ssl_mode']}"
    )

# ✅ FIXED decorator syntax
@cache_resource_singleton()
def get_engine():
    """Cached SQLAlchemy engine."""
    config = load_database_config()
    conn_string = build_connection_string(config)
    
    print(f"📡 Config: {config['source']}")
    print(f"🔌 Connecting to {config['host']}:{config['port']}/{config['database']}")
    
    engine = create_engine(
        f"postgresql://{config['user']}@{config['host']}:{config['port']}/{config['database']}?sslmode={config['ssl_mode']}",
        poolclass=QueuePool,
        pool_size=int(os.getenv('DB_POOL_SIZE', 5)),
        max_overflow=int(os.getenv('DB_MAX_OVERFLOW', 10)),
        pool_recycle=int(os.getenv('DB_POOL_RECYCLE', 1800)),
        pool_pre_ping=True
    )
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.scalar()
        print("✅ Connection successful!")
    
    return engine

def get_sessionmaker():
    engine = get_engine()
    return sessionmaker(bind=engine)

def get_db():
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.scalar()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


    

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