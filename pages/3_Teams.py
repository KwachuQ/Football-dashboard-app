"""
pages/3_Teams.py
Team statistics and performance analysis page
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any
import logging
import math
import matplotlib.pyplot as plt
from mplsoccer import Radar
from matplotlib import font_manager
import warnings


# Import existing components and services
from components.filters import team_selector, home_away_toggle, get_active_league_from_config
from services.queries import get_all_seasons, get_league_standings, get_team_form, get_all_team_stats, get_league_averages, get_team_stats
from services.transforms import (
    calculate_win_rate, 
    calculate_form_sequence,
    calculate_league_stats_and_percentiles,
    calculate_radar_scales,
    normalize_for_radar
)
from services.db import get_engine

# Configure logging
logger = logging.getLogger(__name__)

# Hide default Streamlit sidebar first item (menu)
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] li:first-child {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Page configuration
st.set_page_config(
    page_title="Teams - Football Analytics",
    page_icon="⚽",
    layout="wide"
)

#Compact global styling
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    h1, h2, h3 {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_get(data: Optional[Dict[str, Any]], key: str, default: Any = 0) -> Any:
    """Safely get value from dict, handling None and missing keys."""
    if data is None:
        return default
    return data.get(key, default)

def format_percentage(value: Optional[float]) -> str:
    """Format float as percentage string."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"

def format_number(value: Optional[float], decimals: int = 2) -> str:
    """Format number with specified decimals."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"

def parse_form_results(form_string: Optional[str], max_length: int = 5) -> list:
    """Parse form string (e.g., 'WWDLW') into list of results."""
    if not form_string:
        return []
    results = list(form_string[:max_length])
    return results

def results_to_points(results: list) -> list:
    """Convert W/D/L results to points [3, 1, 0]."""
    points_map = {'W': 3, 'D': 1, 'L': 0}
    return [points_map.get(r, 0) for r in results]

def prepare_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare DataFrame for Streamlit display by converting all columns to strings.
    This prevents Arrow serialization issues with mixed types.
    """
    return df.astype(str)

def draw_team_radar(
    team_stats: dict,
    all_teams_df: pd.DataFrame,
    percentiles: dict,
    league_avg: dict,
    team_name: str,
    metric_config: list,
    radar_color: str = '#fbbf24',
    radar_edge_color: str = '#f59e0b'
):
    """
    Draw a mplsoccer radar chart for team performance.
    
    Args:
        team_stats: Dictionary of team statistics
        all_teams_df: DataFrame with all teams' stats for the league
        percentiles: Dictionary of percentile rankings
        league_avg: Dictionary of league averages
        team_name: Name of the team
        metric_config: List of tuples (metric_key, display_label)
        radar_color: Fill color for team radar (default: gold)
        radar_edge_color: Edge color for team radar (default: orange)
    
    Returns:
        matplotlib figure object
    """
    metrics = [m[0] for m in metric_config]
    labels = [m[1] for m in metric_config]
    
    # Get actual values
    team_values = [float(safe_get(team_stats, m, 0)) for m in metrics]
    league_values = [float(safe_get(league_avg, m, 0)) for m in metrics]
    
    # Calculate min/max boundaries for radar (0 to 95th percentile)
    low = []
    high = []
    for metric in metrics:
        metric_values = all_teams_df[metric].dropna()
        low.append(0) 
        high_val = float(metric_values.quantile(0.95))
        high.append(max(high_val, 0.01))  # Prevent division by zero
    
    # Initialize Radar
    radar = Radar(
        params=labels,
        min_range=low,
        max_range=high,
        num_rings=4, 
        ring_width=1,
        center_circle_radius=0
    )
    
    # Create figure
    fig, ax = plt.subplots(figsize=(4.50, 4.50), facecolor='white', dpi=200)
    
    # Setup radar axis
    radar.setup_axis(ax=ax, facecolor='white')
    
    # Suppress matplotlib warnings
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=RuntimeWarning)
        
        # Draw concentric circles (baseline rings)
        rings_inner = radar.draw_circles(
            ax=ax, 
            facecolor='#f3f4f6',  # Light gray
            edgecolor='#d1d5db',  # Medium gray border
            lw=1.8,
            alpha=0.4
        )
        
        # League Average (background) and Team Performance (foreground)
        league_output = radar.draw_radar_compare(
            league_values,
            team_values,
            ax=ax,
            kwargs_radar={
                'facecolor': '#9ca3af', 
                'alpha': 0.25, 
                'edgecolor': '#6b7280', 
                'linewidth': 2.4
            },
            kwargs_compare={
                'facecolor': radar_color, 
                'alpha': 0.5, 
                'edgecolor': radar_edge_color, 
                'linewidth': 3.6
            }
        )
    
    # Get vertices for markers
    radar_poly1, radar_poly2, vertices1, vertices2 = league_output
    
    # Calculate percentiles for team performance
    team_percentiles = [float(safe_get(percentiles, m, 50)) for m in metrics]
    
    # Add markers for team radar
    for vertex, pct in zip(vertices2, team_percentiles):
        # Use lighter shade if above 60th percentile
        color = radar_color if pct >= 60 else radar_edge_color
        ax.scatter(
            vertex[0], vertex[1],
            c=color,
            s=35,
            edgecolors='white',
            linewidths=1.5,
            zorder=5,
            marker='o'
        )
    
    # Draw range labels (scale values)
    range_labels = radar.draw_range_labels(
        ax=ax,
        fontsize=6,
        color="#8b6469",
        fontweight='normal'
    )
    
    # Draw parameter labels (metric names)
    param_labels = radar.draw_param_labels(
        ax=ax,
        fontsize=9.5,
        color='#0f172a',
        fontweight='bold'
    )
    
    plt.tight_layout(pad=0.65)
    
    return fig

def create_stats_table(metrics_config, team_stats, league_avg, percentiles, inverted_metrics=None):
    """
    Create a statistics table DataFrame.
    
    Args:
        metrics_config: List of tuples (metric_key, display_name, decimals)
        team_stats: Dictionary of team statistics
        league_avg: Dictionary of league averages
        percentiles: Dictionary of percentile values
        inverted_metrics: List of metric keys where lower is better
    
    Returns:
        Prepared DataFrame ready for display
    """
    inverted_metrics = inverted_metrics or []
    
    # Create mapping from metric_key to display_name
    inverted_names = [
        name for key, name, _ in metrics_config if key in inverted_metrics
    ]
    
    data = {
        'Metric': [name for _, name, _ in metrics_config],
        'Team': [
            format_number(safe_get(team_stats, key), decimals) 
            if not key.endswith('_pct') 
            else format_percentage(safe_get(team_stats, key))
            for key, _, decimals in metrics_config
        ],
        'League': [
            format_number(safe_get(league_avg, key), decimals) 
            if not key.endswith('_pct') 
            else format_percentage(safe_get(league_avg, key))
            for key, _, decimals in metrics_config
        ],
        'Percentile': [
            f"{int(100 - percentiles.get(key, 100)) if key in inverted_metrics else int(percentiles.get(key, 0))}%" 
            if percentiles.get(key) is not None else '-'
            for key, _, _ in metrics_config
        ]
    }
    
    df = pd.DataFrame(data)
    df_prepared = prepare_dataframe_for_display(df)
    
    # Store inverted metric names as attribute for styling
    df_prepared.attrs['inverted_names'] = inverted_names
    
    return df_prepared

def style_table(row, inverted_metrics=None):
    """
    Style table rows with color coding.
    
    Args:
        row: DataFrame row
        inverted_metrics: List of metric names where lower is better
    
    Returns:
        List of style strings for each column
    """
    inverted_metrics = inverted_metrics or []
    colors = [''] * len(row)
    
    metric_name = row['Metric']
    is_inverted = metric_name in inverted_metrics
    
    # Compare Team vs League and apply color + bold to Team column (index 1)
    try:
        team_val_str = row['Team']
        league_val_str = row['League']
        
        # Remove any formatting and convert to float for comparison
        team_val = float(team_val_str.replace(',', '').replace('-', '0').replace('%', ''))
        league_val = float(league_val_str.replace(',', '').replace('-', '0').replace('%', ''))
        
        # For inverted metrics, reverse the color logic
        if is_inverted:
            if team_val < league_val:  # Lower is better
                colors[1] = 'color: #178800; font-weight: bold'  # Green
            elif team_val > league_val:  # Higher is worse
                colors[1] = 'color: #d3001c; font-weight: bold'  # Red
            else:
                colors[1] = 'font-weight: bold'
        else:
            if team_val > league_val:  # Higher is better
                colors[1] = 'color: #178800; font-weight: bold'  # Green
            elif team_val < league_val:  # Lower is worse
                colors[1] = 'color: #d3001c; font-weight: bold'  # Red
            else:
                colors[1] = 'font-weight: bold'
    except:
        colors[1] = 'font-weight: bold'
    
    # Color code the Percentile column (index -1)
    pct_str = row['Percentile']
    if pct_str != '-':
        try:
            pct_val = int(pct_str.replace('%', ''))
            
            if pct_val >= 75:
                colors[-1] = 'background-color: #dcfce7; color: #166534; font-weight: bold'
            elif pct_val >= 50:
                colors[-1] = 'background-color: #fef3c7; color: #854d0e; font-weight: bold'
            elif pct_val >= 25:
                colors[-1] = 'background-color: #fed7aa; color: #9a3412; font-weight: bold'
            else:
                colors[-1] = 'background-color: #fee2e2; color: #991b1b; font-weight: bold'
        except:
            pass
    
    return colors

