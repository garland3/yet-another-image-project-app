# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Image management, classification, and collaboration platform with ML analysis visualization capabilities. The system orchestrates ML results from external pipelines without performing model inference internally.

**Stack:**
- Backend: FastAPI (Python 3.11+) with SQLAlchemy ORM
- Frontend: React 18 with react-router-dom
- Database: PostgreSQL 15 (Alembic migrations)
- Storage: S3/MinIO for images and ML artifacts
- Package Management: UV (backend), npm (frontend)

## Essential Commands

### Development Setup

```bash
# Full stack startup
./start.sh

# Or start components separately:
./install.sh                    # Install all dependencies
cd backend && ./run.sh         # Terminal 1 - Backend + DB + MinIO
cd frontend && ./run.sh        # Terminal 2 - React dev server
```

### Backend Development

```bash
cd backend
source .venv/bin/activate      # Always activate venv first
uv pip install -r requirements.txt

# Start backend (includes PostgreSQL & MinIO containers)
./run.sh

# Run backend server directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**IMPORTANT:** All Python commands must use the virtual environment at `/backend/.venv/`

### Frontend Development

```bash
cd frontend
npm run dev                    # Start dev server (optimized)
npm run build                  # Production build
npm run test                   # Run tests
npm run build:analyze          # Analyze bundle size
```

### Database Migrations (Alembic)

Run from `backend/` directory with active venv:

```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history --verbose

# Check current revision
alembic current

# Initial adoption (if DB existed before Alembic)
alembic stamp 20250930_0001_initial
```

**Migration Tips:**
- Ensure all SQLAlchemy models are imported in `core/models.py`
- Review generated migrations before committing (especially drops/alters)
- Use Postgres URL for accurate type generation
- See `backend/migrate.sh` for helper shortcuts

### Testing

```bash
# Run full test suite (from project root)
bash test/run_tests.sh

# Backend tests only (from backend/)
source .venv/bin/activate
pytest -n auto -q tests/

# Frontend tests (from frontend/)
npm test
```

### Docker & Deployment

```bash
# Production Docker build
docker build -t image-project-manager .
docker run -p 8000:8000 image-project-manager

