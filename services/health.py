from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and responsiveness."""
    from services.db import test_connection
    
    try:
        start_time = datetime.now()
        connected = test_connection()
        response_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'status': 'healthy' if connected else 'unhealthy',
            'connected': connected,
            'response_time_seconds': response_time,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'connected': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def check_cache_health() -> Dict[str, Any]:
    """Check cache statistics."""
    try:
        from services.cache import CacheMonitor
        monitor = CacheMonitor()
        stats = monitor.get_stats()
        return {
            'status': 'healthy',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }