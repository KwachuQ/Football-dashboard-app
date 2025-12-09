# Reusable filter components for Streamlit applications

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Literal
import yaml
from pathlib import Path
import logging
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

def date_range_filter(
    label: Optional[str] = None,
    key: str = "date_range_filter",
    min_date: Optional[date] = None,
    max_date: Optional[date] = None,
    default_start: Optional[date] = None,
    default_end: Optional[date] = None,
) -> tuple[Optional[date], Optional[date]]:
    """
    Date range filter component.
    Stores selected start and end dates in session_state.
    
    Args:
        label: Label for the date input
        key: Unique key for session state
        min_date: Minimum selectable date
        max_date: Maximum selectable date
        default_start: Default start date
        default_end: Default end date
    
    Returns:
        tuple of (start_date, end_date) or (None, None) if invalid
    """
    # Defaults

    if default_start is None:
        default_start = date.today() - timedelta(days=30)
    if default_end is None:
        default_end = date.today()

    # Optional label
    if label:
        st.markdown(f"**{label}**")

    # Date inputs side by side
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=default_start,
            min_value=min_date,
            max_value=max_date,
            key=f"{key}_start"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=default_end,
            min_value=min_date,
            max_value=max_date,
            key=f"{key}_end"
        )
    
    if start_date and end_date:
        if start_date > end_date:
            st.error("Start date cannot be after end date.")
            return (None, None)
        

        return (start_date, end_date)
    
    return (None, None)

def match_count_slider(
    label: str = "Minimum Match Count",
    key: str = "match_count",
    min_value: int = 5,
    max_value: int = 100,
    default: int = 10,
) -> Optional[int]:
    """
    Slider to select minimum match count.
    Stores selected value in session_state.
    
    Args:
        label: Label for the slider
        key: Unique key for session state
        min_value: Minimum slider value
        max_value: Maximum slider value
        default: Default slider value
"""
    selected_value = st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=default,
        key=key
    )
    
    st.session_state[f"{key}_value"] = selected_value
    return selected_value

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600)
def load_leagues_from_config() -> List[Dict[str, Any]]:
    """
    Load leagues from config/league_config.yaml (or docs/league_config.yaml).
    Cached for 1 hour to avoid repeated file reads.
    
    Returns:
        List of dicts: [
            {
                'league_id': 202,
                'league_name': 'Ekstraklasa',
                'country': 'Poland',
                'country_id': 1
            },
            ...
        ]
    """
    # Try both possible locations
    possible_paths = [
        Path(__file__).parent.parent / "config" / "league_config.yaml",
        Path(__file__).parent.parent / "docs" / "league_config.yaml"
    ]
    
    config_path = None
    for path in possible_paths:
        if path.exists():
            config_path = path
            break
    
    if not config_path:
        logger.error("league_config.yaml not found in config/ or docs/")
        st.error("⚠️ League configuration file not found")
        return []
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        leagues = []
        
        # Parse structure from your config
        # Format: available_leagues -> country_key -> leagues[]
        available_leagues = config.get('available_leagues', {})
        
        for country_key, country_data in available_leagues.items():
            country_name = country_data.get('country', country_key)
            country_id = country_data.get('country_id', 0)
            
            for league in country_data.get('leagues', []):
                leagues.append({
                    'league_id': league.get('league_id'),
                    'league_name': league.get('name'),
                    'country': country_name,
                    'country_id': country_id
                })
        
        logger.info(f"Loaded {len(leagues)} leagues from {config_path}")
        return leagues
    
    except Exception as e:
        logger.error(f"Failed to load leagues from {config_path}: {e}")
        st.error(f"⚠️ Error loading league config: {e}")
        return []


def league_filter(
    default_league_id: Optional[int] = None,
    label: str = "Select League",
    key: str = "league_filter",
    show_country: bool = True
) -> Optional[int]:
    """
    League selector that loads leagues from config/league_config.yaml.
    Stores selected league_id, league_name, and country in session_state.
    
    Args:
        default_league_id: Default selected league_id (defaults to active_league from config)
        label: Label for the selectbox
        key: Unique key for session state
        show_country: Show country flag and name in display
    
    Returns:
        league_id (int) or None if no selection
    
    Example:
        league_id = league_filter(default_league_id=202, key="main_league")
        
        if league_id:
            league_name = st.session_state.get("main_league_name")
            country = st.session_state.get("main_league_country")
            st.write(f"Selected: {league_name} from {country}")
    """
    # Load leagues from YAML
    leagues_list = load_leagues_from_config()
    
    if not leagues_list:
        st.warning("⚠️ No leagues available")
        return None
    
    # Country emoji mapping
    country_flags = {
        'Poland': '🇵🇱',
        'Austria': '🇦🇹',
        'Czech Republic': '🇨🇿',
        'Germany': '🇩🇪',
        'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
        'Spain': '🇪🇸',
        'France': '🇫🇷',
        'Italy': '🇮🇹',
        'Portugal': '🇵🇹',
        'Netherlands': '🇳🇱',
    }
    
    # Create display names and mappings
    display_dict = {}
    league_data = {}
    
    for league in leagues_list:
        league_id = league['league_id']
        league_name = league['league_name']
        country = league['country']
        
        # Format display name
        if show_country:
            flag = country_flags.get(country, '🌍')
            display_name = f"{flag} {league_name} ({country})"
        else:
            display_name = league_name
        
        display_dict[display_name] = league_id
        league_data[league_id] = {
            'league_name': league_name,
            'country': country,
            'country_id': league.get('country_id', 0)
        }
    
    # Sort display names
    display_names = sorted(display_dict.keys())
    
    # Find default index
    default_index = 0
    if default_league_id:
        for idx, display_name in enumerate(display_names):
            if display_dict[display_name] == default_league_id:
                default_index = idx
                break
    
    # Selectbox
    selected_display = st.selectbox(
        label,
        options=display_names,
        index=default_index,
        key=key,
        help="Select a league to filter data"
    )
    
    if selected_display:
        selected_id = display_dict[selected_display]
        selected_data = league_data[selected_id]
        
        # Store in session state
        st.session_state[f"{key}_id"] = selected_id
        st.session_state[f"{key}_name"] = selected_data['league_name']
        st.session_state[f"{key}_country"] = selected_data['country']
        st.session_state[f"{key}_country_id"] = selected_data['country_id']
        
        return selected_id
    
    return None


def get_active_league_from_config() -> Optional[int]:
    """
    Get the active league ID from config/league_config.yaml.
    
    Returns:
        Active league_id or None
    """
    path = [
        Path(__file__).parent.parent / "config" / "league_config.yaml",
    ]
    
    for config_path in path:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                active_league = config.get('active_league', {})
                return active_league.get('league_id')
            
            except Exception as e:
                logger.error(f"Failed to get active league: {e}")
    
    return None

def home_away_toggle(
    label: str = "Match Location",
    key: str = "home_away_toggle",
    default: Literal["all", "home", "away"] = "all",
    horizontal: bool = True
) -> Literal["all", "home", "away"]:
    """Toggle for filtering matches by location"""
    
    # Explicit type annotation for options
    options: list[Literal["all", "home", "away"]] = ["all", "home", "away"]
    
    selected = st.radio(
        label,
        options=options,  
        index=options.index(default),
        format_func=lambda x: {
            "all": "All Matches",
            "home": "Home Only",
            "away": "Away Only"
        }[x],
        key=key,
        horizontal=horizontal,
        help="Filter matches by location"
    )
    
    # Store in session state
    st.session_state[f"{key}_value"] = selected
    
    return selected

