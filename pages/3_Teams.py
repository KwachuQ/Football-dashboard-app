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
from services.transforms import calculate_win_rate, calculate_form_sequence

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
        attack_stats = get_team_stats(selected_team_id, "attack", selected_season_id)
        
        if attack_stats:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Shots", int(safe_get(attack_stats, 'total_shots', 0)))
                st.metric("Shots on Target", float(safe_get(attack_stats, 'total_shots_on_target', 0)))
            
            with col2:
                st.metric("Shots per Game", format_number(safe_get(attack_stats, 'shots_per_game', 0), 2))
                st.metric("Shots on Target per Game", format_percentage(safe_get(attack_stats, 'shots_on_target_per_game', 0)))
            
            with col3:
                st.metric("Big Chances", int(safe_get(attack_stats, 'total_big_chances_created', 0)))
                st.metric("Big Chances Scored", int(safe_get(attack_stats, 'total_big_chances_scored', 0)))
            
            with col4:
                st.metric("Expected Goals (xG)", format_number(safe_get(attack_stats, 'total_xg', 0), 2))
                st.metric("xG per Game", format_number(safe_get(attack_stats, 'xg_per_game', 0), 2))
        else:
            st.warning("No attack statistics available.")
    except Exception as e:
        logger.error(f"Error loading attack stats: {e}")
        st.error(f"Failed to load attack statistics: {e}")

# ============================================================================
# DEFENSE TAB
# ============================================================================

with defense_tab:
    st.subheader("Defensive Performance")
    
    try:
        defense_stats = get_team_stats(selected_team_id, "defense", selected_season_id)
        
        if defense_stats:
            # Key defensive metrics
            st.markdown("### Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Goals Conceded/Game", format_number(safe_get(defense_stats, 'goalsconcededpergame'), 2))
            
            with col2:
                st.metric("Tackles/Game", format_number(safe_get(defense_stats, 'tacklespergame'), 2))
            
            with col3:
                st.metric("Clearances/Game", format_number(safe_get(defense_stats, 'clearancespergame'), 2))
            
            with col4:
                clean_sheets = safe_get(defense_stats, 'cleansheets', 0)
                st.metric("Clean Sheets", int(clean_sheets))
            
            st.markdown("---")
            
            # Defensive actions chart
            st.markdown("### Defensive Actions per Game")
            
            defensive_actions = {
                'Tackles': safe_get(defense_stats, 'tacklespergame', 0),
                'Interceptions': safe_get(defense_stats, 'interceptionspergame', 0),
                'Clearances': safe_get(defense_stats, 'clearancespergame', 0),
                'Blocked Shots': safe_get(defense_stats, 'blockedshotspergame', 0),
                'Ball Recoveries': safe_get(defense_stats, 'ballrecoveriespergame', 0)
            }
            
            actions_df = pd.DataFrame({
                'Action': list(defensive_actions.keys()),
                'Per Game': list(defensive_actions.values())
            })
            
            fig = px.bar(
                actions_df,
                y='Action',
                x='Per Game',
                orientation='h',
                title="Defensive Actions Breakdown",
                color='Per Game',
                color_continuous_scale='Blues'
            )
            
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch')
            
            st.markdown("---")
            
            # Duel statistics
            st.markdown("### Duel Success Rates")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                aerial_pct = safe_get(defense_stats, 'avgaerialduelspct')
                if aerial_pct:
                    st.metric("Aerial Duels Won", format_percentage(aerial_pct))
            
            with col2:
                ground_pct = safe_get(defense_stats, 'avggroundduelspct')
                if ground_pct:
                    st.metric("Ground Duels Won", format_percentage(ground_pct))
            
            with col3:
                overall_pct = safe_get(defense_stats, 'avgduelswonpct')
                if overall_pct:
                    st.metric("Overall Duels Won", format_percentage(overall_pct))
            
            # Additional defensive stats
            st.markdown("---")
            st.markdown("### Additional Stats")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Goals Conceded", int(safe_get(defense_stats, 'totalgoalsconceded', 0)))
                st.metric("Clean Sheet %", format_percentage(safe_get(defense_stats, 'cleansheetpct')))
            
            with col2:
                tackle_win_pct = safe_get(defense_stats, 'avgtackleswonpct')
                if tackle_win_pct:
                    st.metric("Tackles Won %", format_percentage(tackle_win_pct))
                st.metric("Saves/Game", format_number(safe_get(defense_stats, 'savespergame'), 2))
            
            with col3:
                st.metric("Errors→Goal", int(safe_get(defense_stats, 'totalerrorsleadtogoal', 0)))
                st.metric("Errors→Shot", int(safe_get(defense_stats, 'totalerrorsleadtoshot', 0)))
            
            with col4:
                st.metric("Total Saves", int(safe_get(defense_stats, 'totalsaves', 0)))
                st.metric("Total Tackles", int(safe_get(defense_stats, 'totaltackles', 0)))
        
        else:
            st.warning("No defensive statistics available for this team.")
    
    except Exception as e:
        logger.error(f"Error loading defense stats: {e}")
        st.error("Failed to load defensive statistics")

