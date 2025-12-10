"""
Data transformation and enrichment utilities.

This module provides functions for:
- Rolling averages and moving windows
- Home/away performance splits
- Form indicators and sequences
- Strength of schedule adjustments
- Performance normalization and ranking
"""

from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from scipy.stats import percentileofscore

logger = logging.getLogger(__name__)


# ============================================================================
# Rolling Averages and Windows
# ============================================================================

def calculate_rolling_average(
    df: pd.DataFrame,
    column: str,
    window: int = 5,
    min_periods: int = 1,
    group_by: Optional[str] = None
) -> pd.Series:
    """
    Calculate rolling average for a specified column.
    
    Args:
        df: DataFrame with data
        column: Column name to calculate rolling average for
        window: Rolling window size (default: 5)
        min_periods: Minimum observations in window (default: 1)
        group_by: Optional column to group by (e.g., 'team_id')
    
    Returns:
        Series with rolling averages
    
    Example:
        df['goals_rolling_5'] = calculate_rolling_average(df, 'goals_scored', window=5)
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame")
    
    if group_by:
        return df.groupby(group_by)[column].transform(
            lambda x: x.rolling(window=window, min_periods=min_periods).mean()
        )
    else:
        return df[column].rolling(window=window, min_periods=min_periods).mean()


def calculate_rolling_sum(
    df: pd.DataFrame,
    column: str,
    window: int = 5,
    min_periods: int = 1,
    group_by: Optional[str] = None
) -> pd.Series:
    """
    Calculate rolling sum for a specified column.
    
    Args:
        df: DataFrame with data
        column: Column name to calculate rolling sum for
        window: Rolling window size (default: 5)
        min_periods: Minimum observations in window (default: 1)
        group_by: Optional column to group by (e.g., 'team_id')
    
    Returns:
        Series with rolling sums
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame")
    
    if group_by:
        return df.groupby(group_by)[column].transform(
            lambda x: x.rolling(window=window, min_periods=min_periods).sum()
        )
    else:
        return df[column].rolling(window=window, min_periods=min_periods).sum()


def calculate_ewma(
    df: pd.DataFrame,
    column: str,
    span: int = 5,
    group_by: Optional[str] = None
) -> pd.Series:
    """
    Calculate exponentially weighted moving average.
    
    Recent values are weighted more heavily than older values.
    
    Args:
        df: DataFrame with data
        column: Column name to calculate EWMA for
        span: Span for exponential weighting (default: 5)
        group_by: Optional column to group by
    
    Returns:
        Series with exponentially weighted averages
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame")
    
    if group_by:
        return df.groupby(group_by)[column].transform(
            lambda x: x.ewm(span=span, adjust=False).mean()
        )
    else:
        return df[column].ewm(span=span, adjust=False).mean()


# ============================================================================
# Home/Away Splits
# ============================================================================

def split_home_away(
    df: pd.DataFrame,
    team_id: int,
    home_column: str = 'home_team_id',
    away_column: str = 'away_team_id'
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split DataFrame into home and away matches for a specific team.
    
    Args:
        df: DataFrame with match data
        team_id: Team ID to filter for
        home_column: Column name for home team ID
        away_column: Column name for away team ID
    
    Returns:
        Tuple of (home_matches_df, away_matches_df)
    
    Example:
        home_df, away_df = split_home_away(matches_df, team_id=123)
    """
    home_matches = df[df[home_column] == team_id].copy()
    away_matches = df[df[away_column] == team_id].copy()
    
    return home_matches, away_matches


