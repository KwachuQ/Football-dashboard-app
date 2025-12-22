from asyncio.log import logger
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sys
import os
import time

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
    page_title="Fixtures - Football Analytics",
    page_icon="📅",
    layout="wide"
)

# Lazy imports to avoid circular dependencies
def get_time_page_load():
    from services.cache import time_page_load
    return time_page_load

def show_timings_inline():
    from services.cache import show_timings_inline
    return show_timings_inline

time_page_load = get_time_page_load()

# ============================================================================
# CACHED DATA PREPARATION FUNCTIONS (NOT Plotly objects!)
# ============================================================================

@st.cache_data(ttl=600, show_spinner=False)
def prepare_fixtures_data(start_date, end_date, max_fixtures):
    """
    Fetch and prepare fixtures data with caching.
    Cache key includes date range to invalidate when filters change.
    """
    from services.queries import get_upcoming_fixtures
    
    fixtures_df = get_upcoming_fixtures(
        start_date=start_date,
        end_date=end_date,
        limit=max_fixtures
    )
    return fixtures_df

@st.cache_data(ttl=600, show_spinner=False)
def prepare_bulk_team_forms(team_ids: list, last_n: int = 5):
    """
    BATCH FETCH: Get forms for multiple teams in one cached call.
    Avoids N+1 query problem (1 cache call instead of N individual calls).
    
    Args:
        team_ids: List of unique team IDs
        last_n: Number of recent matches to fetch
    
    Returns:
        Dict mapping team_id -> form_string
    """
    from services.queries import get_team_form
    
    form_cache = {}
    for team_id in team_ids:
        try:
            team_id_int = int(team_id)
            form_data = get_team_form(team_id=team_id_int, last_n_matches=last_n)
            
            if not form_data:
                form_cache[team_id_int] = "N/A"
                continue
            
            last_5 = form_data.get('last_5_results')
            if last_5 and isinstance(last_5, str) and len(last_5.strip()) > 0:
                form_cache[team_id_int] = last_5.strip()[:5]
            else:
                form_cache[team_id_int] = "N/A"
        except Exception:
            pass
    
    return form_cache

@st.cache_data(ttl=600, show_spinner=False)
def prepare_bulk_h2h_records(fixture_pairs: list):
    """
    BATCH FETCH: Get H2H records for multiple fixture pairs.
    
    Args:
        fixture_pairs: List of tuples [(home_id, away_id), ...]
    
    Returns:
        Dict mapping (home_id, away_id) -> h2h_string
    """
    from services.queries import get_head_to_head
    
    h2h_cache = {}
    for home_id, away_id in fixture_pairs:
        try:
            h2h_data = get_head_to_head(home_id, away_id)
            if h2h_data and h2h_data.get('total_matches', 0) > 0:
                if h2h_data['team1_id'] == home_id:
                    h2h_string = f"{h2h_data['team1_wins']}-{h2h_data['draws']}-{h2h_data['team2_wins']}"
                else:
                    h2h_string = f"{h2h_data['team2_wins']}-{h2h_data['draws']}-{h2h_data['team1_wins']}"
                h2h_cache[(home_id, away_id)] = h2h_string
            else:
                h2h_cache[(home_id, away_id)] = "No H2H"
        except:
            h2h_cache[(home_id, away_id)] = "No H2H"
    
    return h2h_cache

# ============================================================================
# HELPER FUNCTIONS (not cached, lightweight)
# ============================================================================

def format_prediction(row):
    """Format prediction as readable string."""
    if pd.isna(row.get('home_win_prob')) or row.get('home_win_prob') is None:
        return "No prediction"
    
    home_prob = float(row['home_win_prob']) * 100
    draw_prob = float(row['draw_prob']) * 100
    away_prob = float(row['away_win_prob']) * 100
    
    if home_prob > draw_prob and home_prob > away_prob:
        return f"Home Win ({home_prob:.1f}%)"
    elif away_prob > draw_prob and away_prob > home_prob:
        return f"Away Win ({away_prob:.1f}%)"
    else:
        return f"Draw ({draw_prob:.1f}%)"

