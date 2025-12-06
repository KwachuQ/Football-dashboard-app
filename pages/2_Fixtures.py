import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from services.queries import (
    get_upcoming_fixtures, 
    get_match_predictions,
    get_team_form,
    get_head_to_head
)

st.set_page_config(
    page_title="Fixtures - Football Analytics",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Upcoming Fixtures")

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    days_ahead = st.slider("Days Ahead", 1, 30, 7)
    limit = st.number_input("Max Fixtures", 10, 100, 50, step=10)

# Fetch fixtures
try:
    fixtures_df = get_upcoming_fixtures(days_ahead=days_ahead, limit=limit)
    
    if fixtures_df.empty:
        st.warning("No upcoming fixtures found.")
    else:
        st.success(f"Found {len(fixtures_df)} upcoming fixtures")
        
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
        
        # Display enhanced fixtures table
        display_df = fixtures_df[[
            'match_date',
            'home_team',
            'home_form',
            'away_team',
            'away_form',
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
        
        st.dataframe(
            display_df,
            column_config={
                'Date': st.column_config.DatetimeColumn('Date', format='DD/MM/YYYY HH:mm'),
                'Form (H)': st.column_config.TextColumn('Form (H)', help="Last 5 matches: W=Win, D=Draw, L=Loss"),
                'Form (A)': st.column_config.TextColumn('Form (A)', help="Last 5 matches: W=Win, D=Draw, L=Loss"),
                'H2H (W-D-L)': st.column_config.TextColumn('H2H', help="Home Wins - Draws - Away Wins"),
                'Prediction': st.column_config.TextColumn('Prediction', help="Model prediction with probability"),
            },
            width='stretch',
            hide_index=True
        )
        
        # Export button
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"fixtures_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
        
        # Show detailed stats in expander
        with st.expander("📊 View Detailed Match Info"):
            selected_match = st.selectbox(
                "Select a match",
                options=range(len(fixtures_df)),
                format_func=lambda x: f"{fixtures_df.iloc[x]['home_team']} vs {fixtures_df.iloc[x]['away_team']}"
            )
            
            match = fixtures_df.iloc[selected_match]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Home Win Probability", 
                         f"{float(match.get('home_win_prob', 0)) * 100:.1f}%" if not pd.isna(match.get('home_win_prob')) else "N/A")
            
            with col2:
                st.metric("Draw Probability",
                         f"{float(match.get('draw_prob', 0)) * 100:.1f}%" if not pd.isna(match.get('draw_prob')) else "N/A")
            
            with col3:
                st.metric("Away Win Probability",
                         f"{float(match.get('away_win_prob', 0)) * 100:.1f}%" if not pd.isna(match.get('away_win_prob')) else "N/A")

except Exception as e:
    st.error(f"Error loading fixtures: {e}")
    st.exception(e)
