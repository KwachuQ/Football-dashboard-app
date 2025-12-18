from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import column, select, func, desc, and_, or_, text
from sqlalchemy.orm import Session
import pandas as pd
# from services.db import get_engine
# from services.cache import cache_query_result
import logging
# from src.models.team_overview import TeamOverview
# from src.models.team_form import TeamForm
# from src.models.team_season_summary import TeamSeasonSummary
# from src.models.team_attack import TeamAttack
# from src.models.team_defense import TeamDefense
# from src.models.team_possession import TeamPossession
# from src.models.team_discipline import TeamDiscipline
# from src.models.head_to_head import HeadToHead
# from src.models.upcoming_predictions import UpcomingPredictions
# from src.models.team_btts_analysis import TeamBttsAnalysis
# from src.models.league_averages import LeagueAverages
# from src.models.fact_match import FactMatch
# from services.db import get_db

logger = logging.getLogger(__name__)

def _safe_int(val: Any, default: int = 0) -> int:
    """Convert DB/ENV values safely to int, treating None/'None'/'' as default."""
    if val is None:
        return default
    s = str(val).strip()
    if s == "" or s.lower() == "none":
        return default
    try:
        return int(s)
    except Exception:
        try:
            return int(float(s))
        except Exception:
            return default

def get_upcoming_fixtures(
    season_id: Optional[int] = None,
    tournament_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
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
    from services.db import get_db

    limit = _safe_int(limit, default=50)
    if season_id is not None:
        season_id = _safe_int(season_id)
    if tournament_id is not None:
        tournament_id = _safe_int(tournament_id)
        
    db = next(get_db())
    try:
         # Default date range if not provided
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=14)

        # Convert date to datetime for SQL comparison
        # Set start to beginning of day (00:00:00)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        # Set end to end of day (23:59:59)
        end_datetime = datetime.combine(end_date, datetime.max.time())


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
            WHERE start_timestamp >= :start_datetime
              AND start_timestamp <= :end_datetime
              AND status_type IN ('notstarted', 'scheduled')
        """
        
        params: Dict[str, Any] = {'start_datetime': start_datetime,
            'end_datetime': end_datetime}
        
        if season_id:
            sql += " AND season_id = :season_id"
            params['season_id'] = _safe_int(season_id)
        
        if tournament_id:
            sql += " AND tournament_id = :tournament_id"
            params['tournament_id'] = _safe_int(tournament_id)

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
    Get team form statistics for the specified number of recent matches.
    
    Args:
        team_id: Team ID
        last_n_matches: Number of recent matches (5, 10, 15, or 20)
    
    Returns:
        Dictionary with form data for the selected window
    """
    from src.models.team_form import TeamForm
    from services.db import get_db
    
    # Convert numpy types to Python int to avoid psycopg2 adapter errors
    team_id = _safe_int(team_id)
    last_n_matches = _safe_int(last_n_matches, default=5)
    
    # Map last_n_matches to column suffix (default to 5 if unsupported)
    supported_windows = {5: '5', 10: '10', 15: '15', 20: '20'}
    suffix = supported_windows.get(last_n_matches, '5')
    
    db = next(get_db())
    try:
        # Get most recent season for this team
        subquery = select(func.max(TeamForm.season_id)).where(
            TeamForm.team_id == team_id
        ).scalar_subquery()
        
        query = select(TeamForm).where(
            and_(
                TeamForm.team_id == _safe_int(team_id),
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
                # Dynamic keys based on suffix
                'last_results': getattr(result, f'last_{suffix}_results', ''),
                'points_last': getattr(result, f'points_last_{suffix}', 0),
                'wins_last': getattr(result, f'wins_last_{suffix}', 0),
                'draws_last': getattr(result, f'draws_last_{suffix}', 0),
                'losses_last': getattr(result, f'losses_last_{suffix}', 0),
                'goals_for_last': getattr(result, f'goals_for_last_{suffix}', 0),
                'goals_against_last': getattr(result, f'goals_against_last_{suffix}', 0),
                'last_5_results_home': getattr(result, 'last_5_results_home', ''),
                'points_last_5_home': getattr(result, 'points_last_5_home', 0),
                'last_5_results_away': getattr(result, 'last_5_results_away', ''),
                'points_last_5_away': getattr(result, 'points_last_5_away', 0),
            }
        
        return {}
        
    finally:
        db.close()

def get_all_team_stats(
    team_id: int,
    season_id: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    from src.models.team_attack import TeamAttack
    from src.models.team_defense import TeamDefense
    from src.models.team_possession import TeamPossession
    from src.models.team_discipline import TeamDiscipline
    from src.models.team_overview import TeamOverview
    from src.models.team_btts_analysis import TeamBttsAnalysis
    from src.models.team_season_summary import TeamSeasonSummary
    from services.db import get_db
    """
    Get all team statistics categories in a single database call.
    
    Args:
        team_id: Team identifier
        season_id: Season to filter by (None for latest)
    
    Returns:
        Dictionary with keys 'attack', 'defense', 'possession', 'discipline', 'overview', 'btts'
        Each value is a dict of statistics for that category
    """
    db = next(get_db())
    team_id = _safe_int(team_id)
    if season_id is not None:
        season_id = _safe_int(season_id)

    try:
        from sqlalchemy import inspect

        model_map = {
            'attack': TeamAttack,
            'defense': TeamDefense,
            'possession': TeamPossession,
            'discipline': TeamDiscipline,
            'overview': TeamOverview,
            'btts': TeamBttsAnalysis,
            'season_summary': TeamSeasonSummary,
        }
        
        results = {}
        
        # If no season_id provided, get latest season once
        if not season_id:
            subquery = select(func.max(TeamOverview.season_id)).where(
                TeamOverview.team_id == team_id
            ).scalar_subquery()
            season_id = db.execute(select(subquery)).scalar()
        
        # Query all models in one transaction
        for stat_type, model in model_map.items():
            query = select(model).where(
                model.team_id == team_id,
                model.season_id == season_id
            )
            
            result = db.execute(query).scalar_one_or_none()
            
            if result:
                mapper = inspect(result.__class__)
                results[stat_type] = {
                    column.key: (
                        float(getattr(result, column.key)) 
                        if isinstance(getattr(result, column.key), Decimal)
                        else getattr(result, column.key)
                    )
                    for column in mapper.columns
                }
            else:
                results[stat_type] = {}
        
        return results
    finally:
        db.close()

def get_team_stats(
    stat_type: str,
    season_id: Optional[int] = None,
    team_id: Optional[int] = None
) -> Dict[str, Any] | pd.DataFrame:
    
    from src.models.team_attack import TeamAttack
    from src.models.team_defense import TeamDefense
    from src.models.team_possession import TeamPossession
    from src.models.team_discipline import TeamDiscipline
    from src.models.team_overview import TeamOverview
    from src.models.team_btts_analysis import TeamBttsAnalysis
    from src.models.team_season_summary import TeamSeasonSummary
    from services.db import get_db
    """
    Get team statistics by category.
    
    Args:
        stat_type: One of 'attack', 'defense', 'possession', 'discipline', 'overview'
        season_id: Season to filter by (None for latest)
        team_id: Team identifier (None for ALL teams - returns DataFrame)
    
    Returns:
        If team_id provided: Dictionary with statistics for that team
        If team_id is None: DataFrame with statistics for ALL teams in the season
    """
    if team_id is not None:
        team_id = _safe_int(team_id)
    if season_id is not None:
        season_id = _safe_int(season_id)

    db = next(get_db())
    try:
        model_map = {
            'attack': TeamAttack,
            'defense': TeamDefense,
            'possession': TeamPossession,
            'discipline': TeamDiscipline,
            'overview': TeamOverview,
            'btts': TeamBttsAnalysis,
        }
        
        if stat_type not in model_map:
            raise ValueError(f"Invalid stat_type. Must be one of: {list(model_map.keys())}")
        
        model = model_map[stat_type]
        
        # Build base query
        if team_id is not None:
            # Single team query
            query = select(model).where(model.team_id == team_id)
            
            if season_id:
                query = query.where(model.season_id == season_id)
            else:
                # Get latest season for this team
                subquery = select(func.max(model.season_id)).where(
                    model.team_id == team_id
                ).scalar_subquery()
                query = query.where(model.season_id == subquery)
            
            result = db.execute(query).scalar_one_or_none()
            
            if not result:
                return {}
            
            # Convert to dict
            from sqlalchemy import inspect
            mapper = inspect(result.__class__)
            
            return {
                column.key: (
                    float(getattr(result, column.key)) 
                    if isinstance(getattr(result, column.key), Decimal) and getattr(result, column.key) is not None
                    else (getattr(result, column.key) if getattr(result, column.key) is not None else 0)
                )
                for column in mapper.columns
            }
        
        else:
            # ALL teams query - return DataFrame
            query = select(model)
            
            if season_id:
                query = query.where(model.season_id == season_id)
            else:
                # Get latest season
                subquery = select(func.max(model.season_id)).scalar_subquery()
                query = query.where(model.season_id == subquery)
            
            results = db.execute(query).scalars().all()
            
            if not results:
                return pd.DataFrame()
            
            # Convert to DataFrame
            from sqlalchemy import inspect
            
            data = []
            for result in results:
                mapper = inspect(result.__class__)
                row = {
                    column.key: (
                        float(getattr(result, column.key)) 
                        if isinstance(getattr(result, column.key), Decimal) and getattr(result, column.key) is not None
                        else (getattr(result, column.key) if getattr(result, column.key) is not None else 0)
                    )
                    for column in mapper.columns
                }
                data.append(row)
            
            return pd.DataFrame(data)
    
    finally:
        db.close()

def get_league_averages(
    season_id: int
) -> Dict[str, Any]:
    from src.models.league_averages import LeagueAverages
    from services.db import get_db
    """
    Get league average statistics for a given season.
    
    Args:
        season_id: Season identifier
    
    Returns:
        Dictionary with league average statistics
    """
    db = next(get_db())
    try:
        query = select(LeagueAverages).where(
            LeagueAverages.season_id == season_id
        )
        
        result = db.execute(query).scalar_one_or_none()
        
        if not result:
            logger.warning(f"No league averages found for season_id: {season_id}")
            return {}
        
        from sqlalchemy import inspect
        mapper = inspect(result.__class__)
        
        return {
            column.key: (
                float(getattr(result, column.key)) 
                if isinstance(getattr(result, column.key), Decimal) and getattr(result, column.key) is not None
                else (getattr(result, column.key) if getattr(result, column.key) is not None else 0)
            )
            for column in mapper.columns
        }
    
    except Exception as e:
        logger.error(f"Error fetching league averages for season {season_id}: {e}")
        raise 
    
    finally:
        db.close()

def get_head_to_head(
    team1_id: int,
    team2_id: int,
    limit: int = 10
) -> Dict[str, Any]:
    from src.models.head_to_head import HeadToHead
    from services.db import get_db

    """Get head-to-head statistics between two teams.
    
    Args:
        team1_id: First team identifier
        team2_id: Second team identifier
        limit: Not used (kept for API compatibility)
    
    Returns:
        Dictionary with h2h stats: matches_played, wins, draws, goals, etc."""
    
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
            'over_15_pct': float(getattr(result, 'over_15_pct')) if getattr(result, 'over_15_pct') is not None else 0.0,
            'over_25_pct': float(getattr(result, 'over_25_pct')) if getattr(result, 'over_25_pct') is not None else 0.0,
            'over_35_pct': float(getattr(result, 'over_35_pct')) if getattr(result, 'over_35_pct') is not None else 0.0,
            'btts_pct': float(getattr(result, 'btts_pct')) if getattr(result, 'btts_pct') is not None else 0.0,
        }
    finally:
        db.close()

def get_h2h_results(team_id_1: int, team_id_2: int, limit: int = 5) -> pd.DataFrame:
    team_id_1 = _safe_int(team_id_1)
    team_id_2 = _safe_int(team_id_2)
    limit = _safe_int(limit, default=5)

    from src.models.fact_match import FactMatch
    from services.db import get_db
    """
    Get actual head-to-head match results between two teams from fact_match table.
    Finds all matches where these two teams played each other, regardless of home/away.
    
    Args:
        team_id_1: First team identifier (from upcoming match, typically home team)
        team_id_2: Second team identifier (from upcoming match, typically away team)
        limit: Number of most recent matches to return (default: 5)
    
    Returns:
        DataFrame with match details as they actually occurred, ordered by most recent first
    """
    db = next(get_db())
    try:
        # Query for ALL matches where these two teams played against each other
        # This includes:
        # - team_id_1 was home, team_id_2 was away
        # - team_id_1 was away, team_id_2 was home
        query = select(
            FactMatch.match_id,
            FactMatch.match_date,
            FactMatch.start_timestamp,
            FactMatch.home_team_id,
            FactMatch.home_team_name,
            FactMatch.away_team_id,
            FactMatch.away_team_name,
            FactMatch.home_score,
            FactMatch.away_score,
            FactMatch.home_score_period1,
            FactMatch.away_score_period1,
            FactMatch.winner_code,
            FactMatch.status_type,
            FactMatch.tournament_name,
            FactMatch.season_name
        ).where(
            and_(
                or_(
                    # Case 1: team_id_1 home, team_id_2 away
                    and_(
                        FactMatch.home_team_id == team_id_1,
                        FactMatch.away_team_id == team_id_2
                    ),
                    # Case 2: team_id_2 home, team_id_1 away
                    and_(
                        FactMatch.home_team_id == team_id_2,
                        FactMatch.away_team_id == team_id_1
                    )
                ),
                FactMatch.status_type == 'finished',  # Only completed matches
                FactMatch.home_score.isnot(None),  # Has score data
                FactMatch.away_score.isnot(None)
            )
        ).order_by(
            desc(FactMatch.start_timestamp)  # Most recent first
        ).limit(limit)
        
        result = db.execute(query).all()
        
        if not result:
            return pd.DataFrame()
        
        # Convert to DataFrame - keep matches as they actually occurred
        data = []
        for r in result:
            row = {
                'match_id': r.match_id,
                'match_date': r.match_date,
                'start_timestamp': r.start_timestamp,
                'home_team_id': r.home_team_id,
                'home_team': r.home_team_name,
                'away_team_id': r.away_team_id,
                'away_team': r.away_team_name,
                'home_score': r.home_score,
                'away_score': r.away_score,
                'home_score_ht': r.home_score_period1,
                'away_score_ht': r.away_score_period1,
                'result': f"{r.home_score}-{r.away_score}",
                'full_result': f"{r.home_team_name} {r.home_score}-{r.away_score} {r.away_team_name}",
                'tournament': r.tournament_name,
                'season': r.season_name,
                'winner_code': r.winner_code
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    except Exception as e:
        logger.error(f"Error fetching H2H results: {e}")
        return pd.DataFrame()
    
    finally:
        db.close()
        
def get_match_predictions(match_ids: List[int]) -> pd.DataFrame:
    
    match_ids = [ _safe_int(m) for m in match_ids ]
    """
    Get predictions for specific matches from upcoming_predictions table.
    
    Args:
        match_ids: List of match identifiers
    
    Returns:
        DataFrame with prediction details for requested matches
    """
    from src.models.upcoming_predictions import UpcomingPredictions
    from services.db import get_db

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
                'home_win_prob': float(r.home_win_probability) / 100 if r.home_win_probability is not None else None, # type: ignore
                'draw_prob': float(r.draw_probability) / 100 if r.draw_probability is not None else None, # type: ignore
                'away_win_prob': float(r.away_win_probability) / 100 if r.away_win_probability is not None else None, # type: ignore
                'predicted_home_goals': float(r.predicted_home_goals) if r.predicted_home_goals is not None else None, # type: ignore
                'predicted_away_goals': float(r.predicted_away_goals) if r.predicted_away_goals is not None else None, # type: ignore
                'match_outlook': r.match_outlook,
                'home_win_fair_odds': float(r.home_win_fair_odds) if r.home_win_fair_odds is not None else None, # type: ignore
                'draw_fair_odds': float(r.draw_fair_odds) if r.draw_fair_odds is not None else None, # type: ignore
                'away_win_fair_odds': float(r.away_win_fair_odds) if r.away_win_fair_odds is not None else None, # type: ignore
            }
            data.append(row)
        
        return pd.DataFrame(data)
    finally:
        db.close()
        
def get_league_standings(season_id: int) -> pd.DataFrame:

    season_id = _safe_int(season_id)

    """
    Get league standings (team overview sorted by points).
    
    Args:
        season_id: Season identifier
    
    Returns:
        DataFrame with team standings sorted by points descending
    """
    from src.models.team_overview import TeamOverview
    from services.db import get_db
    

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
            'total_points', 'points_per_game', 'goals_for', 'goals_against',
            'goal_difference', 'clean_sheets', 'clean_sheet_percentage'
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
    from src.models.team_btts_analysis import TeamBttsAnalysis
    from services.db import get_db

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
            'overall_avg_goals_per_match': float(getattr(result, 'overall_avg_goals_per_match')) if getattr(result, 'overall_avg_goals_per_match') is not None else None,
            'overall_avg_scored': float(getattr(result, 'overall_avg_scored')) if getattr(result, 'overall_avg_scored') is not None else None,
            'overall_avg_conceded': float(getattr(result, 'overall_avg_conceded')) if getattr(result, 'overall_avg_conceded') is not None else None,
            # Home stats
            'home_matches': result.home_matches_played,
            'home_win_pct': float(getattr(result, 'home_win_pct')) if getattr(result, 'home_win_pct') is not None else None,
            'home_btts_pct': float(getattr(result, 'home_btts_pct')) if getattr(result, 'home_btts_pct') is not None else None,
            'home_clean_sheet_pct': float(getattr(result, 'home_clean_sheet_pct')) if getattr(result, 'home_clean_sheet_pct') is not None else None,
            'home_avg_goals_per_match': float(getattr(result, 'home_avg_goals_per_match')) if getattr(result, 'home_avg_goals_per_match') is not None else None,
            'home_avg_scored': float(getattr(result, 'home_avg_scored')) if getattr(result, 'home_avg_scored') is not None else None,
            'home_avg_conceded': float(getattr(result, 'home_avg_conceded')) if getattr(result, 'home_avg_conceded') is not None else None,
            'home_avg_xg': float(getattr(result, 'home_avg_xg')) if getattr(result, 'home_avg_xg') is not None else None,
            'home_avg_xga': float(getattr(result, 'home_avg_xga')) if getattr(result, 'home_avg_xga') is not None else None,
            # Away stats
            'away_matches': result.away_matches_played,
            'away_win_pct': float(getattr(result, 'away_win_pct')) if getattr(result, 'away_win_pct') is not None else None,
            'away_btts_pct': float(getattr(result, 'away_btts_pct')) if getattr(result, 'away_btts_pct') is not None else None,
            'away_clean_sheet_pct': float(getattr(result, 'away_clean_sheet_pct')) if getattr(result, 'away_clean_sheet_pct') is not None else None,
            'away_avg_goals_per_match': float(getattr(result, 'away_avg_goals_per_match')) if getattr(result, 'away_avg_goals_per_match') is not None else None,
            'away_avg_scored': float(getattr(result, 'away_avg_scored')) if getattr(result, 'away_avg_scored') is not None else None,
            'away_avg_conceded': float(getattr(result, 'away_avg_conceded')) if getattr(result, 'away_avg_conceded') is not None else None,
            'away_avg_xg': float(getattr(result, 'away_avg_xg')) if getattr(result, 'away_avg_xg') is not None else None,
            'away_avg_xga': float(getattr(result, 'away_avg_xga')) if getattr(result, 'away_avg_xga') is not None else None,
            
            # Scoring breakdowns
            'home_scored_over_05_pct': float(getattr(result, 'home_scored_over_05_pct')) if getattr(result, 'home_scored_over_05_pct') is not None else 0.0,
            'home_scored_over_15_pct': float(getattr(result, 'home_scored_over_15_pct')) if getattr(result, 'home_scored_over_15_pct') is not None else 0.0,
            'home_scored_over_25_pct': float(getattr(result, 'home_scored_over_25_pct')) if getattr(result, 'home_scored_over_25_pct') is not None else 0.0,
            'home_scored_over_35_pct': float(getattr(result, 'home_scored_over_35_pct')) if getattr(result, 'home_scored_over_35_pct') is not None else 0.0,
            'home_failed_to_score_pct': float(getattr(result, 'home_failed_to_score_pct')) if getattr(result, 'home_failed_to_score_pct') is not None else 0.0,
            
            'away_scored_over_05_pct': float(getattr(result, 'away_scored_over_05_pct')) if getattr(result, 'away_scored_over_05_pct') is not None else 0.0,
            'away_scored_over_15_pct': float(getattr(result, 'away_scored_over_15_pct')) if getattr(result, 'away_scored_over_15_pct') is not None else 0.0,
            'away_scored_over_25_pct': float(getattr(result, 'away_scored_over_25_pct')) if getattr(result, 'away_scored_over_25_pct') is not None else 0.0,
            'away_scored_over_35_pct': float(getattr(result, 'away_scored_over_35_pct')) if getattr(result, 'away_scored_over_35_pct') is not None else 0.0,
            'away_failed_to_score_pct': float(getattr(result, 'away_failed_to_score_pct')) if getattr(result, 'away_failed_to_score_pct') is not None else 0.0,
            
            'home_conceded_over_05_pct': float(getattr(result, 'home_conceded_over_05_pct')) if getattr(result, 'home_conceded_over_05_pct') is not None else 0.0,
            'home_conceded_over_15_pct': float(getattr(result, 'home_conceded_over_15_pct')) if getattr(result, 'home_conceded_over_15_pct') is not None else 0.0,
            'home_conceded_over_25_pct': float(getattr(result, 'home_conceded_over_25_pct')) if getattr(result, 'home_conceded_over_25_pct') is not None else 0.0,
            'home_conceded_over_35_pct': float(getattr(result, 'home_conceded_over_35_pct')) if getattr(result, 'home_conceded_over_35_pct') is not None else 0.0,
            
            'away_conceded_over_05_pct': float(getattr(result, 'away_conceded_over_05_pct')) if getattr(result, 'away_conceded_over_05_pct') is not None else 0.0,
            'away_conceded_over_15_pct': float(getattr(result, 'away_conceded_over_15_pct')) if getattr(result, 'away_conceded_over_15_pct') is not None else 0.0,
            'away_conceded_over_25_pct': float(getattr(result, 'away_conceded_over_25_pct')) if getattr(result, 'away_conceded_over_25_pct') is not None else 0.0,
            'away_conceded_over_35_pct': float(getattr(result, 'away_conceded_over_35_pct')) if getattr(result, 'away_conceded_over_35_pct') is not None else 0.0,
        }
    finally:
        db.close()


# def get_data_freshness() -> pd.DataFrame:
#     """
#     Check data freshness across all gold mart tables.
    
#     Returns:
#         DataFrame with table_name and last_updated timestamp
#     """
#     # Note: Your tables don't have updated_at columns based on the schema.
#     # This function returns a placeholder. You'll need to add updated_at columns
#     # to your DBT models or track freshness via a metadata table.
#     from services.db import get_db

#     tables = [
#         'mart_team_overview',
#         'mart_team_form',
#         'mart_team_attack',
#         'mart_team_defense',
#         'mart_team_possession',
#         'mart_team_discipline',
#         'mart_match_predictions',
#         'mart_head_to_head',
#         'mart_team_season_summary',
#         'mart_team_btts_analysis'
#     ]
    
#     freshness_data = []
#     db = next(get_db())
    
#     try:
#         for table in tables:
#             # Get row count as a proxy for data presence
#             # In production, add an updated_at column to track actual freshness
#             from sqlalchemy import text
#             result = db.execute(text(f"SELECT COUNT(*) as count FROM gold.{table}"))
#             count = result.scalar()
            
#             freshness_data.append({
#                 'table_name': table,
#                 'row_count': count,
#                 'last_updated': None,  # Placeholder - add updated_at column to tables
#                 'status': 'OK' if count is not None and count > 0 else 'EMPTY'
#             })
        