# Kubernetes (minikube)
minikube start
docker build -t image-project-manager:latest .
minikube image load image-project-manager:latest
kubectl apply -f deployment-test/
minikube service image-project-manager --url
```

**Note:** The dev container includes minikube, kubectl, and helm pre-installed.

## Architecture

### Backend Structure

**Core Components:**
- `core/models.py` - SQLAlchemy ORM models (User, Project, DataInstance, ImageClass, MLAnalysis, etc.)
- `core/schemas.py` - Pydantic request/response schemas
- `core/config.py` - Settings management via pydantic-settings
- `core/database.py` - Async database session management
- `core/group_auth.py` - Group-based authorization logic

**Routers (API Endpoints):**
- `routers/projects.py` - Project CRUD
- `routers/images.py` - Image upload/download/classification
- `routers/users.py` - User management
- `routers/image_classes.py` - Classification labels
- `routers/comments.py` - Image comments
- `routers/project_metadata.py` - Project metadata key-value pairs
- `routers/api_keys.py` - API key management
- `routers/ml_analyses.py` - ML analysis orchestration (user + pipeline endpoints)

**Middleware:**
- `middleware/cors_debug.py` - CORS handling
- `middleware/auth.py` - Authentication (header-based or mock)
- `middleware/security_headers.py` - Security headers (CSP, XFO, etc.)
- `middleware/body_cache.py` - Request body caching for HMAC verification

**Utilities:**
- `utils/boto3_client.py` - S3/MinIO client wrapper with presigned URLs
- `utils/dependencies.py` - FastAPI dependencies (auth, HMAC verification)

### Frontend Structure

**Main Components:**
- `App.js` - Main application router and layout
- `Project.js` - Project view with image gallery
- `ImageView.js` - Single image detail view
- `ApiKeys.js` - API key management UI

**Reusable Components (`components/`):**
- `ImageGallery.js` - Grid display of images with filtering
- `ImageDisplay.js` - Image viewer with ML overlay support
- `ImageClassifications.js` - Classification UI
- `ImageComments.js` - Comment thread UI
- `ImageMetadata.js` - Metadata editor
- `MLAnalysisPanel.js` - ML analysis results viewer
- `BoundingBoxOverlay.js` - Bounding box visualization
- `HeatmapOverlay.js` - Heatmap visualization overlay
- `ClassManager.js` - Manage classification labels
- `ProjectReport.js` - Export project reports

### ML Analysis Feature

**User Flow:**
1. Users view ML analyses via `MLAnalysisPanel.js` in the image sidebar
2. Frontend fetches analyses from `GET /api/images/{image_id}/analyses`
3. Overlays (bounding boxes, heatmaps) rendered via `ImageDisplay.js`
4. Export results as JSON/CSV

**Pipeline Integration (External Systems):**
1. Create analysis: `POST /api/images/{image_id}/analyses` (returns queued status)
2. Update status: `PATCH /api/analyses/{analysis_id}/status` (queued→processing)
3. Upload artifacts: `POST /api/analyses/{analysis_id}/artifacts/presign` → S3 direct upload
4. Post annotations: `POST /api/analyses/{analysis_id}/annotations:bulk` (HMAC-secured)
5. Finalize: `POST /api/analyses/{analysis_id}/finalize` (mark completed/failed)

**Security:** Pipeline endpoints require HMAC authentication via `X-ML-Signature` and `X-ML-Timestamp` headers. Configure `ML_CALLBACK_HMAC_SECRET` in environment.

**Testing:** Use `scripts/test_ml_pipeline.py` to simulate external pipeline behavior.

### Authentication Model

- **Production:** Header-based auth via `X-User-Id` and `X-Proxy-Secret` (reverse proxy expected)
- **Development:** Mock auth via `MOCK_USER_EMAIL` and `MOCK_USER_GROUPS_JSON`
- **Group Authorization:** Project access controlled by `meta_group_id` matching user groups

### Image Deletion Workflow

- **Soft Delete:** Images marked `deleted_at`, retained for `IMAGE_DELETE_RETENTION_DAYS` (default: 60 days)
- **Hard Delete:** Background job purges expired soft-deleted images from DB and S3
- **Audit Trail:** All deletion events logged in `image_deletion_events` table

### Key Configuration

**Environment Variables (.env):**
- `DEBUG` - Enable debug logging and detailed errors
- `FAST_TEST_MODE` - Skip external calls for tests
- `SKIP_HEADER_CHECK` - Disable auth header validation (dev only)
- `DATABASE_URL` - Postgres connection string
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` - S3/MinIO config
- `ML_ANALYSIS_ENABLED` - Toggle ML features
- `ML_ALLOWED_MODELS` - Comma-separated model allow-list
- `ML_CALLBACK_HMAC_SECRET` - HMAC secret for pipeline authentication
- `PROXY_SHARED_SECRET` - Auth proxy shared secret (production)

### Adding Dependencies

**Backend:**
1. Add to `backend/requirements.txt`
2. Run: `cd backend && source .venv/bin/activate && uv pip install -r requirements.txt`

**Frontend:**
1. Run: `cd frontend && npm install <package>`
2. Commit updated `package.json` and `package-lock.json`

### Common Patterns

**Adding a New API Endpoint:**
1. Define Pydantic schema in `core/schemas.py`
2. Create router function in `routers/<module>.py`
3. Add database model to `core/models.py` if needed
4. Create Alembic migration: `alembic revision --autogenerate -m "add_<feature>"`
5. Register router in `main.py` (if new module)

**Adding Frontend Component:**
1. Create component in `frontend/src/components/`
2. Import and use in `ImageView.js` or `App.js`
3. Fetch data via `/api/*` endpoints (proxy configured to port 8000)

**Access Control:**
- All image/project operations check group membership via `verify_user_in_meta_group()`
- API keys validated via `get_current_api_key()` dependency
- ML pipeline endpoints use `verify_hmac_signature_flexible()` for HMAC auth

### Important Constraints

- **Virtual Environment:** All backend Python commands MUST activate `.venv` first
- **Port Allocation:** Backend (8000), Frontend (3000), PostgreSQL (5433), MinIO (9000/9001)
- **Image Formats:** Supports JPEG, PNG, TIFF (with Pillow processing)
- **ML Analysis:** User cannot trigger analyses directly—only external pipelines can (security design)
- **Database:** Use Alembic for schema changes (do not modify `create_db_and_tables()` for migrations)

### File References

Refer to code locations using `file:line` format:
- Main app entry: `backend/main.py:1`
- Database models: `backend/core/models.py:1`
- Auth middleware: `backend/middleware/auth.py:1`
- ML analysis router: `backend/routers/ml_analyses.py:1`
- Frontend image view: `frontend/src/ImageView.js:1`