def format_form_html(form_string):
    """Convert form string to HTML with colored boxes."""
    if form_string == "N/A" or not form_string:
        return "N/A"
    
    colors = {'W': '#22c55e', 'D': '#eab308', 'L': '#ef4444'}
    
    html_parts = []
    for char in form_string:
        color = colors.get(char, '#6b7280')
        html_parts.append(
            f'<span style="display:inline-block; width:20px; height:20px; '
            f'background-color:{color}; color:white; text-align:center; '
            f'line-height:20px; margin:1px; border-radius:3px; '
            f'font-weight:bold; font-size:12px;">{char}</span>'
        )
    
    return ''.join(html_parts)

def render_fixtures_table(fixtures_df):
    """
    Render fixtures overview table WITHOUT detailed expanders.
    FAST: Only table rendering, no heavy computations.
    """
    display_df = fixtures_df[[
        'match_date', 'home_team', 'home_form_html',
        'away_team', 'away_form_html', 'h2h',
        'prediction', 'round_number', 'tournament'
    ]].copy()
    
    display_df.columns = [
        'Date', 'Home Team', 'Form (H)',
        'Away Team', 'Form (A)', 'H2H (W-D-L)',
        'Prediction', 'Round', 'Tournament'
    ]
    
    # HTML table with custom styling
    html_table = '<table style="width:100%; border-collapse: collapse;">'
    html_table += '<thead><tr style="background-color: #f0f2f6;">'
    for col in display_df.columns:
        html_table += f'<th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">{col}</th>'
    html_table += '</tr></thead><tbody>'
    
    for idx, row in display_df.iterrows():
        html_table += '<tr style="border-bottom: 1px solid #eee;">'
        html_table += f'<td style="padding: 10px;">{row["Date"].strftime("%Y-%m-%d %H:%M")}</td>'
        html_table += f'<td style="padding: 10px;">{row["Home Team"]}</td>'
        html_table += f'<td style="padding: 10px;">{fixtures_df.loc[idx, "home_form_html"]}</td>'
        html_table += f'<td style="padding: 10px;">{row["Away Team"]}</td>'
        html_table += f'<td style="padding: 10px;">{fixtures_df.loc[idx, "away_form_html"]}</td>'
        html_table += f'<td style="padding: 10px; text-align: center;">{row["H2H (W-D-L)"]}</td>'
        html_table += f'<td style="padding: 10px;">{row["Prediction"]}</td>'
        html_table += f'<td style="padding: 10px; text-align: center;">{row["Round"]}</td>'
        html_table += f'<td style="padding: 10px;">{row["Tournament"]}</td>'
        html_table += '</tr>'
    
    html_table += '</tbody></table>'
    st.markdown(html_table, unsafe_allow_html=True)

