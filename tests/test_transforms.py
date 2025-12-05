"""Tests for data transformation utilities."""

import pytest
import pandas as pd
import numpy as np
from services.transforms import (
    calculate_rolling_average,
    calculate_rolling_sum,
    calculate_ewma,
    split_home_away,
    calculate_home_away_stats,
    calculate_form_sequence,
    calculate_form_score,
    calculate_win_rate,
    get_current_streak,
    calculate_sos_rating,
    normalize_metrics,
    calculate_percentile_rank,
    calculate_composite_score,
    add_match_result,
    calculate_points,
    calculate_goal_difference,
)


class TestRollingAverages:
    """Test rolling average calculations."""
    
    def test_rolling_average_basic(self):
        """Test basic rolling average calculation."""
        df = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
        result = calculate_rolling_average(df, 'value', window=3)
        
        expected = pd.Series([1.0, 1.5, 2.0, 3.0, 4.0], name='value')  # Add name='value'
        pd.testing.assert_series_equal(result, expected)
    
    def test_rolling_average_with_groupby(self):
        """Test rolling average with grouping."""
        df = pd.DataFrame({
            'team_id': [1, 1, 1, 2, 2, 2],
            'goals': [1, 2, 3, 4, 5, 6]
        })
        result = calculate_rolling_average(df, 'goals', window=2, group_by='team_id')
        
        # Each team should have separate rolling averages
        assert result[0] == 1.0  # Team 1, first match
        assert result[1] == 1.5  # Team 1, avg of 1,2
        assert result[3] == 4.0  # Team 2, first match
        assert result[4] == 4.5  # Team 2, avg of 4,5
    
    def test_rolling_sum_basic(self):
        """Test rolling sum calculation."""
        df = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
        result = calculate_rolling_sum(df, 'value', window=3)
        
        expected = pd.Series([1.0, 3.0, 6.0, 9.0, 12.0], name='value')  # Add name='value'
        pd.testing.assert_series_equal(result, expected)

    def test_ewma_basic(self):
        """Test exponentially weighted moving average."""
        df = pd.DataFrame({'value': [1, 2, 3, 4, 5]})
        result = calculate_ewma(df, 'value', span=3)
        
        # EWMA should weight recent values more
        assert result.iloc[-1] > result.iloc[0]


class TestHomeAwaySplits:
    """Test home/away split functionality."""
    
    @pytest.fixture
    def match_data(self):
        """Sample match data."""
        return pd.DataFrame({
            'home_team_id': [1, 2, 1, 3, 1],
            'away_team_id': [2, 1, 3, 1, 2],
            'home_goals': [2, 1, 3, 0, 1],
            'away_goals': [1, 2, 1, 2, 1]
        })
    
    def test_split_home_away(self, match_data):
        """Test splitting matches into home and away."""
        home_df, away_df = split_home_away(match_data, team_id=1)
        
        assert len(home_df) == 3  # Team 1 played 3 home matches
        assert len(away_df) == 2  # Team 1 played 2 away matches
    
    def test_calculate_home_away_stats(self, match_data):
        """Test calculating home/away statistics."""
        # Add points column
        match_data['points'] = [3, 0, 3, 3, 1]
        
        stats = calculate_home_away_stats(
            match_data,
            team_id=1,
            metrics=['points', 'home_goals']
        )
        
        assert 'home' in stats
        assert 'away' in stats
        assert 'differential' in stats
        assert stats['home']['matches'] == 3
        assert stats['away']['matches'] == 2


