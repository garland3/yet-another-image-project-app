# CI/CD Pipeline Setup

## Overview

This project uses GitHub Actions for a complete CI/CD pipeline with security scanning, container builds, and automated deployments.

## Workflows

### 1. CI/CD Pipeline (`.github/workflows/docker-image.yml`)
**Triggers**: Push/PR to main branch

**Jobs**:
- ✅ **Test Job**: Runs Python tests with PostgreSQL service
- ✅ **Build Job**: Builds Docker container, tests in container, pushes to registry

**Features**:
- PostgreSQL integration testing
- Container health checks  
- Tests run inside built container
- Docker layer caching
- Only pushes on main branch (not PRs)

### 2. Security Scanning (`.github/workflows/container-scan-trivy.yml`)
**Triggers**: Push/PR to main, weekly schedule

**Jobs**:
- ✅ **Container Scan**: Trivy vulnerability scanning
- ✅ **Dependency Scan**: Python (Safety, Bandit, Semgrep) security analysis
- ✅ **GraphQL Scan**: Detects GraphQL usage and security recommendations

**SARIF Integration**: Results appear in GitHub Security tab

### 3. CodeQL Analysis (`.github/workflows/codeql-analysis.yml`)
**Triggers**: Push/PR to main, weekly schedule

**Features**:
- Python and JavaScript/TypeScript analysis
- Security-focused queries
- Custom configuration for path filtering

### 4. Deployment (`.github/workflows/deploy.yml`)
**Triggers**: Successful CI/CD completion, manual dispatch

**Features**:
- Staging/Production environment support
- GitHub Deployments integration
- Health checks post-deployment
- Automatic rollback on failure

## Dependabot Configuration

**File**: `.github/dependabot.yml`

**Updates**:
- Python dependencies (weekly, Mondays)
- Node.js dependencies (weekly, Mondays)  
- Docker base images (weekly, Tuesdays)
- GitHub Actions (weekly, Tuesdays)

**Features**:
- Grouped security updates
- Grouped minor/patch updates
- Auto-assignment and labeling
- Conventional commit messages

## Container Optimization

**File**: `.dockerignore`

**Excludes**:
- Development files and caches
- CI/CD configurations
- Security scan results
- Documentation
- Environment files

## Required Secrets

### GitHub Repository Secrets

```bash
# Docker Hub
DOCKERHUB_TOKEN=your-docker-hub-access-token

# Optional: Deployment secrets
DEPLOY_SSH_KEY=your-ssh-private-key
DEPLOY_HOST=your-deployment-server
KUBECONFIG=your-kubernetes-config
```

### Environment Files

**Production** (`.env`):
```bash
# REQUIRED - Security
PROXY_SHARED_SECRET=strong-random-secret-here
DEBUG=false
SKIP_HEADER_CHECK=false

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# S3/Storage
S3_ENDPOINT=s3.amazonaws.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=your-bucket
```

**Development** (use `.env.example` as template):
```bash
cp .env.example .env
# Edit with your local development settings
```

## Security Features

### 1. Container Security
- Multi-stage builds for minimal attack surface
- Non-root user execution
- Vulnerability scanning with Trivy
- Regular base image updates

### 2. Code Security  
- Static analysis with CodeQL
- Python security linting (Bandit)
- Dependency vulnerability scanning (Safety)
- SAST with Semgrep

### 3. Runtime Security
- Proxy authentication enforcement
- Security headers middleware
- Input sanitization
- Admin access controls

### 4. GraphQL Security (when detected)
- Query depth limiting recommendations  
- Complexity analysis warnings
- Authentication/authorization reminders
- Input validation guidance

## Deployment Process

### Automatic (Production)
1. Code pushed to `main` branch
2. Tests run with PostgreSQL
3. Container built and tested
4. Security scans executed
5. Container pushed to registry
6. Deployment triggered automatically
7. Health checks performed
8. Rollback if health checks fail

### Manual Deployment
```bash
# Via GitHub UI: Actions → Deploy to Production → Run workflow
# Select environment: staging/production
```

### Local Testing
```bash
# Build container locally
docker build -t test-app .

# Run tests in container  
docker run --rm -e FAST_TEST_MODE=true test-app \
  bash -c "cd backend && bash ../test/run_tests.sh"

# Test container health
docker run -d -p 8000:8000 --name test test-app
curl http://localhost:8000/api/users/me
docker stop test && docker rm test
```

## Monitoring & Observability

### GitHub Features
- **Security Tab**: View vulnerability reports
- **Actions Tab**: Monitor workflow runs  
- **Deployments**: Track deployment status
- **Dependency Graph**: View dependency insights

### Recommended Additions
- Application metrics (Prometheus/Grafana)
- Log aggregation (ELK/Loki)
- Uptime monitoring (Pingdom/UptimeRobot)
- Error tracking (Sentry)

## Troubleshooting

### Common Issues

**Test Failures**:
```bash
# Check test logs in Actions tab
# Run tests locally: bash test/run_tests.sh
```

**Container Build Failures**:
```bash
# Check Dockerfile syntax
# Verify all COPY paths exist
# Check for missing dependencies
```

**Security Scan Failures**:
```bash
# Review SARIF results in Security tab
# Update dependencies: dependabot PRs
# Fix code issues: CodeQL suggestions
```

**Deployment Failures**:
```bash
# Check deployment logs
# Verify environment secrets
# Review health check endpoints
```

### Debug Commands

```bash
# View workflow logs
gh run list --limit 5
gh run view <run-id>

# Check security alerts  
gh api repos/:owner/:repo/security-advisories

# Monitor deployments
gh api repos/:owner/:repo/deployments
```

## Next Steps

1. **Configure deployment target** (K8s/Docker Swarm/Cloud)
2. **Set up monitoring** (metrics, logs, alerts)
3. **Add integration tests** (API testing, E2E)
4. **Configure staging environment**
5. **Set up backup/recovery procedures**