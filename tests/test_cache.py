import pytest
import time
from services.cache import (
    CacheManager,
    CacheMonitor,
    cache_query_result,
    cache_resource_singleton,
    generate_cache_key,
)


@pytest.mark.unit
class TestCacheUtilities:
    """Test cache utility functions."""
    
    def test_generate_cache_key_consistent(self):
        """Test that same inputs generate same key."""
        key1 = generate_cache_key(1, 2, foo='bar')
        key2 = generate_cache_key(1, 2, foo='bar')
        assert key1 == key2
    
    def test_generate_cache_key_different(self):
        """Test that different inputs generate different keys."""
        key1 = generate_cache_key(1, 2)
        key2 = generate_cache_key(1, 3)
        assert key1 != key2


@pytest.mark.unit  
class TestCacheMonitor:
    """Test cache monitoring functionality."""
    
    def test_record_hit(self):
        """Test recording cache hits."""
        monitor = CacheMonitor()
        monitor.reset_stats()
        
        monitor.record_hit()
        stats = monitor.get_stats()
        
        assert stats['hits'] == 1
        assert stats['misses'] == 0
    
    def test_record_miss(self):
        """Test recording cache misses."""
        monitor = CacheMonitor()
        monitor.reset_stats()
        
        monitor.record_miss()
        stats = monitor.get_stats()
        
        assert stats['hits'] == 0
        assert stats['misses'] == 1
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        monitor = CacheMonitor()
        monitor.reset_stats()
        
        # Record 8 hits and 2 misses = 80% hit rate
        for _ in range(8):
            monitor.record_hit()
        for _ in range(2):
            monitor.record_miss()
        
        stats = monitor.get_stats()
        assert stats['hit_rate'] == 80.0


@pytest.mark.integration
class TestCachePerformance:
    """Test cache performance characteristics."""
    
    def test_cache_speeds_up_queries(self):
        """Test that caching actually speeds up repeated calls."""
        
        @cache_query_result(ttl=60)
        def slow_function():
            time.sleep(0.1)  # Simulate slow operation
            return "result"
        
        # First call (cache miss) should be slow
        start1 = time.time()
        result1 = slow_function()
        time1 = time.time() - start1
        
        # Second call (cache hit) should be fast
        start2 = time.time()
        result2 = slow_function()
        time2 = time.time() - start2
        
        assert result1 == result2
        assert time2 < time1 / 2  # Cached call should be at least 2x faster