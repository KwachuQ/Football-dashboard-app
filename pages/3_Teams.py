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


# Import existing components and services
from components.filters import team_selector, home_away_toggle, get_active_league_from_config
from services.queries import get_all_seasons, get_league_standings, get_team_form, get_team_stats
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

# Page configuration
st.set_page_config(
    page_title="Teams - Football Analytics",
    page_icon="⚽",
    layout="wide"
)

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


# ============================================================================
# MAIN PAGE
# ============================================================================

st.title("⚽ Team Statistics & Performance")
st.markdown("Detailed team analysis across attack, defense, possession, and discipline")

# ============================================================================
# SIDEBAR FILTERS
# ============================================================================

with st.sidebar:
    st.header("Filters")
    
    # Season selector
    st.subheader("Season")
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
    
    # Time period selector
    st.subheader("Time Period")
    form_window = st.select_slider(
        "Form Window (matches)",
        options=[5, 10, 15, 20],
        value=5,
        key="teams_form_window",
        help="Number of recent matches to analyze"
    )
    
    # Home/Away toggle
    st.subheader("Match Location")
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
    team_row = standings_df[standings_df['team_id'] == selected_team_id].iloc[0]
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

st.markdown(f"## {team_name}")

# Quick stats header
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "League Position",
        f"{team_position} / {total_teams}",
        help="Current standing in the league"
    )

with col2:
    st.metric(
        "Matches Played",
        int(team_row.get('matches_played', 0))
    )

with col3:
    st.metric(
        "Points",
        int(team_row.get('total_points', 0))
    )

with col4:
    st.metric(
        "Goal Difference",
        f"{int(team_row.get('goal_difference', 0)):+d}",
        help="Goals scored minus goals conceded"
    )

with col5:
    st.metric(
        "Points/Game",
        format_number(team_row.get('points_per_game'), 2)
    )

st.markdown("---")

# ============================================================================
# TABS LAYOUT
# ============================================================================

overview_tab, form_tab, attack_tab, defense_tab, possession_tab, discipline_tab = st.tabs([
    "📊 Overview",
    "📈 Form",
    "⚔️ Attack",
    "🛡️ Defense",
    "🎯 Possession",
    "⚠️ Discipline"
])

# ============================================================================
# OVERVIEW TAB
# ============================================================================