class TestFormIndicators:
    """Test form calculation functions."""
    
    def test_calculate_form_sequence(self):
        """Test form sequence generation."""
        results = ['W', 'W', 'D', 'L', 'W']
        sequence = calculate_form_sequence(results, max_length=5)
        
        assert sequence == 'WWDLW'
    
    def test_calculate_form_sequence_limited(self):
        """Test form sequence with limit."""
        results = ['W', 'W', 'D', 'L', 'W', 'W']
        sequence = calculate_form_sequence(results, max_length=3)
        
        assert sequence == 'LWW'  # Last 3 only
    
    def test_calculate_form_score_all_wins(self):
        """Test form score for all wins."""
        results = ['W', 'W', 'W', 'W', 'W']
        score = calculate_form_score(results)
        
        assert score == 100.0  # Perfect score
    
    def test_calculate_form_score_all_losses(self):
        """Test form score for all losses."""
        results = ['L', 'L', 'L', 'L', 'L']
        score = calculate_form_score(results)
        
        assert score == 0.0  # Worst score
    
    def test_calculate_form_score_mixed(self):
        """Test form score for mixed results."""
        results = ['W', 'D', 'L', 'W', 'W']
        score = calculate_form_score(results)
        
        # Should be between 0 and 100
        assert 0 < score < 100
    
    def test_calculate_win_rate(self):
        """Test win rate calculation."""
        results = ['W', 'W', 'D', 'L', 'W']
        win_rate = calculate_win_rate(results, 'W')
        
        assert win_rate == 60.0  # 3 wins out of 5
    
    def test_get_current_streak_winning(self):
        """Test current winning streak."""
        results = ['L', 'W', 'W', 'W']
        streak = get_current_streak(results)
        
        assert streak['type'] == 'W'
        assert streak['length'] == 3
    
    def test_get_current_streak_single(self):
        """Test streak of one match."""
        results = ['W', 'W', 'L']
        streak = get_current_streak(results)
        
        assert streak['type'] == 'L'
        assert streak['length'] == 1


class TestNormalization:
    """Test metric normalization functions."""
    
    def test_normalize_metrics_minmax(self):
        """Test min-max normalization."""
        df = pd.DataFrame({'goals': [0, 5, 10]})
        result = normalize_metrics(df, ['goals'], scale=100, method='minmax')
        
        assert 'goals_normalized' in result.columns
        assert result['goals_normalized'].iloc[0] == 0.0
        assert result['goals_normalized'].iloc[2] == 100.0
        assert result['goals_normalized'].iloc[1] == 50.0
    
    def test_normalize_metrics_zscore(self):
        """Test z-score normalization."""
        df = pd.DataFrame({'goals': [10, 20, 30, 40, 50]})
        result = normalize_metrics(df, ['goals'], scale=100, method='zscore')
        
        assert 'goals_normalized' in result.columns
        # Mean should be around 50
        assert 40 < result['goals_normalized'].mean() < 60
    
        def test_calculate_percentile_rank(self):
            """Test percentile rank calculation."""
            df = pd.DataFrame({'score': [10, 20, 30, 40, 50]})
            ranks = calculate_percentile_rank(df, 'score', ascending=True)
            
            # With ascending=True, lower values get higher percentiles
            assert ranks.iloc[0] == 100.0  # Lowest value (10) gets 100
            assert ranks.iloc[4] == 0.0    # Highest value (50) gets 0

class TestCompositeMetrics:
    """Test composite score calculations."""
    
    def test_calculate_composite_score(self):
        """Test weighted composite score."""
        df = pd.DataFrame({
            'attack': [80, 70, 60],
            'defense': [60, 70, 80]
        })
        
        score = calculate_composite_score(df, {
            'attack': 0.6,
            'defense': 0.4
        })
        
        # First row: 80*0.6 + 60*0.4 = 72
        assert score.iloc[0] == 72.0


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_add_match_result(self):
        """Test match result determination."""
        df = pd.DataFrame({
            'goals_for': [3, 1, 2],
            'goals_against': [1, 1, 3]
        })
        
        results = add_match_result(df, team_id=1)
        
        assert results.iloc[0] == 'W'  # 3-1 win
        assert results.iloc[1] == 'D'  # 1-1 draw
        assert results.iloc[2] == 'L'  # 2-3 loss
    
    def test_calculate_points(self):
        """Test points calculation."""
        results = ['W', 'D', 'L', 'W', 'W']
        points = calculate_points(results)
        
        assert points == 10  # 3+1+0+3+3
    
    def test_calculate_goal_difference(self):
        """Test goal difference calculation."""
        gd = calculate_goal_difference([3, 2, 1], [1, 2, 3])
        
        assert gd == 0  # (3+2+1) - (1+2+3) = 0