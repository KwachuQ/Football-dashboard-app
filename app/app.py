import os
import sys
import streamlit as st
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# Ensure project root is importable when running `streamlit run app/app.py`
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Import services - let these fail early if not available
from services.db import test_connection, get_engine
from services.queries import get_data_freshness, get_all_seasons
from services.cache import CacheManager, CacheMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PAGES = {
    "Home": "home",
    "Fixtures": "fixtures",
    "Teams": "teams",
    "Head-to-Head": "h2h",
    "Insights": "insights",
}


# ============================================================================
# Helper Functions for Home Page
# ============================================================================

@st.cache_data(ttl=3600)
def load_league_config() -> Dict[str, Any]:
    """Load league configuration from YAML file."""
    config_path = Path(PROJECT_ROOT) / "docs" / "league_config.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading league config: {e}")
        st.error(f"Failed to load league configuration: {e}")
        return {}


def get_available_leagues(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract available leagues from configuration."""
    leagues = {}
    
    if 'available_leagues' not in config:
        return leagues
    
    for country_key, country_data in config['available_leagues'].items():
        country_name = country_data.get('country', country_key)
        country_id = country_data.get('country_id', 0)
        
        for league in country_data.get('leagues', []):
            league_name = league.get('name', 'Unknown')
            league_id = league.get('league_id', 0)
            
            display_name = f"{country_name} - {league_name}"
            
            leagues[display_name] = {
                'country': country_name,
                'country_id': country_id,
                'league_name': league_name,
                'league_id': league_id,
            }
    
    return leagues


def get_active_league(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get currently active league from configuration."""
    active = config.get('active_league', {})
    return {
        'country': active.get('country', 'Poland'),
        'league_id': active.get('league_id', 202),
    }


def get_active_season(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get currently active season from configuration."""
    active = config.get('active_season', {})
    return {
        'name': active.get('name', 'Ekstraklasa 25/26'),
        'season_id': active.get('season_id', 76477),
    }


def check_database_status() -> Dict[str, Any]:
    """
    Check database connection and status.
    
    Returns:
        Dictionary with status information
    """
    try:
        is_connected = test_connection()
        
        if is_connected:
            engine = get_engine()
            
            # Test query to verify connection works
            with engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            return {
                'status': '🟢 Connected',
                'healthy': True,
                'engine_type': engine.name,
                'dialect': engine.dialect.name,
            }
        else:
            return {
                'status': '🔴 Disconnected',
                'healthy': False,
                'error': 'Unable to connect to database'
            }
    
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return {
            'status': '🔴 Error',
            'healthy': False,
            'error': str(e)
        }

def calculate_data_age(last_update: Optional[datetime]) -> str:
    """Calculate how old the data is."""
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


# ============================================================================
# Page Functions
# ============================================================================

def render_header(title: str):
    """Render page header with configuration."""
    st.set_page_config(
        page_title="Football Analytics Dashboard",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title(f"⚽ {title}")


def page_home():
    """Home page with league selector, freshness dashboard, and system health."""
    render_header("Football Analytics Dashboard")
    st.markdown("Real-time football statistics, predictions, and team analysis")
    
    # Load configuration
    config = load_league_config()
    
    if not config:
        st.error("Failed to load configuration. Please check league_config.yaml")
        return
    
    # Sidebar - League Selector
    with st.sidebar:
        st.header("League Selection")
        
        # Get available leagues and active league
        available_leagues = get_available_leagues(config)
        active_league = get_active_league(config)
        active_season = get_active_season(config)
        
        # Create display name for active league
        active_display = f"{active_league['country']} - Ekstraklasa"
        
        # League selector
        league_options = sorted(available_leagues.keys()) if available_leagues else [active_display]
        
        default_index = league_options.index(active_display) if active_display in league_options else 0
        
        selected_league_display = st.selectbox(
            "Select League",
            options=league_options,
            index=default_index,
            help="Choose a league to analyze"
        )
        
        # Display active league info
        st.info(
            f"**Active League:** Ekstraklasa\n\n"
            f"**Country:** {active_league['country']}\n\n"
            f"**League ID:** {active_league['league_id']}"
        )
        
        # Display active season info
        st.success(
            f"**Active Season:** {active_season['name']}\n\n"
            f"**Season ID:** {active_season['season_id']}"
        )
        
        # Cache controls
        st.markdown("---")
        st.subheader("Cache Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Clear Cache", help="Clear all cached data"):
                try:
                    if CacheManager.clear_query_cache():
                        st.success("Cache cleared!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col2:
            if st.button("Reset Stats", help="Reset cache statistics"):
                try:
                    monitor = CacheMonitor()
                    monitor.reset_stats()
                    st.success("Stats reset!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # Main content
    st.markdown("---")
    
    # Quick Stats Cards
    st.header("Quick Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Get season_id for queries
    season_id = active_season.get('season_id')
    
    # Total Seasons
    try:
        seasons_df = get_all_seasons()
        total_seasons = len(seasons_df) if not seasons_df.empty else 0
    except Exception as e:
        logger.error(f"Failed to get seasons: {e}")
        total_seasons = 0
    
    with col1:
        st.metric("Total Seasons", total_seasons, help="Number of seasons in database")
    
    # Active League (fixed value for now)
    with col2:
        st.metric("Active League", "Ekstraklasa", help="Currently selected league")
    
    # Upcoming Fixtures Count
    with col3:
        try:
            from services.queries import get_upcoming_fixtures_count
            fixtures_count = get_upcoming_fixtures_count(season_id=season_id)
            st.metric("Upcoming Fixtures", fixtures_count, help="Number of upcoming matches")
        except Exception as e:
            logger.error(f"Failed to get fixtures count: {e}")
            st.metric("Upcoming Fixtures", "Error", help="Failed to load")
    
    # Last Prediction Time
    with col4:
        try:
            from services.queries import get_last_prediction_time
            last_pred = get_last_prediction_time(season_id=season_id)
            
            if last_pred:
                time_ago = datetime.now() - last_pred
                if time_ago.days > 0:
                    pred_text = f"{time_ago.days}d ago"
                elif time_ago.seconds > 3600:
                    pred_text = f"{time_ago.seconds // 3600}h ago"
                else:
                    pred_text = f"{time_ago.seconds // 60}m ago"
                st.metric("Last Prediction", pred_text, help="Time since last prediction update")
            else:
                st.metric("Last Prediction", "N/A", help="No predictions found")
        except Exception as e:
            logger.error(f"Failed to get last prediction time: {e}")
            st.metric("Last Prediction", "Error", help="Failed to load")
    
    st.markdown("---")
    
    # Data Freshness Dashboard
    st.header("Data Freshness")
    st.markdown("Last update time for each data mart")
    
    try:
        freshness_df = get_data_freshness()
        
        if not freshness_df.empty:
            # Add age column
            freshness_df['data_age'] = freshness_df.apply(
                lambda row: calculate_data_age(row.get('last_updated')), 
                axis=1
            )
            
            # Determine status based on row_count and last_updated
            def get_status(row):
                if row['row_count'] == 0 or row['row_count'] is None:
                    return "🔴 Empty"
                
                last_updated = row.get('last_updated')
                if last_updated is None or pd.isna(last_updated):
                    return "⚪ Unknown"
                
                age = datetime.now() - last_updated
                
                if age < timedelta(minutes=5):
                    return "🟢 Fresh"
                elif age < timedelta(hours=1):
                    return "🟡 Recent"
                elif age < timedelta(days=1):
                    return "🟠 Aging"
                else:
                    return "🔴 Stale"
            
            freshness_df['status'] = freshness_df.apply(get_status, axis=1)
            
            # Display as formatted table
            st.dataframe(
                freshness_df[['table_name', 'row_count', 'last_updated', 'data_age', 'status']],
                column_config={
                    'table_name': st.column_config.TextColumn('Table', width='large'),
                    'row_count': st.column_config.NumberColumn('Records', format='%d'),
                    'last_updated': st.column_config.DatetimeColumn('Last Update', format='YYYY-MM-DD HH:mm:ss'),
                    'data_age': st.column_config.TextColumn('Age', width='medium'),
                    'status': st.column_config.TextColumn('Status', width='medium'),
                },
                hide_index=True,
                width='stretch'
            )
            
            # Visual indicators for critical tables
            st.markdown("### Critical Tables Status")
            
            critical_tables = ['mart_team_overview', 'mart_upcoming_fixtures', 'mart_match_predictions']
            critical_df = freshness_df[freshness_df['table_name'].isin(critical_tables)]
            
            if not critical_df.empty:
                cols = st.columns(len(critical_df))
                
                for idx, (_, row) in enumerate(critical_df.iterrows()):
                    with cols[idx]:
                        status = row['status']
                        
                        st.metric(
                            label=row['table_name'].replace('mart_', '').replace('_', ' ').title(),
                            value=f"{row['row_count']} rows",
                            delta=row['data_age'],
                            delta_color="off"
                        )
                        
                        # Show status badge
                        if '🟢' in status:
                            st.success(status)
                        elif '🟡' in status or '🟠' in status:
                            st.warning(status)
                        else:
                            st.error(status)
            else:
                st.info("Critical tables: " + ", ".join(critical_tables))
        else:
            st.warning("No data freshness information available")
    
    except Exception as e:
        logger.error(f"Failed to get data freshness: {e}")
        st.error(f"Error loading data freshness: {e}")
    
    st.markdown("---")
    
    # System Health Indicators
    st.header("System Health")
    
    col1, col2, col3 = st.columns(3)
    
    # Database Status
    with col1:
        st.subheader("Database")
        db_status = check_database_status()
        
        if db_status['healthy']:
            st.success(db_status['status'])
            st.info(f"**Engine:** {db_status.get('engine_type', 'N/A')}")
            st.info(f"**Dialect:** {db_status.get('dialect', 'N/A')}")
        else:
            st.error(db_status['status'])
            if 'error' in db_status:
                with st.expander("Error Details"):
                    st.code(db_status['error'])
    
    # Cache Performance
    with col2:
        st.subheader("Cache Performance")
        try:
            monitor = CacheMonitor()
            cache_stats = monitor.get_stats()
            
            hit_rate = cache_stats.get('hit_rate', 0.0)
            
            if hit_rate >= 80:
                st.success(f"Hit Rate: {hit_rate:.1f}%")
            elif hit_rate >= 50:
                st.warning(f"Hit Rate: {hit_rate:.1f}%")
            else:
                st.error(f"Hit Rate: {hit_rate:.1f}%")
            
            st.metric("Cache Hits", cache_stats.get('hits', 0))
            st.metric("Cache Misses", cache_stats.get('misses', 0))
        except Exception as e:
            st.error(f"Cache error: {e}")
    
    # Error Monitoring
    with col3:
        st.subheader("Error Monitoring")
        try:
            monitor = CacheMonitor()
            cache_stats = monitor.get_stats()
            errors = cache_stats.get('errors', 0)
            
            if errors == 0:
                st.success("No Errors")
            else:
                st.error(f"{errors} Error(s)")
            
            st.metric("Cache Errors", errors)
        except Exception as e:
            st.error(f"Monitor error: {e}")
    
    st.markdown("---")
    
    # Footer
    st.markdown("### About")
    st.info(
        "This dashboard provides real-time analytics for football leagues. "
        "Data is sourced from Sofascore and processed through a DBT data warehouse."
    )


def page_fixtures():
    render_header("Fixtures")
    st.write("Upcoming fixtures and predictions will appear here.")
    st.warning("To be implemented: data query and table display.")


def page_teams():
    render_header("Teams")
    st.write("Team statistics, form, and performance metrics.")
    st.warning("To be implemented: filters, charts, and KPIs.")


def page_h2h():
    render_header("Head-to-Head")
    st.write("Compare two teams across historical matches.")
    st.warning("To be implemented: selectors and comparison charts.")


def page_insights():
    render_header("Insights")
    st.write("League-wide trends, anomalies, and calibration.")
    st.warning("To be implemented: dashboards and visualizations.")


def main():
    st.sidebar.markdown("## Navigation")
    selection = st.sidebar.radio("Go to:", list(PAGES.keys()), index=0)

    route = PAGES[selection]
    if route == "home":
        page_home()
    elif route == "fixtures":
        page_fixtures()
    elif route == "teams":
        page_teams()
    elif route == "h2h":
        page_h2h()
    elif route == "insights":
        page_insights()
    else:
        st.error("Page not found.")


if __name__ == "__main__":
    main()