with overview_tab:
    st.subheader("Season Summary")
    
    try:
        overview_stats = get_team_stats(selected_team_id, "overview", selected_season_id)
        
        if overview_stats:
            # Performance metrics
            st.markdown("### Performance Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Matches Played", int(safe_get(overview_stats, 'matches_played', 0)))
                st.metric("Wins", int(safe_get(overview_stats, 'wins', 0)))
            
            with col2:
                st.metric("Draws", int(safe_get(overview_stats, 'draws', 0)))
                st.metric("Losses", int(safe_get(overview_stats, 'losses', 0)))
            
            with col3:
                st.metric("Total Points", int(safe_get(overview_stats, 'total_points', 0)))
                st.metric("Points/Game", format_number(safe_get(overview_stats, 'points_per_game'), 2))
            
            with col4:
                wins = safe_get(overview_stats, 'wins', 0)
                matches = safe_get(overview_stats, 'matches_played', 1)
                win_rate = (wins / matches * 100) if matches > 0 else 0
                st.metric("Win Rate", format_percentage(win_rate))
            
            st.markdown("---")
            
            # Goal statistics
            st.markdown("### Goal Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Goals For", int(safe_get(overview_stats, 'goals_for', 0)))
            
            with col2:
                st.metric("Goals Against", int(safe_get(overview_stats, 'goals_against', 0)))
            
            with col3:
                goal_diff = safe_get(overview_stats, 'goal_difference', 0)
                st.metric("Goal Difference", f"{int(goal_diff):+d}")
            
            with col4:
                clean_sheets = safe_get(overview_stats, 'clean_sheets', 0)
                st.metric("Clean Sheets", int(clean_sheets))
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
    
    try:
        form_data = get_team_form(selected_team_id, last_n_matches=form_window)
        
        if form_data:
            # Parse form results - use correct column name
            form_string = safe_get(form_data, 'last_5_results', '')
            results_list = parse_form_results(form_string, form_window)
            
            if results_list:
                # Form display
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Visual form indicator
                    st.markdown("#### Recent Results")
                    form_html = ""
                    colors = {'W': '#22c55e', 'D': '#eab308', 'L': '#ef4444'}
                    
                    for result in results_list:
                        color = colors.get(result, '#6b7280')
                        form_html += f'<span style="display:inline-block; width:40px; height:40px; background-color:{color}; color:white; text-align:center; line-height:40px; margin:2px; border-radius:5px; font-weight:bold; font-size:16px;">{result}</span>'
                    
                    st.markdown(form_html, unsafe_allow_html=True)
                    st.caption("W = Win | D = Draw | L = Loss (most recent on right)")
                
                with col2:
                    # Form statistics
                    wins = results_list.count('W')
                    draws = results_list.count('D')
                    losses = results_list.count('L')
                    
                    st.metric("Wins", wins)
                    st.metric("Draws", draws)
                    st.metric("Losses", losses)
                
                st.markdown("---")
                
                # Points chart
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("#### Points Per Match")
                    
                    # Create points progression
                    points_list = results_to_points(results_list)
                    match_numbers = list(range(1, len(points_list) + 1))
                    
                    form_df = pd.DataFrame({
                        'Match': match_numbers,
                        'Points': points_list,
                        'Result': results_list
                    })
                    
                    # Create line chart
                    fig = px.line(
                        form_df,
                        x='Match',
                        y='Points',
                        markers=True,
                        title=f"Points per match (Last {len(results_list)} matches)",
                        labels={'Match': 'Match Number', 'Points': 'Points Earned'}
                    )
                    
                    fig.update_traces(
                        marker=dict(size=10),
                        line=dict(width=3)
                    )
                    
                    fig.update_layout(
                        yaxis=dict(range=[-0.5, 3.5], tickvals=[0, 1, 3]),
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, width='stretch')
                
                with col2:
                    st.markdown("#### Win/Draw/Loss Distribution")
                    
                    # Create pie chart
                    wdl_df = pd.DataFrame({
                        'Result': ['Wins', 'Draws', 'Losses'],
                        'Count': [wins, draws, losses]
                    })
                    
                    fig_pie = px.pie(
                        wdl_df,
                        values='Count',
                        names='Result',
                        color='Result',
                        color_discrete_map={'Wins': '#22c55e', 'Draws': '#eab308', 'Losses': '#ef4444'}
                    )
                    
                    fig_pie.update_traces(textinfo='value+percent')
                    st.plotly_chart(fig_pie, width='stretch')
                
                # Additional form metrics - use correct column names
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_points = safe_get(form_data, 'points_last_5', 0)
                    st.metric("Total Points", int(total_points))
                
                with col2:
                    goals_for = safe_get(form_data, 'goals_for_last_5', 0)
                    st.metric("Goals Scored", int(goals_for))
                
                with col3:
                    goals_against = safe_get(form_data, 'goals_against_last_5', 0)
                    st.metric("Goals Conceded", int(goals_against))
                
                with col4:
                    goal_diff = goals_for - goals_against
                    st.metric("Goal Difference", f"{int(goal_diff):+d}")
                
            else:
                st.info("No recent form data available.")
        else:
            st.warning("No form data available for this team.")
    
    except Exception as e:
        logger.error(f"Error loading form data: {e}")
        st.error(f"Failed to load form data: {e}")
        st.exception(e)

# ============================================================================
# ATTACK TAB
# ============================================================================

