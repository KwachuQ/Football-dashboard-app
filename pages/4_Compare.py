"""
pages/4_Compare.py
Team comparison page based on upcoming fixtures
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional, Dict, Any, Tuple
import logging
import os
import sys
from datetime import date, timedelta

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from components.filters import date_range_filter
from services.queries import (
    get_upcoming_fixtures,
    get_head_to_head,
    get_all_team_stats,
    get_team_form,
    get_league_standings,
    get_btts_analysis,
    get_h2h_results
)

# Configure logging
logger = logging.getLogger(__name__)

# Hide default Streamlit sidebar first item
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] li:first-child {
        display: none;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        padding: 8px;
        border-bottom: 1px solid #e0e0e0;
    }
    .stat-label {
        font-weight: 600;
        color: #555;
    }
    .stat-value {
        font-weight: bold;
        color: #000;
    }
    </style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="Compare Teams - Football Analytics",
    layout="wide"
)
# Custom CSS for styling
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] li:first-child {
        display: none;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        padding: 8px;
        border-bottom: 1px solid #e0e0e0;
    }
    .stat-label {
        font-weight: 600;
        color: #555;
    }
    .stat-value {
        font-weight: bold;
        color: #000;
    }
    /* H2H Match Result Boxes */
    .h2h-match-box {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 4px 0;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .h2h-match-box.winner {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-color: #28a745;
        font-weight: 600;
    }
    .h2h-team-name {
        font-size: 13px;
        flex-grow: 1;
    }
    .h2h-score {
        font-size: 15px;
        font-weight: bold;
        min-width: 20px;
        text-align: center;
        margin-left: 8px;
    }
    /* Team Name Boxes */
    .team-name-box {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px 20px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        font-size: 30px;
        font-weight: 700;
        line-height: 1.05;
    }
    /* Stat Boxes */
    .stat-box {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px 16px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 4px 0;
    }
    .stat-box-label {
        font-size: 12px;
        color: #6b7280;
        margin-bottom: 4px;
    }
    .stat-box-value {
        font-size: 24px;
        font-weight: 700;
        color: #111827;
    }
    </style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_get(data: Optional[Dict[str, Any]], key: str, default: Any = 0) -> Any:
    """Safely get value from dict."""
    if not data:
        return default
    value = data.get(key, default)
    return default if value is None else value

def format_percentage(value: Optional[float]) -> str:
    """Format float as percentage string."""
    if value is None:
        return "N/A"
    return f"{float(value):.1f}%"

def format_number(value: Optional[float], decimals: int = 2) -> str:
    """Format number with specified decimals."""
    if value is None:
        return "N/A"
    return f"{float(value):.{decimals}f}"

def calculate_percentage_diff(val1: float, val2: float) -> Tuple[float, str]:
    """Calculate percentage difference between two values."""
    if val2 == 0:
        return 0.0, "0%"
    diff = ((val1 - val2) / val2) * 100
    sign = "+" if diff > 0 else ""
    return diff, f"{sign}{diff:.1f}%"

def get_chance_category(percentage_diff: float) -> Tuple[str, str]:
    """Determine scoring chance category based on percentage difference."""
    abs_diff = abs(percentage_diff)
    
    if abs_diff < 45:
        return "Uncertain", "🟡"
    elif abs_diff < 60:
        return "Medium Chance", "🟠"
    else:
        return "High Chance", "🟢"

def parse_form_string(form_string: Optional[str], max_length: int = 5) -> list:
    """Parse form string (e.g., 'WWDLW') into list."""
    if not form_string:
        return []
    return list(form_string[:max_length])

def format_form_html(results: list) -> str:
    """Convert form results to HTML with colored boxes."""
    colors = {"W": "#22c55e", "D": "#eab308", "L": "#ef4444"}
    html = ""
    for result in results:
        color = colors.get(result, "#6b7280")
        html += (
            f'<span style="display:inline-block; width:30px; height:30px; '
            f'background-color:{color}; color:white; text-align:center; '
            f'line-height:30px; margin:2px; border-radius:4px; '
            f'font-weight:bold; font-size:12px;">{result}</span>'
        )
    return html

# ============================================================================
# MAIN PAGE
# ============================================================================

st.title("Head 2 Head Teams Comparison")
st.markdown("Compare two teams based on upcoming fixtures")
st.markdown("---")

# ============================================================================
# FIXTURE SELECTOR
# ============================================================================

with st.sidebar:
    st.header("Select Fixture")
    
    # Get active season from session state (set in Home page)
    season_id = st.session_state.get('active_season_id', 1)
    
    try:
        # Get upcoming fixtures with explicit date range
        
        
        today = date.today()
        default_end = today + timedelta(days=45)  # Look ahead 45 days
        
        start_date, end_date = date_range_filter(
        key="fixtures_date_range",
        min_date=today,
        max_date=today + timedelta(days=365),
        default_start=today,
        default_end=default_end,
    )
        fixtures_df = get_upcoming_fixtures(
            season_id=season_id,
            start_date=today,
            end_date=end_date,
            limit=50
        )
        
        if fixtures_df.empty:
            st.warning("No upcoming fixtures available for the selected season")
            st.info(f"Looking for fixtures between {today} and {end_date}")
            st.stop()
        
        # Create fixture display string
        fixtures_df['fixture_display'] = fixtures_df.apply(
            lambda row: f"{row['home_team']} vs {row['away_team']} - {row['match_date'].strftime('%d-%m-%Y')}",
            axis=1
        )
        
        selected_fixture = st.selectbox(
            "Choose a fixture to compare",
            options=fixtures_df['fixture_display'].tolist(),
            key="compare_fixture_selector"
        )
        
        # Get selected match data
        selected_idx = fixtures_df[fixtures_df['fixture_display'] == selected_fixture].index[0]
        match_data = fixtures_df.loc[selected_idx]
        
        home_team_id = int(match_data['home_team_id'])
        away_team_id = int(match_data['away_team_id'])
        home_team_name = match_data['home_team']
        away_team_name = match_data['away_team']
        match_date = match_data['match_date']
        
    except Exception as e:
        logger.error(f"Error loading fixtures: {e}")
        st.error(f"Failed to load fixtures: {e}")
        st.exception(e)
        st.stop()


# ============================================================================
# LOAD DATA FOR BOTH TEAMS
# ============================================================================

try:
    # Get head-to-head data
    h2h_data = get_head_to_head(home_team_id, away_team_id)
    
    # Get all stats for both teams
    home_stats = get_all_team_stats(home_team_id, season_id)
    away_stats = get_all_team_stats(away_team_id, season_id)
    
    # Get BTTS analysis
    home_btts = get_btts_analysis(home_team_id, season_id)
    away_btts = get_btts_analysis(away_team_id, season_id)
    
    # Get team forms (last 5, 10, 15, 20)
    home_form_5 = get_team_form(home_team_id, 5)
    away_form_5 = get_team_form(away_team_id, 5)
    
    # Get league standings for position
    standings_df = get_league_standings(season_id)
    home_position = standings_df[standings_df['team_id'] == home_team_id].index[0] + 1 if not standings_df.empty else "N/A"
    away_position = standings_df[standings_df['team_id'] == away_team_id].index[0] + 1 if not standings_df.empty else "N/A"
    total_teams = len(standings_df)
    
except Exception as e:
    logger.error(f"Error loading team data: {e}")
    st.error(f"Failed to load team data: {e}")
    st.stop()

# ============================================================================
# SECTION 1: HEAD-TO-HEAD STATISTICS
# ============================================================================

with st.expander("Head-to-Head Statistics", expanded=True, width='stretch'):
    if h2h_data and h2h_data.get('total_matches', 0) > 0:
        
        # Determine which team is team1 and team2
        if h2h_data['team1_id'] == home_team_id:
            home_wins = h2h_data['team1_wins']
            away_wins = h2h_data['team2_wins']
            home_goals = h2h_data['team1_goals']
            away_goals = h2h_data['team2_goals']
        else:
            home_wins = h2h_data['team2_wins']
            away_wins = h2h_data['team1_wins']
            home_goals = h2h_data['team2_goals']
            away_goals = h2h_data['team1_goals']
        
        draws = h2h_data['draws']
        total_matches = h2h_data['total_matches']
        
        # Win percentages
        home_win_pct = (home_wins / total_matches) * 100
        draw_pct = (draws / total_matches) * 100
        away_win_pct = (away_wins / total_matches) * 100
        
        # --- Visual bar (H2H) ---

        # --- normalize to 100 ---
        total_pct = home_win_pct + draw_pct + away_win_pct
        if total_pct > 0:
            s = 100.0 / total_pct
            hw, dr, aw = home_win_pct * s, draw_pct * s, away_win_pct * s
        else:
            hw = dr = aw = 0.0

        total_matches = home_wins + draws + away_wins

        # ---------- Single row: home | center(date+bar) | away ----------
        left_col, center_col, right_col = st.columns(
            [1, 2, 1],
            gap="small",
            vertical_alignment="center",
            border=False
        )

        with left_col:
            st.markdown(
                f"""
                <div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; padding: 8px;">
                    <div class="team-name-box" style="width: 100%;">
                        {home_team_name}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
                width="stretch",
            )

        with right_col:
            st.markdown(
                f"""
                <div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; padding: 8px;">
                    <div class="team-name-box" style="width: 100%;">
                        {away_team_name}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
                width="stretch",
            )

        # ---------- Center column: match date + bar ----------
        with center_col:
            st.markdown(
                f"""
                <div style="text-align:center; white-space:nowrap; color:#6b7280; font-size:12px; margin-bottom:8px;">
                    Match Date: {match_date.strftime('%Y-%m-%d %H:%M')}
                </div>
                """,
                unsafe_allow_html=True
            )

            # Visual bar (rectangle, no rounding)
            fig = go.Figure()

            fig.add_trace(go.Bar(
                y=["H2H"],
                x=[home_win_pct],
                orientation="h",
                marker=dict(color="#22c55e"),
                text=[f"<b>{home_win_pct:.0f}%</b>"],
                textposition="inside",
                insidetextanchor="middle",
                name=home_team_name,
            ))
            fig.add_trace(go.Bar(
                y=["H2H"],
                x=[draw_pct],
                orientation="h",
                marker=dict(color="#eab308"),
                text=[f"<b>{draw_pct:.0f}%</b>"],
                textposition="inside",
                insidetextanchor="middle",
                name="Draws",
            ))
            fig.add_trace(go.Bar(
                y=["H2H"],
                x=[away_win_pct],
                orientation="h",
                marker=dict(color="#ef4444"),
                text=[f"<b>{away_win_pct:.0f}%</b>"],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white"),
                name=away_team_name,
            ))

            fig.update_layout(
                barmode="stack",
                showlegend=False,
                height=230,
                margin=dict(l=0, r=0, t=70, b=65),
                xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, zeroline=False),
                yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                uniformtext=dict(minsize=20, mode="hide"),
            )

            fig.add_annotation(
                x=0.5, y=1.23, xref="paper", yref="paper",
                text=f"<b>{total_matches} Matches</b>",
                showarrow=False, xanchor="center", yanchor="bottom",
                font=dict(size=22, color="#111827"),
            )

            mid_home = home_win_pct / 2
            mid_draw = home_win_pct + draw_pct / 2
            mid_away = home_win_pct + draw_pct + away_win_pct / 2

            fig.add_annotation(
                x=mid_home, y=-0.14, xref="x", yref="paper",
                text=f"<b>{home_wins} Wins</b>",
                showarrow=False, align="center",
                font=dict(size=15, color="#111827"),
            )
            fig.add_annotation(
                x=mid_draw, y=-0.14, xref="x", yref="paper",
                text=f"<b>{draws} Draws</b>",
                showarrow=False, align="center",
                font=dict(size=15, color="#111827"),
            )
            fig.add_annotation(
                x=mid_away, y=-0.14, xref="x", yref="paper",
                text=f"<b>{away_wins} Wins</b>",
                showarrow=False, align="center",
                font=dict(size=15, color="#111827"),
            )

            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

                    
        # Statistics grid
        st.markdown("#### Match Statistics")
                    
        col1, col2, col3, col4 = st.columns(4)
                    
        with col1:
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-box-label">{home_team_name} Goals</div>
                    <div class="stat-box-value">{home_goals}</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-box-label">{away_team_name} Goals</div>
                    <div class="stat-box-value">{away_goals}</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            home_cs_pct = safe_get(home_btts, 'overall_clean_sheet_pct', 0)
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-box-label">{home_team_name} Clean Sheets</div>
                    <div class="stat-box-value">{format_percentage(home_cs_pct)}</div>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            away_cs_pct = safe_get(away_btts, 'overall_clean_sheet_pct', 0)
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-box-label">{away_team_name} Clean Sheets</div>
                    <div class="stat-box-value">{format_percentage(away_cs_pct)}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Over/Under stats
        st.markdown("#### Goal Totals in H2H Matches")
        
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-box-label">Over 1.5 Goals</div>
                    <div class="stat-box-value">{format_percentage(safe_get(h2h_data, 'over_15_pct', 0))}</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-box-label">Over 2.5 Goals</div>
                    <div class="stat-box-value">{format_percentage(safe_get(h2h_data, 'over_25_pct', 0))}</div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-box-label">Over 3.5 Goals</div>
                    <div class="stat-box-value">{format_percentage(safe_get(h2h_data, 'over_35_pct', 0))}</div>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-box-label">BTTS</div>
                    <div class="stat-box-value">{format_percentage(safe_get(h2h_data, 'btts_pct', 0))}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Past results - actual match history
        st.markdown("#### Last 5 Meetings")
        
        try:
            h2h_results_df = get_h2h_results(home_team_id, away_team_id, limit=5)
            
            if not h2h_results_df.empty:
                # Create columns for each match
                cols = st.columns(len(h2h_results_df))
                
                for idx, (col, (_, row)) in enumerate(zip(cols, h2h_results_df.iterrows())):
                    with col:
                        # Format date
                        match_date = pd.to_datetime(row['match_date']).strftime('%b %d, %Y')
                        st.caption(match_date)
                        
                        # Determine winner
                        home_won = row['home_score'] > row['away_score']
                        away_won = row['away_score'] > row['home_score']
                        
                        # Display home team box
                        home_class = "h2h-match-box winner" if home_won else "h2h-match-box"
                        st.markdown(
                            f'<div class="{home_class}">'
                            f'<span class="h2h-team-name">{row["home_team"]}</span>'
                            f'<span class="h2h-score">{int(row["home_score"])}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        
                        # Display away team box
                        away_class = "h2h-match-box winner" if away_won else "h2h-match-box"
                        st.markdown(
                            f'<div class="{away_class}">'
                            f'<span class="h2h-team-name">{row["away_team"]}</span>'
                            f'<span class="h2h-score">{int(row["away_score"])}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                
            else:
                st.info("No previous matches found between these teams in the database")
                
        except Exception as e:
            logger.error(f"Error loading H2H match results: {e}")
            st.warning("Could not load recent match results")
# ============================================================================
# SECTIONS 2 & 3: TEAM CARDS (Side by Side)
# ============================================================================

st.markdown("---")
st.markdown("## Team Profiles")

col_home, col_away = st.columns(2)

def render_team_card(
    col,
    team_name: str,
    team_position: int | str,
    total_teams: int,
    stats: Dict[str, Any],
    btts_data: Dict[str, Any],
    form_data: Dict[str, Any],
    location: str = "home"  # "home" or "away"
):
    """Render team card with form and stats."""
    with col:
        st.markdown(f"### {team_name}")
        st.caption(f"League Position: {team_position}/{total_teams}")
        
        # Form section
        with st.expander(f"📈 Form", expanded=True):
            # Overall form
            overall_results = parse_form_string(safe_get(form_data, 'last_results', ''), 5)
            overall_ppg = safe_get(form_data, 'points_last', 0) / 5 if overall_results else 0
            
            st.markdown("**Overall (Last 5)**")
            if overall_results:
                st.markdown(format_form_html(overall_results), unsafe_allow_html=True)
                st.caption(f"PPG: {overall_ppg:.2f}")
            
            # Home/Away specific form
            st.markdown(f"**{location.capitalize()} (Last 5)**")
            
            # Use last_5_results_home or last_5_results_away from form_data
            location_key = f'last_5_results_{location}'
            points_key = f'points_last_5_{location}'
            
            location_results = parse_form_string(safe_get(form_data, location_key, ''), 5)
            location_ppg = safe_get(form_data, points_key, 0) / 5 if location_results else 0
            
            if location_results:
                st.markdown(format_form_html(location_results), unsafe_allow_html=True)
                st.caption(f"PPG: {location_ppg:.2f}")
            else:
                st.info(f"No {location} form data available") 
        
        # Stats table
        with st.expander("📊 Statistics", expanded=True):
            # Get relevant stats based on location
            overview = stats.get('overview', {})
            attack = stats.get('attack', {})
            defense = stats.get('defense', {})
            
            # Create tabs for Overall, Home, Away
            tab1, tab2, tab3 = st.tabs(["Overall", "Home", "Away"])
            
            with tab1:
                render_stats_table(overview, attack, defense, btts_data, "overall")
            
            with tab2:
                render_stats_table(overview, attack, defense, btts_data, "home")
            
            with tab3:
                render_stats_table(overview, attack, defense, btts_data, "away")

def render_stats_table(overview, attack, defense, btts_data, location_key):
    """Render statistics table for a specific location (overall/home/away)."""
    
    if location_key == "overall":
        win_pct = safe_get(overview, 'wins', 0) / safe_get(overview, 'matches_played', 1) * 100 if overview else 0
        avg_total = safe_get(btts_data, 'overall_avg_goals_per_match', 0)
        scored = safe_get(attack, 'goals_per_game', 0)
        conceded = safe_get(defense, 'goals_conceded_per_game', 0)
        btts_pct = safe_get(btts_data, 'overall_btts_pct', 0)
        cs_pct = safe_get(btts_data, 'overall_clean_sheet_pct', 0)
        # Calculate FTS from BTTS data
        fts_pct = safe_get(btts_data, 'overall_clean_sheet_pct', 0)  # Opponent didn't score = we failed to score
        xg = safe_get(attack, 'xg_per_game', 0)
        xga = safe_get(defense, 'xga_per_game', 0)
    elif location_key == "home":
        win_pct = safe_get(btts_data, 'home_win_pct', 0)
        avg_total = safe_get(btts_data, 'home_avg_goals_per_match', 0)
        scored = safe_get(btts_data, 'home_avg_scored', 0)
        conceded = safe_get(btts_data, 'home_avg_conceded', 0)
        btts_pct = safe_get(btts_data, 'home_btts_pct', 0)
        cs_pct = safe_get(btts_data, 'home_clean_sheet_pct', 0)
        fts_pct = safe_get(btts_data, 'home_failed_to_score_pct', 0)
        xg = safe_get(btts_data, 'home_avg_xg', 0)
        xga = safe_get(btts_data, 'home_avg_xga', 0)
    else:  # away
        win_pct = safe_get(btts_data, 'away_win_pct', 0)
        avg_total = safe_get(btts_data, 'away_avg_goals_per_match', 0)
        scored = safe_get(btts_data, 'away_avg_scored', 0)
        conceded = safe_get(btts_data, 'away_avg_conceded', 0)
        btts_pct = safe_get(btts_data, 'away_btts_pct', 0)
        cs_pct = safe_get(btts_data, 'away_clean_sheet_pct', 0)
        fts_pct = safe_get(btts_data, 'away_failed_to_score_pct', 0)
        xg = safe_get(btts_data, 'away_avg_xg', 0)
        xga = safe_get(btts_data, 'away_avg_xga', 0)
    
    data = {
        'Stat': ['Win %', 'AVG', 'Scored', 'Conceded', 'BTTS %', 'CS %', 'FTS %', 'xG', 'xGA'],
        'Value': [
            format_percentage(win_pct),
            format_number(avg_total, 2),
            format_number(scored, 2),
            format_number(conceded, 2),
            format_percentage(btts_pct),
            format_percentage(cs_pct),
            format_percentage(fts_pct),
            format_number(xg, 2),
            format_number(xga, 2)
        ]
    }
    
    df = pd.DataFrame(data)
    st.dataframe(df, hide_index=True, width='stretch')

# Render both team cards
render_team_card(
    col_home,
    home_team_name,
    home_position,
    total_teams,
    home_stats,
    home_btts,
    home_form_5,
    "home"
)

render_team_card(
    col_away,
    away_team_name,
    away_position,
    total_teams,
    away_stats,
    away_btts,
    away_form_5,
    "away"
)

# ============================================================================
# SECTION 4: CURRENT FORM COMPARISON
# ============================================================================

st.markdown("---")
st.markdown("## 📊 Current Form Comparison")

with st.expander("Form Analysis", expanded=True):
    # PPG comparison - Home team's home PPG vs Away team's away PPG
    # Get actual home/away wins, draws, losses from season summary
    season_summary_home = home_stats.get('season_summary', {})
    season_summary_away = away_stats.get('season_summary', {})
    
    # Home team's home record
    home_wins_home = safe_get(season_summary_home, 'home_wins', 0)
    home_draws_home = safe_get(season_summary_home, 'home_draws', 0)
    home_losses_home = safe_get(season_summary_home, 'home_losses', 0)
    home_matches_home = home_wins_home + home_draws_home + home_losses_home
    
    # Calculate PPG for home team at home
    home_ppg_home = (home_wins_home * 3 + home_draws_home * 1) / home_matches_home if home_matches_home > 0 else 0
    
    # Away team's away record
    away_wins_away = safe_get(season_summary_away, 'away_wins', 0)
    away_draws_away = safe_get(season_summary_away, 'away_draws', 0)
    away_losses_away = safe_get(season_summary_away, 'away_losses', 0)
    away_matches_away = away_wins_away + away_draws_away + away_losses_away
    
    # Calculate PPG for away team away
    away_ppg_away = (away_wins_away * 3 + away_draws_away * 1) / away_matches_away if away_matches_away > 0 else 0
    
    ppg_diff, ppg_diff_str = calculate_percentage_diff(home_ppg_home, away_ppg_away)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.metric(f"{home_team_name} PPG (Home)", f"{home_ppg_home:.2f}")
        st.caption(f"{home_wins_home}W {home_draws_home}D in {home_matches_home} matches")
    
    with col2:
        st.markdown(f"### {home_team_name} (Home) is {ppg_diff_str} in PPG compared to {away_team_name} (Away)")
        
        # Visual comparison bar
        max_ppg = max(home_ppg_home, away_ppg_away, 3.0)
        home_pct = (home_ppg_home / max_ppg) * 100
        away_pct = (away_ppg_away / max_ppg) * 100
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=[f"{home_team_name} (Home)"],
            x=[home_ppg_home],
            orientation='h',
            marker=dict(color='#22c55e'),
            text=f"{home_ppg_home:.2f}",
            textposition='inside'
        ))
        fig.add_trace(go.Bar(
            y=[f"{away_team_name} (Away)"],
            x=[away_ppg_away],
            orientation='h',
            marker=dict(color='#ef4444'),
            text=f"{away_ppg_away:.2f}",
            textposition='inside'
        ))
        
        fig.update_layout(
            showlegend=False,
            height=150,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(title="Points Per Game (Current Season)"),
        )
        st.plotly_chart(fig, width = 'stretch')
    
    with col3:
        st.metric(f"{away_team_name} PPG (Away)", f"{away_ppg_away:.2f}")
        st.caption(f"{away_wins_away}W {away_draws_away}D in {away_matches_away} matches")
    
    # Last 5 results breakdown
    st.markdown("#### Last 5 Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Overall**")
        home_results = parse_form_string(safe_get(home_form_5, 'last_results', ''), 5)
        away_results = parse_form_string(safe_get(away_form_5, 'last_results', ''), 5)
        
        st.markdown(f"{home_team_name}: {format_form_html(home_results)}", unsafe_allow_html=True)
        st.markdown(f"{away_team_name}: {format_form_html(away_results)}", unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Home**")
        home_home_results = parse_form_string(safe_get(home_form_5, 'last_5_results_home', ''), 5)
        away_home_results = parse_form_string(safe_get(away_form_5, 'last_5_results_home', ''), 5)
        
        if home_home_results:
            st.markdown(f"{home_team_name}: {format_form_html(home_home_results)}", unsafe_allow_html=True)
            home_home_ppg = safe_get(home_form_5, 'points_last_5_home', 0) / 5
            st.caption(f"PPG: {home_home_ppg:.2f}")
        else:
            st.info("No home form data available")
            
        if away_home_results:
            st.markdown(f"{away_team_name}: {format_form_html(away_home_results)}", unsafe_allow_html=True)
            away_home_ppg = safe_get(away_form_5, 'points_last_5_home', 0) / 5
            st.caption(f"PPG: {away_home_ppg:.2f}")
        else:
            st.info("No home form data available")
    
    with col3:
        st.markdown("**Away**")
        home_away_results = parse_form_string(safe_get(home_form_5, 'last_5_results_away', ''), 5)
        away_away_results = parse_form_string(safe_get(away_form_5, 'last_5_results_away', ''), 5)
        
        if home_away_results:
            st.markdown(f"{home_team_name}: {format_form_html(home_away_results)}", unsafe_allow_html=True)
            home_away_ppg = safe_get(home_form_5, 'points_last_5_away', 0) / 5
            st.caption(f"PPG: {home_away_ppg:.2f}")
        else:
            st.info("No away form data available")
            
        if away_away_results:
            st.markdown(f"{away_team_name}: {format_form_html(away_away_results)}", unsafe_allow_html=True)
            away_away_ppg = safe_get(away_form_5, 'points_last_5_away', 0) / 5
            st.caption(f"PPG: {away_away_ppg:.2f}")
        else:
            st.info("No away form data available")

# ============================================================================
# SECTION 5: GOALS SCORED COMPARISON
# ============================================================================

st.markdown("---")
st.markdown("## ⚽ Goals Scored Comparison")

with st.expander("Scoring Analysis", expanded=True):
    # ...existing scoring comparison code...
    
    # Scored per game breakdown
    st.markdown("#### Scored Per Game")
    
    # Tabs for Full-Time vs Halves
    tab1, tab2 = st.tabs(["Full-Time", "1st Half / 2nd Half"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**{home_team_name} (Home)**")
            home_scoring_data = {
                'Metric': ['Over 0.5', 'Over 1.5', 'Over 2.5', 'Over 3.5', 'Failed to Score'],
                'Percentage': [
                    format_percentage(safe_get(home_btts, 'home_scored_over_05_pct', 0)),
                    format_percentage(safe_get(home_btts, 'home_scored_over_15_pct', 0)),
                    format_percentage(safe_get(home_btts, 'home_scored_over_25_pct', 0)),
                    format_percentage(safe_get(home_btts, 'home_scored_over_35_pct', 0)),
                    format_percentage(safe_get(home_btts, 'home_failed_to_score_pct', 0))
                ]
            }
            st.dataframe(home_scoring_data, hide_index=True, width='stretch')
        
        with col2:
            st.markdown(f"**{away_team_name} (Away)**")
            away_scoring_data = {
                'Metric': ['Over 0.5', 'Over 1.5', 'Over 2.5', 'Over 3.5', 'Failed to Score'],
                'Percentage': [
                    format_percentage(safe_get(away_btts, 'away_scored_over_05_pct', 0)),
                    format_percentage(safe_get(away_btts, 'away_scored_over_15_pct', 0)),
                    format_percentage(safe_get(away_btts, 'away_scored_over_25_pct', 0)),
                    format_percentage(safe_get(away_btts, 'away_scored_over_35_pct', 0)),
                    format_percentage(safe_get(away_btts, 'away_failed_to_score_pct', 0))
                ]
            }
            st.dataframe(away_scoring_data, hide_index=True, width='stretch')
    
    with tab2:
        # Get season summary data for half-time stats
        try:
            home_season = get_all_team_stats(home_team_id, season_id).get('season_summary', {})
            away_season = get_all_team_stats(away_team_id, season_id).get('season_summary', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**{home_team_name} (Home)**")
                home_halves_data = {
                    'Metric': ['Scored in 1H', 'Scored in 2H', 'Both Halves', 'Avg 1H Goals', 'Avg 2H Goals'],
                    'Value': [
                        format_percentage(safe_get(home_season, 'home_scored_1h_pct', 0)),
                        format_percentage(safe_get(home_season, 'home_scored_2h_pct', 0)),
                        format_percentage(safe_get(home_season, 'home_scored_both_halves_pct', 0)),
                        format_number(safe_get(home_season, 'home_avg_goals_1h', 0), 2),
                        format_number(safe_get(home_season, 'home_avg_goals_2h', 0), 2)
                    ]
                }
                st.dataframe(home_halves_data, hide_index=True, width='stretch')
            
            with col2:
                st.markdown(f"**{away_team_name} (Away)**")
                away_halves_data = {
                    'Metric': ['Scored in 1H', 'Scored in 2H', 'Both Halves', 'Avg 1H Goals', 'Avg 2H Goals'],
                    'Value': [
                        format_percentage(safe_get(away_season, 'away_scored_1h_pct', 0)),
                        format_percentage(safe_get(away_season, 'away_scored_2h_pct', 0)),
                        format_percentage(safe_get(away_season, 'away_scored_both_halves_pct', 0)),
                        format_number(safe_get(away_season, 'away_avg_goals_1h', 0), 2),
                        format_number(safe_get(away_season, 'away_avg_goals_2h', 0), 2)
                    ]
                }
                st.dataframe(away_halves_data, hide_index=True, width='stretch')
                
        except Exception as e:
            logger.error(f"Error loading half-time scoring data: {e}")
            st.info("⚠️ Half-time scoring data not available")

# ============================================================================
# SECTION 6: GOALS CONCEDED COMPARISON
# ============================================================================

st.markdown("---")
st.markdown("## 🛡️ Goals Conceded Comparison")

with st.expander("Defensive Analysis", expanded=True):
    # ...existing defensive comparison code...
    
    # Conceded per game breakdown
    st.markdown("#### Conceded Per Game")
    
    tab1, tab2 = st.tabs(["Full-Time", "1st Half / 2nd Half"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**{home_team_name} (Home)**")
            home_conceded_data = {
                'Metric': ['Over 0.5', 'Over 1.5', 'Over 2.5', 'Over 3.5', 'Clean Sheets'],
                'Percentage': [
                    format_percentage(safe_get(home_btts, 'home_conceded_over_05_pct', 0)),
                    format_percentage(safe_get(home_btts, 'home_conceded_over_15_pct', 0)),
                    format_percentage(safe_get(home_btts, 'home_conceded_over_25_pct', 0)),
                    format_percentage(safe_get(home_btts, 'home_conceded_over_35_pct', 0)),
                    format_percentage(safe_get(home_btts, 'home_clean_sheet_pct', 0))
                ]
            }
            st.dataframe(home_conceded_data, hide_index=True, width='stretch')
        
        with col2:
            st.markdown(f"**{away_team_name} (Away)**")
            away_conceded_data = {
                'Metric': ['Over 0.5', 'Over 1.5', 'Over 2.5', 'Over 3.5', 'Clean Sheets'],
                'Percentage': [
                    format_percentage(safe_get(away_btts, 'away_conceded_over_05_pct', 0)),
                    format_percentage(safe_get(away_btts, 'away_conceded_over_15_pct', 0)),
                    format_percentage(safe_get(away_btts, 'away_conceded_over_25_pct', 0)),
                    format_percentage(safe_get(away_btts, 'away_conceded_over_35_pct', 0)),
                    format_percentage(safe_get(away_btts, 'away_clean_sheet_pct', 0))
                ]
            }
            st.dataframe(away_conceded_data, hide_index=True, width='stretch')
    
    with tab2:
        try:
            home_season = get_all_team_stats(home_team_id, season_id).get('season_summary', {})
            away_season = get_all_team_stats(away_team_id, season_id).get('season_summary', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**{home_team_name} (Home)**")
                home_def_halves = {
                    'Metric': ['1H Clean Sheet', '2H Clean Sheet', 'Avg 1H Conceded', 'Avg 2H Conceded'],
                    'Value': [
                        format_percentage(safe_get(home_season, 'home_clean_sheet_1h_pct', 0)),
                        format_percentage(safe_get(home_season, 'home_clean_sheet_2h_pct', 0)),
                        format_number(safe_get(home_season, 'home_avg_conceded_1h', 0), 2),
                        format_number(safe_get(home_season, 'home_avg_conceded_2h', 0), 2)
                    ]
                }
                st.dataframe(home_def_halves, hide_index=True, width='stretch')
            
            with col2:
                st.markdown(f"**{away_team_name} (Away)**")
                away_def_halves = {
                    'Metric': ['1H Clean Sheet', '2H Clean Sheet', 'Avg 1H Conceded', 'Avg 2H Conceded'],
                    'Value': [
                        format_percentage(safe_get(away_season, 'away_clean_sheet_1h_pct', 0)),
                        format_percentage(safe_get(away_season, 'away_clean_sheet_2h_pct', 0)),
                        format_number(safe_get(away_season, 'away_avg_conceded_1h', 0), 2),
                        format_number(safe_get(away_season, 'away_avg_conceded_2h', 0), 2)
                    ]
                }
                st.dataframe(away_def_halves, hide_index=True, width='stretch')
                
        except Exception as e:
            logger.error(f"Error loading half-time defensive data: {e}")
            st.info("⚠️ Half-time defensive data not available")

# ============================================================================
# SECTION 7: WILL TEAMS SCORE?
# ============================================================================

st.markdown("---")
st.markdown("## 🎯 Will Teams Score?")

with st.expander("Scoring Probability", expanded=True):
    # Home team scoring probability
    home_scored_pct = safe_get(home_btts, 'home_scored_over_05_pct', 0)  # % of home matches where they scored
    away_cs_pct = safe_get(away_btts, 'away_clean_sheet_pct', 0)  # % of away matches where opponent didn't score
    
    # Away team scoring probability
    away_scored_pct = safe_get(away_btts, 'away_scored_over_05_pct', 0)
    home_cs_pct = safe_get(home_btts, 'home_clean_sheet_pct', 0)
    
    # Calculate scoring chances
    home_score_diff = home_scored_pct - away_cs_pct
    away_score_diff = away_scored_pct - home_cs_pct
    
    home_chance_category, home_chance_icon = get_chance_category(home_score_diff)
    away_chance_category, away_chance_icon = get_chance_category(away_score_diff)
    
    # Display
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### Will {home_team_name} Score?")
        
        st.metric(
            f"{home_team_name} scored in (Home)",
            format_percentage(home_scored_pct),
            help="Percentage of home matches where this team scored"
        )
        st.metric(
            f"{away_team_name} clean sheets (Away)",
            format_percentage(away_cs_pct),
            help="Percentage of away matches where opponent didn't score"
        )
        
        # Verdict
        st.markdown(f"### {home_chance_icon} {home_chance_category}")
        
        if home_score_diff > 0:
            st.success(f"{home_team_name} has scored in {home_scored_pct:.1f}% of home matches, while {away_team_name} kept clean sheets in only {away_cs_pct:.1f}% of away matches.")
        else:
            st.warning(f"{away_team_name} has strong away defense ({away_cs_pct:.1f}% clean sheets), which may limit {home_team_name}'s scoring.")
        
        # Visual gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=home_scored_pct,
            title={'text': "Scoring Probability"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#22c55e"},
                'steps': [
                    {'range': [0, 50], 'color': "#fee2e2"},
                    {'range': [50, 75], 'color': "#fef3c7"},
                    {'range': [75, 100], 'color': "#dcfce7"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': away_cs_pct
                }
            }
        ))
        fig.update_layout(height=250)
        st.plotly_chart(fig, width = 'stretch')
    
    with col2:
        st.markdown(f"### Will {away_team_name} Score?")
        
        st.metric(
            f"{away_team_name} scored in (Away)",
            format_percentage(away_scored_pct),
            help="Percentage of away matches where this team scored"
        )
        st.metric(
            f"{home_team_name} clean sheets (Home)",
            format_percentage(home_cs_pct),
            help="Percentage of home matches where opponent didn't score"
        )
        
        # Verdict
        st.markdown(f"### {away_chance_icon} {away_chance_category}")
        
        if away_score_diff > 0:
            st.success(f"{away_team_name} has scored in {away_scored_pct:.1f}% of away matches, while {home_team_name} kept clean sheets in only {home_cs_pct:.1f}% of home matches.")
        else:
            st.warning(f"{home_team_name} has strong home defense ({home_cs_pct:.1f}% clean sheets), which may limit {away_team_name}'s scoring.")
        
        # Visual gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=away_scored_pct,
            title={'text': "Scoring Probability"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#ef4444"},
                'steps': [
                    {'range': [0, 50], 'color': "#fee2e2"},
                    {'range': [50, 75], 'color': "#fef3c7"},
                    {'range': [75, 100], 'color': "#dcfce7"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': home_cs_pct
                }
            }
        ))
        fig.update_layout(height=250)
        st.plotly_chart(fig, width = 'stretch')

st.markdown("---")
st.caption(f"*Data from current season - {home_team_name} (Home) vs {away_team_name} (Away)*")