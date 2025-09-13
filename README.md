# Image Project Manager

Image management, classification, and collaboration platform for organizing and labeling visual content.

## Requirements

- Node.js 22+
- Python 3.11+
- Docker (for PostgreSQL and MinIO)

## Quick Start

### Production (Docker)

```bash
docker build -t image-project-manager .
docker run -p 8000:8000 image-project-manager
```

Access at http://localhost:8000

### Development

```bash
# Install dependencies and start services
./start.sh

# Or start components separately:
# ./install.sh
# cd backend && ./run.sh    # Terminal 1 - Backend + DB
# cd frontend && ./run.sh   # Terminal 2 - Frontend
```

Backend: http://localhost:8000
Frontend: http://localhost:3000

## Features

- Project organization and management
- Image classification with custom labels
- Team collaboration with comments
- Metadata storage for projects and images
- User access control

## Configuration

Copy `.env.example` to `.env` and configure:
- Database credentials
- S3/MinIO storage settings
- Authentication settings

## Scripts

- `./install.sh` - Install all dependencies
- `./start.sh` - Start development environment
- `backend/run.sh` - Start backend with PostgreSQL/MinIO
- `frontend/run.sh` - Start React development server

## Kubernetes Deployment Test

Test deployment on minikube:

Noe: in the dev conatainer, I added minikube and kubectl, so you can run this directly from the dev container.
* it will have minikube, kubectl, and helm installed

```bash
# Start minikube
minikube start
# minikube start --driver=docker

# Build and load image
docker build -t image-project-manager:latest .
minikube image load image-project-manager:latest

# Deploy to cluster
kubectl apply -f deployment-test/

# Access application
minikube service image-project-manager --url
```

See `deployment-test/` folder for Kubernetes manifests.

## License

MIT
