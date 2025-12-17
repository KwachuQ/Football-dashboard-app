import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sys
import os
from components.filters import date_range_filter

# Ensure project root is importable
# PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# if PROJECT_ROOT not in sys.path:
#     sys.path.append(PROJECT_ROOT)

from services.queries import (
    get_upcoming_fixtures, 
    get_match_predictions,
    get_team_form,
    get_head_to_head
)

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

# ============================================================================
# Compact Header with inline date info
# ============================================================================
col1, col2 = st.columns([3, 1])

with col1:
    st.title("⚽ Upcoming Fixtures")

with col2:
    # Empty space or optional quick actions
    pass

# ============================================================================
# Sidebar filters
# ============================================================================
with st.sidebar:
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

# ============================================================================
# Compact date range display (single line)
# ============================================================================
if start_date and end_date:
    days_count = (end_date - start_date).days + 1
    
    # Single line info
    st.caption(
        f"📅 Showing fixtures from **{start_date.strftime('%d %b')}** to "
        f"**{end_date.strftime('%d %b %Y')}** ({days_count} days)"
    )
else:
    st.warning("⚠️ Please select a valid date range")
    st.stop()

# Fetch fixtures
try:
    if not start_date or not end_date:
        st.warning("⚠️ Please select a valid date range")
        st.stop()
    
    with st.spinner("Loading fixtures..."):
        # Update your query function to accept start_date and end_date
        fixtures_df = get_upcoming_fixtures(
            start_date=start_date,
            end_date=end_date,
            limit=max_fixtures
        )
    
    if fixtures_df.empty:
        st.info(f"📅 No fixtures found between {start_date} and {end_date}")
        st.info("Try expanding your date range or check back later.")
    else:
        st.success(f"✅ Found {len(fixtures_df)} fixtures")
        
        # Extract match IDs for predictions
        match_ids = fixtures_df['match_id'].tolist()
        
        # Create prediction summary column
        def format_prediction(row):
            """Format prediction as readable string."""
            # Check if probabilities exist and are not None/NaN
            if pd.isna(row.get('home_win_prob')) or row.get('home_win_prob') is None:
                return "No prediction"
            
            # Values are already in 0-1 range
            home_prob = float(row['home_win_prob']) * 100
            draw_prob = float(row['draw_prob']) * 100
            away_prob = float(row['away_win_prob']) * 100
            
            if home_prob > draw_prob and home_prob > away_prob:
                return f"Home Win ({home_prob:.1f}%)"
            elif away_prob > draw_prob and away_prob > home_prob:
                return f"Away Win ({away_prob:.1f}%)"
            else:
                return f"Draw ({draw_prob:.1f}%)"
        
        # Apply prediction formatting directly

        fixtures_df['prediction'] = fixtures_df.apply(format_prediction, axis=1)
        
        # Add team form (last 5 matches)
        def get_form_string(team_id):
            """Get form string (e.g., 'WWDLL') for a team."""
            try:
                # Convert numpy.int64 to native Python int
                team_id = int(team_id)
                
                # get_team_form returns dict with all TeamForm columns
                form_data = get_team_form(team_id=team_id, last_n_matches=5)
                
                if not form_data:
                    return "N/A"
                
                # Extract last_5_results from the returned dict
                last_5 = form_data.get('last_5_results')
                
                if last_5 and isinstance(last_5, str) and len(last_5) > 0:
                    return last_5[:5]  # First 5 characters
                
                return "N/A"
                
            except Exception as e:
                # Log the error but don't break the page
                print(f"Error getting form for team {team_id}: {e}")
                return "N/A"
        
        def format_form_html(form_string):
            """Convert form string to HTML with colored boxes."""
            if form_string == "N/A" or not form_string:
                return "N/A"
            
            colors = {
                'W': '#22c55e',  # Green
                'D': '#eab308',  # Yellow
                'L': '#ef4444'   # Red
            }
            
            html_parts = []
            for char in form_string:
                color = colors.get(char, '#6b7280')  # Gray for unknown
                html_parts.append(
                    f'<span style="display:inline-block; width:20px; height:20px; '
                    f'background-color:{color}; color:white; text-align:center; '
                    f'line-height:20px; margin:1px; border-radius:3px; '
                    f'font-weight:bold; font-size:12px;">{char}</span>'
                )
            
            return ''.join(html_parts)

        # Get unique team IDs and convert to Python int
        unique_team_ids = pd.concat([
            fixtures_df['home_team_id'],
            fixtures_df['away_team_id']
        ]).unique()

        # Convert numpy types to Python int
        unique_team_ids = [int(tid) for tid in unique_team_ids]

        # Build form cache with progress indicator
        with st.spinner("Loading team forms..."):
            form_cache = {}
            for team_id in unique_team_ids:
                form_cache[team_id] = get_form_string(team_id)

        # Map back (pandas will handle the conversion)
        fixtures_df['home_form'] = fixtures_df['home_team_id'].apply(lambda x: form_cache.get(int(x), "N/A"))
        fixtures_df['away_form'] = fixtures_df['away_team_id'].apply(lambda x: form_cache.get(int(x), "N/A"))
        
        # Create HTML formatted form for display
        fixtures_df['home_form_html'] = fixtures_df['home_form'].apply(format_form_html)
        fixtures_df['away_form_html'] = fixtures_df['away_form'].apply(format_form_html)

        
        # Add Head-to-Head records
        def get_h2h_record(home_id, away_id):
            """Get H2H record as string (e.g., '3-1-2')."""
            try:
                h2h_data = get_head_to_head(home_id, away_id)
                if h2h_data and h2h_data.get('total_matches', 0) > 0:
                    # Format: Home Wins - Draws - Away Wins
                    if h2h_data['team1_id'] == home_id:
                        return f"{h2h_data['team1_wins']}-{h2h_data['draws']}-{h2h_data['team2_wins']}"
                    else:
                        return f"{h2h_data['team2_wins']}-{h2h_data['draws']}-{h2h_data['team1_wins']}"
                return "No H2H"
            except:
                return "No H2H"
        
        with st.spinner("Loading head-to-head records..."):
            fixtures_df['h2h'] = fixtures_df.apply(
                lambda row: get_h2h_record(row['home_team_id'], row['away_team_id']),
                axis=1
            )
        
        display_df = fixtures_df[[
            'match_date',
            'home_team',
            'home_form_html',
            'away_team',
            'away_form_html',
            'h2h',
            'prediction',
            'round_number',
            'tournament'
        ]].copy()
        
        # Rename columns for better display
        display_df.columns = [
            'Date',
            'Home Team',
            'Form (H)',
            'Away Team',
            'Form (A)',
            'H2H (W-D-L)',
            'Prediction',
            'Round',
            'Tournament'
        ]
        # Display enhanced fixtures table using markdown for HTML rendering
        st.markdown("### 📋 Fixtures Overview")
        
        # Convert dataframe to HTML table with custom styling
        html_table = '<table style="width:100%; border-collapse: collapse;">'
        html_table += '<thead><tr style="background-color: #f0f2f6;">'
        for col in ['Date', 'Home Team', 'Form (H)', 'Away Team', 'Form (A)', 'H2H (W-D-L)', 'Prediction', 'Round', 'Tournament']:
            html_table += f'<th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">{col}</th>'
        html_table += '</tr></thead><tbody>'
        
        for idx, row in display_df.iterrows():
            html_table += '<tr style="border-bottom: 1px solid #eee;">'
            html_table += f'<td style="padding: 10px;">{row["Date"].strftime("%Y-%m-%d %H:%M")}</td>'
            html_table += f'<td style="padding: 10px;">{row["Home Team"]}</td>'
            html_table += f'<td style="padding: 10px;">{fixtures_df.loc[idx, "home_form_html"]}</td>' # type: ignore
            html_table += f'<td style="padding: 10px;">{row["Away Team"]}</td>'
            html_table += f'<td style="padding: 10px;">{fixtures_df.loc[idx, "away_form_html"]}</td>' # type: ignore
            html_table += f'<td style="padding: 10px; text-align: center;">{row["H2H (W-D-L)"]}</td>'
            html_table += f'<td style="padding: 10px;">{row["Prediction"]}</td>'
            html_table += f'<td style="padding: 10px; text-align: center;">{row["Round"]}</td>'
            html_table += f'<td style="padding: 10px;">{row["Tournament"]}</td>'
            html_table += '</tr>'
        
        html_table += '</tbody></table>'
        
        st.markdown(html_table, unsafe_allow_html=True)
        
        # Detailed match view with expanders
        st.markdown("---")
        st.subheader("📊 Detailed Match Information")
        
        for idx, match in fixtures_df.iterrows():
            with st.expander(f"🏆 {match['home_team']} vs {match['away_team']} - {match['match_date'].strftime('%Y-%m-%d %H:%M')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("### 🎯 Match Prediction")
                    if not pd.isna(match.get('home_win_prob')):
                        home_prob = float(match['home_win_prob']) * 100
                        draw_prob = float(match['draw_prob']) * 100
                        away_prob = float(match['away_win_prob']) * 100
                        
                        st.metric("Home Win", f"{home_prob:.1f}%")
                        st.metric("Draw", f"{draw_prob:.1f}%")
                        st.metric("Away Win", f"{away_prob:.1f}%")
                        
                        # Outlook badge
                        outlook = match.get('match_outlook', 'N/A')
                        outlook_colors = {
                            'HOME_FAVORITE': '🟢',
                            'AWAY_FAVORITE': '🔵',
                            'BALANCED': '🟡'
                        }
                        st.info(f"{outlook_colors.get(outlook, '⚪')} **{outlook.replace('_', ' ')}**")
                    else:
                        st.warning("No prediction available")
                
                with col2:
                    st.markdown("### ⚽ Predicted Goals (xG)")
                    if not pd.isna(match.get('predicted_home_goals')):
                        home_xg = float(match['predicted_home_goals'])
                        away_xg = float(match['predicted_away_goals'])
                        total_xg = float(match.get('predicted_total_xg', home_xg + away_xg))
                        
                        st.metric(f"{match['home_team']}", f"{home_xg:.2f} xG", 
                                 delta=None, delta_color="off")
                        st.metric(f"{match['away_team']}", f"{away_xg:.2f} xG",
                                 delta=None, delta_color="off")
                        st.metric("Total Expected Goals", f"{total_xg:.2f}",
                                 delta=None, delta_color="off")
                        
                        # Visual bar comparison
                        total = home_xg + away_xg
                        if total > 0:
                            home_pct = (home_xg / total) * 100
                            away_pct = (away_xg / total) * 100
                            st.progress(home_pct / 100, text=f"Home: {home_pct:.0f}% | Away: {away_pct:.0f}%")
                    else:
                        st.warning("No xG prediction available")
                
                with col3:
                    st.markdown("### 💰 Fair Odds")
                    if not pd.isna(match.get('home_win_fair_odds')):
                        home_odds = float(match['home_win_fair_odds'])
                        draw_odds = float(match['draw_fair_odds'])
                        away_odds = float(match['away_win_fair_odds'])
                        
                        # Display as betting odds format
                        st.metric("Home Win Odds", f"{home_odds:.2f}", 
                                 help="Fair betting odds for home win")
                        st.metric("Draw Odds", f"{draw_odds:.2f}",
                                 help="Fair betting odds for draw")
                        st.metric("Away Win Odds", f"{away_odds:.2f}",
                                 help="Fair betting odds for away win")
                        
                        # Show implied probabilities
                        st.caption("_Calculated fair odds based on prediction model_")
                    else:
                        st.warning("No odds available")
                
                # Additional match info
                st.markdown("---")
                col4, col5, col6 = st.columns(3)
                
                with col4:
                    st.markdown("**📅 Match Details**")
                    st.text(f"Date: {match['match_date'].strftime('%Y-%m-%d')}")
                    st.text(f"Time: {match['match_date'].strftime('%H:%M')}")
                    st.text(f"Round: {match['round_number']}")
                
                with col5:
                    st.markdown("**📊 Recent Form**")
                    st.markdown(f"**{match['home_team']}:** {match.get('home_form_html', 'N/A')}", unsafe_allow_html=True)
                    st.markdown(f"**{match['away_team']}:** {match.get('away_form_html', 'N/A')}", unsafe_allow_html=True)
                
                with col6:
                    st.markdown("**🏆 Competition**")
                    st.text(f"{match['tournament']}")
                    st.text(f"Season: {match.get('season_year', 'N/A')}")
                    if match.get('h2h'):
                        st.text(f"H2H: {match['h2h']}")

except Exception as e:
    st.error(f"Error loading fixtures: {e}")
    st.exception(e)
