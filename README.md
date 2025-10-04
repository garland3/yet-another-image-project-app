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
- **ML Analysis Visualization** - View and export machine learning analysis results

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

## ML Analysis (Preview)

This feature enables visualization of machine learning analysis results. **Users cannot trigger analyses directly** - all ML analyses are initiated by external systems (cron jobs, webhooks, ML pipelines).

### For End Users

1. Navigate to an image in the UI
2. If ML analyses exist, the "ML Analyses" panel appears in the sidebar
3. Click an analysis to view annotations
4. Use "Overlays" controls to toggle bounding boxes/heatmaps
5. Adjust opacity slider or switch to side-by-side view
6. Export analysis results as JSON or CSV

### For System Administrators / Pipeline Developers

1. **Enable the feature**: Set `ML_ANALYSIS_ENABLED=true` in your environment
2. **Configure HMAC secret**: Set `ML_CALLBACK_HMAC_SECRET=<your_secret>` for secure pipeline authentication
3. **Set allowed models**: Configure `ML_ALLOWED_MODELS=yolo_v8,resnet50_classifier` (comma-separated list)

#### API Workflow

External ML pipelines interact with the platform via REST API:

```bash
# 1. Create analysis (queued status)
POST /api/images/{image_id}/analyses
{
  "image_id": "...",
  "model_name": "yolo_v8",
  "model_version": "1.0.0",
  "parameters": {"threshold": 0.5}
}

# 2. Update status to processing
PATCH /api/analyses/{analysis_id}/status
{"status": "processing"}

# 3. Request presigned upload URL for artifacts
POST /api/analyses/{analysis_id}/artifacts/presign
{"artifact_type": "heatmap", "filename": "heatmap.png"}

# 4. Upload artifact to presigned URL (direct to S3/MinIO)
PUT <presigned_url>
<binary_data>

# 5. Post annotations
POST /api/analyses/{analysis_id}/annotations:bulk
{
  "annotations": [
    {
      "annotation_type": "bounding_box",
      "class_name": "cat",
      "confidence": 0.95,
      "data": {"x_min": 10, "y_min": 20, "x_max": 100, "y_max": 200, ...}
    },
    {
      "annotation_type": "heatmap",
      "data": {"width": 512, "height": 512},
      "storage_path": "ml_outputs/{analysis_id}/heatmap.png"
    }
  ]
}

# 6. Finalize analysis
POST /api/analyses/{analysis_id}/finalize
{"status": "completed"}
```

All pipeline endpoints (steps 2-6) require HMAC authentication headers:
- `X-ML-Signature`: HMAC-SHA256 signature
- `X-ML-Timestamp`: Unix timestamp

#### Testing

Use the provided simulation script to test the complete pipeline flow:

```bash
# Set HMAC secret
export ML_CALLBACK_HMAC_SECRET='your_secret_here'

# Run simulation
python scripts/test_ml_pipeline.py --image-id <image_uuid>
```

For detailed integration instructions, see [`docs/ML_PIPELINE_INTEGRATION.md`](docs/ML_PIPELINE_INTEGRATION.md) (coming soon).

## License

MIT