with attack_tab:
    st.subheader("Attacking Statistics")
    
    try:
        # Pobierz statystyki dla wszystkich drużyn w lidze
        engine = get_engine()
        query = f"""
            SELECT * 
            FROM gold.mart_team_attack
            WHERE season_id = {selected_season_id}
        """
        
        with engine.connect() as conn:
            all_teams_df = pd.read_sql(query, conn)
        
        if not all_teams_df.empty:
            # Statystyki dla wybranej drużyny
            team_stats_row = all_teams_df[all_teams_df['team_id'] == selected_team_id]
            
            if team_stats_row.empty:
                st.warning("No attack statistics available for this team.")
            else:
                team_stats = team_stats_row.iloc[0].to_dict()
                
                # Oblicz średnie ligowe i percentyle
                league_avg, percentiles = calculate_league_stats_and_percentiles(
                    all_teams_df, 
                    team_stats
                )
                
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown("### Attack Radar")
                    
                    # Definicja metryk
                    metric_config = [
                        ('goals_per_game', 'Goals/Game'),
                        ('xg_per_game', 'xG/Game'),
                        ('shots_on_target_per_game', 'Shots on Target/Game'),
                        ('big_chances_created_per_game', 'Big Chances/Game'),
                        ('shots_per_game', 'Shots/Game'),
                        ('corners_per_game', 'Corners/Game')
                    ]
                    
                    metrics = [m[0] for m in metric_config]
                    labels = [m[1] for m in metric_config]
                    
                    # Oblicz skale
                    scales = calculate_radar_scales(all_teams_df, metrics, padding_pct=0.15)
                    
                    # Pobierz wartości
                    team_values = [float(safe_get(team_stats, m, 0)) for m in metrics]
                    league_values = [float(safe_get(league_avg, m, 0)) for m in metrics]
                    
                    # Normalizuj
                    team_normalized = normalize_for_radar(team_values, scales, metrics)
                    league_normalized = normalize_for_radar(league_values, scales, metrics)
                    
                    # Stwórz radar
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=team_normalized,
                        theta=labels,
                        fill='toself',
                        name=team_name,
                        line_color='#3b82f6',
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata}<extra></extra>',
                        customdata=[f"{v:.2f}" for v in team_values]
                    ))
                    
                    fig.add_trace(go.Scatterpolar(
                        r=league_normalized,
                        theta=labels,
                        fill='toself',
                        name='League Average',
                        line_color='#9ca3af',
                        opacity=0.5,
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata}<extra></extra>',
                        customdata=[f"{v:.2f}" for v in league_values]
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 1],
                                showticklabels=False
                            )
                        ),
                        showlegend=True,
                        height=500
                    )
                    
                    st.plotly_chart(fig, width='stretch')
                    
                    # Legenda ze skalami
                    st.caption("**Scales for each metric:**")
                    scale_text = " | ".join([
                        f"{labels[i]}: {scales[metrics[i]][0]:.1f}-{scales[metrics[i]][1]:.1f}"
                        for i in range(len(metrics))
                    ])
                    st.caption(scale_text)
                
                with col2:
                    st.markdown("### Attack Statistics")
                    
                    attack_data = {
                        'Metric': [
                            'Goals per Game',
                            'Total Goals',
                            'xG per Game',
                            'Total xG',
                            'xG Difference',
                            'Shots per Game',
                            'Shots on Target/Game',
                            'Big Chances/Game',
                            'Big Chances Scored/Game',
                            'Corners per Game',
                            'Touches in Box/Game'
                        ],
                        'Team': [
                            format_number(safe_get(team_stats, 'goals_per_game'), 2),
                            format_number(safe_get(team_stats, 'total_goals'), 0),
                            format_number(safe_get(team_stats, 'xg_per_game'), 2),
                            format_number(safe_get(team_stats, 'total_xg'), 2),
                            format_number(safe_get(team_stats, 'xg_difference'), 2),
                            format_number(safe_get(team_stats, 'shots_per_game'), 2),
                            format_number(safe_get(team_stats, 'shots_on_target_per_game'), 2),
                            format_number(safe_get(team_stats, 'big_chances_created_per_game'), 2),
                            format_number(safe_get(team_stats, 'big_chances_scored_per_game'), 2),
                            format_number(safe_get(team_stats, 'corners_per_game'), 2),
                            format_number(safe_get(team_stats, 'touches_in_box_per_game'), 2)
                        ],
                        'League': [
                            format_number(safe_get(league_avg, 'goals_per_game'), 2),
                            format_number(safe_get(league_avg, 'total_goals'), 1),
                            format_number(safe_get(league_avg, 'xg_per_game'), 2),
                            format_number(safe_get(league_avg, 'total_xg'), 2),
                            format_number(safe_get(league_avg, 'xg_difference'), 2),
                            format_number(safe_get(league_avg, 'shots_per_game'), 2),
                            format_number(safe_get(league_avg, 'shots_on_target_per_game'), 2),
                            format_number(safe_get(league_avg, 'big_chances_created_per_game'), 2),
                            format_number(safe_get(league_avg, 'big_chances_scored_per_game'), 2),
                            format_number(safe_get(league_avg, 'corners_per_game'), 2),
                            format_number(safe_get(league_avg, 'touches_in_box_per_game'), 2)
                        ],
                        'Pct': [
                            f"{int(percentiles.get('goals_per_game', 0))}%" if percentiles.get('goals_per_game') else '-',
                            f"{int(percentiles.get('total_goals', 0))}%" if percentiles.get('total_goals') else '-',
                            f"{int(percentiles.get('xg_per_game', 0))}%" if percentiles.get('xg_per_game') else '-',
                            f"{int(percentiles.get('total_xg', 0))}%" if percentiles.get('total_xg') else '-',
                            f"{int(percentiles.get('xg_difference', 0))}%" if percentiles.get('xg_difference') else '-',
                            f"{int(percentiles.get('shots_per_game', 0))}%" if percentiles.get('shots_per_game') else '-',
                            f"{int(percentiles.get('shots_on_target_per_game', 0))}%" if percentiles.get('shots_on_target_per_game') else '-',
                            f"{int(percentiles.get('big_chances_created_per_game', 0))}%" if percentiles.get('big_chances_created_per_game') else '-',
                            f"{int(percentiles.get('big_chances_scored_per_game', 0))}%" if percentiles.get('big_chances_scored_per_game') else '-',
                            f"{int(percentiles.get('corners_per_game', 0))}%" if percentiles.get('corners_per_game') else '-',
                            f"{int(percentiles.get('touches_in_box_per_game', 0))}%" if percentiles.get('touches_in_box_per_game') else '-'
                        ]
                    }
                    
                    attack_df = pd.DataFrame(attack_data)
                    
                    # Convert all columns to strings to avoid Arrow serialization issues
                    attack_df = prepare_dataframe_for_display(attack_df)
                    
                    # Stylizacja
                    def highlight_percentile(row):
                        colors = [''] * len(row)
                        pct_str = row['Pct']
                        
                        if pct_str == '-':
                            return colors
                        
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
                    
                    styled_df = attack_df.style.apply(highlight_percentile, axis=1)
                    st.dataframe(styled_df, width='stretch', height=425,hide_index=True)
                    
                    st.caption("💡 **Pct** = Percentile (% teams with worse stats)")
        else:
            st.warning("No attack statistics available for this season.")
            
    except Exception as e:
        logger.error(f"Error loading attack stats: {e}")
        st.error(f"Failed to load attack statistics: {e}")
        st.exception(e)