# ============================================================================
# POSSESSION TAB
# ============================================================================

with possession_tab:
    st.subheader("Possession & Passing")
    
    try:
        possession_stats = get_team_stats(selected_team_id, "possession", selected_season_id)
        
        if possession_stats:
            # Key possession metrics
            st.markdown("### Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                possession_pct = safe_get(possession_stats, 'avgpossessionpct')
                st.metric("Avg Possession", format_percentage(possession_pct))
            
            with col2:
                pass_accuracy = safe_get(possession_stats, 'passaccuracypct')
                st.metric("Pass Accuracy", format_percentage(pass_accuracy))
            
            with col3:
                passes_per_game = safe_get(possession_stats, 'totalpassespergame')
                st.metric("Passes/Game", format_number(passes_per_game, 1))
            
            with col4:
                final_third = safe_get(possession_stats, 'finalthirdentriespergame')
                st.metric("Final Third Entries/Game", format_number(final_third, 2))
            
            st.markdown("---")
            
            # Possession and passing visualization
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Territory Control")
                
                # Create gauge chart for possession
                possession_val = safe_get(possession_stats, 'avgpossessionpct', 50)
                
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=possession_val,
                    title={'text': "Average Possession %"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#3b82f6"},
                        'steps': [
                            {'range': [0, 40], 'color': "#fee2e2"},
                            {'range': [40, 60], 'color': "#fef3c7"},
                            {'range': [60, 100], 'color': "#dcfce7"}
                        ],
                        'threshold': {
                            'line': {'color': "green", 'width': 4},
                            'thickness': 0.75,
                            'value': 70
                        }
                    }
                ))
                
                fig.update_layout(height=300)
                st.plotly_chart(fig, width='stretch')
            
            with col2:
                st.markdown("### Pass Accuracy")
                
                # Pass accuracy gauge
                accuracy_val = safe_get(possession_stats, 'passaccuracypct', 70)
                
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=accuracy_val,
                    title={'text': "Pass Completion %"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#22c55e"},
                        'steps': [
                            {'range': [0, 70], 'color': "#fee2e2"},
                            {'range': [70, 80], 'color': "#fef3c7"},
                            {'range': [80, 100], 'color': "#dcfce7"}
                        ]
                    }
                ))
                
                fig.update_layout(height=300)
                st.plotly_chart(fig, width='stretch')
            
            st.markdown("---")
            
            # Passing statistics
            st.markdown("### Passing Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Passes", int(safe_get(possession_stats, 'totalpasses', 0)))
                st.metric("Accurate Passes", int(safe_get(possession_stats, 'totalaccuratepasses', 0)))
            
            with col2:
                st.metric("Accurate Passes/Game", format_number(safe_get(possession_stats, 'accuratepassespergame'), 1))
                st.metric("Long Balls/Game", format_number(safe_get(possession_stats, 'accuratelongballspergame'), 2))
            
            with col3:
                st.metric("Accurate Crosses/Game", format_number(safe_get(possession_stats, 'accuratecrossespergame'), 2))
                st.metric("Touches in Box/Game", format_number(safe_get(possession_stats, 'touchesinboxpergame', 0), 2))
            
            st.markdown("---")
            
            # Additional stats
            st.markdown("### Additional Stats")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Dispossessed/Game", format_number(safe_get(possession_stats, 'dispossessedpergame'), 2))
            
            with col2:
                throw_ins = safe_get(possession_stats, 'throwinspergame')
                if throw_ins:
                    st.metric("Throw-ins/Game", format_number(throw_ins, 2))
            
            with col3:
                goal_kicks = safe_get(possession_stats, 'goalkickspergame')
                if goal_kicks:
                    st.metric("Goal Kicks/Game", format_number(goal_kicks, 2))
            
            with col4:
                st.metric("Final Third Entries", int(safe_get(possession_stats, 'totalfinalthirdentries', 0)))
        
        else:
            st.warning("No possession statistics available for this team.")
    
    except Exception as e:
        logger.error(f"Error loading possession stats: {e}")
        st.error("Failed to load possession statistics")

