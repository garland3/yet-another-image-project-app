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

## Backend

the backend uses uv for package managment. 

```
cd backend
pip install uv
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

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

## Database Migrations (Alembic)

The project now uses Alembic for schema migrations.

### Setup
Before running any Alembic commands, ensure you're in the `backend/` directory with a virtual environment active (see Backend section above).

### For New Projects
If starting from scratch with no existing database, run this to create the schema:

```bash
alembic upgrade head
```

This applies all migrations and sets up your database based on the current models.

### Common Commands
Run these from the `backend/` directory (ensure a virtual environment with dependencies is active):

```bash
alembic revision --autogenerate -m "describe change"   # Create new migration based on model diffs
alembic upgrade head                                   # Apply latest migrations
alembic downgrade -1                                   # Roll back last migration
alembic history --verbose                              # Show migration history
alembic current                                        # Show current DB revision
alembic stamp head                                     # Mark DB as up-to-date without applying (use cautiously)
```

### Initial Adoption
If you already had a database before Alembic was introduced and the schema matches the initial revision, stamp instead of applying:

```bash
alembic stamp 20250930_0001_initial
```

### Autogenerate Tips
- Ensure all SQLAlchemy models are imported in `core/models.py` and referenced by `Base.metadata`.
- Review generated migration files before committing—especially dropped/altered columns.

### Troubleshooting
| Issue | Resolution |
|-------|------------|
| Autogenerate misses table | Verify model imported and Base.metadata includes it. |
| Dialect errors (SQLite vs Postgres) | Use a Postgres URL for accurate types. |
| Drift between models & DB | Run `alembic upgrade head` then regenerate; add test (see below). |

### Consistency Test
A test will compare model metadata vs database (after upgrade) to guard against un-migrated changes.

### Helper Script
See `backend/migrate.sh` for ergonomic shortcuts.

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