# ============================================================================
# DEFENSE TAB
# ============================================================================

with defense_tab:
    st.subheader("Defensive Performance")
    
    try:
        # Pobierz statystyki dla wszystkich drużyn w lidze
        engine = get_engine()
        query = f"""
            SELECT * 
            FROM gold.mart_team_defense
            WHERE season_id = {selected_season_id}
        """
        
        with engine.connect() as conn:
            all_teams_df = pd.read_sql(query, conn)
        
        if not all_teams_df.empty:
            team_stats_row = all_teams_df[all_teams_df['team_id'] == selected_team_id]
            
            if team_stats_row.empty:
                st.warning("No defense statistics available for this team.")
            else:
                team_stats = team_stats_row.iloc[0].to_dict()
                
                league_avg, percentiles = calculate_league_stats_and_percentiles(
                    all_teams_df, 
                    team_stats
                )
                
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown("### Defense Radar")
                    
                    metric_config = [
                        ('tackles_per_game', 'Tackles/Game'),
                        ('interceptions_per_game', 'Interceptions/Game'),
                        ('clearances_per_game', 'Clearances/Game'),
                        ('blocked_shots_per_game', 'Blocked Shots/Game'),
                        ('ball_recoveries_per_game', 'Ball Recoveries/Game'),
                        ('clean_sheet_pct', 'Clean Sheet %')
                    ]
                    
                    metrics = [m[0] for m in metric_config]
                    labels = [m[1] for m in metric_config]
                    
                    scales = calculate_radar_scales(all_teams_df, metrics, padding_pct=0.15)
                    
                    team_values = [float(safe_get(team_stats, m, 0)) for m in metrics]
                    league_values = [float(safe_get(league_avg, m, 0)) for m in metrics]
                    
                    team_normalized = normalize_for_radar(team_values, scales, metrics)
                    league_normalized = normalize_for_radar(league_values, scales, metrics)
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=team_normalized,
                        theta=labels,
                        fill='toself',
                        name=team_name,
                        line_color='#ef4444',
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata}<extra></extra>',
                        customdata=[f"{v:.2f}" for v in team_values]
                    ))
                    
                    fig.add_trace(go.Scatterpolar(
                        r=league_normalized,
                        theta=labels,
                        fill='toself',
                        name='League Average',
                        line_color='#9ca3af',
                        opacity=0.5,
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata}<extra></extra>',
                        customdata=[f"{v:.2f}" for v in league_values]
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 1],
                                showticklabels=False
                            )
                        ),
                        showlegend=True,
                        height=500
                    )
                    
                    st.plotly_chart(fig, width='stretch')
                    
                    st.caption("**Scales for each metric:**")
                    scale_text = " | ".join([
                        f"{labels[i]}: {scales[metrics[i]][0]:.1f}-{scales[metrics[i]][1]:.1f}"
                        for i in range(len(metrics))
                    ])
                    st.caption(scale_text)
                
                with col2:
                    st.markdown("### Defense Statistics")
                    
                    defense_data = {
                        'Metric': [
                            'Goals Conceded/Game',
                            'Total Goals Conceded',
                            'Clean Sheets',
                            'Clean Sheet %',
                            'Tackles/Game',
                            'Tackles Won %',
                            'Interceptions/Game',
                            'Clearances/Game',
                            'Blocked Shots/Game',
                            'Ball Recoveries/Game',
                            'Aerial Duels Won %',
                            'Ground Duels Won %',
                            'Saves/Game'
                        ],
                        'Team': [
                            format_number(safe_get(team_stats, 'goals_conceded_per_game'), 2),
                            format_number(safe_get(team_stats, 'total_goals_conceded'), 0),
                            format_number(safe_get(team_stats, 'clean_sheets'), 0),
                            format_percentage(safe_get(team_stats, 'clean_sheet_pct')),
                            format_number(safe_get(team_stats, 'tackles_per_game'), 2),
                            format_percentage(safe_get(team_stats, 'avg_tackles_won_pct')),
                            format_number(safe_get(team_stats, 'interceptions_per_game'), 2),
                            format_number(safe_get(team_stats, 'clearances_per_game'), 2),
                            format_number(safe_get(team_stats, 'blocked_shots_per_game'), 2),
                            format_number(safe_get(team_stats, 'ball_recoveries_per_game'), 2),
                            format_percentage(safe_get(team_stats, 'avg_aerial_duels_pct')),
                            format_percentage(safe_get(team_stats, 'avg_ground_duels_pct')),
                            format_number(safe_get(team_stats, 'saves_per_game'), 2)
                        ],
                        'League': [
                            format_number(safe_get(league_avg, 'goals_conceded_per_game'), 2),
                            format_number(safe_get(league_avg, 'total_goals_conceded'), 1),
                            format_number(safe_get(league_avg, 'clean_sheets'), 1),
                            format_percentage(safe_get(league_avg, 'clean_sheet_pct')),
                            format_number(safe_get(league_avg, 'tackles_per_game'), 2),
                            format_percentage(safe_get(league_avg, 'avg_tackles_won_pct')),
                            format_number(safe_get(league_avg, 'interceptions_per_game'), 2),
                            format_number(safe_get(league_avg, 'clearances_per_game'), 2),
                            format_number(safe_get(league_avg, 'blocked_shots_per_game'), 2),
                            format_number(safe_get(league_avg, 'ball_recoveries_per_game'), 2),
                            format_percentage(safe_get(league_avg, 'avg_aerial_duels_pct')),
                            format_percentage(safe_get(league_avg, 'avg_ground_duels_pct')),
                            format_number(safe_get(league_avg, 'saves_per_game'), 2)
                        ],
                        'Pct': [
                            # Goals conceded - lower is better, so invert percentile
                            f"{int(100 - percentiles.get('goals_conceded_per_game', 100))}%" if percentiles.get('goals_conceded_per_game') else '-',
                            f"{int(100 - percentiles.get('total_goals_conceded', 100))}%" if percentiles.get('total_goals_conceded') else '-',
                            f"{int(percentiles.get('clean_sheets', 0))}%" if percentiles.get('clean_sheets') else '-',
                            f"{int(percentiles.get('clean_sheet_pct', 0))}%" if percentiles.get('clean_sheet_pct') else '-',
                            f"{int(percentiles.get('tackles_per_game', 0))}%" if percentiles.get('tackles_per_game') else '-',
                            f"{int(percentiles.get('avg_tackles_won_pct', 0))}%" if percentiles.get('avg_tackles_won_pct') else '-',
                            f"{int(percentiles.get('interceptions_per_game', 0))}%" if percentiles.get('interceptions_per_game') else '-',
                            f"{int(percentiles.get('clearances_per_game', 0))}%" if percentiles.get('clearances_per_game') else '-',
                            f"{int(percentiles.get('blocked_shots_per_game', 0))}%" if percentiles.get('blocked_shots_per_game') else '-',
                            f"{int(percentiles.get('ball_recoveries_per_game', 0))}%" if percentiles.get('ball_recoveries_per_game') else '-',
                            f"{int(percentiles.get('avg_aerial_duels_pct', 0))}%" if percentiles.get('avg_aerial_duels_pct') else '-',
                            f"{int(percentiles.get('avg_ground_duels_pct', 0))}%" if percentiles.get('avg_ground_duels_pct') else '-',
                            f"{int(percentiles.get('saves_per_game', 0))}%" if percentiles.get('saves_per_game') else '-'
                        ]
                    }
                    
                    defense_df = pd.DataFrame(defense_data)
                    defense_df = prepare_dataframe_for_display(defense_df)
                    
                    def highlight_percentile(row):
                        colors = [''] * len(row)
                        pct_str = row['Pct']
                        
                        if pct_str == '-':
                            return colors
                        
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
                    
                    styled_df = defense_df.style.apply(highlight_percentile, axis=1)
                    st.dataframe(styled_df, width='stretch', height=495, hide_index=True)
                    
                    st.caption("💡 **Pct** = Percentile (% teams with worse stats)")
        else:
            st.warning("No defense statistics available for this season.")
    
    except Exception as e:
        logger.error(f"Error loading defense stats: {e}")
        st.error(f"Failed to load defense statistics: {e}")
        st.exception(e)


