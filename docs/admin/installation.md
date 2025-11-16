# Installation & Deployment

This guide covers installation and deployment options for the Image Project Manager application.

## System Requirements

### Hardware Requirements

**Minimum (Development):**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB (plus storage for images)

**Recommended (Production):**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 50 GB (plus storage for images)
- Network: 1 Gbps

### Software Requirements

**Required:**
- Docker 20.10+ and Docker Compose 2.0+
- PostgreSQL 15+ (or Docker container)
- S3-compatible object storage (MinIO or AWS S3)
- Reverse proxy with authentication (nginx, Apache, etc.)

**For Development:**
- Python 3.11+
- Node.js 22+
- uv (Python package manager)

### Network Requirements

- HTTP/HTTPS access for web interface
- PostgreSQL port (default 5432)
- S3/MinIO endpoint (default 9000)
- All components should be on a trusted network or properly firewalled

## Docker Deployment (Recommended)

The easiest way to deploy the application is using Docker.

### Step 1: Clone Repository

```bash
git clone https://github.com/garland3/yet-another-image-project-app.git
cd yet-another-image-project-app
```

### Step 2: Configure Environment

```bash
cp .env.example .env
# Edit .env with your production settings
```

See [Configuration Guide](configuration.md) for detailed environment variable documentation.

### Step 3: Build Docker Image

```bash
docker build -t image-project-manager:latest .
```

### Step 4: Start Infrastructure

```bash
# Start PostgreSQL and MinIO
docker compose up -d postgres minio
```

### Step 5: Run Database Migrations

```bash
docker run --rm \
  --network host \
  -e DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/postgres" \
  image-project-manager:latest \
  alembic upgrade head
```

See [Database Management](database.md) for more details on migrations.

### Step 6: Start Application

```bash
docker run -d \
  --name image-project-manager \
  --network host \
  --env-file .env \
  --restart unless-stopped \
  image-project-manager:latest
```

### Step 7: Verify Deployment

```bash
# Check container status
docker ps

# Check logs
docker logs image-project-manager

# Test health endpoint
curl http://localhost:8000/health
```

## Kubernetes Deployment

For production environments requiring high availability and scalability.

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm (optional, recommended)

### Using Provided Manifests

Example Kubernetes manifests are available in `deployment-test/`:

```bash
# Apply all manifests
kubectl apply -f deployment-test/

# Check deployment status
kubectl get pods -l app=image-project-manager

# View logs
kubectl logs -f deployment/image-project-manager

# Access service
kubectl port-forward service/image-project-manager 8000:8000
```

### Customizing for Production

1. **Update ConfigMap** (`deployment-test/configmap.yaml`):
   - Set production database URL
   - Configure S3 endpoint
   - Set production URLs

2. **Update Secrets** (`deployment-test/secret.yaml`):
   - Generate secure secrets (base64 encoded)
   - Update database passwords
   - Set S3 credentials

3. **Configure Ingress**:
   - Add ingress controller
   - Configure TLS certificates
   - Set up domain routing

4. **Add Persistent Volumes**:
   - PostgreSQL data persistence
   - MinIO data persistence
   - Application logs

Example production deployment structure:

```yaml
# postgres-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: standard

# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: image-project-manager
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - app.example.com
      secretName: app-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: image-project-manager
                port:
                  number: 8000
```

### Helm Deployment

For more flexible deployments, consider creating a Helm chart:

```bash
# Create Helm chart
helm create image-project-manager

# Install
helm install image-project-manager ./image-project-manager \
  --set image.tag=latest \
  --set postgresql.enabled=true \
  --set minio.enabled=true
```

## Manual Installation

For development or custom deployments without Docker.

### Step 1: Install Dependencies

```bash
# Python backend
pip install uv
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Node.js frontend
cd frontend
npm install
npm run build
cd ..
```

### Step 2: Set Up Infrastructure

```bash
# Start PostgreSQL and MinIO via Docker
docker compose up -d postgres minio

# Or install natively on your system
# PostgreSQL: https://www.postgresql.org/download/
# MinIO: https://min.io/download
```

### Step 3: Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### Step 4: Run Migrations

```bash
cd backend
alembic upgrade head
cd ..
```

### Step 5: Start Backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Or use the helper script
./run.sh
```

The application will serve both the API and frontend static files.

### Step 6: Verify Installation

Visit:
- Application: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Docker Compose Full Stack

For development or small deployments, use Docker Compose to run everything:

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: imagemanager
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${S3_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY}
    volumes:
      - minio-data:/data
    restart: unless-stopped

  app:
    image: image-project-manager:latest
    depends_on:
      - postgres
      - minio
    env_file:
      - .env
    ports:
      - "8000:8000"
    restart: unless-stopped

volumes:
  postgres-data:
  minio-data:
```

Deploy with:

```bash
docker-compose -f docker-compose.production.yml up -d
```

## Updating the Application

### Docker Update

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker build -t image-project-manager:latest .

# Run migrations
docker run --rm \
  --env-file .env \
  image-project-manager:latest \
  alembic upgrade head

# Stop old container
docker stop image-project-manager
docker rm image-project-manager

# Start new container
docker run -d \
  --name image-project-manager \
  --network host \
  --env-file .env \
  --restart unless-stopped \
  image-project-manager:latest
```

### Kubernetes Update

```bash
# Update image
docker build -t image-project-manager:v1.1.0 .
docker push your-registry/image-project-manager:v1.1.0

# Update deployment
kubectl set image deployment/image-project-manager \
  app=your-registry/image-project-manager:v1.1.0

# Or use rolling update
kubectl apply -f deployment-test/

# Check rollout status
kubectl rollout status deployment/image-project-manager
```

## Scaling

### Horizontal Scaling

Run multiple application instances:

**Docker:**
```bash
# Run multiple containers behind a load balancer
docker run -d --name app-1 ... image-project-manager:latest
docker run -d --name app-2 ... image-project-manager:latest
docker run -d --name app-3 ... image-project-manager:latest
```

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: image-project-manager
spec:
  replicas: 3  # Run 3 instances
  # ...
```

### Vertical Scaling

Increase resources for single instance:

**Docker:**
```bash
docker run -d \
  --cpus="4" \
  --memory="8g" \
  image-project-manager:latest
```

**Kubernetes:**
```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "2"
  limits:
    memory: "8Gi"
    cpu: "4"
```

## Post-Installation

After installation:

1. Configure reverse proxy with authentication - See [Authentication Guide](authentication.md)
2. Set up monitoring - See [Monitoring Guide](monitoring.md)
3. Configure backups - See [Database Guide](database.md#backup--recovery)
4. Review security settings - See [Security Checklist](authentication.md#security-checklist)
5. Test the deployment
6. Train users - Provide [User Guide](../user-guide.md)

## Next Steps

- [Configure the application](configuration.md)
- [Set up authentication](authentication.md)
- [Configure database and storage](database.md)
- [Enable monitoring](monitoring.md)