# ============================================================================
# DISCIPLINE TAB
# ============================================================================

with discipline_tab:
    st.subheader("Discipline & Fair Play")
    
    try:
        discipline_stats = get_team_stats(selected_team_id, "discipline", selected_season_id)
        
        if discipline_stats:
            # Key discipline metrics
            st.markdown("### Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                yellow_per_game = safe_get(discipline_stats, 'yellowcardspergame')
                st.metric("Yellow Cards/Game", format_number(yellow_per_game, 2))
            
            with col2:
                red_cards = safe_get(discipline_stats, 'totalredcards', 0)
                st.metric("Total Red Cards", int(red_cards))
            
            with col3:
                fouls_per_game = safe_get(discipline_stats, 'foulspergame')
                st.metric("Fouls/Game", format_number(fouls_per_game, 2))
            
            with col4:
                offsides_per_game = safe_get(discipline_stats, 'offsidespergame')
                st.metric("Offsides/Game", format_number(offsides_per_game, 2))
            
            st.markdown("---")
            
            # Card distribution
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Card Distribution")
                
                total_yellows = safe_get(discipline_stats, 'totalyellowcards', 0)
                total_reds = safe_get(discipline_stats, 'totalredcards', 0)
                
                cards_df = pd.DataFrame({
                    'Card Type': ['Yellow Cards', 'Red Cards'],
                    'Total': [total_yellows, total_reds]
                })
                
                fig = px.bar(
                    cards_df,
                    x='Card Type',
                    y='Total',
                    title="Total Cards Received",
                    color='Card Type',
                    color_discrete_map={'Yellow Cards': '#eab308', 'Red Cards': '#ef4444'}
                )
                
                st.plotly_chart(fig, width='stretch')
            
            with col2:
                st.markdown("### Fouls & Offsides")
                
                total_fouls = safe_get(discipline_stats, 'totalfouls', 0)
                total_offsides = safe_get(discipline_stats, 'totaloffsides', 0)
                
                fouls_df = pd.DataFrame({
                    'Type': ['Fouls Committed', 'Offsides'],
                    'Total': [total_fouls, total_offsides]
                })
                
                fig = px.bar(
                    fouls_df,
                    x='Type',
                    y='Total',
                    title="Fouls and Offsides",
                    color='Type',
                    color_discrete_map={'Fouls Committed': '#f59e0b', 'Offsides': '#8b5cf6'}
                )
                
                st.plotly_chart(fig, width='stretch')
            
            st.markdown("---")
            
            # Additional stats
            st.markdown("### Additional Stats")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Yellow Cards", int(total_yellows))
            
            with col2:
                st.metric("Total Fouls", int(total_fouls))
            
            with col3:
                st.metric("Total Offsides", int(total_offsides))
            
            with col4:
                free_kicks = safe_get(discipline_stats, 'freekickspergame')
                if free_kicks:
                    st.metric("Free Kicks/Game", format_number(free_kicks, 2))
            
            # Fair play indicator
            st.markdown("---")
            
            # Calculate fair play score (lower is better)
            matches_played = safe_get(discipline_stats, 'matchesplayed', 1)
            fair_play_score = ((total_yellows * 1) + (total_reds * 3)) / matches_played if matches_played > 0 else 0
            
            if fair_play_score < 2:
                fair_play_rating = "Excellent"
                color = "green"
            elif fair_play_score < 3:
                fair_play_rating = "Good"
                color = "blue"
            elif fair_play_score < 4:
                fair_play_rating = "Average"
                color = "orange"
            else:
                fair_play_rating = "Poor"
                color = "red"
            
            st.markdown(f"**Fair Play Rating:** :{color}[{fair_play_rating}] (Score: {fair_play_score:.2f} cards per game)")
            st.caption("Fair play score = (Yellow cards × 1 + Red cards × 3) / Matches played")
        
        else:
            st.warning("No discipline statistics available for this team.")
    
    except Exception as e:
        logger.error(f"Error loading discipline stats: {e}")
        st.error("Failed to load discipline statistics")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    f"*Data for {selected_season_name} | Selected team: {team_name} | "
    f"Form window: Last {form_window} matches*"
)
