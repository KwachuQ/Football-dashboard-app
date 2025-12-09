import os
import sys
import streamlit as st
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from services.db import test_connection, get_engine
from services.queries import get_data_freshness, get_all_seasons
from services.cache import CacheManager, CacheMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Home",
    page_icon="⚽",
    layout="wide"
)

# Helper functions
@st.cache_data(ttl=3600)
def load_league_config() -> Dict[str, Any]:
    config_path = Path(PROJECT_ROOT) / "config" / "league_config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading league config: {e}")
        return {}

def get_active_league(config: Dict[str, Any]) -> Dict[str, Any]:
    active = config.get('active_league', {})
    return {
        'country': active.get('country', 'Poland'),
        'league_id': active.get('league_id', 202),
    }

def get_active_season(config: Dict[str, Any]) -> Dict[str, Any]:
    active = config.get('active_season', {})
    return {
        'name': active.get('name', 'Ekstraklasa 25/26'),
        'season_id': active.get('season_id', 76477),
    }

def calculate_data_age(last_update: Optional[datetime]) -> str:
    if last_update is None:
        return "Never"
    
    now = datetime.now()
    delta = now - last_update
    
    if delta < timedelta(minutes=1):
        return "Just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = delta.days
        return f"{days} day{'s' if days != 1 else ''} ago"

# Main page content
st.title("⚽ Football Analytics Dashboard")
st.markdown("Real-time football statistics, predictions, and team analysis")

config = load_league_config()

if not config:
    st.error("Failed to load configuration. Please check league_config.yaml")
    st.stop()

active_league = get_active_league(config)
active_season = get_active_season(config)

# Store in session state
if 'active_season_id' not in st.session_state:
    st.session_state.active_season_id = active_season.get('season_id')

# Display active info
col1, col2 = st.columns(2)
with col1:
    st.info(
        f"**Active League:** Ekstraklasa\n\n"
        f"**Country:** {active_league['country']}\n\n"
        f"**League ID:** {active_league['league_id']}"
    )
with col2:
    st.success(
        f"**Active Season:** {active_season['name']}\n\n"
        f"**Season ID:** {active_season['season_id']}"
    )

st.markdown("---")

# Quick Stats
st.header("Quick Statistics")

col1, col2, col3, col4 = st.columns(4)

season_id = active_season.get('season_id')

with col1:
    try:
        seasons_df = get_all_seasons()
        total_seasons = len(seasons_df) if not seasons_df.empty else 0
        st.metric("Total Seasons", total_seasons)
    except Exception as e:
        st.metric("Total Seasons", "Error")

with col2:
    st.metric("Active League", "Ekstraklasa")

with col3:
    try:
        from services.queries import get_upcoming_fixtures_count
        fixtures_count = get_upcoming_fixtures_count(season_id=season_id)
        st.metric("Upcoming Fixtures", fixtures_count)
    except Exception as e:
        st.metric("Upcoming Fixtures", "Error")

st.markdown("---")

# # Data Freshness
# st.header("Data Freshness")

# try:
#     freshness_df = get_data_freshness()
    
#     if not freshness_df.empty:
#         freshness_df['data_age'] = freshness_df.apply(
#             lambda row: calculate_data_age(row.get('last_updated')), 
#             axis=1
#         )
        
#         def get_status(row):
#             if row['row_count'] == 0 or row['row_count'] is None:
#                 return "🔴 Empty"
            
#             last_updated = row.get('last_updated')
#             if last_updated is None or pd.isna(last_updated):
#                 return "⚪ Unknown"
            
#             age = datetime.now() - last_updated
            
#             if age < timedelta(minutes=5):
#                 return "🟢 Fresh"
#             elif age < timedelta(hours=1):
#                 return "🟡 Recent"
#             elif age < timedelta(days=1):
#                 return "🟠 Aging"
#             else:
#                 return "🔴 Stale"
        
#         freshness_df['status'] = freshness_df.apply(get_status, axis=1)
        
#         st.dataframe(
#             freshness_df[['table_name', 'row_count', 'last_updated', 'data_age', 'status']],
#             width='stretch',
#             hide_index=True
#         )
#     else:
#         st.warning("No data freshness information available")

# except Exception as e:
#     logger.error(f"Failed to get data freshness: {e}")
#     st.error(f"Error loading data freshness: {e}")
