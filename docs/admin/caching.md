# Caching System

This guide explains the caching system in the Image Project Manager application, including setup, configuration, and usage.

## Overview

The application includes a pluggable caching system with two backends:

- **Disk Cache** (default) - File-based caching for single-instance deployments
- **Redis Cache** (optional) - Distributed caching for multi-instance deployments

The cache is used to improve performance for:
- Project image listings
- Image metadata queries
- Thumbnail data
- Frequently accessed API responses

## Cache Backends

### Disk Cache (Default)

**Characteristics:**
- Zero configuration required
- Suitable for single-instance deployments
- Data stored in `backend/_cache/` directory
- LRU (Least Recently Used) eviction policy
- Size limit configurable via `CACHE_SIZE_MB`

**Configuration:**
```bash
# .env
REDIS_ENABLED=false  # or omit (default)
CACHE_SIZE_MB=1000   # 1 GB limit
```

**When to use:**
- Single server deployment
- Development environment
- Testing
- No Redis infrastructure available

### Redis Cache (Optional)

**Characteristics:**
- Shared cache across multiple application instances
- Better performance for distributed deployments
- Supports cache sharing and atomic operations
- Automatic fallback to disk cache if unavailable
- Requires Redis server

**Configuration:**
```bash
# .env
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-password  # Optional
```

**When to use:**
- Multi-instance deployments (load balanced)
- Kubernetes/container orchestration
- Production environments with high traffic
- When cache consistency across instances matters

## Setup

### Using Disk Cache

No setup required. Disk cache is enabled by default.

### Using Redis Cache

#### Development (Docker Compose)

1. Start Redis:
```bash
docker compose up -d redis
```

2. Configure application:
```bash
# .env
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

3. Verify Redis is running:
```bash
docker compose ps redis
redis-cli ping  # Should return "PONG"
```

#### Production (Docker)

```bash
# Start Redis with persistence
docker run -d \
  --name redis \
  --restart unless-stopped \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine redis-server --appendonly yes --requirepass your-secure-password

# Configure application
REDIS_ENABLED=true
REDIS_HOST=redis-hostname
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-password
```

#### Production (Managed Services)

Use managed Redis services for production:

**AWS ElastiCache:**
```bash
REDIS_ENABLED=true
REDIS_HOST=your-cluster.cache.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=your-auth-token
```

**Azure Cache for Redis:**
```bash
REDIS_ENABLED=true
REDIS_HOST=your-cache.redis.cache.windows.net
REDIS_PORT=6380
REDIS_PASSWORD=your-access-key
```

**Google Cloud Memorystore:**
```bash
REDIS_ENABLED=true
REDIS_HOST=10.0.0.3  # Private IP
REDIS_PORT=6379
```

## Cache Behavior

### What Gets Cached

The cache stores:

1. **Project Image Listings** - List of images in a project with pagination
2. **Image Metadata** - Individual image details and metadata
3. **Thumbnail Data** - Pre-generated thumbnail information
4. **Query Results** - Filtered and searched image results

### Cache Keys

Cache keys follow consistent patterns:

```
project_images:{project_id}:skip:0:limit:100:include_deleted:false:...
image:{image_id}:metadata
thumbnail:{image_id}:640x480
analysis:{analysis_id}:results
```

### Cache Invalidation

Cache is automatically invalidated when data changes:

**On Image Upload:**
```python
# Clears all cached project image listings
cache.clear_pattern(f"project_images:{project_id}")
```

**On Image Update:**
```python
# Clears specific image metadata cache
cache.delete(f"image:{image_id}:metadata")
cache.clear_pattern(f"project_images:{project_id}")
```

**On Image Delete:**
```python
# Clears both image cache and project listings
cache.delete(f"image:{image_id}:metadata")
cache.clear_pattern(f"project_images:{project_id}")
```

### Cache Expiration

- **Default TTL:** No automatic expiration (manual invalidation only)
- **With expiration:** Use `expire` parameter when setting cache entries
- **Pattern-based clearing:** Efficient for related cache entries

## Monitoring

### Check Cache Backend

Application logs show which cache backend is active:

```
INFO - Using Redis cache backend
# or
INFO - Using disk cache backend
# or
WARNING - Redis cache initialization failed, falling back to disk cache
```

### Cache Statistics

Get cache statistics programmatically:

```python
from utils.cache_manager import get_cache

cache = get_cache()
stats = cache.stats()