def calculate_home_away_stats(
    df: pd.DataFrame,
    team_id: int,
    metrics: List[str],
    home_column: str = 'home_team_id',
    away_column: str = 'away_team_id'
) -> Dict[str, Dict[str, float]]:
    """
    Calculate statistics separately for home and away matches.
    
    Args:
        df: DataFrame with match data
        team_id: Team ID to analyze
        metrics: List of metric columns to calculate stats for
        home_column: Column name for home team ID
        away_column: Column name for away team ID
    
    Returns:
        Dictionary with home and away statistics
        
    Example:
        stats = calculate_home_away_stats(
            df, team_id=123, 
            metrics=['goals_scored', 'goals_conceded', 'points']
        )
        # Returns: {'home': {'goals_scored': 2.1, ...}, 'away': {...}}
    """
    home_df, away_df = split_home_away(df, team_id, home_column, away_column)
    
    result = {
        'home': {},
        'away': {},
        'differential': {}
    }
    
    for metric in metrics:
        if metric not in df.columns:
            logger.warning(f"Metric '{metric}' not found in DataFrame")
            continue
        
        home_avg = home_df[metric].mean() if len(home_df) > 0 else 0.0
        away_avg = away_df[metric].mean() if len(away_df) > 0 else 0.0
        
        result['home'][metric] = round(home_avg, 2)
        result['away'][metric] = round(away_avg, 2)
        result['differential'][metric] = round(home_avg - away_avg, 2)
    
    # Add match counts
    result['home']['matches'] = len(home_df)
    result['away']['matches'] = len(away_df)
    
    return result


# ============================================================================
# Form Indicators
# ============================================================================

def calculate_form_sequence(
    results: List[str],
    max_length: int = 5
) -> str:
    """
    Convert list of results into form sequence string.
    
    Args:
        results: List of match results ('W', 'D', 'L')
        max_length: Maximum length of sequence to return
    
    Returns:
        Form sequence string (e.g., 'WWDLW')
    
    Example:
        form = calculate_form_sequence(['W', 'W', 'D', 'L', 'W'])
        # Returns: 'WWDLW'
    """
    if not results:
        return ''
    
    # Take most recent matches up to max_length
    recent = results[-max_length:]
    return ''.join(recent)


