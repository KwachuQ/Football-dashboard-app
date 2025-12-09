# Reusable filter components for Streamlit applications

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional
from services.queries import get_team_stats



# Team selector filter to get team name from a dataframe (get_team_names function in queries.py)

def team_selector(
    df: pd.DataFrame, 
    label: str = "Select Team",
    key: str = "team_selector"
) -> Optional[int]:
    """
    Stores team_name in session_state and returns team_id
    
    Returns:
        team_id (int) or None
    """

    # Validation 
    if df.empty or 'team_name' not in df.columns or 'team_id' not in df.columns:
        st.warning("No teams available for selection.")
        return None
    
    # Cache mapping for performance

    cache_key =f'{key}_mapping'
    if cache_key not in st.session_state:
        st.session_state[cache_key] = dict(zip(df['team_name'], df['team_id']))

    team_dict = st.session_state[cache_key]
    team_names = sorted(team_dict.keys())

    # Selectbox for team selection
    selected_name = st.selectbox(label, team_names, key=key)
    
    if selected_name:
        st.session_state[f"{key}_name"] = selected_name
        return team_dict[selected_name]
    
    return None

# Teams selector filter to get multiple team names from a dataframe

def teams_selector(
    df: pd.DataFrame, 
    label: str = "Select Teams",
    key: str = "teams_selector",
    default: Optional[list] = None,
    max_selections: Optional[int] = 18,
) -> list[int]:
    """
    Multiple teams selector with autocomplete.
    Stores team_names in session_state[f"{key}_names"]
    
    Args:
        df: DataFrame with 'team_id' and 'team_name' columns
        label: Label for the multiselect
        default: Default selected team names
        max_selections: Maximum number of teams to select
        key: Unique key for session state
    
    Returns:
        list of team_ids (empty list if no selection)
    """

    # Validation
    if df.empty or 'team_name' not in df.columns or 'team_id' not in df.columns:
        st.warning("No teams available for selection.")
        return []
    
    # Cache mapping for performance
    cache_key =f'{key}_mapping'
    if cache_key not in st.session_state:
        st.session_state[cache_key] = dict(zip(df['team_name'], df['team_id']))

    team_dict = st.session_state[cache_key]
    team_names = sorted(team_dict.keys())
    
    # Multiselect for team selection
    selected_names = st.multiselect(label, team_names, key=key, default=default, max_selections=max_selections)
    
    if selected_names:
        st.session_state[f"{key}_names"] = selected_names
        return [team_dict[name] for name in selected_names]
    
    return []