# ============================================================================
# POSSESSION TAB
# ============================================================================

with possession_tab:
    st.subheader("Possession & Passing")
    
    try:
        # Pobierz statystyki dla wszystkich drużyn w lidze
        engine = get_engine()
        query = f"""
            SELECT * 
            FROM gold.mart_team_possession
            WHERE season_id = {selected_season_id}
        """
        
        with engine.connect() as conn:
            all_teams_df = pd.read_sql(query, conn)
        
        if not all_teams_df.empty:
            team_stats_row = all_teams_df[all_teams_df['team_id'] == selected_team_id]
            
            if team_stats_row.empty:
                st.warning("No possession statistics available for this team.")
            else:
                team_stats = team_stats_row.iloc[0].to_dict()
                
                league_avg, percentiles = calculate_league_stats_and_percentiles(
                    all_teams_df, 
                    team_stats
                )
                
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown("### Possession Radar")
                    
                    metric_config = [
                        ('avg_possession_pct', 'Possession %'),
                        ('pass_accuracy_pct', 'Pass Accuracy %'),
                        ('accurate_passes_per_game', 'Accurate Passes/Game'),
                        ('accurate_long_balls_per_game', 'Long Balls/Game'),
                        ('final_third_entries_per_game', 'Final Third Entries/Game'),
                        ('touches_in_box_per_game', 'Touches in Box/Game')
                    ]
                    
                    metrics = [m[0] for m in metric_config]
                    labels = [m[1] for m in metric_config]
                    
                    scales = calculate_radar_scales(all_teams_df, metrics, padding_pct=0.15)
                    
                    team_values = [float(safe_get(team_stats, m, 0)) for m in metrics]
                    league_values = [float(safe_get(league_avg, m, 0)) for m in metrics]
                    
                    team_normalized = normalize_for_radar(team_values, scales, metrics)
                    league_normalized = normalize_for_radar(league_values, scales, metrics)
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=team_normalized,
                        theta=labels,
                        fill='toself',
                        name=team_name,
                        line_color='#8b5cf6',
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata}<extra></extra>',
                        customdata=[f"{v:.2f}" for v in team_values]
                    ))
                    
                    fig.add_trace(go.Scatterpolar(
                        r=league_normalized,
                        theta=labels,
                        fill='toself',
                        name='League Average',
                        line_color='#9ca3af',
                        opacity=0.5,
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata}<extra></extra>',
                        customdata=[f"{v:.2f}" for v in league_values]
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 1],
                                showticklabels=False
                            )
                        ),
                        showlegend=True,
                        height=500
                    )
                    
                    st.plotly_chart(fig, width='stretch')
                    
                    st.caption("**Scales for each metric:**")
                    scale_text = " | ".join([
                        f"{labels[i]}: {scales[metrics[i]][0]:.1f}-{scales[metrics[i]][1]:.1f}"
                        for i in range(len(metrics))
                    ])
                    st.caption(scale_text)
                
                with col2:
                    st.markdown("### Possession Statistics")
                    
                    possession_data = {
                        'Metric': [
                            'Avg Possession %',
                            'Pass Accuracy %',
                            'Total Passes/Game',
                            'Accurate Passes/Game',
                            'Long Balls/Game',
                            'Accurate Crosses/Game',
                            'Final Third Entries/Game',
                            'Touches in Box/Game',
                            'Dispossessed/Game',
                            'Total Accurate Passes',
                            'Total Passes'
                        ],
                        'Team': [
                            format_percentage(safe_get(team_stats, 'avg_possession_pct')),
                            format_percentage(safe_get(team_stats, 'pass_accuracy_pct')),
                            format_number(safe_get(team_stats, 'total_passes_per_game'), 1),
                            format_number(safe_get(team_stats, 'accurate_passes_per_game'), 1),
                            format_number(safe_get(team_stats, 'accurate_long_balls_per_game'), 2),
                            format_number(safe_get(team_stats, 'accurate_crosses_per_game'), 2),
                            format_number(safe_get(team_stats, 'final_third_entries_per_game'), 2),
                            format_number(safe_get(team_stats, 'touches_in_box_per_game'), 2),
                            format_number(safe_get(team_stats, 'dispossessed_per_game'), 2),
                            format_number(safe_get(team_stats, 'total_accurate_passes'), 0),
                            format_number(safe_get(team_stats, 'total_passes'), 0)
                        ],
                        'League': [
                            format_percentage(safe_get(league_avg, 'avg_possession_pct')),
                            format_percentage(safe_get(league_avg, 'pass_accuracy_pct')),
                            format_number(safe_get(league_avg, 'total_passes_per_game'), 1),
                            format_number(safe_get(league_avg, 'accurate_passes_per_game'), 1),
                            format_number(safe_get(league_avg, 'accurate_long_balls_per_game'), 2),
                            format_number(safe_get(league_avg, 'accurate_crosses_per_game'), 2),
                            format_number(safe_get(league_avg, 'final_third_entries_per_game'), 2),
                            format_number(safe_get(league_avg, 'touches_in_box_per_game'), 2),
                            format_number(safe_get(league_avg, 'dispossessed_per_game'), 2),
                            format_number(safe_get(league_avg, 'total_accurate_passes'), 1),
                            format_number(safe_get(league_avg, 'total_passes'), 1)
                        ],
                        'Pct': [
                            f"{int(percentiles.get('avg_possession_pct', 0))}%" if percentiles.get('avg_possession_pct') else '-',
                            f"{int(percentiles.get('pass_accuracy_pct', 0))}%" if percentiles.get('pass_accuracy_pct') else '-',
                            f"{int(percentiles.get('total_passes_per_game', 0))}%" if percentiles.get('total_passes_per_game') else '-',
                            f"{int(percentiles.get('accurate_passes_per_game', 0))}%" if percentiles.get('accurate_passes_per_game') else '-',
                            f"{int(percentiles.get('accurate_long_balls_per_game', 0))}%" if percentiles.get('accurate_long_balls_per_game') else '-',
                            f"{int(percentiles.get('accurate_crosses_per_game', 0))}%" if percentiles.get('accurate_crosses_per_game') else '-',
                            f"{int(percentiles.get('final_third_entries_per_game', 0))}%" if percentiles.get('final_third_entries_per_game') else '-',
                            f"{int(percentiles.get('touches_in_box_per_game', 0))}%" if percentiles.get('touches_in_box_per_game') else '-',
                            # Dispossessed - lower is better
                            f"{int(100 - percentiles.get('dispossessed_per_game', 100))}%" if percentiles.get('dispossessed_per_game') else '-',
                            f"{int(percentiles.get('total_accurate_passes', 0))}%" if percentiles.get('total_accurate_passes') else '-',
                            f"{int(percentiles.get('total_passes', 0))}%" if percentiles.get('total_passes') else '-'
                        ]
                    }
                    
                    possession_df = pd.DataFrame(possession_data)
                    possession_df = prepare_dataframe_for_display(possession_df)
                    
                    def highlight_percentile(row):
                        colors = [''] * len(row)
                        pct_str = row['Pct']
                        
                        if pct_str == '-':
                            return colors
                        
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
                    
                    styled_df = possession_df.style.apply(highlight_percentile, axis=1)
                    st.dataframe(styled_df, width='stretch', height=425,hide_index=True)
                    
                    st.caption("💡 **Pct** = Percentile (% teams with worse stats)")
        else:
            st.warning("No possession statistics available for this season.")
    
    except Exception as e:
        logger.error(f"Error loading possession stats: {e}")
        st.error(f"Failed to load possession statistics: {e}")
        st.exception(e)