def render_match_details(match, idx):
    """
    Render detailed match expander.
    LAZY: Only called for visible/expanded matches.
    """
    with st.expander(f"{match['home_team']} vs {match['away_team']} - {match['match_date'].strftime('%Y-%m-%d %H:%M')}"):
        col1, col2, col3 = st.columns(3)
        
        # Column 1: Match Prediction
        with col1:
            st.markdown("### Match Prediction")
            if not pd.isna(match.get('home_win_prob')):
                home_prob = float(match['home_win_prob']) * 100
                draw_prob = float(match['draw_prob']) * 100
                away_prob = float(match['away_win_prob']) * 100
                
                st.metric("Home Win", f"{home_prob:.1f}%")
                st.metric("Draw", f"{draw_prob:.1f}%")
                st.metric("Away Win", f"{away_prob:.1f}%")
                
                outlook = match.get('match_outlook', 'N/A')
                st.info(f"**{outlook.replace('_', ' ')}**")
            else:
                st.warning("No prediction available")
        
        # Column 2: Expected Goals
        with col2:
            st.markdown("### Predicted Goals (xG)")
            if not pd.isna(match.get('predicted_home_goals')):
                home_xg = float(match['predicted_home_goals'])
                away_xg = float(match['predicted_away_goals'])
                total_xg = float(match.get('predicted_total_xg', home_xg + away_xg))
                
                st.metric(f"{match['home_team']}", f"{home_xg:.2f} xG", delta=None, delta_color="off")
                st.metric(f"{match['away_team']}", f"{away_xg:.2f} xG", delta=None, delta_color="off")
                st.metric("Total Expected Goals", f"{total_xg:.2f}", delta=None, delta_color="off")
                
                total = home_xg + away_xg
                if total > 0:
                    home_pct = (home_xg / total) * 100
                    away_pct = (away_xg / total) * 100
                    st.progress(home_pct / 100, text=f"Home: {home_pct:.0f}% | Away: {away_pct:.0f}%")
            else:
                st.warning("No xG prediction available")
        
        # Column 3: Fair Odds
        with col3:
            st.markdown("### Fair Odds")
            if not pd.isna(match.get('home_win_fair_odds')):
                home_odds = float(match['home_win_fair_odds'])
                draw_odds = float(match['draw_fair_odds'])
                away_odds = float(match['away_win_fair_odds'])
                
                st.metric("Home Win Odds", f"{home_odds:.2f}", help="Fair betting odds for home win")
                st.metric("Draw Odds", f"{draw_odds:.2f}", help="Fair betting odds for draw")
                st.metric("Away Win Odds", f"{away_odds:.2f}", help="Fair betting odds for away win")
                st.caption("Calculated fair odds based on prediction model")
            else:
                st.warning("No odds available")
        
        # Additional match info
        st.markdown("---")
        col4, col5, col6 = st.columns(3)
        
        with col4:
            st.markdown("**Match Details**")
            st.text(f"Date: {match['match_date'].strftime('%Y-%m-%d')}")
            st.text(f"Time: {match['match_date'].strftime('%H:%M')}")
            st.text(f"Round: {match['round_number']}")
        
        with col5:
            st.markdown("**Recent Form**")
            st.markdown(f"**{match['home_team']}:** {match.get('home_form_html', 'N/A')}", unsafe_allow_html=True)
            st.markdown(f"**{match['away_team']}:** {match.get('away_form_html', 'N/A')}", unsafe_allow_html=True)
        
        with col6:
            st.markdown("**Competition**")
            st.text(f"{match['tournament']}")
            st.text(f"Season: {match.get('season_year', 'N/A')}")
            if match.get('h2h'):
                st.text(f"H2H: {match['h2h']}")

# ============================================================================
# MAIN PAGE FUNCTION
# ============================================================================

