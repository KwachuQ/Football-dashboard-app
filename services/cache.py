"""
Caching utilities for Streamlit application.
Implements cache decorators, monitoring, and management.
"""
import streamlit as st
from functools import wraps
from typing import Any, Callable, Optional, Dict
from datetime import datetime
import logging
import hashlib
import json
import time

logger = logging.getLogger(__name__)

# ============================================================================
# Loading time logging
# ============================================================================

def time_page_load(func: Callable) -> Callable:
    """Decorator measures page load time and saves it to session_state.timings"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        load_time = time.time() - start_time
        
        if 'timings' not in st.session_state:
            st.session_state.timings = {}
        
        page_name = func.__name__.replace('_', ' ').title()
        st.session_state.timings[page_name] = f"{load_time:.2f}s"
        
        logger.info(f"Page '{page_name}' loaded in {load_time:.2f}s")
        
        return result
    return wrapper

def show_timings_sidebar():
    """Displays page load times in the sidebar"""
    if 'timings' in st.session_state and st.session_state.timings:
        st.sidebar.markdown("### Page Load Times")
        for page, duration in st.session_state.timings.items():
            st.sidebar.markdown(f"**{page}**: {duration}")
        st.sidebar.markdown("---")

def show_timings_inline():
    """Inline timings display"""
    if 'timings' in st.session_state and st.session_state.timings:
        st.markdown("---")
        st.markdown("#### Page Load Time")
        for page, duration in st.session_state.timings.items():
            st.markdown(f"**{page}**: {duration}")
        st.markdown("---")

# ============================================================================
# Streamlit Cache Decorators
# ============================================================================

def cache_resource_singleton():
    """
    Decorator for caching singleton resources like database engines.
    
    Usage:
        @cache_resource_singleton()
        def get_engine():
            return create_engine(...)
    """
    return st.cache_resource(ttl=None, show_spinner=False)


def cache_query_result(ttl: int = 600):
    """
    Decorator for caching query results.
    
    Args:
        ttl: Time to live in seconds (default: 600 = 10 minutes)
    
    Usage:
        @cache_query_result(ttl=300)
        def get_team_stats(team_id: int):
            ...
    """
    return st.cache_data(ttl=ttl, show_spinner=False)


# ============================================================================
# Cache Management
# ============================================================================

class CacheManager:
    """Manage Streamlit cache operations."""
    
    @staticmethod
    def clear_query_cache() -> bool:
        """
        Clear all cached query results.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            st.cache_data.clear()
            logger.info("Query cache cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear query cache: {e}")
            return False
    
    @staticmethod
    def clear_resource_cache() -> bool:
        """
        Clear all cached resources (DB connections, etc.).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            st.cache_resource.clear()
            logger.info("Resource cache cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear resource cache: {e}")
            return False
    
    @staticmethod
    def clear_all_caches() -> bool:
        """
        Clear all caches (data and resources).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            st.cache_data.clear()
            st.cache_resource.clear()
            logger.info("All caches cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear all caches: {e}")
            return False

class CacheWarmer:
    """Pre-populate cache with commonly used data."""
    
    @staticmethod
    def warm_common_queries(season_id: Optional[int] = None):
        """
        Pre-load common queries into cache.
        
        Args:
            season_id: Optional season ID to warm cache for
        """
        from services.queries import (
            get_all_seasons,
            get_upcoming_fixtures,
            get_league_standings,
            get_bulk_league_stats
        )
        
        try:
            logger.info("Starting cache warm-up...")
            
            # Warm season data
            seasons_df = get_all_seasons()
            if not seasons_df.empty and not season_id:
                season_id = seasons_df.iloc[0]['season_id']
            
            # Warm league standings and stats
            if season_id:
                get_league_standings(season_id)
                get_bulk_league_stats(season_id)
            
            # Warm upcoming fixtures and its team data to speed up Compare page
            fixtures_df = get_upcoming_fixtures(season_id=season_id, limit=20)
            if not fixtures_df.empty:
                # Warm first 5 fixtures specifically for Compare page
                from services.queries import get_all_team_stats, get_btts_analysis, get_team_form, get_head_to_head
                
                # Deduplicate team IDs
                teams_to_warm = set()
                h2h_to_warm = []
                
                for _, row in fixtures_df.head(5).iterrows():
                    teams_to_warm.add(row['home_team_id'])
                    teams_to_warm.add(row['away_team_id'])
                    h2h_to_warm.append((row['home_team_id'], row['away_team_id']))
                
                for tid in teams_to_warm:
                    get_all_team_stats(tid, season_id)
                    get_btts_analysis(tid, season_id)
                    get_team_form(tid, 5)
                
                for t1, t2 in h2h_to_warm:
                    get_head_to_head(t1, t2)
            
            logger.info("Cache warm-up completed")
            
        except Exception as e:
            logger.error(f"Error during cache warm-up: {e}")

