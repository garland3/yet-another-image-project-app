import os
from pathlib import Path
from typing import Optional, Any
from diskcache import Cache
from core.config import settings

class CacheManager:
    """Simple wrapper around diskcache with project-specific configuration."""
    
    def __init__(self):
        cache_dir = Path(__file__).parent.parent / '_cache'
        cache_dir.mkdir(exist_ok=True)
        
        # Convert MB to bytes for size limit
        size_limit = settings.CACHE_SIZE_MB * 1024 * 1024
        
        self.cache = Cache(
            directory=str(cache_dir),
            size_limit=size_limit,
            eviction_policy='least-recently-used'
        )
    
    def set(self, key: str, value: Any, expire: Optional[float] = None):
        """Set a cache entry with optional expiration in seconds."""
        return self.cache.set(key, value, expire=expire)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a cache entry, return default if not found."""
        return self.cache.get(key, default)
    
    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        return self.cache.delete(key)
    
    def clear_pattern(self, pattern: str):
        """Clear all cache entries whose keys contain the pattern."""
        keys_to_delete = []
        for key in self.cache:
            if pattern in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            self.cache.delete(key)
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
    
    def stats(self) -> dict:
        """Get cache statistics."""
        volume = self.cache.volume()
        size_limit = settings.CACHE_SIZE_MB * 1024 * 1024
        
        return {
            'size_bytes': volume,
            'size_mb': round(volume / (1024 * 1024), 2),
            'limit_mb': settings.CACHE_SIZE_MB,
            'usage_percent': round((volume / size_limit) * 100, 2) if size_limit > 0 else 0,
            'count': len(self.cache)
        }

# Global cache manager instance
_cache_manager: Optional[CacheManager] = None

def get_cache() -> CacheManager:
    """Get or create the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager