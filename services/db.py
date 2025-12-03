import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

# Load environment variables from .env if present
load_dotenv()

# Read credentials from environment (no hardcoded sensitive defaults)
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
PG_DB = os.getenv("POSTGRES_DB")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")  # non-sensitive default
PG_PORT = os.getenv("POSTGRES_PORT", "5432")       # non-sensitive default

# Fail fast if mandatory credentials are missing
missing = [name for name, val in {
    "POSTGRES_USER": PG_USER,
    "POSTGRES_PASSWORD": PG_PASSWORD,
    "POSTGRES_DB": PG_DB,
}.items() if not val]
if missing:
    raise RuntimeError(f"Missing required database env vars: {', '.join(missing)}")

from config.settings import get_settings
settings = get_settings()
DATABASE_URL = settings.build_sqlalchemy_url()

# Engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.SQLALCHEMY_ECHO,
    future=True,
)

# Thread-safe session factory
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
)

def get_db() -> Generator:
    """
    Yield a session and ensure it closes after use.
    Usage:
        with contextlib.closing(next(get_db())) as db: ...
    Or in frameworks that expect dependency yields.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_connection() -> bool:
    """
    Quick connectivity check: returns True if 'SELECT 1' succeeds.
    """
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT 1")).scalar() == 1
    except Exception:
        return False