def calculate_form_score(
    results: List[str],
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate weighted form score from match results.
    
    More recent matches are weighted more heavily.
    
    Args:
        results: List of match results ('W', 'D', 'L')
        weights: Optional custom weights for W/D/L (default: W=3, D=1, L=0)
    
    Returns:
        Weighted form score (0-100 scale)
    
    Example:
        score = calculate_form_score(['W', 'W', 'D', 'L', 'W'])
        # Returns: 65.5 (weighted average, recent matches worth more)
    """
    if not results:
        return 0.0
    
    # Default weights (same as points)
    if weights is None:
        weights = {'W': 3, 'D': 1, 'L': 0}
    
    # Exponential decay weights (most recent = 1.0, oldest = 0.5)
    n = len(results)
    time_weights = [0.5 + 0.5 * (i / max(n - 1, 1)) for i in range(n)]
    
    weighted_sum = 0.0
    weight_total = 0.0
    
    for result, time_weight in zip(results, time_weights):
        result_weight = weights.get(result, 0)
        weighted_sum += result_weight * time_weight
        weight_total += time_weight
    
    if weight_total == 0:
        return 0.0
    
    # Scale to 0-100
    max_possible = 3.0  # Maximum points per match
    score = (weighted_sum / weight_total / max_possible) * 100
    
    return round(score, 2)


def calculate_win_rate(
    results: List[str],
    result_type: str = 'W'
) -> float:
    """
    Calculate win/draw/loss rate from results.
    
    Args:
        results: List of match results ('W', 'D', 'L')
        result_type: Type to calculate rate for ('W', 'D', or 'L')
    
    Returns:
        Rate as percentage (0-100)
    
    Example:
        win_rate = calculate_win_rate(['W', 'W', 'D', 'L', 'W'], 'W')
        # Returns: 60.0
    """
    if not results:
        return 0.0
    
    count = sum(1 for r in results if r == result_type)
    rate = (count / len(results)) * 100
    
    return round(rate, 2)


def get_current_streak(results: List[str]) -> Dict[str, Optional[str] | int]:
    """
    Get current winning/drawing/losing streak.
    
    Args:
        results: List of match results ('W', 'D', 'L'), oldest to newest
    
    Returns:
        Dictionary with streak type and length
    
    Example:
        streak = get_current_streak(['L', 'W', 'W', 'W'])
        # Returns: {'type': 'W', 'length': 3}
    """
    if not results:
        return {'type': None, 'length': 0}
    
    # Start from most recent result
    current_result = results[-1]
    streak_length = 1
    
    # Count consecutive same results going backwards
    for i in range(len(results) - 2, -1, -1):
        if results[i] == current_result:
            streak_length += 1
        else:
            break
    
    return {
        'type': current_result,
        'length': streak_length
    }


# ============================================================================
# Strength of Schedule
# ============================================================================

def calculate_opponent_strength(
    df: pd.DataFrame,
    team_id: int,
    opponent_metric: str = 'league_position',
    home_column: str = 'home_team_id',
    away_column: str = 'away_team_id',
    opponent_home_column: str = 'away_team_id',
    opponent_away_column: str = 'home_team_id'
) -> pd.Series:
    """
    Calculate average opponent strength for each match.
    
    Args:
        df: DataFrame with match data including opponent metrics
        team_id: Team ID to analyze
        opponent_metric: Metric to use for opponent strength
        home_column: Column for home team ID
        away_column: Column for away team ID
        opponent_home_column: Column for opponent (when team is home)
        opponent_away_column: Column for opponent (when team is away)
    
    Returns:
        Series with opponent strength values
    """
    # Create opponent strength column
    opponent_strength = pd.Series(index=df.index, dtype=float)
    
    # For home matches
    home_mask = df[home_column] == team_id
    opponent_strength[home_mask] = df.loc[home_mask, f'{opponent_metric}_away']
    
    # For away matches
    away_mask = df[away_column] == team_id
    opponent_strength[away_mask] = df.loc[away_mask, f'{opponent_metric}_home']
    
    return opponent_strength


def adjust_for_sos(
    df: pd.DataFrame,
    metric_column: str,
    opponent_strength_column: str,
    league_average: Optional[float] = None
) -> pd.Series:
    """
    Adjust performance metric for strength of schedule.
    
    Better performance against stronger opponents is weighted higher.
    
    Args:
        df: DataFrame with performance data
        metric_column: Column with raw performance metric
        opponent_strength_column: Column with opponent strength values
        league_average: Average opponent strength (computed if not provided)
    
    Returns:
        Series with SOS-adjusted metric
    
    Example:
        df['goals_sos_adjusted'] = adjust_for_sos(
            df, 'goals_scored', 'opponent_rating'
        )
    """
    if league_average is None:
        league_average = df[opponent_strength_column].mean()
    
    if league_average == 0:
        return df[metric_column]
    
    # Adjustment factor: opponent_strength / league_average
    adjustment = df[opponent_strength_column] / league_average
    
    # Apply adjustment
    adjusted = df[metric_column] * adjustment
    
    return adjusted


def calculate_sos_rating(
    df: pd.DataFrame,
    team_id: int,
    opponent_metric: str = 'points_per_game',
    home_column: str = 'home_team_id',
    away_column: str = 'away_team_id'
) -> float:
    """
    Calculate overall strength of schedule rating for a team.
    
    Args:
        df: DataFrame with match data
        team_id: Team ID to analyze
        opponent_metric: Metric to measure opponent strength
        home_column: Column for home team ID
        away_column: Column for away team ID
    
    Returns:
        SOS rating (average opponent strength, 0-100 scale)
    
    Example:
        sos = calculate_sos_rating(matches_df, team_id=123)
        # Returns: 65.5 (opponents averaged 65.5% of max strength)
    """
    # Filter matches for this team
    team_matches = df[
        (df[home_column] == team_id) | (df[away_column] == team_id)
    ].copy()
    
    if len(team_matches) == 0:
        return 0.0
    
    # Get opponent strengths
    opponent_strengths = calculate_opponent_strength(
        team_matches, team_id, opponent_metric,
        home_column, away_column
    )
    
    # Calculate average
    avg_sos = opponent_strengths.mean()
    
    return round(avg_sos, 2)


# ============================================================================
# Performance Normalization
# ============================================================================

def normalize_metrics(
    df: pd.DataFrame,
    columns: List[str],
    scale: int = 100,
    method: str = 'minmax'
) -> pd.DataFrame:
    """
    Normalize metrics to a common scale.
    
    Args:
        df: DataFrame with metrics to normalize
        columns: List of column names to normalize
        scale: Target scale (default: 0-100)
        method: Normalization method ('minmax' or 'zscore')
    
    Returns:
        DataFrame with normalized columns (original + normalized versions)
    
    Example:
        df = normalize_metrics(df, ['goals', 'assists'], scale=100)
        # Adds columns: goals_normalized, assists_normalized
    """
    result = df.copy()
    
    for column in columns:
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found in DataFrame")
            continue
        
        if method == 'minmax':
            # Min-Max normalization
            col_min = df[column].min()
            col_max = df[column].max()
            
            if col_max - col_min == 0:
                result[f'{column}_normalized'] = scale / 2
            else:
                normalized = ((df[column] - col_min) / (col_max - col_min)) * scale
                result[f'{column}_normalized'] = normalized.round(2)
        
        elif method == 'zscore':
            # Z-score normalization
            mean = df[column].mean()
            std = df[column].std()
            
            if std == 0:
                result[f'{column}_normalized'] = scale / 2
            else:
                # Scale z-scores to 0-100 (assuming +/- 3 std dev covers most)
                normalized = ((df[column] - mean) / std + 3) * (scale / 6)
                result[f'{column}_normalized'] = normalized.clip(0, scale).round(2)
        
        else:
            raise ValueError(f"Unknown normalization method: {method}")
    
    return result


def calculate_percentile_rank(
    df: pd.DataFrame,
    column: str,
    ascending: bool = False
) -> pd.Series:
    """
    Calculate percentile rank for a column.
    
    Args:
        df: DataFrame with data
        column: Column to rank
        ascending: If True, lower values get higher ranks
    
    Returns:
        Series with percentile ranks (0-100)
    
    Example:
        df['goals_percentile'] = calculate_percentile_rank(df, 'goals_scored')
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame")
    
    rank = df[column].rank(ascending=ascending, pct=True) * 100
    
    return rank.round(2)


# ============================================================================
# Composite Metrics
# ============================================================================

def calculate_composite_score(
    df: pd.DataFrame,
    metrics: Dict[str, float]
) -> pd.Series:
    """
    Calculate weighted composite score from multiple metrics.
    
    Args:
        df: DataFrame with metric columns
        metrics: Dictionary mapping column names to weights
    
    Returns:
        Series with composite scores
    
    Example:
        score = calculate_composite_score(df, {
            'goals_scored': 0.4,
            'goals_conceded': 0.3,
            'possession': 0.3
        })
    """
    total_weight = sum(metrics.values())
    
    if total_weight == 0:
        raise ValueError("Total weight cannot be zero")
    
    composite = pd.Series(0.0, index=df.index)
    
    for column, weight in metrics.items():
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found in DataFrame")
            continue
        
        # Normalize weight
        normalized_weight = weight / total_weight
        composite += df[column] * normalized_weight
    
    return composite.round(2)


# ============================================================================
# Utility Functions
# ============================================================================

def add_match_result(
    df: pd.DataFrame,
    team_id: int,
    goals_for_col: str = 'goals_for',
    goals_against_col: str = 'goals_against'
) -> pd.Series:
    """
    Add match result column (W/D/L) for a specific team.
    
    Args:
        df: DataFrame with match data
        team_id: Team ID to determine results for
        goals_for_col: Column name for goals scored by team
        goals_against_col: Column name for goals conceded by team
    
    Returns:
        Series with match results ('W', 'D', 'L')
    """
    results = []
    
    for _, row in df.iterrows():
        goals_for = row[goals_for_col]
        goals_against = row[goals_against_col]
        
        if goals_for > goals_against:
            results.append('W')
        elif goals_for < goals_against:
            results.append('L')
        else:
            results.append('D')
    
    return pd.Series(results, index=df.index)


def calculate_points(results: List[str]) -> int:
    """
    Calculate total points from match results.
    
    Args:
        results: List of match results ('W', 'D', 'L')
    
    Returns:
        Total points (W=3, D=1, L=0)
    """
    points_map = {'W': 3, 'D': 1, 'L': 0}
    return sum(points_map.get(r, 0) for r in results)


def calculate_goal_difference(
    goals_for: List[int],
    goals_against: List[int]
) -> int:
    """
    Calculate total goal difference.
    
    Args:
        goals_for: List of goals scored
        goals_against: List of goals conceded
    
    Returns:
        Total goal difference
    """
    return sum(goals_for) - sum(goals_against)

# ============================================================================
# League Statistics and Percentiles
# ============================================================================

def calculate_league_stats_and_percentiles(
    all_teams_df: pd.DataFrame,
    team_stats: Dict[str, Any],
    exclude_cols: Optional[List[str]] = None
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Calculate league-wide statistics and percentiles for a specific team.
    
    Args:
        all_teams_df: DataFrame with statistics for all teams in the league
        team_stats: Dictionary with statistics for the specific team
        exclude_cols: List of columns to exclude from calculations
    
    Returns:
        Tuple of (league_averages, percentiles)
    """
    if exclude_cols is None:
        exclude_cols = ['team_id', 'team_name', 'season_id', 'season_name', 'season_year']
    
    # Get numeric columns only
    numeric_cols = all_teams_df.select_dtypes(include=[np.number]).columns
    numeric_cols = [col for col in numeric_cols if col not in exclude_cols]
    
    # Calculate league averages
    league_avg = all_teams_df[numeric_cols].mean().to_dict()
    
    # Calculate percentiles for each metric
    percentiles = {}
    for col in numeric_cols:
        if col in team_stats and pd.notna(team_stats[col]):
            try:
                percentile = percentileofscore(
                    all_teams_df[col].dropna(), 
                    team_stats[col], 
                    kind='rank'
                )
                percentiles[col] = round(float(percentile), 1)
            except Exception as e:
                logger.warning(f"Failed to calculate percentile for {col}: {e}")
                percentiles[col] = None
        else:
            percentiles[col] = None
    
    return league_avg, percentiles


def calculate_radar_scales(
    all_teams_df: pd.DataFrame,
    metrics: List[str],
    padding_pct: float = 0.1
) -> Dict[str, Tuple[float, float]]:
    """
    Calculate individual min/max scales for radar chart metrics.
    """
    scales = {}
    
    for metric in metrics:
        if metric not in all_teams_df.columns:
            logger.warning(f"Metric '{metric}' not found in DataFrame")
            scales[metric] = (0, 1)
            continue
        
        values = all_teams_df[metric].dropna()
        
        if len(values) == 0:
            scales[metric] = (0, 1)
            continue
        
        min_val = float(values.min())
        max_val = float(values.max())
        
        range_val = max_val - min_val
        if range_val == 0:
            min_val = min_val * 0.9 if min_val > 0 else -0.5
            max_val = max_val * 1.1 if max_val > 0 else 0.5
        else:
            padding = range_val * padding_pct
            min_val = max(0, min_val - padding)
            max_val = max_val + padding
        
        scales[metric] = (round(min_val, 2), round(max_val, 2))
    
    return scales


def normalize_for_radar(
    values: List[float],
    scales: Dict[str, Tuple[float, float]],
    metrics: List[str]
) -> List[float]:
    """
    Normalize values to 0-1 scale for radar chart.
    """
    normalized = []
    
    for value, metric in zip(values, metrics):
        if metric not in scales:
            normalized.append(0.5)
            continue
        
        min_val, max_val = scales[metric]
        
        if max_val - min_val == 0:
            normalized.append(0.5)
        else:
            norm_val = (value - min_val) / (max_val - min_val)
            norm_val = max(0, min(1, norm_val))
            normalized.append(round(norm_val, 3))
    
    return normalized


def get_all_teams_stats(
    season_id: int,
    stat_type: str
) -> pd.DataFrame:
    """
    Fetch all teams statistics for a given season and stat type.
    
    Args:
        season_id: Season ID to filter by
        stat_type: Type of statistics ('attack', 'defense', 'possession', 'discipline')
    
    Returns:
        DataFrame with all teams statistics
    """
    from services.db import get_engine
    
    table_map = {
        'attack': 'mart_team_attack',
        'defense': 'mart_team_defense',
        'possession': 'mart_team_possession',
        'discipline': 'mart_team_discipline'
    }
    
    table_name = table_map.get(stat_type)
    if not table_name:
        raise ValueError(f"Invalid stat_type: {stat_type}")
    
    query = f"""
        SELECT * 
        FROM gold.{table_name}
        WHERE season_id = {season_id}
    """
    
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    return df
