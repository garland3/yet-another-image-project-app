import json
import logging
from typing import Optional, Any
import redis
from core.config import settings

logger = logging.getLogger(__name__)

class RedisCacheManager:
    """Redis-based cache manager with the same interface as CacheManager."""
    
    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=False,  # We'll handle serialization ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis cache initialized at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage in Redis."""
        return json.dumps(value).encode('utf-8')
    
    def _deserialize(self, value: Optional[bytes]) -> Any:
        """Deserialize value from Redis."""
        if value is None:
            return None
        return json.loads(value.decode('utf-8'))
    
    def set(self, key: str, value: Any, expire: Optional[float] = None):
        """Set a cache entry with optional expiration in seconds."""
        try:
            serialized = self._serialize(value)
            if expire:
                # Redis expects expiration in seconds as an integer
                self.redis_client.setex(key, int(expire), serialized)
            else:
                self.redis_client.set(key, serialized)
            return True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a cache entry, return default if not found."""
        try:
            value = self.redis_client.get(key)
            if value is None:
                return default
            return self._deserialize(value)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str):
        """Clear all cache entries whose keys contain the pattern."""
        try:
            # Use SCAN to iterate through keys matching the pattern
            # SCAN is more efficient than KEYS for production use
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=f"*{pattern}*", count=100)
                if keys:
                    self.redis_client.delete(*keys)
                if cursor == 0:
                    break
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis clear_pattern error for pattern {pattern}: {e}")
    
    def clear(self):
        """Clear all cache entries."""
        try:
            self.redis_client.flushdb()
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis clear error: {e}")
    
    def stats(self) -> dict:
        """Get cache statistics."""
        try:
            info = self.redis_client.info('memory')
            db_info = self.redis_client.info('keyspace')
            
            # Get total memory used by Redis
            used_memory = info.get('used_memory', 0)
            
            # Get number of keys in the current database
            db_key = f'db{settings.REDIS_DB}'
            key_count = 0
            if db_key in db_info:
                # Parse format: "keys=123,expires=45,avg_ttl=1234567"
                keys_info = db_info[db_key]
                if 'keys' in keys_info:
                    key_count = keys_info['keys']
            
            # Convert to MB
            size_mb = round(used_memory / (1024 * 1024), 2)
            
            # Note: Redis doesn't have a fixed size limit like diskcache
            # We'll use CACHE_SIZE_MB as a reference for usage percent
            limit_mb = settings.CACHE_SIZE_MB
            usage_percent = round((size_mb / limit_mb) * 100, 2) if limit_mb > 0 else 0
            
            return {
                'size_bytes': used_memory,
                'size_mb': size_mb,
                'limit_mb': limit_mb,
                'usage_percent': usage_percent,
                'count': key_count
            }
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis stats error: {e}")
            return {
                'size_bytes': 0,
                'size_mb': 0,
                'limit_mb': settings.CACHE_SIZE_MB,
                'usage_percent': 0,
                'count': 0
            }
