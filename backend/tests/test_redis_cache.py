import pytest
import redis
from unittest.mock import patch, MagicMock
from utils.redis_cache import RedisCacheManager
from core.config import settings


class TestRedisCacheManager:
    """Unit tests for the RedisCacheManager."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing without a real Redis server."""
        with patch('utils.redis_cache.redis.Redis') as mock:
            redis_mock = MagicMock()
            mock.return_value = redis_mock
            # Mock successful ping
            redis_mock.ping.return_value = True
            yield redis_mock
    
    @pytest.fixture
    def redis_cache(self, mock_redis):
        """Create a RedisCacheManager with mocked Redis."""
        return RedisCacheManager()
    
    def test_redis_cache_initialization(self, mock_redis):
        """Test Redis cache initialization."""
        cache = RedisCacheManager()
        assert cache.redis_client is not None
        mock_redis.ping.assert_called_once()
    
    def test_redis_cache_initialization_failure(self):
        """Test Redis cache initialization failure handling."""
        with patch('utils.redis_cache.redis.Redis') as mock:
            mock.return_value.ping.side_effect = redis.ConnectionError("Connection failed")
            with pytest.raises(redis.ConnectionError):
                RedisCacheManager()
    
    def test_cache_set_and_get(self, redis_cache, mock_redis):
        """Test basic cache set and get operations."""
        # Mock Redis get to return serialized value
        mock_redis.get.return_value = b'"test_value"'
        
        # Test string value
        redis_cache.set("test_key", "test_value")
        mock_redis.set.assert_called()
        
        result = redis_cache.get("test_key")
        mock_redis.get.assert_called_with("test_key")
        assert result == "test_value"
        
        # Test dict value
        test_data = {"name": "test", "count": 42}
        mock_redis.get.return_value = b'{"name": "test", "count": 42}'
        redis_cache.set("dict_key", test_data)
        result = redis_cache.get("dict_key")
        assert result == test_data
        
        # Test non-existent key
        mock_redis.get.return_value = None
        result = redis_cache.get("nonexistent", "default")
        assert result == "default"
    
    def test_cache_set_with_expiration(self, redis_cache, mock_redis):
        """Test cache set with expiration."""
        redis_cache.set("expire_key", "expire_value", expire=60)
        mock_redis.setex.assert_called_with("expire_key", 60, b'"expire_value"')
    
    def test_cache_delete(self, redis_cache, mock_redis):
        """Test cache deletion."""
        mock_redis.delete.return_value = 1
        success = redis_cache.delete("delete_key")
        assert success is True
        mock_redis.delete.assert_called_with("delete_key")
        
        # Delete non-existent key
        mock_redis.delete.return_value = 0
        success = redis_cache.delete("nonexistent")
        assert success is False
    
    def test_cache_clear_pattern(self, redis_cache, mock_redis):
        """Test pattern-based cache clearing."""
        # Mock SCAN to return keys
        mock_redis.scan.side_effect = [
            (0, [b'project:123:images', b'project:123:metadata']),
        ]
        
        redis_cache.clear_pattern("project:123")
        
        # Verify SCAN was called with pattern
        mock_redis.scan.assert_called_with(0, match="*project:123*", count=100)
        # Verify delete was called with found keys
        mock_redis.delete.assert_called_with(b'project:123:images', b'project:123:metadata')
    
    def test_cache_clear(self, redis_cache, mock_redis):
        """Test clearing all cache entries."""
        redis_cache.clear()
        mock_redis.flushdb.assert_called_once()
    
    def test_cache_stats(self, redis_cache, mock_redis):
        """Test cache statistics."""
        # Mock Redis info responses
        mock_redis.info.side_effect = [
            {'used_memory': 1048576},  # 1 MB
            {'db0': {'keys': 10, 'expires': 5}}
        ]
        
        stats = redis_cache.stats()
        
        # Check stats structure
        assert "size_bytes" in stats
        assert "size_mb" in stats
        assert "limit_mb" in stats
        assert "usage_percent" in stats
        assert "count" in stats
        
        # Check values
        assert stats["size_bytes"] == 1048576
        assert stats["size_mb"] == 1.0
        assert stats["count"] == 10
    
    def test_serialization_edge_cases(self, redis_cache):
        """Test serialization of various data types."""
        # Test None
        serialized = redis_cache._serialize(None)
        deserialized = redis_cache._deserialize(serialized)
        assert deserialized is None
        
        # Test list
        test_list = [1, 2, 3, "four"]
        serialized = redis_cache._serialize(test_list)
        deserialized = redis_cache._deserialize(serialized)
        assert deserialized == test_list
        
        # Test nested dict
        test_nested = {"outer": {"inner": "value"}}
        serialized = redis_cache._serialize(test_nested)
        deserialized = redis_cache._deserialize(serialized)
        assert deserialized == test_nested
    
    def test_connection_error_handling(self, redis_cache, mock_redis):
        """Test handling of Redis connection errors."""
        # Simulate connection error on set
        mock_redis.set.side_effect = redis.ConnectionError("Connection lost")
        result = redis_cache.set("key", "value")
        assert result is False
        
        # Simulate connection error on get
        mock_redis.get.side_effect = redis.ConnectionError("Connection lost")
        result = redis_cache.get("key", "default")
        assert result == "default"
        
        # Simulate connection error on delete
        mock_redis.delete.side_effect = redis.ConnectionError("Connection lost")
        result = redis_cache.delete("key")
        assert result is False


