# Configuration

This guide covers all configuration options for the Image Project Manager application.

## Configuration Overview

All configuration is done via environment variables, typically stored in a `.env` file at the project root.

### Configuration File

```bash
# Copy template
cp .env.example .env

# Edit with your settings
nano .env  # or vim, code, etc.
```

## Application Settings

### Basic Settings

```bash
# Application name
APP_NAME="Image Project Manager"

# Debug mode (MUST be false in production)
DEBUG=false

# Skip authentication header checks (development only)
SKIP_HEADER_CHECK=false

# Fast test mode (skips external dependencies in tests)
FAST_TEST_MODE=false
```

**Important:**
- Set `DEBUG=false` in production to prevent information leakage
- Set `SKIP_HEADER_CHECK=false` in production for security
- Only use `FAST_TEST_MODE=true` in test environments

## Authentication & Authorization

### Development Mode

For local development and testing:

```bash
# Enable mock user (when SKIP_HEADER_CHECK=true)
MOCK_USER_EMAIL="admin@example.com"
MOCK_USER_GROUPS_JSON='["admin-group", "data-scientists", "project-alpha"]'

# Enable mock group membership checks
CHECK_MOCK_MEMBERSHIP=true
```

### Production Mode

For production deployments with reverse proxy authentication:

```bash
# Shared secret between reverse proxy and backend
PROXY_SHARED_SECRET="your-secure-random-secret-here"

# Header names for authentication
X_USER_ID_HEADER="X-User-Email"
X_PROXY_SECRET_HEADER="X-Proxy-Secret"

# Auth server URL (for documentation/reference)
AUTH_SERVER_URL="https://auth.example.com"
```

**Generate Secure Secret:**
```bash
openssl rand -hex 32
```

### API Key Authentication

API keys are managed through the web interface. No special configuration required.

## Database Configuration

### PostgreSQL Settings

```bash
# Individual connection parameters
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=imagemanager
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432

# Or use complete connection URL (takes precedence)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/imagemanager
```

**Production Examples:**

Remote database:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@db.example.com:5432/imagemanager
```

Docker internal network:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/imagemanager
```

With SSL:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
```

### Database Pool Settings

```bash
# Connection pool size (optional)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

### Migration Settings

```bash
# Enable/disable Alembic migrations (default: true)
USE_ALEMBIC_MIGRATIONS=true
```

## Storage Configuration

### S3/MinIO Settings

```bash
# S3 endpoint (without http/https prefix)
S3_ENDPOINT=s3.amazonaws.com           # AWS S3
# or
S3_ENDPOINT=localhost:9000             # Local MinIO

# Credentials
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key

# Bucket name
S3_BUCKET=image-project-manager

# SSL/TLS
S3_USE_SSL=true                        # Use https
S3_USE_SSL=false                       # Use http (local MinIO)

# Region (AWS S3 only)
S3_REGION=us-east-1
```

### MinIO Example

```bash
S3_ENDPOINT=minio.example.com:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadminpassword
S3_BUCKET=images
S3_USE_SSL=true
S3_REGION=us-east-1
```

### AWS S3 Example

```bash
S3_ENDPOINT=s3.amazonaws.com
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_BUCKET=my-image-bucket
S3_USE_SSL=true
S3_REGION=us-west-2
```

## ML Analysis Configuration

Optional feature for machine learning integration.

```bash
# Enable ML analysis feature
ML_ANALYSIS_ENABLED=true

# HMAC secret for pipeline authentication
ML_CALLBACK_HMAC_SECRET=your-hmac-secret

# Allowed model names (comma-separated)
ML_ALLOWED_MODELS=yolo_v8,resnet50,custom_model,ensemble_v1
```

**Generate HMAC Secret:**
```bash
openssl rand -hex 32
```

See [ML Analysis API Guide](../api-ml-guide.md) for integration details.

## Security Headers

### CORS Configuration

```bash
# Allowed origins (comma-separated)
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com

# Or allow all (development only!)
ALLOWED_ORIGINS=*
```

