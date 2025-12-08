from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import column, select, func, desc, and_, or_, text
from sqlalchemy.orm import Session
import pandas as pd
from services.db import get_engine
from services.cache import cache_query_result
import logging

logger = logging.getLogger(__name__)

from src.models import (
    TeamOverview,
    TeamForm,
    TeamSeasonSummary,
    TeamAttack,
    TeamDefense,
    TeamPossession,
    TeamDiscipline,
    HeadToHead,
    UpcomingPredictions,
    TeamBttsAnalysis,
)
from services.db import get_db


def get_upcoming_fixtures(
    season_id: Optional[int] = None,
    tournament_id: Optional[int] = None,
    days_ahead: int = 7,
    limit: int = 50
) -> pd.DataFrame:
    """
    Retrieve upcoming fixtures from mart_upcoming_fixtures.
    
    Args:
        season_id: Filter by season (None for all active seasons)
        tournament_id: Filter by tournament/league (None for all)
        days_ahead: Number of days to look ahead from today
        limit: Maximum number of fixtures to return
    
    Returns:
        DataFrame with columns: match_id, match_date, home_team_name, away_team_name,
                                tournament_name, season_name, round_number, status_type
    """
    from sqlalchemy import text
    
    db = next(get_db())
    try:
        today = datetime.now()
        end_date = today + timedelta(days=days_ahead)
        
        # Build dynamic SQL query
        sql = """
            SELECT 
                match_id,
                start_timestamp as match_date,
                home_team_id,
                home_team_name,
                away_team_id,
                away_team_name,
                tournament_id,
                tournament_name,
                season_id,
                season_name,
                season_year,
                round_number,
                status_type,
                match_slug,
                extraction_date
            FROM gold.mart_upcoming_fixtures
            WHERE start_timestamp >= :today
              AND start_timestamp <= :end_date
              AND status_type IN ('notstarted', 'scheduled')
        """
        
        params: Dict[str, Any] = {'today': today, 'end_date': end_date}
        
        if season_id:
            sql += " AND season_id = :season_id"
            params['season_id'] = season_id
        
        if tournament_id:
            sql += " AND tournament_id = :tournament_id"
            params['tournament_id'] = tournament_id
        
        # Use string formatting for LIMIT instead of parameterization
        sql += f" ORDER BY start_timestamp ASC LIMIT {limit}"
        
        result = db.execute(text(sql), params).fetchall()
        
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result, columns=[
            'match_id', 'match_date', 'home_team_id', 'home_team', 
            'away_team_id', 'away_team', 'tournament_id', 'tournament',
            'season_id', 'season_name', 'season_year', 'round_number',
            'status', 'match_slug', 'extraction_date'
        ])
        
        # Optionally join with predictions if available
        if not df.empty:
            match_ids = df['match_id'].tolist()
            predictions = get_match_predictions(match_ids)
            
            if not predictions.empty:
                df = df.merge(
                    predictions[['match_id', 'home_win_prob', 'draw_prob', 
                                'away_win_prob', 'predicted_home_goals', 
                                'predicted_away_goals', 'match_outlook', 
                                'home_win_fair_odds', 'draw_fair_odds', 'away_win_fair_odds']],
                    on='match_id',
                    how='left'
                )
        
        return df
    finally:
        db.close()