class TestCacheManagerRedisIntegration:
    """Integration tests for cache_manager with Redis backend."""
    
    def test_cache_manager_uses_redis_when_enabled(self, monkeypatch):
        """Test that get_cache() returns Redis cache when REDIS_ENABLED=true."""
        # Reset global cache manager
        from utils import cache_manager
        cache_manager._cache_manager = None
        
        # Mock settings and Redis
        with patch('utils.cache_manager.settings') as mock_settings, \
             patch('utils.redis_cache.RedisCacheManager') as mock_redis_cls:
            mock_settings.REDIS_ENABLED = True
            mock_redis_instance = MagicMock()
            mock_redis_cls.return_value = mock_redis_instance
            
            cache = cache_manager.get_cache()
            
            # Verify Redis cache was created
            mock_redis_cls.assert_called_once()
            assert cache == mock_redis_instance
            
            # Reset for next test
            cache_manager._cache_manager = None
    
    def test_cache_manager_uses_disk_cache_when_disabled(self):
        """Test that get_cache() returns disk cache when REDIS_ENABLED=false."""
        # Reset global cache manager
        from utils import cache_manager
        cache_manager._cache_manager = None
        
        with patch('utils.cache_manager.settings') as mock_settings:
            mock_settings.REDIS_ENABLED = False
            mock_settings.CACHE_SIZE_MB = 100
            
            cache = cache_manager.get_cache()
            
            # Verify disk cache was created
            from utils.cache_manager import CacheManager
            assert isinstance(cache, CacheManager) or hasattr(cache, '_memory_cache')
            
            # Reset for next test
            cache_manager._cache_manager = None
    
    def test_cache_manager_fallback_on_redis_failure(self):
        """Test that get_cache() falls back to disk cache if Redis fails."""
        # Reset global cache manager
        from utils import cache_manager
        cache_manager._cache_manager = None
        
        with patch('utils.cache_manager.settings') as mock_settings, \
             patch('utils.redis_cache.RedisCacheManager') as mock_redis_cls:
            mock_settings.REDIS_ENABLED = True
            mock_settings.CACHE_SIZE_MB = 100
            # Simulate Redis initialization failure
            mock_redis_cls.side_effect = redis.ConnectionError("Redis unavailable")
            
            cache = cache_manager.get_cache()
            
            # Verify fallback to disk cache
            from utils.cache_manager import CacheManager
            assert isinstance(cache, CacheManager) or hasattr(cache, '_memory_cache')
            
            # Reset for next test
            cache_manager._cache_manager = None