### Content Security Policy

```bash
# CSP policy string
CSP_POLICY="default-src 'self'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline'"
```

Default CSP if not set:
- `default-src 'self'`
- `img-src 'self' data: https:`
- `script-src 'self'`
- `style-src 'self' 'unsafe-inline'`

## Logging Configuration

```bash
# Log level
LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Log file path
LOG_FILE_PATH=/var/log/image-manager/app.log

# Enable JSON logging
LOG_JSON=true
```

## Cache Configuration

The application supports two caching backends: **disk cache** (default) and **Redis** (optional).

### Disk Cache (Default)

Disk cache is enabled by default and requires no additional setup.

```bash
# Cache size limit (MB)
CACHE_SIZE_MB=1000

# Redis disabled (default)
REDIS_ENABLED=false
```

**Disk cache characteristics:**
- Zero configuration required
- Suitable for single-instance deployments
- Data persists in `backend/_cache/` directory
- LRU (Least Recently Used) eviction policy

### Redis Cache (Optional)

Redis provides better performance for distributed deployments and allows cache sharing across multiple application instances.

```bash
# Enable Redis cache
REDIS_ENABLED=true

# Redis connection settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Redis password (optional, for secured Redis instances)
REDIS_PASSWORD=your-redis-password
```

**Redis cache characteristics:**
- Shared cache across multiple application instances
- Better performance for distributed deployments
- Automatic fallback to disk cache if Redis is unavailable
- Requires Redis server (see setup below)

### Starting Redis with Docker Compose

For development and testing:

```bash
# Start Redis alongside other services
docker compose up -d redis

# Verify Redis is running
docker compose ps redis
```

### Production Redis Setup

**Using Docker:**
```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine redis-server --appendonly yes
```

**Using managed Redis:**
- AWS ElastiCache
- Azure Cache for Redis
- Google Cloud Memorystore
- Redis Cloud

Configure the connection in `.env`:
```bash
REDIS_ENABLED=true
REDIS_HOST=your-redis-host.example.com
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-password
```

### Cache Behavior

The cache is used for:
- Project image listings
- Image metadata
- Thumbnail data
- API responses for frequently accessed data

**Cache invalidation:**
- Automatically cleared when data is modified (create, update, delete operations)
- Pattern-based clearing for related cache entries
- Manual clearing via admin endpoints (if available)

**Cache keys format:**
```
project_images:{project_id}:skip:{skip}:limit:{limit}:...
image:{image_id}:metadata
thumbnail:{image_id}:{size}
```

### Monitoring Cache Performance

Check cache statistics programmatically:
```python
from utils.cache_manager import get_cache

cache = get_cache()
stats = cache.stats()

# Returns:
# {
#   'size_bytes': 1234567,
#   'size_mb': 1.18,
#   'limit_mb': 1000,
#   'usage_percent': 0.12,
#   'count': 42  # number of cache entries
# }
```

### Troubleshooting

**Redis connection failures:**
- Application automatically falls back to disk cache
- Check logs for "Redis cache initialization failed, falling back to disk cache"
- Verify Redis is running: `redis-cli ping` (should return "PONG")
- Check firewall rules if Redis is on another host

**Cache not being used:**
- Verify `REDIS_ENABLED=true` is set correctly
- Check application logs for cache backend initialization
- Confirm Redis connectivity with `redis-cli -h <host> -p <port> ping`

## Deletion Configuration

```bash
# Soft delete retention period (days)
DELETION_RETENTION_DAYS=60             # Default: 60 days

# Enable automatic hard deletion after retention period
AUTO_HARD_DELETE=true
```

## Performance Tuning

### Worker Configuration

For production with Gunicorn:

```bash
# Number of worker processes
WORKERS=4

# Worker class
WORKER_CLASS=uvicorn.workers.UvicornWorker

# Connections per worker
WORKER_CONNECTIONS=1000

# Timeout
TIMEOUT=30
```

### Request Limits

