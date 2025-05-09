# CI/CD and Deployment Configuration

This document explains the CI/CD configurations for both GitHub Actions and GitLab CI/CD in this project, as well as the deployment configurations for Docker Compose and Kubernetes.

## CI/CD Overview

Both CI/CD configurations accomplish the same core task: building and pushing a Docker image to a container registry when code is pushed to the main branch or when pull/merge requests are created. The GitHub Actions workflow pushes to Docker Hub, while the GitLab CI/CD configuration pushes to Quay.io.

## GitHub Actions Workflow (`.github/workflows/docker-image.yml`)

The GitHub Actions workflow is defined in `.github/workflows/docker-image.yml` and performs the following steps:

1. **Trigger Conditions**: 
   - Runs on pushes to the `main` branch
   - Runs on pull requests to the `main` branch

2. **Environment**:
   - Uses `ubuntu-latest` as the runner

3. **Steps**:
   - Checks out the code using `actions/checkout@v4`
   - Logs in to Docker Hub using `docker/login-action@v3` with credentials:
     * Username from environment variable (`DOCKER_USERNAME`)
     * Password from GitHub secrets (`DOCKERHUB_TOKEN`)
   - Builds and pushes the Docker image using `docker/build-push-action@v5` with tags:
     * `latest`
     * The commit SHA (using GitHub's `github.sha` context variable)

## GitLab CI/CD Configuration (`.gitlab-ci.yml`)

The GitLab CI/CD configuration is defined in `.gitlab-ci.yml` and performs the following steps:

1. **Trigger Conditions**:
   - Runs on pushes to the `main` branch
   - Runs on merge requests (GitLab's equivalent to pull requests)

2. **Environment**:
   - Uses `docker:latest` as the runner image
   - Uses Docker-in-Docker (`docker:dind`) service to enable Docker commands

3. **Steps**:
   - Logs in to Quay.io registry using credentials:
     * Username from GitLab CI/CD variable (`QUAY_USERNAME`)
     * Password from GitLab CI/CD variable (`QUAY_PASSWORD`)
   - Builds the Docker image with tags:
     * `latest`
     * The commit SHA (using GitLab's `CI_COMMIT_SHA` variable)
   - Pushes both tagged images to Quay.io

## Key Differences

1. **Platform-Specific Syntax**:
   - GitHub Actions uses YAML with a specific structure for jobs and steps
   - GitLab CI/CD uses YAML with stages and jobs

2. **Container Registry**:
   - GitHub workflow pushes to Docker Hub
   - GitLab configuration pushes to Quay.io

3. **Authentication**:
   - GitHub uses Docker Hub credentials
   - GitLab uses Quay.io credentials

4. **Docker Build Process**:
   - GitHub uses the `docker/build-push-action` action
   - GitLab uses direct Docker commands in the script section

## Setup Requirements

### GitHub Actions

1. Add the `.github/workflows/docker-image.yml` file to your repository
2. In GitHub repository settings, add the following secrets:
   - `DOCKERHUB_TOKEN`: Your Docker Hub access token

### GitLab CI/CD

1. Add the `.gitlab-ci.yml` file to your repository
2. In GitLab project settings (Settings > CI/CD > Variables), add:
   - `QUAY_USERNAME`: Your Quay.io username
   - `QUAY_PASSWORD`: Your Quay.io password or token (mark as "Masked" for security)

## Deployment Configurations

This project includes two deployment configurations: Docker Compose for local development and Kubernetes for production deployment.

### Docker Compose (`docker-compose.yml`)

The Docker Compose configuration sets up a local development environment with three services:

1. **PostgreSQL Database (`db`)**:
   - Uses PostgreSQL 15
   - Includes health checks
   - Persists data using a named volume
   - Exposes port 5433 (mapped to internal port 5432)

2. **MinIO Object Storage (`minio`)**:
   - Uses the latest MinIO image
   - Includes health checks
   - Persists data using a named volume
   - Exposes ports 9000 (API) and 9090 (Console)

3. **FastAPI Application (`app`)**:
   - Built from the local Dockerfile
   - Includes both the backend API and frontend UI in a single container
   - The FastAPI app serves both API endpoints and static frontend content from port 8000
   - Depends on both the database and MinIO services
   - Exposes port 8007 (mapped to internal port 8000)

All services are connected via a bridge network named `data_mgmt_net`.

### Kubernetes (`k8s.yaml`)

The Kubernetes configuration is designed for production deployment and includes:

1. **Namespace**:
   - Creates a dedicated `data-mgmt` namespace for all resources

2. **Secrets**:
   - `app-env-secret`: Contains environment variables for the application
   - `quay-registry-secret`: Contains credentials for pulling images from Quay.io

3. **Persistent Volume Claims**:
   - For PostgreSQL and MinIO data persistence

4. **Deployments**:
   - **PostgreSQL**: With readiness and liveness probes
   - **MinIO**: With readiness and liveness probes
   - **FastAPI Application**: 
     * Uses the image from Quay.io with readiness probe
     * Contains both backend API and frontend UI in a single container
     * No separate frontend deployment is needed as the FastAPI app serves both API endpoints and static frontend content

5. **Services**:
   - ClusterIP services for internal communication
   - NodePort services for external access:
     * FastAPI app on port 30807
     * MinIO console on port 30909

### Relationship to CI/CD

The CI/CD pipelines build and push the Docker image that is referenced in the Kubernetes configuration. The GitLab CI/CD pipeline pushes to Quay.io, and the Kubernetes configuration is set up to pull from this registry.

To deploy to Kubernetes after a successful CI/CD run:

1. Ensure you have the Quay.io registry secret set up in your Kubernetes cluster:
   ```bash
   kubectl create secret docker-registry quay-registry-secret \
     --namespace=data-mgmt \
     --docker-server=quay.io \
     --docker-username=<your-quay-username> \
     --docker-password=<your-quay-password>
   ```

2. Apply the Kubernetes configuration:
   ```bash
   kubectl apply -f k8s.yaml
   ```

3. Access the application via the NodePort service (port 30807 on any cluster node).