def get_team_form(team_id: int, last_n_matches: int = 5) -> Dict[str, Any]:
    """
    Get team form statistics.
    
    Args:
        team_id: Team ID
        last_n_matches: Number of recent matches (not used in current implementation)
        
    Returns:
        Dictionary with form data
    """
    from sqlalchemy import select, and_, func
    from src.models.team_form import TeamForm
    
    # Convert numpy types to Python int to avoid psycopg2 adapter errors
    team_id = int(team_id)
    
    db = next(get_db())
    try:
        # Get most recent season for this team
        subquery = select(func.max(TeamForm.season_id)).where(
            TeamForm.team_id == team_id
        ).scalar_subquery()
        
        query = select(TeamForm).where(
            and_(
                TeamForm.team_id == team_id,
                TeamForm.season_id == subquery
            )
        )
        
        result = db.execute(query).scalar_one_or_none()
        
        if result:
            return {
                'team_id': result.team_id,
                'team_name': result.team_name,
                'season_id': result.season_id,
                'season_name': result.season_name,
                'last_5_results': result.last_5_results,
                'points_last_5': result.points_last_5,
                'wins_last_5': result.wins_last_5,
                'draws_last_5': result.draws_last_5,
                'losses_last_5': result.losses_last_5,
                'goals_for_last_5': result.goals_for_last_5,
                'goals_against_last_5': result.goals_against_last_5,
            }
        
        return {}
        
    finally:
        db.close()

