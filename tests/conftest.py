import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for testing."""
    from config.settings import get_settings
    settings = get_settings()
    engine = create_engine(
        settings.build_sqlalchemy_url(),
        pool_pre_ping=True,
        echo=False  # Set to True for SQL debugging
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    SessionLocal = scoped_session(
        sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        SessionLocal.remove()


@pytest.fixture(scope="session")
def verify_schema(db_engine):
    """Verify that required tables exist in the database."""
    required_tables = [
        'mart_team_overview',
        'mart_team_form',
        'mart_team_attack',
        'mart_team_defense',
        'mart_team_possession',
        'mart_team_discipline',
        'mart_match_predictions',
        'mart_head_to_head',
        'mart_team_season_summary',
        'mart_team_btts_analysis',
        'mart_upcoming_fixtures',
    ]
    
    with db_engine.connect() as conn:
        for table in required_tables:
            result = conn.execute(text(
                f"SELECT EXISTS (SELECT FROM information_schema.tables "
                f"WHERE table_schema = 'gold' AND table_name = '{table}')"
            ))
            exists = result.scalar()
            if not exists:
                pytest.skip(f"Required table gold.{table} does not exist")


@pytest.fixture(scope="session")
def sample_season_id(db_engine):
    """Get a sample season ID from the database."""
    with db_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT season_id FROM gold.mart_team_overview LIMIT 1"
        ))
        season_id = result.scalar()
        if not season_id:
            pytest.skip("No data in mart_team_overview")
        return season_id


@pytest.fixture(scope="session")
def sample_team_id(db_engine):
    """Get a sample team ID from the database."""
    with db_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT team_id FROM gold.mart_team_overview LIMIT 1"
        ))
        team_id = result.scalar()
        if not team_id:
            pytest.skip("No data in mart_team_overview")
        return team_id


@pytest.fixture(scope="session")
def sample_tournament_id(db_engine):
    """Get a sample tournament ID from upcoming fixtures."""
    with db_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT tournament_id FROM gold.mart_upcoming_fixtures LIMIT 1"
        ))
        tournament_id = result.scalar()
        return tournament_id  # May be None if no upcoming fixtures