print(stats)
# {
#   'size_bytes': 12345678,
#   'size_mb': 11.77,
#   'limit_mb': 1000,
#   'usage_percent': 1.18,
#   'count': 142  # number of cached entries
# }
```

### Redis Monitoring

Monitor Redis directly:

```bash
# Connect to Redis CLI
redis-cli -h localhost -p 6379

# Check info
INFO memory
INFO keyspace

# List keys (use carefully in production)
KEYS project_images:*

# Get key count
DBSIZE

# Monitor commands in real-time
MONITOR
```

## Troubleshooting

### Redis Connection Issues

**Symptom:** Application logs show "Redis cache initialization failed, falling back to disk cache"

**Causes and solutions:**

1. **Redis not running:**
   ```bash
   # Check if Redis is running
   docker compose ps redis
   # or
   systemctl status redis
   
   # Start Redis
   docker compose up -d redis
   ```

2. **Wrong host/port:**
   ```bash
   # Test connection
   redis-cli -h localhost -p 6379 ping
   
   # Verify .env settings
   echo $REDIS_HOST
   echo $REDIS_PORT
   ```

3. **Authentication required:**
   ```bash
   # Test with password
   redis-cli -h localhost -p 6379 -a your-password ping
   
   # Update .env
   REDIS_PASSWORD=your-password
   ```

4. **Firewall/network issues:**
   ```bash
   # Test connectivity
   telnet redis-host 6379
   # or
   nc -zv redis-host 6379
   
   # Check firewall rules
   sudo ufw status
   ```

### Cache Not Working

**Symptom:** Same data fetched repeatedly, no performance improvement

**Solutions:**

1. **Verify cache is enabled:**
   ```bash
   # Check logs for cache initialization
   grep "cache" /var/log/app.log
   ```

2. **Check cache size:**
   ```python
   cache = get_cache()
   print(cache.stats())
   # If count=0, cache is empty (may be too aggressive invalidation)
   ```

3. **Verify cache invalidation isn't too aggressive:**
   - Review cache invalidation patterns in code
   - Check if `cache.clear()` is called too frequently

### Performance Issues

**Symptom:** Slow cache operations

**Redis-specific:**
```bash
# Check Redis latency
redis-cli --latency

# Check slow log
redis-cli SLOWLOG GET 10

# Monitor memory usage
redis-cli INFO memory
```

**Disk cache-specific:**
```bash
# Check disk I/O
iostat -x 1

# Check cache directory size
du -sh backend/_cache/
```

### Cache Inconsistency

**Symptom:** Different instances show different data

**Only affects Redis cache:**

1. **Verify all instances use same Redis:**
   ```bash
   # All instances should have same REDIS_HOST
   echo $REDIS_HOST
   ```

2. **Check Redis clustering/replication:**
   ```bash
   redis-cli INFO replication
   ```

3. **Force cache clear:**
   ```python
   cache = get_cache()
   cache.clear()  # Nuclear option - clears everything
   ```

## Best Practices

### Development
- Use disk cache for simplicity
- Clear cache between tests
- Monitor cache hit/miss ratios

### Production
- Use Redis for multi-instance deployments
- Enable Redis persistence (AOF)
- Monitor Redis memory usage
- Set up Redis replication for high availability
- Use managed Redis services when possible
- Configure appropriate `CACHE_SIZE_MB` based on available memory

### Code
- Always invalidate cache when data changes
- Use consistent cache key patterns
- Use pattern-based clearing for related entries
- Test with cache disabled to catch bugs
- Add cache warming for critical paths if needed

## Migration

### Switching from Disk to Redis

1. **Set up Redis** (see Setup section above)

2. **Update configuration:**
   ```bash
   REDIS_ENABLED=true
   REDIS_HOST=your-redis-host
   REDIS_PORT=6379
   ```

3. **Restart application**

4. **Verify in logs:**
   ```
   INFO - Using Redis cache backend
   ```

Existing disk cache will be ignored (not migrated). Cache will rebuild naturally as data is accessed.

### Switching from Redis to Disk

1. **Update configuration:**
   ```bash
   REDIS_ENABLED=false
   ```

2. **Restart application**

3. **Verify in logs:**
   ```
   INFO - Using disk cache backend
   ```

Cache will rebuild naturally. No data loss (cache is ephemeral by design).

## References

- [Configuration Guide](configuration.md) - Full configuration options
- [Developer Guide](../developer-guide.md) - Using cache in code
- [Redis Documentation](https://redis.io/docs/) - Official Redis docs
- [diskcache Documentation](http://www.grantjenks.com/docs/diskcache/) - Disk cache library
