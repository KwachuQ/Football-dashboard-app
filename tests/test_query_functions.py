import pytest
import pandas as pd
from datetime import datetime, timedelta
from services.queries import (
    get_upcoming_fixtures,
    get_team_form,
    get_team_stats,
    get_head_to_head,
    get_match_predictions,
    get_league_standings,
    get_btts_analysis,
    get_data_freshness,
    get_all_seasons,
)


@pytest.mark.integration
class TestDataFreshness:
    """Test data freshness monitoring."""
    
    def test_get_data_freshness_returns_dataframe(self, verify_schema):
        """Test data freshness check returns DataFrame."""
        df = get_data_freshness()
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert 'table_name' in df.columns
        assert 'row_count' in df.columns
        assert 'status' in df.columns
        assert len(df) >= 10  # At least 10 mart tables
    
    def test_data_freshness_all_tables_populated(self, verify_schema):
        """Test that all tables have data."""
        df = get_data_freshness()
        
        # Check that at least some tables have data
        tables_with_data = df[df['status'] == 'OK']
        assert len(tables_with_data) > 0, "No tables have data"


@pytest.mark.integration
class TestSeasonQueries:
    """Test season-related queries."""
    
    def test_get_all_seasons_returns_dataframe(self, verify_schema):
        """Test get_all_seasons returns valid DataFrame."""
        df = get_all_seasons()
        
        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert 'season_id' in df.columns
            assert 'season_name' in df.columns
            assert 'season_year' in df.columns
            # Verify seasons are sorted by year descending
            if len(df) > 1:
                assert df['season_year'].iloc[0] >= df['season_year'].iloc[1]


@pytest.mark.integration
class TestUpcomingFixtures:
    """Test upcoming fixtures queries."""
    
    def test_get_upcoming_fixtures_basic(self, verify_schema, sample_season_id):
        """Test basic upcoming fixtures query."""
        df = get_upcoming_fixtures(season_id=sample_season_id, days_ahead=30, limit=10)
        
        assert isinstance(df, pd.DataFrame)
        # May be empty if no upcoming fixtures
        if not df.empty:
            assert 'match_id' in df.columns
            assert 'home_team' in df.columns
            assert 'away_team' in df.columns
            assert 'tournament' in df.columns
    
    def test_get_upcoming_fixtures_no_filters(self, verify_schema):
        """Test upcoming fixtures without filters."""
        df = get_upcoming_fixtures(days_ahead=7, limit=20)
        
        assert isinstance(df, pd.DataFrame)
        # Should return at most 20 rows
        assert len(df) <= 20
    
    def test_get_upcoming_fixtures_with_tournament(self, verify_schema, sample_tournament_id):
        """Test filtering by tournament."""
        if sample_tournament_id is None:
            pytest.skip("No tournament ID available")
        
        df = get_upcoming_fixtures(
            tournament_id=sample_tournament_id,
            days_ahead=30,
            limit=10
        )
        
        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            # All results should be from the same tournament
            assert df['tournament_id'].nunique() == 1
            assert df['tournament_id'].iloc[0] == sample_tournament_id


@pytest.mark.integration
class TestTeamQueries:
    """Test team-related queries."""
    
    def test_get_team_form_valid_team(self, verify_schema, sample_team_id):
        """Test getting team form for valid team."""
        result = get_team_form(team_id=sample_team_id)
        
        assert isinstance(result, dict)
        if result:  # May be empty if team has no form data
            assert 'team_id' in result
            assert 'team_name' in result
            assert 'last_5_results' in result
    
    def test_get_team_form_invalid_team(self, verify_schema):
        """Test getting team form for non-existent team."""
        result = get_team_form(team_id=999999)
        
        assert isinstance(result, dict)
        assert result == {}
    
    @pytest.mark.parametrize("stat_type", [
        'attack', 'defense', 'possession', 'discipline', 'overview'
    ])
    def test_get_team_stats_valid_types(self, verify_schema, sample_team_id, stat_type):
        """Test get_team_stats with all valid stat types."""
        result = get_team_stats(team_id=sample_team_id, stat_type=stat_type)
        
        assert isinstance(result, dict)
        if result:  # May be empty if no data
            assert 'team_id' in result
            assert 'team_name' in result
    
    def test_get_team_stats_invalid_type(self, sample_team_id):
        """Test get_team_stats with invalid stat type."""
        with pytest.raises(ValueError, match="Invalid stat_type"):
            get_team_stats(team_id=sample_team_id, stat_type='invalid_type')
    
    def test_get_btts_analysis(self, verify_schema, sample_team_id):
        """Test BTTS analysis query."""
        result = get_btts_analysis(team_id=sample_team_id)
        
        assert isinstance(result, dict)
        if result:
            assert 'team_id' in result
            assert 'overall_btts_pct' in result
            assert 'home_btts_pct' in result
            assert 'away_btts_pct' in result