def map_league_averages(league_averages: Dict[str, Any], stat_type: str) -> Dict[str, float]:
    """
    Map league averages columns (with avg_ prefix) to team stat columns.
    
    Args:
        league_averages: Dictionary with league-wide averages (from mart_league_averages)
        stat_type: One of 'attack', 'defense', 'possession', 'discipline'
    
    Returns:
        Dictionary with mapped column names matching team stats
    """
    if not league_averages:
        return {}
    
    # Define mappings for each stat type
    mappings = {
        'attack': {
            'goals_per_game': 'avg_goals_per_game_per_team',
            'xg_per_game': 'avg_xg_per_game',
            'xg_difference': 'avg_xg_difference',
            'xg_diff_per_game': 'avg_xg_diff_per_game',
            'big_chances_created_per_game': 'avg_big_chances_created_per_game',
            'big_chances_missed_per_game': 'avg_big_chances_missed_per_game',
            'big_chances_scored_per_game': 'avg_big_chances_scored_per_game',
            'shots_per_game': 'avg_shots_per_game',
            'shots_on_target_per_game': 'avg_shots_on_target_per_game',
            'shots_off_target_per_game': 'avg_shots_off_target_per_game',
            'blocked_shots_per_game': 'avg_blocked_shots_per_game',
            'shots_inside_box_per_game': 'avg_shots_inside_box_per_game',
            'shots_outside_box_per_game': 'avg_shots_outside_box_per_game',
            'corners_per_game': 'avg_corners_per_game',
            'touches_in_box_per_game': 'avg_touches_in_box_per_game',
        },
        'defense': {
            'goals_conceded_per_game': 'avg_goals_conceded_per_game',
            'xga_per_game': 'avg_xga_per_game',
            'xga_difference': 'avg_xga_difference',
            'xga_difference_per_game': 'avg_xga_difference_per_game',
            'clean_sheet_pct': 'avg_clean_sheet_pct',
            'saves_per_game': 'avg_saves_per_game',
            'tackles_per_game': 'avg_tackles_per_game',
            'avg_tackles_won_pct': 'avg_tackles_won_pct',
            'interceptions_per_game': 'avg_interceptions_per_game',
            'clearances_per_game': 'avg_clearances_per_game',
            'blocked_shots_per_game': 'avg_blocked_shots_per_game_def',
            'ball_recoveries_per_game': 'avg_ball_recoveries_per_game',
            'avg_aerial_duels_pct': 'avg_aerial_duels_pct',
            'avg_ground_duels_pct': 'avg_ground_duels_pct',
            'avg_duels_won_pct': 'avg_duels_won_pct',
        },
        'possession': {
            'avg_possession_pct': 'avg_possession_pct',
            'pass_accuracy_pct': 'avg_pass_accuracy_pct',
            'accurate_passes_per_game': 'avg_accurate_passes_per_game',
            'total_passes_per_game': 'avg_total_passes_per_game',
            'accurate_long_balls_per_game': 'avg_accurate_long_balls_per_game',
            'accurate_crosses_per_game': 'avg_accurate_crosses_per_game',
            'final_third_entries_per_game': 'avg_final_third_entries_per_game',
            'touches_in_box_per_game': 'avg_touches_in_box_per_game_poss',
            'dispossessed_per_game': 'avg_dispossessed_per_game',
        },
        'discipline': {
            'yellow_cards_per_game': 'avg_yellow_cards_per_game',
            'fouls_per_game': 'avg_fouls_per_game',
            'offsides_per_game': 'avg_offsides_per_game',
            'free_kicks_per_game': 'avg_free_kicks_per_game',
        }
    }
    
    mapping = mappings.get(stat_type, {})
    
    # Map the values
    mapped_averages = {}
    for team_col, league_col in mapping.items():
        if league_col in league_averages and league_averages[league_col] is not None:
            mapped_averages[team_col] = float(league_averages[league_col])
    
    return mapped_averages
# ============================================================================
# MAIN PAGE
# ============================================================================

st.markdown("## ⚽ Team Statistics & Performance")

# ============================================================================
# SIDEBAR FILTERS
# ============================================================================

with st.sidebar:
    st.header("Filters")
    
    # Season selector
    try:
        seasons_df = get_all_seasons()
        if not seasons_df.empty:
            season_options = seasons_df['season_name'].tolist()
            season_ids = seasons_df['season_id'].tolist()
            
            selected_season_name = st.selectbox(
                "Select Season",
                options=season_options,
                index=0,
                key="teams_season"
            )
            
            # Get corresponding season ID
            selected_season_idx = season_options.index(selected_season_name)
            selected_season_id = season_ids[selected_season_idx]
        else:
            st.error("No seasons available")
            st.stop()

    except Exception as e:
        logger.error(f"Failed to load seasons: {e}")
        st.error("Failed to load seasons")
        st.stop()
    
    # Home/Away toggle
    location = home_away_toggle(
        label="Filter by location",
        key="teams_location",
        default="all"
    )
    
    if location != "all":
        st.info("⚠️ Home/Away filtering will be available once per-match data is integrated.")

# ============================================================================
# TEAM SELECTOR
# ============================================================================

st.markdown("---")

