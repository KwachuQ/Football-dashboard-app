import pytest
from sqlalchemy import inspect, text
from src.models import (
    Base,
    TeamOverview,
    TeamForm,
    TeamAttack,
    TeamDefense,
    TeamPossession,
    TeamDiscipline,
    HeadToHead,
    MatchPredictions,
    TeamBttsAnalysis,
    TeamSeasonSummary,
    UpcomingFixtures,
)


@pytest.mark.unit
class TestModelDefinitions:
    """Test that SQLAlchemy models are properly defined."""
    
    def test_base_exists(self):
        """Test that Base class exists."""
        assert Base is not None
    
    def test_all_models_have_tablename(self):
        """Test that all models have __tablename__ defined."""
        models = [
            TeamOverview, TeamForm, TeamAttack, TeamDefense,
            TeamPossession, TeamDiscipline, HeadToHead,
            MatchPredictions, TeamBttsAnalysis, TeamSeasonSummary,
            UpcomingFixtures
        ]
        for model in models:
            assert hasattr(model, '__tablename__')
            assert model.__tablename__ is not None
    
    def test_team_overview_columns(self):
        """Test TeamOverview has expected columns."""
        expected_columns = {
            'season_id', 'team_id', 'team_name', 'matches_played',
            'wins', 'draws', 'losses', 'total_points', 'goals_for',
            'goals_against', 'goal_difference'
        }
        mapper = inspect(TeamOverview)
        actual_columns = {col.key for col in mapper.columns}
        assert expected_columns.issubset(actual_columns)
    
    def test_match_predictions_columns(self):
        """Test MatchPredictions has expected columns."""
        expected_columns = {
            'match_id', 'match_date', 'home_team_id', 'away_team_id',
            'home_win_probability', 'draw_probability', 'away_win_probability',
            'predicted_home_goals', 'predicted_away_goals'
        }
        mapper = inspect(MatchPredictions)
        actual_columns = {col.key for col in mapper.columns}
        assert expected_columns.issubset(actual_columns)


@pytest.mark.integration
class TestModelQueries:
    """Test querying models against actual database."""
    
    def test_can_query_team_overview(self, db_session, verify_schema):
        """Test querying TeamOverview table."""
        from sqlalchemy import select
        stmt = select(TeamOverview).limit(1)
        result = db_session.execute(stmt).scalar_one_or_none()
        
        if result:
            assert result.team_id is not None
            assert result.team_name is not None
    
    def test_can_query_team_form(self, db_session, verify_schema):
        """Test querying TeamForm table."""
        from sqlalchemy import select
        stmt = select(TeamForm).limit(1)
        result = db_session.execute(stmt).scalar_one_or_none()
        
        if result:
            assert result.team_id is not None
    
    def test_can_query_match_predictions(self, db_session, verify_schema):
        """Test querying MatchPredictions table."""
        from sqlalchemy import select
        stmt = select(MatchPredictions).limit(1)
        result = db_session.execute(stmt).scalar_one_or_none()
        
        if result:
            assert result.match_id is not None
    
    def test_upcoming_fixtures_model(self, db_session, verify_schema):
        """Test querying UpcomingFixtures table."""
        from sqlalchemy import select
        stmt = select(UpcomingFixtures).limit(1)
        result = db_session.execute(stmt).scalar_one_or_none()
        
        # May be None if no upcoming fixtures
        if result:
            assert result.match_id is not None
            assert result.home_team_name is not None
            assert result.away_team_name is not None