@time_page_load
def fixtures():
    page_start = time.time()
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Upcoming Fixtures")
    
    # Sidebar filters
    with st.sidebar:
        from components.filters import date_range_filter
        
        st.header("Filters")
        
        today = date.today()
        default_end = today + timedelta(days=45)
        
        start_date, end_date = date_range_filter(
            key="fixtures_date_range",
            min_date=today,
            max_date=today + timedelta(days=365),
            default_start=today,
            default_end=default_end,
        )
        
        st.markdown("---")
        max_fixtures = st.number_input(
            "Max Fixtures",
            min_value=10,
            max_value=200,
            value=50,
            step=10
        )
    
    # Date range display
    if start_date and end_date:
        days_count = (end_date - start_date).days + 1
        st.caption(
            f"Showing fixtures from **{start_date.strftime('%d %b')}** to "
            f"**{end_date.strftime('%d %b %Y')}** ({days_count} days)"
        )
    else:
        st.warning("Please select a valid date range")
        st.stop()
    
    # ========================================================================
    # FETCH DATA (CACHED) - Single point of data loading
    # ========================================================================
    try:
        # STEP 1: Fetch fixtures (CACHED by date range + limit)
        fixtures_df = prepare_fixtures_data(start_date, end_date, max_fixtures)
        
        if fixtures_df.empty:
            st.info(f"No fixtures found between {start_date} and {end_date}")
            st.info("Try expanding your date range or check back later.")
            st.stop()
        
        st.success(f"Found {len(fixtures_df)} fixtures")
        
        # STEP 2: Prepare unique team IDs for BATCH fetching
        unique_team_ids = list(set(
            list(fixtures_df['home_team_id'].astype(int)) + 
            list(fixtures_df['away_team_id'].astype(int))
        ))
        
        # STEP 3: BATCH FETCH team forms (CACHED - single call for all teams!)
        form_cache = prepare_bulk_team_forms(unique_team_ids, last_n=5)
        
        # STEP 4: BATCH FETCH H2H records (CACHED)
        fixture_pairs = list(zip(
            fixtures_df['home_team_id'].astype(int),
            fixtures_df['away_team_id'].astype(int)
        ))
        h2h_cache = prepare_bulk_h2h_records(fixture_pairs)
        
        # STEP 5: Enrich fixtures_df with cached data (FAST - no DB calls!)
        fixtures_df['home_form'] = fixtures_df['home_team_id'].apply(lambda x: form_cache.get(int(x), "N/A"))
        fixtures_df['away_form'] = fixtures_df['away_team_id'].apply(lambda x: form_cache.get(int(x), "N/A"))
        fixtures_df['home_form_html'] = fixtures_df['home_form'].apply(format_form_html)
        fixtures_df['away_form_html'] = fixtures_df['away_form'].apply(format_form_html)
        fixtures_df['h2h'] = fixtures_df.apply(
            lambda row: h2h_cache.get((int(row['home_team_id']), int(row['away_team_id'])), "No H2H"),
            axis=1
        )
        fixtures_df['prediction'] = fixtures_df.apply(format_prediction, axis=1)
        
    except Exception as e:
        st.error(f"Error loading fixtures: {e}")
        st.exception(e)
        st.stop()
    
    # ========================================================================
    # DISPLAY: Table (always shown, fast)
    # ========================================================================
    st.markdown("### Fixtures Overview")
    render_fixtures_table(fixtures_df)
    
    # ========================================================================
    # LAZY LOADING: Detailed Match Info (CONDITIONAL RENDERING)
    # ========================================================================
    st.markdown("---")
    st.subheader("Detailed Match Information")
    
    # Initialize session state for "show all" toggle
    if 'show_all_fixtures' not in st.session_state:
        st.session_state.show_all_fixtures = False
    
    # STRATEGY: Limit initial render to 10 fixtures
    initial_limit = 10
    total_fixtures = len(fixtures_df)
    
    if total_fixtures <= initial_limit:
        # Render all if less than limit
        for idx, match in fixtures_df.iterrows():
            render_match_details(match, idx)
    else:
        # LAZY: Show only first 10 initially
        if not st.session_state.show_all_fixtures:
            st.info(f"Showing {initial_limit} of {total_fixtures} fixtures. Click 'Load More' to see all.")
            for idx, match in fixtures_df.head(initial_limit).iterrows():
                render_match_details(match, idx)
            
            # Load More button
            if st.button(f"Load {total_fixtures - initial_limit} More Fixtures", type="primary"):
                st.session_state.show_all_fixtures = True
                st.rerun()
        else:
            # Show all (user clicked Load More)
            for idx, match in fixtures_df.iterrows():
                render_match_details(match, idx)
            
            # Collapse button
            if st.button("Show Less (top 10 only)", type="secondary"):
                st.session_state.show_all_fixtures = False
                st.rerun()
    
    # ========================================================================
    # TIMING DISPLAY
    # ========================================================================
    current_time = time.time() - page_start
    if 'timings' not in st.session_state:
        st.session_state.timings = {}
    st.session_state.timings['Fixtures'] = f"{current_time:.2f}s"
    
    show_timings = show_timings_inline()
    show_timings()

if __name__ == "__main__":
    fixtures()