# Load league standings for team selection
try:
    standings_df = get_league_standings(selected_season_id)
    
    if standings_df.empty:
        st.warning(f"No team data available for season: {selected_season_name}")
        st.stop()
    
    # Add position column (rank by points, goal difference, goals for)
    standings_df = standings_df.sort_values(
        by=['total_points', 'goal_difference', 'goals_for'],
        ascending=[False, False, False]
    ).reset_index(drop=True)
    standings_df['position'] = standings_df.index + 1
    
    # Team selector using existing component
    selected_team_id = team_selector(
        df=standings_df,
        label="🔍 Search and select a team",
        key="teams_team_selector"
    )
    
    if selected_team_id is None:
        st.info("👆 Please select a team to view statistics")
        st.stop()
    
    # Get selected team info
    team_filtered = standings_df[standings_df['team_id'] == selected_team_id]

    if team_filtered.empty:
        # Get the team name from session state if available
        team_name = st.session_state.get('teams_team_selector_name', 'Selected team')
        st.warning(f"⚠️ **{team_name}** did not play in Ekstraklasa during the **{selected_season_name}** season.")
        st.info("👆 Please select a different team or change the season.")
        st.stop()

    team_row = team_filtered.iloc[0]
    team_name = team_row['team_name']
    team_position = int(team_row['position'])
    total_teams = len(standings_df)
        
except Exception as e:
    logger.error(f"Failed to load teams: {e}")
    st.error(f"Failed to load team data: {e}")
    st.exception(e)
    st.stop()

# ============================================================================
# TEAM HEADER
# ============================================================================

st.markdown(f" ### {team_name}")

# Quick stats header
with st.container(border=True):
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Position",
            f"{team_position}/{total_teams}",
            help="Current league standing",
        )

    with col2:
        st.metric(
            "Matches played",
            int(team_row.get("matches_played", 0)),
        )

    with col3:
        st.metric(
            "Points",
            int(team_row.get("total_points", 0)),
        )

    with col4:
         st.metric(
            "Points per Game",
            format_number(team_row.get("points_per_game"), 2),
        )
        

    with col5:
       st.metric(
            "Goal Diff",
            f"{int(team_row.get('goal_difference', 0)):+d}",
            help="Goals scored minus goals conceded",
        )

# ============================================================================
# LOAD ALL TEAM STATS
# ============================================================================

# Initialize all variables

attack_stats = defense_stats = possession_stats = discipline_stats = overview_stats = btts_stats = {}
all_teams_attack = all_teams_defense = all_teams_possession = all_teams_discipline = pd.DataFrame()
league_averages = {}

try:
    # Get selected team's stats in ONE database call
    all_stats = get_all_team_stats(selected_team_id, selected_season_id)
    
    attack_stats = all_stats.get('attack', {})
    defense_stats = all_stats.get('defense', {})
    possession_stats = all_stats.get('possession', {})
    discipline_stats = all_stats.get('discipline', {})
    overview_stats = all_stats.get('overview', {})
    btts_stats = all_stats.get('btts', {})
    
    # Get league averages
    league_averages = get_league_averages(selected_season_id)
    
    # Get ALL teams' data for percentile calculations (4 calls total for all tabs)
    all_teams_attack = get_team_stats('attack', season_id=selected_season_id, team_id=None)
    all_teams_defense = get_team_stats('defense', season_id=selected_season_id, team_id=None)
    all_teams_possession = get_team_stats('possession', season_id=selected_season_id, team_id=None)
    all_teams_discipline = get_team_stats('discipline', season_id=selected_season_id, team_id=None)

except Exception as e:
    logger.error(f"Error loading team stats: {e}")
    st.error(f"Failed to load team statistics: {e}")

# ============================================================================
# TABS LAYOUT
# ============================================================================

overview_tab, form_tab, attack_tab, defense_tab, possession_tab, discipline_tab = st.tabs([
    "Overview",
    "Form",
    "Attack",
    "Defense",
    "Possession",
    "Discipline"
])

# ============================================================================
# OVERVIEW TAB
# ============================================================================