```bash
# Maximum upload file size (bytes)
MAX_UPLOAD_SIZE=10485760               # 10 MB

# Request timeout (seconds)
REQUEST_TIMEOUT=30
```

## Environment-Specific Configurations

### Development

```bash
DEBUG=true
SKIP_HEADER_CHECK=true
MOCK_USER_EMAIL=dev@example.com
MOCK_USER_GROUPS_JSON='["admin-group"]'
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/postgres
S3_ENDPOINT=localhost:9000
S3_USE_SSL=false
ALLOWED_ORIGINS=*
LOG_LEVEL=DEBUG
```

### Staging

```bash
DEBUG=false
SKIP_HEADER_CHECK=false
PROXY_SHARED_SECRET=<staging-secret>
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/imagemanager
S3_ENDPOINT=staging-s3.example.com
S3_USE_SSL=true
ALLOWED_ORIGINS=https://staging.example.com
LOG_LEVEL=INFO
```

### Production

```bash
DEBUG=false
SKIP_HEADER_CHECK=false
PROXY_SHARED_SECRET=<production-secret>
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/imagemanager
S3_ENDPOINT=s3.amazonaws.com
S3_USE_SSL=true
ALLOWED_ORIGINS=https://app.example.com
LOG_LEVEL=WARNING
ML_ANALYSIS_ENABLED=true
ML_CALLBACK_HMAC_SECRET=<ml-secret>
AUTO_HARD_DELETE=true
```

## Docker-Specific Configuration

### Host Port Mapping

When running backend/database in Docker but accessing from host:

```bash
# Host machine connects to Docker PostgreSQL
HOST_DB_PORT=5433
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/postgres

# Docker-to-Docker communication uses service name
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/postgres
```

### Docker Compose Environment

Environment variables can be set in `docker-compose.yml`:

```yaml
services:
  app:
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/imagemanager
      - S3_ENDPOINT=minio:9000
```

## Kubernetes Configuration

Use ConfigMaps and Secrets:

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  S3_ENDPOINT: "s3.amazonaws.com"
  S3_BUCKET: "image-project-manager"

# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  PROXY_SHARED_SECRET: "your-secret"
  DATABASE_URL: "postgresql+asyncpg://user:pass@postgres:5432/db"
  S3_ACCESS_KEY: "access-key"
  S3_SECRET_KEY: "secret-key"
```

## Configuration Validation

The application validates configuration on startup. Common issues:

**Missing Required Variables:**
```
Error: DATABASE_URL is required
```
Solution: Set DATABASE_URL in .env

**Invalid Database URL:**
```
Error: Invalid DATABASE_URL format
```
Solution: Ensure URL follows format: `postgresql+asyncpg://user:pass@host:port/db`

**Invalid S3 Configuration:**
```
Error: Could not connect to S3
```
Solution: Verify S3_ENDPOINT, credentials, and SSL settings

## Testing Configuration

Test your configuration:

```bash
# Test database connection
python -c "from backend.core.database import engine; import asyncio; asyncio.run(engine.connect())"

# Test S3 connection
python -c "from backend.utils.boto3_client import get_s3_client; s3 = get_s3_client(); s3.list_buckets()"

# Test application startup
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Configuration Best Practices

1. **Never commit secrets** to version control
2. **Use strong random secrets** for PROXY_SHARED_SECRET and ML_CALLBACK_HMAC_SECRET
3. **Set appropriate CORS origins** - never use `*` in production
4. **Enable SSL/TLS** for all external connections
5. **Use environment-specific configs** - separate .env files for dev/staging/prod
6. **Document custom settings** - add comments to .env file
7. **Rotate secrets regularly** - especially PROXY_SHARED_SECRET
8. **Monitor configuration changes** - use version control for .env.example
9. **Validate before deployment** - test configuration in staging first
10. **Use secrets managers** in production (AWS Secrets Manager, Vault, etc.)

## Next Steps

- [Set up authentication](authentication.md)
- [Configure database](database.md)
- [Configure storage](storage.md)