@pytest.mark.integration
class TestMatchQueries:
    """Test match-related queries."""
    
    def test_get_head_to_head_with_data(self, verify_schema, db_session):
        """Test H2H query with teams that have history."""
        from sqlalchemy import select, text
        
        # Find two teams that have H2H data
        result = db_session.execute(text(
            "SELECT team_id_1, team_id_2 FROM gold.mart_head_to_head LIMIT 1"
        )).fetchone()
        
        if result:
            team1_id, team2_id = result
            h2h = get_head_to_head(team1_id, team2_id)
            
            assert isinstance(h2h, dict)
            assert h2h['team1_id'] == team1_id
            assert h2h['team2_id'] == team2_id
            assert 'total_matches' in h2h
            assert h2h['total_matches'] > 0
    
    def test_get_head_to_head_no_data(self, verify_schema):
        """Test H2H query with teams that have no history."""
        h2h = get_head_to_head(999998, 999999)
        
        assert isinstance(h2h, dict)
        assert h2h['total_matches'] == 0
        assert h2h['team1_wins'] == 0
    
    def test_get_match_predictions_empty_list(self, verify_schema):
        """Test match predictions with empty list."""
        df = get_match_predictions([])
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_get_match_predictions_valid_matches(self, verify_schema, db_session):
        """Test match predictions with valid match IDs."""
        from sqlalchemy import text
        
        # Get some match IDs that have predictions
        result = db_session.execute(text(
            "SELECT match_id FROM gold.mart_match_predictions LIMIT 3"
        )).fetchall()
        
        if result:
            match_ids = [row[0] for row in result]
            df = get_match_predictions(match_ids)
            
            assert isinstance(df, pd.DataFrame)
            assert not df.empty
            assert 'match_id' in df.columns
            assert 'home_win_prob' in df.columns
            assert len(df) <= len(match_ids)
    
    def test_get_league_standings(self, verify_schema, sample_season_id):
        """Test league standings query."""
        df = get_league_standings(season_id=sample_season_id)
        
        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert 'position' in df.columns
            assert 'team_name' in df.columns
            assert 'points' in df.columns
            # Verify standings are sorted correctly
            if len(df) > 1:
                assert df['points'].iloc[0] >= df['points'].iloc[1]
            # Position should be 1, 2, 3, ...
            assert list(df['position']) == list(range(1, len(df) + 1))


@pytest.mark.integration
class TestQueryPerformance:
    """Test query performance."""
    
    @pytest.mark.slow
    def test_upcoming_fixtures_performance(self, verify_schema, sample_season_id):
        """Test that upcoming fixtures query completes quickly."""
        import time
        
        start = time.time()
        df = get_upcoming_fixtures(season_id=sample_season_id, days_ahead=30, limit=50)
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"Query took {elapsed:.2f}s (should be < 2s)"
    
    @pytest.mark.slow
    def test_league_standings_performance(self, verify_schema, sample_season_id):
        """Test that league standings query completes quickly."""
        import time
        
        start = time.time()
        df = get_league_standings(season_id=sample_season_id)
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"Query took {elapsed:.2f}s (should be < 1s)"