#         return pd.DataFrame(freshness_data)
#     finally:
#         db.close()


# Helper function to get all seasons
def get_all_seasons() -> pd.DataFrame:
    """
    Get list of all available seasons.
    
    Returns:
        DataFrame with season_id, season_name, season_year
    """
    from src.models.team_overview import TeamOverview
    from services.db import get_db

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

from services.cache import cache_query_result

@cache_query_result(ttl=300)
def get_upcoming_fixtures_count(
    tournament_id: Optional[int] = None, 
    season_id: Optional[int] = None
) -> int:
    """Get count of upcoming fixtures with error handling."""
    from services.db import get_db
    
    if tournament_id is not None:
        tournament_id = _safe_int(tournament_id)
    if season_id is not None:
        season_id = _safe_int(season_id)
    
    db = next(get_db())
    try:
        today = datetime.now().date()
        
        sql = """
            SELECT COUNT(*) 
            FROM gold.mart_upcoming_fixtures
            WHERE start_timestamp >= :today
              AND status_type IN ('notstarted', 'scheduled')
        """
        
        # Explicitly type the params dictionary to allow mixed types
        params: Dict[str, Any] = {'today': today}
        
        if season_id is not None:  # More explicit None check
            sql += " AND season_id = :season_id"
            params['season_id'] = season_id
        
        if tournament_id is not None:  # More explicit None check
            sql += " AND tournament_id = :tournament_id"
            params['tournament_id'] = tournament_id
        
        result = db.execute(text(sql), params).scalar()
        return _safe_int(result, default=0)  # Safe default
        
    except Exception as e:
        logger.error(f"Error getting upcoming fixtures count: {e}")
        return 0  # Return 0 instead of crashing
    finally:
        db.close()

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
        from services.db import get_engine

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
    
def get_team_names() -> pd.DataFrame:
    """
    Get list of all team names.
    
    Returns:
        DataFrame with team_id and team_name
    """
    from src.models.team_overview import TeamOverview
    from services.db import get_db

    db = next(get_db())
    try:
        query = select(
            TeamOverview.team_id,
            TeamOverview.team_name
        ).distinct().order_by(TeamOverview.team_name)
        
        result = db.execute(query).all()
        return pd.DataFrame(result, columns=['team_id', 'team_name'])
    finally:
        db.close()