def get_team_stats(
    team_id: int,
    stat_type: str,
    season_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get team statistics by category.
    
    Args:
        team_id: Team identifier
        stat_type: One of 'attack', 'defense', 'possession', 'discipline', 'overview'
        season_id: Season to filter by (None for latest)
    
    Returns:
        Dictionary with relevant statistics for the stat_type
    """
    db = next(get_db())
    try:
        model_map = {
            'attack': TeamAttack,
            'defense': TeamDefense,
            'possession': TeamPossession,
            'discipline': TeamDiscipline,
            'overview': TeamOverview,
        }
        
        if stat_type not in model_map:
            raise ValueError(f"Invalid stat_type. Must be one of: {list(model_map.keys())}")
        
        model = model_map[stat_type]
        query = select(model).where(model.team_id == team_id)
        
        if season_id:
            query = query.where(model.season_id == season_id)
        else:
            # Get latest season
            subquery = select(func.max(model.season_id)).where(
                model.team_id == team_id
            ).scalar_subquery()
            query = query.where(model.season_id == subquery)
        
        result = db.execute(query).scalar_one_or_none()
        
        if not result:
            return {}
        
        # Convert SQLAlchemy model to dict, handling Decimal types
        from sqlalchemy import inspect
        mapper = inspect(result.__class__)
        
        return {
            column.key: (
                float(getattr(result, column.key)) 
                if isinstance(getattr(result, column.key), Decimal)
                else getattr(result, column.key)
            )
            for column in mapper.columns
        }
    finally:
        db.close()

def get_head_to_head(
    team1_id: int,
    team2_id: int,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get head-to-head statistics between two teams.
    
    Args:
        team1_id: First team identifier
        team2_id: Second team identifier
        limit: Not used (kept for API compatibility)
    
    Returns:
        Dictionary with h2h stats: matches_played, wins, draws, goals, etc.
    """
    db = next(get_db())
    try:
        # H2H table stores pairs in both directions, query both
        query = select(HeadToHead).where(
            or_(
                and_(
                    HeadToHead.team_id_1 == team1_id,
                    HeadToHead.team_id_2 == team2_id
                ),
                and_(
                    HeadToHead.team_id_1 == team2_id,
                    HeadToHead.team_id_2 == team1_id
                )
            )
        )
        
        result = db.execute(query).scalar_one_or_none()
        
        if not result:
            return {
                'team1_id': team1_id,
                'team2_id': team2_id,
                'total_matches': 0,
                'team1_wins': 0,
                'draws': 0,
                'team2_wins': 0,
            }
        
        # Normalize so team1 is always first
        # Get the actual Python boolean value, not SQLAlchemy expression
        is_swapped = bool(result.team_id_1 == team2_id)
        
        return {
            'team1_id': team1_id,
            'team2_id': team2_id,
            'team1_name': result.team_2_name if is_swapped else result.team_1_name,
            'team2_name': result.team_1_name if is_swapped else result.team_2_name,
            'total_matches': result.total_matches,
            'team1_wins': result.team_2_wins if is_swapped else result.team_1_wins,
            'draws': result.draws,
            'team2_wins': result.team_1_wins if is_swapped else result.team_2_wins,
            'team1_goals': result.team_2_goals if is_swapped else result.team_1_goals,
            'team2_goals': result.team_1_goals if is_swapped else result.team_2_goals,
            'team1_avg_goals': float(getattr(result, 'team_2_avg_goals')) if is_swapped and getattr(result, 'team_2_avg_goals') is not None else (float(getattr(result, 'team_1_avg_goals')) if getattr(result, 'team_1_avg_goals') is not None else None),
            'team2_avg_goals': float(getattr(result, 'team_1_avg_goals')) if is_swapped and getattr(result, 'team_1_avg_goals') is not None else (float(getattr(result, 'team_2_avg_goals')) if getattr(result, 'team_2_avg_goals') is not None else None),
            'last_meeting_date': result.last_meeting_date,
            'last_5_results': result.last_5_results,
        }
    finally:
        db.close()


def get_match_predictions(match_ids: List[int]) -> pd.DataFrame:
    """
    Get predictions for specific matches from upcoming_predictions table.
    
    Args:
        match_ids: List of match identifiers
    
    Returns:
        DataFrame with prediction details for requested matches
    """
    db = next(get_db())
    try:
        query = select(UpcomingPredictions).where(
            UpcomingPredictions.match_id.in_(match_ids)
        )
        
        result = db.execute(query).scalars().all()
        
        if not result:
            return pd.DataFrame()
        
        # Convert to DataFrame - handle integer probability values (0-100 range)
        data = []
        for r in result:
            row = {
                'match_id': r.match_id,
                'match_date': r.match_date,
                'home_team': r.home_team_name,
                'away_team': r.away_team_name,
                'home_win_prob': float(r.home_win_probability) / 100 if r.home_win_probability is not None else None,
                'draw_prob': float(r.draw_probability) / 100 if r.draw_probability is not None else None,
                'away_win_prob': float(r.away_win_probability) / 100 if r.away_win_probability is not None else None,
                'predicted_home_goals': float(r.predicted_home_goals) if r.predicted_home_goals is not None else None,
                'predicted_away_goals': float(r.predicted_away_goals) if r.predicted_away_goals is not None else None,
                'match_outlook': r.match_outlook,
                'home_win_fair_odds': float(r.home_win_fair_odds) if r.home_win_fair_odds is not None else None,
                'draw_fair_odds': float(r.draw_fair_odds) if r.draw_fair_odds is not None else None,
                'away_win_fair_odds': float(r.away_win_fair_odds) if r.away_win_fair_odds is not None else None,
            }
            data.append(row)
        
        return pd.DataFrame(data)
    finally:
        db.close()
        
def get_league_standings(season_id: int) -> pd.DataFrame:
    """
    Get league standings (team overview sorted by points).
    
    Args:
        season_id: Season identifier
    
    Returns:
        DataFrame with team standings sorted by points descending
    """
    db = next(get_db())
    try:
        query = select(
            TeamOverview.team_id,
            TeamOverview.team_name,
            TeamOverview.matches_played,
            TeamOverview.wins,
            TeamOverview.draws,
            TeamOverview.losses,
            TeamOverview.total_points,
            TeamOverview.points_per_game,
            TeamOverview.goals_for,
            TeamOverview.goals_against,
            TeamOverview.goal_difference,
            TeamOverview.clean_sheets,
            TeamOverview.clean_sheet_percentage,
        ).where(
            TeamOverview.season_id == season_id
        ).order_by(
            desc(TeamOverview.total_points),
            desc(TeamOverview.goal_difference),
            desc(TeamOverview.goals_for)
        )
        
        result = db.execute(query).all()
        
        df = pd.DataFrame(result, columns=[
            'team_id', 'team_name', 'matches_played', 'wins', 'draws', 'losses',
            'points', 'points_per_game', 'goals_for', 'goals_against',
            'goal_difference', 'clean_sheets', 'clean_sheet_pct'
        ])
        
        # Add position column
        df.insert(0, 'position', range(1, len(df) + 1))
        
        return df
    finally:
        db.close()


def get_btts_analysis(team_id: int, season_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get Both Teams To Score (BTTS) analysis for a team.
    
    Args:
        team_id: Team identifier
        season_id: Season to filter by (None for latest)
    
    Returns:
        Dictionary with BTTS statistics (overall, home, away)
    """
    db = next(get_db())
    try:
        query = select(TeamBttsAnalysis).where(TeamBttsAnalysis.team_id == team_id)
        
        if season_id:
            query = query.where(TeamBttsAnalysis.season_id == season_id)
        else:
            # Get latest season
            subquery = select(func.max(TeamBttsAnalysis.season_id)).where(
                TeamBttsAnalysis.team_id == team_id
            ).scalar_subquery()
            query = query.where(TeamBttsAnalysis.season_id == subquery)
        
        result = db.execute(query).scalar_one_or_none()
        
        if not result:
            return {}
        
        return {
            'team_id': result.team_id,
            'team_name': result.team_name,
            'season_name': result.season_name,
            'matches_played': result.matches_played,
            # Overall stats
            'overall_win_pct': float(getattr(result, 'overall_win_pct')) if getattr(result, 'overall_win_pct') is not None else None,
            'overall_btts_pct': float(getattr(result, 'overall_btts_pct')) if getattr(result, 'overall_btts_pct') is not None else None,
            'overall_clean_sheet_pct': float(getattr(result, 'overall_clean_sheet_pct')) if getattr(result, 'overall_clean_sheet_pct') is not None else None,
            'overall_avg_goals': float(getattr(result, 'overall_avg_goals_per_match')) if getattr(result, 'overall_avg_goals_per_match') is not None else None,
            'overall_avg_scored': float(getattr(result, 'overall_avg_scored')) if getattr(result, 'overall_avg_scored') is not None else None,
            'overall_avg_conceded': float(getattr(result, 'overall_avg_conceded')) if getattr(result, 'overall_avg_conceded') is not None else None,
            # Home stats
            'home_matches': result.home_matches_played,
            'home_win_pct': float(getattr(result, 'home_win_pct')) if getattr(result, 'home_win_pct') is not None else None,
            'home_btts_pct': float(getattr(result, 'home_btts_pct')) if getattr(result, 'home_btts_pct') is not None else None,
            'home_clean_sheet_pct': float(getattr(result, 'home_clean_sheet_pct')) if getattr(result, 'home_clean_sheet_pct') is not None else None,
            'home_avg_goals': float(getattr(result, 'home_avg_goals_per_match')) if getattr(result, 'home_avg_goals_per_match') is not None else None,
            # Away stats
            'away_matches': result.away_matches_played,
            'away_win_pct': float(getattr(result, 'away_win_pct')) if getattr(result, 'away_win_pct') is not None else None,
            'away_btts_pct': float(getattr(result, 'away_btts_pct')) if getattr(result, 'away_btts_pct') is not None else None,
            'away_clean_sheet_pct': float(getattr(result, 'away_clean_sheet_pct')) if getattr(result, 'away_clean_sheet_pct') is not None else None,
            'away_avg_goals': float(getattr(result, 'away_avg_goals_per_match')) if getattr(result, 'away_avg_goals_per_match') is not None else None,
        }
    finally:
        db.close()


def get_data_freshness() -> pd.DataFrame:
    """
    Check data freshness across all gold mart tables.
    
    Returns:
        DataFrame with table_name and last_updated timestamp
    """
    # Note: Your tables don't have updated_at columns based on the schema.
    # This function returns a placeholder. You'll need to add updated_at columns
    # to your DBT models or track freshness via a metadata table.
    
    tables = [
        'mart_team_overview',
        'mart_team_form',
        'mart_team_attack',
        'mart_team_defense',
        'mart_team_possession',
        'mart_team_discipline',
        'mart_match_predictions',
        'mart_head_to_head',
        'mart_team_season_summary'
        # 'mart_team_btts_analysis',
    ]
    
    freshness_data = []
    db = next(get_db())
    
    try:
        for table in tables:
            # Get row count as a proxy for data presence
            # In production, add an updated_at column to track actual freshness
            from sqlalchemy import text
            result = db.execute(text(f"SELECT COUNT(*) as count FROM gold.{table}"))
            count = result.scalar()
            
            freshness_data.append({
                'table_name': table,
                'row_count': count,
                'last_updated': None,  # Placeholder - add updated_at column to tables
                'status': 'OK' if count is not None and count > 0 else 'EMPTY'
            })
        
        return pd.DataFrame(freshness_data)
    finally:
        db.close()


# Helper function to get all seasons
def get_all_seasons() -> pd.DataFrame:
    """
    Get list of all available seasons.
    
    Returns:
        DataFrame with season_id, season_name, season_year
    """
    db = next(get_db())
    try:
        query = select(
            TeamOverview.season_id,
            TeamOverview.season_name,
            TeamOverview.season_year,
        ).distinct().order_by(desc(TeamOverview.season_year))
        
        result = db.execute(query).all()
        return pd.DataFrame(result, columns=['season_id', 'season_name', 'season_year'])
    finally:
        db.close()

@cache_query_result(ttl=300)  # Cache for 5 minutes
def get_upcoming_fixtures_count(tournament_id: Optional[int] = None, season_id: Optional[int] = None) -> int:
    """
    Get count of upcoming fixtures.
    
    Args:
        tournament_id: Optional tournament ID to filter by
        season_id: Optional season ID to filter by
    
    Returns:
        Count of upcoming fixtures
    """
    try:
        engine = get_engine()
        from sqlalchemy import text
        
        # Build query dynamically
        sql = """
        SELECT COUNT(*) as fixture_count
        FROM gold.mart_upcoming_fixtures
        WHERE start_timestamp > CURRENT_TIMESTAMP
          AND status_type IN ('notstarted', 'scheduled')
        """
        
        # Build params dict - don't include datetime in params
        params = {}
        
        if tournament_id is not None:
            sql += " AND tournament_id = :tournament_id"
            params['tournament_id'] = tournament_id
        
        if season_id is not None:
            sql += " AND season_id = :season_id"
            params['season_id'] = season_id
        
        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            row = result.fetchone()
            
            if row:
                return int(row[0])
            return 0
    
    except Exception as e:
        logger.error(f"Error getting upcoming fixtures count: {e}")
        return 0

@cache_query_result(ttl=600)
def get_upcoming_fixtures_list(
    tournament_id: Optional[int] = None,
    season_id: Optional[int] = None,
    limit: int = 10
) -> pd.DataFrame:
    """
    Get upcoming fixtures with team information.
    
    Args:
        tournament_id: Optional tournament ID to filter by
        season_id: Optional season ID to filter by
        limit: Maximum number of fixtures to return
    
    Returns:
        DataFrame with upcoming fixtures
    """
    try:
        engine = get_engine()
        from sqlalchemy import text
        
        sql = """
        SELECT 
            fixture_id,
            home_team_name,
            away_team_name,
            start_timestamp,
            round_number,
            tournament_name
        FROM gold.mart_upcoming_fixtures
        WHERE start_timestamp > CURRENT_TIMESTAMP
          AND status_type IN ('notstarted', 'scheduled')
        """
        
        params = {'limit': limit}
        
        if tournament_id is not None:
            sql += " AND tournament_id = :tournament_id"
            params['tournament_id'] = tournament_id
        
        if season_id is not None:
            sql += " AND season_id = :season_id"
            params['season_id'] = season_id
        
        sql += """
        ORDER BY start_timestamp ASC
        LIMIT :limit
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
            return df
    
    except Exception as e:
        logger.error(f"Error getting upcoming fixtures: {e}")
        return pd.DataFrame()