# ============================================================================
# DISCIPLINE TAB
# ============================================================================

with discipline_tab:
    st.subheader("Discipline & Fair Play")
    
    try:
        # Pobierz statystyki dla wszystkich drużyn w lidze
        engine = get_engine()
        query = f"""
            SELECT * 
            FROM gold.mart_team_discipline
            WHERE season_id = {selected_season_id}
        """
        
        with engine.connect() as conn:
            all_teams_df = pd.read_sql(query, conn)
        
        if not all_teams_df.empty:
            team_stats_row = all_teams_df[all_teams_df['team_id'] == selected_team_id]
            
            if team_stats_row.empty:
                st.warning("No discipline statistics available for this team.")
            else:
                team_stats = team_stats_row.iloc[0].to_dict()
                
                league_avg, percentiles = calculate_league_stats_and_percentiles(
                    all_teams_df, 
                    team_stats
                )
                
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown("### Discipline Radar")
                    
                    # For discipline - lower values are better, so we'll invert for visualization
                    metric_config = [
                        ('yellow_cards_per_game', 'Yellow Cards/Game'),
                        ('total_red_cards', 'Red Cards'),
                        ('fouls_per_game', 'Fouls/Game'),
                        ('offsides_per_game', 'Offsides/Game'),
                        ('total_fouls', 'Total Fouls'),
                        ('total_offsides', 'Total Offsides')
                    ]
                    
                    metrics = [m[0] for m in metric_config]
                    labels = [m[1] for m in metric_config]
                    
                    scales = calculate_radar_scales(all_teams_df, metrics, padding_pct=0.15)
                    
                    team_values = [float(safe_get(team_stats, m, 0)) for m in metrics]
                    league_values = [float(safe_get(league_avg, m, 0)) for m in metrics]
                    
                    # For discipline metrics, invert normalization (lower is better)
                    # We'll normalize but then invert the values for display
                    team_normalized_raw = normalize_for_radar(team_values, scales, metrics)
                    league_normalized_raw = normalize_for_radar(league_values, scales, metrics)
                    
                    # Invert: good discipline = high on radar
                    team_normalized = [1 - v for v in team_normalized_raw]
                    league_normalized = [1 - v for v in league_normalized_raw]
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=team_normalized,
                        theta=labels,
                        fill='toself',
                        name=team_name,
                        line_color='#f59e0b',
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata}<extra></extra>',
                        customdata=[f"{v:.2f}" for v in team_values]
                    ))
                    
                    fig.add_trace(go.Scatterpolar(
                        r=league_normalized,
                        theta=labels,
                        fill='toself',
                        name='League Average',
                        line_color='#9ca3af',
                        opacity=0.5,
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata}<extra></extra>',
                        customdata=[f"{v:.2f}" for v in league_values]
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 1],
                                showticklabels=False
                            )
                        ),
                        showlegend=True,
                        height=500
                    )
                    
                    st.plotly_chart(fig, width='stretch')
                    
                    st.caption("**Scales for each metric (lower values = better discipline):**")
                    scale_text = " | ".join([
                        f"{labels[i]}: {scales[metrics[i]][0]:.1f}-{scales[metrics[i]][1]:.1f}"
                        for i in range(len(metrics))
                    ])
                    st.caption(scale_text)
                
                with col2:
                    st.markdown("### Discipline Statistics")
                    
                    discipline_data = {
                        'Metric': [
                            'Yellow Cards/Game',
                            'Total Yellow Cards',
                            'Red Cards',
                            'Fouls/Game',
                            'Total Fouls',
                            'Offsides/Game',
                            'Total Offsides',
                            'Free Kicks/Game',
                            'Total Free Kicks'
                        ],
                        'Team': [
                            format_number(safe_get(team_stats, 'yellow_cards_per_game'), 2),
                            format_number(safe_get(team_stats, 'total_yellow_cards'), 0),
                            format_number(safe_get(team_stats, 'total_red_cards'), 0),
                            format_number(safe_get(team_stats, 'fouls_per_game'), 2),
                            format_number(safe_get(team_stats, 'total_fouls'), 0),
                            format_number(safe_get(team_stats, 'offsides_per_game'), 2),
                            format_number(safe_get(team_stats, 'total_offsides'), 0),
                            format_number(safe_get(team_stats, 'free_kicks_per_game'), 2),
                            format_number(safe_get(team_stats, 'total_free_kicks'), 0)
                        ],
                        'League': [
                            format_number(safe_get(league_avg, 'yellow_cards_per_game'), 2),
                            format_number(safe_get(league_avg, 'total_yellow_cards'), 1),
                            format_number(safe_get(league_avg, 'total_red_cards'), 1),
                            format_number(safe_get(league_avg, 'fouls_per_game'), 2),
                            format_number(safe_get(league_avg, 'total_fouls'), 1),
                            format_number(safe_get(league_avg, 'offsides_per_game'), 2),
                            format_number(safe_get(league_avg, 'total_offsides'), 1),
                            format_number(safe_get(league_avg, 'free_kicks_per_game'), 2),
                            format_number(safe_get(league_avg, 'total_free_kicks'), 1)
                        ],
                        'Pct': [
                            # For discipline - lower is better, so invert
                            f"{int(100 - percentiles.get('yellow_cards_per_game', 100))}%" if percentiles.get('yellow_cards_per_game') else '-',
                            f"{int(100 - percentiles.get('total_yellow_cards', 100))}%" if percentiles.get('total_yellow_cards') else '-',
                            f"{int(100 - percentiles.get('total_red_cards', 100))}%" if percentiles.get('total_red_cards') else '-',
                            f"{int(100 - percentiles.get('fouls_per_game', 100))}%" if percentiles.get('fouls_per_game') else '-',
                            f"{int(100 - percentiles.get('total_fouls', 100))}%" if percentiles.get('total_fouls') else '-',
                            f"{int(100 - percentiles.get('offsides_per_game', 100))}%" if percentiles.get('offsides_per_game') else '-',
                            f"{int(100 - percentiles.get('total_offsides', 100))}%" if percentiles.get('total_offsides') else '-',
                            f"{int(100 - percentiles.get('free_kicks_per_game', 100))}%" if percentiles.get('free_kicks_per_game') else '-',
                            f"{int(100 - percentiles.get('total_free_kicks', 100))}%" if percentiles.get('total_free_kicks') else '-'
                        ]
                    }
                    
                    discipline_df = pd.DataFrame(discipline_data)
                    discipline_df = prepare_dataframe_for_display(discipline_df)
                    
                    def highlight_percentile(row):
                        colors = [''] * len(row)
                        pct_str = row['Pct']
                        
                        if pct_str == '-':
                            return colors
                        
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
                    
                    styled_df = discipline_df.style.apply(highlight_percentile, axis=1)
                    st.dataframe(styled_df, width='stretch', hide_index=True)
                    
                    st.caption("💡 **Pct** = Percentile (% teams with better discipline - lower values are better)")
                    
                    # Fair Play Score
                    st.markdown("---")
                    st.markdown("### Fair Play Rating")
                    
                    total_yellows = safe_get(team_stats, 'total_yellow_cards', 0)
                    total_reds = safe_get(team_stats, 'total_red_cards', 0)
                    matches_played = safe_get(team_stats, 'matches_played', 1)
                    
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
            st.warning("No discipline statistics available for this season.")
    
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