# ============================================================================
# Cache Monitoring
# ============================================================================

class CacheMonitor:
    """Monitor cache performance and statistics."""
    
    _stats_key = "_cache_stats"
    
    def __init__(self):
        """Initialize cache monitor with session state."""
        if self._stats_key not in st.session_state:
            st.session_state[self._stats_key] = {
                'hits': 0,
                'misses': 0,
                'errors': 0,
                'last_reset': datetime.now()
            }
    
    def record_hit(self):
        """Record a cache hit."""
        st.session_state[self._stats_key]['hits'] += 1
    
    def record_miss(self):
        """Record a cache miss."""
        st.session_state[self._stats_key]['misses'] += 1
    
    def record_error(self):
        """Record a cache error."""
        st.session_state[self._stats_key]['errors'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache performance metrics
        """
        stats = st.session_state[self._stats_key]
        total = stats['hits'] + stats['misses']
        
        return {
            'hits': stats['hits'],
            'misses': stats['misses'],
            'errors': stats['errors'],
            'total_requests': total,
            'hit_rate': (stats['hits'] / total * 100) if total > 0 else 0.0,
            'last_reset': stats['last_reset']
        }
    
    def reset_stats(self):
        """Reset cache statistics."""
        st.session_state[self._stats_key] = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'last_reset': datetime.now()
        }
        logger.info("Cache statistics reset")


# ============================================================================
# Cache Utilities
# ============================================================================

def generate_cache_key(*args, **kwargs) -> str:
    """
    Generate a unique cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        MD5 hash of serialized arguments
    """
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    serialized = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode()).hexdigest()


def cache_with_monitoring(ttl: int = 600):
    """
    Decorator that adds cache monitoring to cached functions.
    
    Args:
        ttl: Time to live in seconds
    
    Usage:
        @cache_with_monitoring(ttl=300)
        def expensive_query():
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Apply Streamlit cache
        cached_func = st.cache_data(ttl=ttl, show_spinner=False)(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = CacheMonitor()
            
            try:
                # Try to get from cache
                result = cached_func(*args, **kwargs)
                monitor.record_hit()
                return result
            except Exception as e:
                monitor.record_error()
                logger.error(f"Cache error in {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator


def invalidate_cache_on_error(func: Callable) -> Callable:
    """
    Decorator that invalidates cache if function raises an error.
    
    Usage:
        @invalidate_cache_on_error
        @st.cache_data(ttl=300)
        def fragile_query():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Error in {func.__name__}, clearing cache: {e}")
            st.cache_data.clear()
            raise
    
    return wrapper


# ============================================================================
# Cache Warming
# ============================================================================



# ============================================================================
# Freshness Tracking
# ============================================================================

# class FreshnessTracker:
#     """Track data freshness and trigger cache invalidation."""
    
#     _freshness_key = "_data_freshness"
    
#     def __init__(self):
#         """Initialize freshness tracker."""
#         if self._freshness_key not in st.session_state:
#             st.session_state[self._freshness_key] = {
#                 'last_check': None,
#                 'stale_tables': []
#             }
    
    # def check_freshness(self, max_age_minutes: int = 60):
    #     """
    #     Check data freshness and invalidate cache if stale.
        
    #     Args:
    #         max_age_minutes: Maximum acceptable data age in minutes
    #     """
    #     from services.queries import # get_data_freshness
        
    #     try:
    #         freshness_df = # get_data_freshness()
            
    #         if freshness_df.empty:
    #             return
            
    #         # Check which tables are stale
    #         stale = []
    #         for _, row in freshness_df.iterrows():
    #             if row['status'] in ['🔴 Stale', 'EMPTY']:
    #                 stale.append(row['table_name'])
            
    #         # If stale tables changed, clear cache
    #         if stale != st.session_state[self._freshness_key]['stale_tables']:
    #             logger.warning(f"Stale tables detected: {stale}. Clearing cache.")
    #             CacheManager.clear_query_cache()
    #             st.session_state[self._freshness_key]['stale_tables'] = stale
            
    #         st.session_state[self._freshness_key]['last_check'] = datetime.now()
            
    #     except Exception as e:
    #         logger.error(f"Error checking freshness: {e}")