with overview_tab:
    try:
        if attack_stats and defense_stats:
            with st.expander("General stats", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Goals for", int(safe_get(attack_stats, "total_goals", 0)))
                    st.metric("Total xG", float(safe_get(attack_stats, "total_xg", 0)))
                    st.metric("xG Diff", float(safe_get(attack_stats, "xg_difference", 0)))
                
                with col2:
                    st.metric("Goals against", int(safe_get(defense_stats, "total_goals_conceded", 0)))
                    st.metric("Total xGA", format_number(safe_get(defense_stats, "total_xga", 0)))
                    st.metric("xGA Diff", format_number(safe_get(defense_stats, "xga_difference", 0)))
                    
                with col3:
                    st.metric("Clean Sheets", int(safe_get(defense_stats, "clean_sheets", 0)))
                    st.metric("Clean Sheets %", format_percentage(safe_get(defense_stats, "clean_sheet_pct", 0)))
                    
        if btts_stats:
            with st.expander("BTTS Statistics", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("AVG Goals per Match", float(safe_get(btts_stats, "overall_avg_goals_per_match", 0)))
                    st.metric("BTTS %", format_percentage(safe_get(btts_stats, "overall_btts_pct", 0)))
                    
                with col2:
                    st.metric("AVG Goals For", float(safe_get(btts_stats, "overall_avg_scored", 0)))
                    st.metric("AVG xG per Match", float(safe_get(btts_stats, "overall_avg_xg", 0)))
                with col3:
                    st.metric("AVG Goals Against", float(safe_get(btts_stats, "overall_avg_conceded", 0)))
                    st.metric("AVG xGA per Match", float(safe_get(btts_stats, "overall_avg_xga", 0)))
           
        else:
            st.warning("No overview statistics available for this team.")
    except Exception as e:
        logger.error(f"Error loading overview stats: {e}")
        st.error(f"Failed to load overview statistics: {e}")

# ============================================================================
# FORM TAB
# ============================================================================

with form_tab:
    st.subheader("Recent Form")

    # Time period selector
    form_window = st.select_slider(
        "Form window (matches)",
        options=[5, 10, 15, 20],
        value=5,
        key="teams_form_window",
        help="Number of recent matches to analyze",
    )
    try:
        form_data = get_team_form(selected_team_id, last_n_matches=form_window)

        if form_data:
            # Use dynamic key 'last_results' instead of hardcoded "last_5_results"
            form_string = safe_get(form_data, "last_results", "")
            results_list = parse_form_results(form_string, form_window)

            if results_list:
                # Visual form indicator (unchanged)
                colors = {"W": "#22c55e", "D": "#eab308", "L": "#ef4444"}
                form_html = ""
                for result in results_list:
                    color = colors.get(result, "#6b7280")
                    form_html += (
                        f'<span style="display:inline-block; width:40px; height:40px; '
                        f'background-color:{color}; color:white; text-align:center; '
                        f'line-height:40px; margin:2px; border-radius:5px; '
                        f'font-weight:bold; font-size:16px;">{result}</span>'
                    )

                st.markdown(form_html, unsafe_allow_html=True)
                st.caption("W = Win | D = Draw | L = Loss (most recent on right)")

                wins = results_list.count("W")
                draws = results_list.count("D")
                losses = results_list.count("L")

                # Compact metrics row (unchanged)
                with st.container(border=True):
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        st.metric("Wins", wins)
                    with m2:
                        st.metric("Draws", draws)
                    with m3:
                        st.metric("Losses", losses)

                # Charts section (unchanged)
                col1, col2 = st.columns([2, 1])

                points_list = results_to_points(results_list)
                match_numbers = list(range(1, len(points_list) + 1))
                form_df = pd.DataFrame(
                    {"Match": match_numbers, "Points": points_list, "Result": results_list}
                )

                with col1:
                    st.markdown("#### Points per match")
                    fig = px.line(
                        form_df,
                        x="Match",
                        y="Points",
                        markers=True,
                        labels={"Match": "Match", "Points": "Points"},
                    )
                    fig.update_traces(marker=dict(size=8), line=dict(width=2))
                    fig.update_layout(
                        height=350,
                        yaxis=dict(range=[-0.5, 3.5], tickvals=[0, 1, 3]),
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig, width='stretch')

                with col2:
                    st.markdown("#### Result distribution")
                    wdl_df = pd.DataFrame(
                        {"Result": ["Wins", "Draws", "Losses"], "Count": [wins, draws, losses]}
                    )
                    fig_pie = px.pie(
                        wdl_df,
                        values="Count",
                        names="Result",
                        color="Result",
                        color_discrete_map={
                            "Wins": "#22c55e",
                            "Draws": "#eab308",
                            "Losses": "#ef4444",
                        },
                    )
                    fig_pie.update_traces(textinfo="value+percent")
                    fig_pie.update_layout(height=350)
                    st.plotly_chart(fig_pie, width='stretch')

                # Additional form metrics in one compact row (updated to use dynamic keys)
                total_points = safe_get(form_data, "points_last", 0)
                goals_for = safe_get(form_data, "goals_for_last", 0)
                goals_against = safe_get(form_data, "goals_against_last", 0)
                goal_diff = goals_for - goals_against

                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Total points", int(total_points))
                    with c2:
                        st.metric("Goals scored", int(goals_for))
                    with c3:
                        st.metric("Goals conceded", int(goals_against))
                    with c4:
                        st.metric("Goal diff", f"{int(goal_diff):+d}")
            else:
                st.info("No recent form data available.")
        else:
            st.warning("No form data available for this team.")
    except Exception as e:
        logger.error(f"Error loading form data: {e}")
        st.error(f"Failed to load form data: {e}")

# ============================================================================
# ATTACK TAB
# ============================================================================

with attack_tab:
    try:
        if isinstance(all_teams_attack, pd.DataFrame) and not all_teams_attack.empty and attack_stats:
            # Calculate percentiles using pre-loaded data
            league_avg_attack, percentiles = calculate_league_stats_and_percentiles(
                all_teams_attack, 
                attack_stats,       
                None     
            )

            # Override with actual league averages using mapped column names
            mapped_league_avg = map_league_averages(league_averages, 'attack')
            league_avg_attack.update(mapped_league_avg)
                
            # Layout with radar and stats table
            col1, col2 = st.columns([1.2, 1])
                
            with col1:
                st.markdown("### Attack Radar")
                    
                # Metric configuration
                attack_radar_metrics = [
                    ('goals_per_game', 'Goals/Game'),
                    ('xg_per_game', 'xG/Game'),
                    ('shots_per_game', 'Shots/Game'),
                    ('shots_on_target_per_game', 'Shots on Target/Game'),
                    ('big_chances_created_per_game', 'Big Chances/Game'),
                    ('touches_in_box_per_game', 'Touches In Box/Game'),
                ]
                
                # Draw radar using reusable function
                fig = draw_team_radar(
                    team_stats=attack_stats,           # Selected team's stats
                    all_teams_df=all_teams_attack,     # ALL teams for percentile calculation
                    percentiles=percentiles,            # Calculated percentiles
                    league_avg=league_avg_attack,      # League averages
                    team_name=team_name,
                    metric_config=attack_radar_metrics,
                    radar_color='#fbbf24',  # Gold
                    radar_edge_color='#f59e0b'  # Orange
                )
                
                # Display radar
                radar_col1, radar_col2, radar_col3 = st.columns([0.3, 1, 0.3])
                with radar_col2:
                    st.pyplot(fig, width='stretch')
                plt.close()
                
                # Legend
                st.markdown(f"""
                <div style="display: flex; justify-content: center; gap: 15px; margin-top: 8px; font-size: 11px;">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 14px; height: 14px; background-color: #fbbf24; margin-right: 5px; border-radius: 2px;"></div>
                        <span>{team_name}</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 14px; height: 14px; background-color: #9ca3af; margin-right: 5px; border-radius: 2px;"></div>
                        <span>League Average</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown("### Attack Statistics")
                
                attack_metrics = [
                    ('goals_per_game', 'Goals per Game', 2),
                    ('total_goals', 'Total Goals', 0),
                    ('xg_per_game', 'xG per Game', 2),
                    ('total_xg', 'Total xG', 2),
                    ('xg_difference', 'xG Difference', 2),
                    ('shots_per_game', 'Shots per Game', 2),
                    ('shots_on_target_per_game', 'Shots on Target/Game', 2),
                    ('big_chances_created_per_game', 'Big Chances/Game', 2),
                    ('big_chances_scored_per_game', 'Big Chances Scored/Game', 2),
                    ('corners_per_game', 'Corners per Game', 2),
                    ('touches_in_box_per_game', 'Touches in Box/Game', 2)
                ]
                
                # Create stats table (no inverted metrics for attack)
                attack_df = create_stats_table(
                    attack_metrics, 
                    attack_stats,           # Selected team's stats
                    league_avg_attack,      # League averages
                    percentiles             # Calculated percentiles
                )
                
                inverted_names = attack_df.attrs.get('inverted_names', [])
                styled_df = attack_df.style.apply(lambda row: style_table(row, inverted_names), axis=1)
                st.dataframe(styled_df, width='stretch', height=425, hide_index=True)
        else:
            st.warning("No attack statistics available for this team.")
                            
    except Exception as e:
        logger.error(f"Error loading attack stats: {e}")
        st.error(f"Failed to load attack statistics: {e}")
        st.exception(e)

# ============================================================================
# DEFENSE TAB
# ============================================================================

with defense_tab:
    try:
        if isinstance(all_teams_defense, pd.DataFrame) and defense_stats:
            # Calculate percentiles using pre-loaded data
            league_avg_defense, percentiles = calculate_league_stats_and_percentiles(
                all_teams_defense, 
                defense_stats,       
                None     
            )
            
            # Override with actual league averages using mapped column names
            mapped_league_avg = map_league_averages(league_averages, 'defense')
            league_avg_defense.update(mapped_league_avg)

            # Layout with radar and stats table
            col1, col2 = st.columns([1.2, 1])
            
            with col1:
                st.markdown("### Defense Radar")
                
                defense_radar_metrics = [
                    ('tackles_per_game', 'Tackles/Game'),
                    ('interceptions_per_game', 'Interceptions/Game'),
                    ('clearances_per_game', 'Clearances/Game'),
                    ('blocked_shots_per_game', 'Blocked Shots/Game'),
                    ('ball_recoveries_per_game', 'Ball Recoveries/Game'),
                    ('clean_sheet_pct', 'Clean Sheet %'),
                ]
                
                # Draw radar with RED color scheme
                fig = draw_team_radar(
                    team_stats=defense_stats,
                    all_teams_df=all_teams_defense,
                    percentiles=percentiles,
                    league_avg=league_avg_defense,
                    team_name=team_name,
                    metric_config=defense_radar_metrics,
                    radar_color='#ef4444',  # Red
                    radar_edge_color='#dc2626'  # Dark red
                )
                
                radar_col1, radar_col2, radar_col3 = st.columns([0.3, 1, 0.3])
                with radar_col2:
                    st.pyplot(fig, width='stretch')
                plt.close()
                
                # Legend with red color
                st.markdown(f"""
                <div style="display: flex; justify-content: center; gap: 15px; margin-top: 8px; font-size: 11px;">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 14px; height: 14px; background-color: #ef4444; margin-right: 5px; border-radius: 2px;"></div>
                        <span>{team_name}</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 14px; height: 14px; background-color: #9ca3af; margin-right: 5px; border-radius: 2px;"></div>
                        <span>League Average</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("### Defense Statistics")
                
                defense_metrics = [
                    ('goals_conceded_per_game', 'Goals Conceded/Game', 2),
                    ('total_goals_conceded', 'Total Goals Conceded', 0),
                    ('xga_per_game', 'xGA/Game', 2),
                    ('total_xga', 'Total xGA', 2),
                    ('xga_difference', 'xGA Difference', 2),
                    ('xga_difference_per_game', 'xGA Difference/Game', 2),
                    ('clean_sheets', 'Clean Sheets', 0),
                    ('clean_sheet_pct', 'Clean Sheet %', 1),
                    ('tackles_per_game', 'Tackles/Game', 2),
                    ('avg_tackles_won_pct', 'Tackles Won %', 1),
                    ('interceptions_per_game', 'Interceptions/Game', 2),
                    ('clearances_per_game', 'Clearances/Game', 2),
                    ('blocked_shots_per_game', 'Blocked Shots/Game', 2),
                    ('ball_recoveries_per_game', 'Ball Recoveries/Game', 2),
                    ('avg_aerial_duels_pct', 'Aerial Duels Won %', 1),
                    ('avg_ground_duels_pct', 'Ground Duels Won %', 1),
                    ('saves_per_game', 'Saves/Game', 2)
                ]
                
                # Metrics where lower is better
                inverted = ['goals_conceded_per_game', 'total_goals_conceded', 'xga_per_game', 'total_xga']
                
                defense_df = create_stats_table(
                    defense_metrics, 
                    defense_stats, 
                    league_avg_defense, 
                    percentiles, 
                    inverted
                )
                inverted_names = defense_df.attrs.get('inverted_names', [])
                styled_df = defense_df.style.apply(lambda row: style_table(row, inverted_names), axis=1)
                st.dataframe(styled_df, width='stretch', height=625, hide_index=True)
        else:
            st.warning("No defense statistics available for this team.")
    
    except Exception as e:
        logger.error(f"Error loading defense stats: {e}")
        st.error(f"Failed to load defense statistics: {e}")
        st.exception(e)


# ============================================================================
# POSSESSION TAB
# ============================================================================

with possession_tab:
    try:
        if isinstance(all_teams_possession, pd.DataFrame) and possession_stats:
            # Calculate percentiles using pre-loaded data
            league_avg_possession, percentiles = calculate_league_stats_and_percentiles(
                all_teams_possession,  
                possession_stats,     
                None        
            )

            # Override with actual league averages using mapped column names
            mapped_league_avg = map_league_averages(league_averages, 'possession')
            league_avg_possession.update(mapped_league_avg)

            # Layout with radar and stats table
            col1, col2 = st.columns([1.2, 1])
            
            with col1:
                st.markdown("### Possession Radar")
        
                possession_radar_metrics = [
                    ('avg_possession_pct', 'Possession %'),
                    ('pass_accuracy_pct', 'Pass Accuracy %'),
                    ('accurate_passes_per_game', 'Accurate Passes/Game'),
                    ('accurate_long_balls_per_game', 'Long Balls/Game'),
                    ('final_third_entries_per_game', 'Final Third Entries/Game'),
                    ('touches_in_box_per_game', 'Touches In Box/Game'),
                ]

                # Draw radar with PURPLE color scheme
                fig = draw_team_radar(
                    team_stats=possession_stats,
                    all_teams_df=all_teams_possession,
                    percentiles=percentiles,
                    league_avg=league_avg_possession,
                    team_name=team_name,
                    metric_config=possession_radar_metrics,
                    radar_color='#8b5cf6',  # Purple
                    radar_edge_color='#7c3aed'  # Dark purple
                )

                radar_col1, radar_col2, radar_col3 = st.columns([0.3, 1, 0.3])
                with radar_col2:
                    st.pyplot(fig, width='stretch')
                plt.close()
                
                st.markdown(f"""
                <div style="display: flex; justify-content: center; gap: 15px; margin-top: 8px; font-size: 11px;">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 14px; height: 14px; background-color: #8b5cf6; margin-right: 5px; border-radius: 2px;"></div>
                        <span>{team_name}</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 14px; height: 14px; background-color: #9ca3af; margin-right: 5px; border-radius: 2px;"></div>
                        <span>League Average</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("### Possession Statistics")
                
                possession_metrics = [
                    ('avg_possession_pct', 'Avg Possession %', 1),
                    ('pass_accuracy_pct', 'Pass Accuracy %', 1),
                    ('total_passes_per_game', 'Total Passes/Game', 1),
                    ('accurate_passes_per_game', 'Accurate Passes/Game', 1),
                    ('accurate_long_balls_per_game', 'Long Balls/Game', 2),
                    ('accurate_crosses_per_game', 'Accurate Crosses/Game', 2),
                    ('final_third_entries_per_game', 'Final Third Entries/Game', 2),
                    ('touches_in_box_per_game', 'Touches in Box/Game', 2),
                    ('dispossessed_per_game', 'Dispossessed/Game', 2),
                    ('total_accurate_passes', 'Total Accurate Passes', 0),
                    ('total_passes', 'Total Passes', 0)
                ]
                
                inverted = ['dispossessed_per_game']
                
                possession_df = create_stats_table(
                    possession_metrics, 
                    possession_stats, 
                    league_avg_possession, 
                    percentiles, 
                    inverted
                )
                inverted_names = possession_df.attrs.get('inverted_names', [])
                styled_df = possession_df.style.apply(lambda row: style_table(row, inverted_names), axis=1)
                st.dataframe(styled_df, width='stretch', height=425, hide_index=True)
        else:
            st.warning("No possession statistics available for this team.")

    except Exception as e:
        logger.error(f"Error loading possession stats: {e}")
        st.error(f"Failed to load possession statistics: {e}")
        st.exception(e)

# ============================================================================
# DISCIPLINE TAB
# ============================================================================

with discipline_tab:
    try:
        if isinstance(all_teams_discipline, pd.DataFrame) and discipline_stats:
            # Calculate percentiles using pre-loaded data
            league_avg_discipline, percentiles = calculate_league_stats_and_percentiles(
                all_teams_discipline, 
                discipline_stats,       
                None       
            )

            # Override with actual league averages using mapped column names
            mapped_league_avg = map_league_averages(league_averages, 'discipline')
            league_avg_discipline.update(mapped_league_avg)

            # Layout with stats table
            col1 = st.columns([1])
            
            with col1[0]:
                st.markdown("### Discipline Statistics")
                
                discipline_metrics = [
                    ('yellow_cards_per_game', 'Yellow Cards/Game', 2),
                    ('total_yellow_cards', 'Total Yellow Cards', 0),
                    ('total_red_cards', 'Red Cards', 0),
                    ('fouls_per_game', 'Fouls/Game', 2),
                    ('total_fouls', 'Total Fouls', 0),
                    ('offsides_per_game', 'Offsides/Game', 2),
                    ('total_offsides', 'Total Offsides', 0),
                    ('free_kicks_per_game', 'Free Kicks/Game', 2),
                    ('total_free_kicks', 'Total Free Kicks', 0)
                ]
                
                # All discipline metrics - lower is better
                inverted = [metric[0] for metric in discipline_metrics]
                
                discipline_df = create_stats_table(
                    discipline_metrics, 
                    discipline_stats, 
                    league_avg_discipline, 
                    percentiles, 
                    inverted
                )
                inverted_names = discipline_df.attrs.get('inverted_names', [])
                styled_df = discipline_df.style.apply(lambda row: style_table(row, inverted_names), axis=1)
                st.dataframe(styled_df, width='stretch', height=425, hide_index=True)
                
                # Fair Play Score
                st.markdown("### Fair Play Rating")
                
                total_yellows = safe_get(discipline_stats, 'total_yellow_cards', 0)
                total_reds = safe_get(discipline_stats, 'total_red_cards', 0)
                matches_played = safe_get(discipline_stats, 'matches_played', 1)
                
                fair_play_score = ((total_yellows * 1) + (total_reds * 3)) / matches_played if matches_played > 0 else 0
                
                if fair_play_score < 2:
                    fair_play_rating = "Excellent ⭐⭐⭐"
                    color = "green"
                elif fair_play_score < 3:
                    fair_play_rating = "Good ⭐⭐"
                    color = "blue"
                elif fair_play_score < 4:
                    fair_play_rating = "Average ⭐"
                    color = "orange"
                else:
                    fair_play_rating = "Poor ⚠️"
                    color = "red"
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fair Play Score", f"{fair_play_score:.2f}")
                with col2:
                    st.markdown(f"**Rating:** :{color}[{fair_play_rating}]")
                
                st.caption("Fair Play Score = (Yellow cards × 1 + Red cards × 3) / Matches played")
        else:
            st.warning("No discipline statistics available for this team.")
    
    except Exception as e:
        logger.error(f"Error loading discipline stats: {e}")
        st.error(f"Failed to load discipline statistics: {e}")
        st.exception(e)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    f"*Data for {selected_season_name} | Selected team: {team_name} | "
    f"Form window: Last {form_window} matches*"
)
