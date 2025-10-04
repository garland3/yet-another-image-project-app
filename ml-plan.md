# ML Analysis Integration Plan

This document defines a four–phase plan to add Machine Learning (ML) analysis visualization to the platform **without performing model inference inside this service**. An external ML pipeline will perform computation and push results back via secure APIs.

---
## Guiding Principles
- **Externalized Compute**: This service only orchestrates, stores, and serves results.
- **Additive & Backward Compatible**: All DB changes are additive; existing features remain unaffected.
- **Idempotent & Observable**: External callbacks can be retried safely; every state transition is auditable.
- **Separation of Concerns**: Storage vs. metadata vs. visualization concerns are isolated.
- **Security First**: Strong authentication (API keys / HMAC), provenance, and tamper resistance.

---
## Data Model Overview (New)
| Table | Purpose |
|-------|---------|
| `ml_analyses` | One analysis execution request for an image (one model + parameters). |
| `ml_annotations` | Atomic structured outputs (classification, bounding_box, heatmap ref, segmentation, custom). |
| `ml_artifacts` (optional future) | Large binary/derived artifacts (tiles, masks) separated from logical annotations. |

### `ml_analyses` (proposed columns)
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | Internal identifier. |
| `image_id` | FK -> `data_instances.id` | Target image. Indexed. |
| `model_name` | text | e.g. `yolo_v8`, `resnet50_classifier`. |
| `model_version` | text | Semantic or git hash. |
| `status` | text | `queued|processing|completed|failed|canceled`. |
| `error_message` | text (nullable) | Last failure reason. |
| `parameters` | JSON (nullable) | Hyperparameters / thresholds. |
| `provenance` | JSON (nullable) | Source info: commit SHA, container tag, environment. |
| `requested_by_id` | FK users.id | User who initiated. |
| `created_at` | timestamptz default now | Creation time. |
| `started_at` | timestamptz nullable | External pipeline start. |
| `completed_at` | timestamptz nullable | Completion time. |
| `updated_at` | timestamptz on update | Status change tracking. |
| `external_job_id` | text nullable | Correlates with external system. Unique partial index. |
| `priority` | smallint default 0 | Scheduling preference. |

### `ml_annotations`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `analysis_id` | FK -> ml_analyses.id | Indexed. Cascade delete. |
| `annotation_type` | text | `classification|bounding_box|heatmap|segmentation|polygon|keypoint|custom`. |
| `class_name` | text nullable | Class label for detection / classification. |
| `confidence` | numeric(5,4) nullable | 0–1 range. |
| `data` | JSON | Structure varies by type (see below). |
| `storage_path` | text nullable | Object storage key for large artifact (heatmap PNG, mask). |
| `ordering` | int nullable | For multi-step sequences or ranking. |
| `created_at` | timestamptz default now | |

#### `data` JSON shape examples
- **Bounding Box**: `{"x_min": 12, "y_min": 33, "x_max": 240, "y_max": 300, "image_width": 1024, "image_height": 768}`
- **Classification**: `{ "topk": [{"class": "cat", "confidence": 0.91}, ...] }` OR atomic per row with `class_name` + `confidence`.
- **Heatmap Reference**: `{ "width": 512, "height": 512, "color_map": "viridis" }` with binary PNG at `storage_path`.
- **Segmentation**: `{ "format": "rle", "counts": "...", "bbox": [...], "area": 12345 }` or pointer to mask.

### Indexing Strategy
- `idx_ml_analyses_image_id` (image lookup)
- `idx_ml_analyses_status` (queue/polling)
- Partial unique: `(external_job_id) WHERE external_job_id IS NOT NULL`
- `idx_ml_annotations_analysis_id`
- Optional GIN on `ml_annotations (data)` if querying structured coordinates later (deferred until needed).

---
## DB Migration Strategy

### Approach
1. **Initial Migration (Phase 1)** adds new tables; no existing table modifications required.
2. **Forward-Compatible Enum Handling**: Represent statuses as TEXT (no strict enum) initially to avoid locking migrations; later we can optionally introduce a constrained CHECK.
3. **Incremental Additions**: Additional columns (e.g. `priority`, `external_job_id`) come in separate migrations to minimize rollback complexity.
4. **Rollback Safety**: Never drop columns in rollback; instead leave unused columns (soft deprecation). Rollback script will only drop *new tables* if absolutely required and data is considered disposable in early phases.
5. **Zero Downtime**: Deploy order:
   - Apply migration (tables available, not used yet).
   - Deploy backend code referencing them in *read-tolerant* way (gracefully handles empty sets).
   - Enable feature flag `ML_ANALYSIS_ENABLED`.
6. **Idempotency**: External pipeline can retry posting; DB unique constraints + upsert logic prevent duplication.

### Alembic Migration Pseudocode
```python
# revision identifiers, used by Alembic
revision = "20250101_add_ml_analysis"
down_revision = "<last_revision>"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

def upgrade():
    op.create_table(
        'ml_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('image_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_instances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('status', sa.String(40), nullable=False, server_default='queued'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('provenance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('requested_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('external_job_id', sa.String(255), nullable=True),
        sa.Column('priority', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ml_analyses_image_id', 'ml_analyses', ['image_id'])
    op.create_index('idx_ml_analyses_status', 'ml_analyses', ['status'])
    op.create_unique_constraint('uq_ml_analyses_external_job_id', 'ml_analyses', ['external_job_id'])

    op.create_table(
        'ml_annotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('annotation_type', sa.String(50), nullable=False),
        sa.Column('class_name', sa.String(255), nullable=True),
        sa.Column('confidence', sa.Numeric(5,4), nullable=True),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('storage_path', sa.String(1024), nullable=True),
        sa.Column('ordering', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_ml_annotations_analysis_id', 'ml_annotations', ['analysis_id'])


def downgrade():
    op.drop_index('idx_ml_annotations_analysis_id', table_name='ml_annotations')
    op.drop_table('ml_annotations')
    op.drop_index('idx_ml_analyses_status', table_name='ml_analyses')
    op.drop_index('idx_ml_analyses_image_id', table_name='ml_analyses')
    op.drop_constraint('uq_ml_analyses_external_job_id', 'ml_analyses', type_='unique')
    op.drop_table('ml_analyses')
```

### Future Migrations
- Add `analysis_group_id` to relate batch runs.
- Add GIN index: `CREATE INDEX ... ON ml_annotations USING GIN ((data -> 'class_name'));` when query demand justifies.
- Add `deleted_at` to support soft deletion of analysis if needed.

---
## Phase 1: Schema & API Foundations (Current Sprint Target)
**Goals**: Persistence & external contract baseline.

### Deliverables
1. DB tables + Alembic migration.
2. Pydantic schemas:
   - `MLAnalysisCreate`, `MLAnalysis`, `MLAnnotationCreate`, `MLAnnotation`.
3. REST Endpoints (initial):
   - `POST /api/images/{image_id}/analyses` → create queued analysis (called by external services only; requires API key authentication; optionally returns presigned download URL for image if pipeline pulls rather than receives push trigger).
   - `GET /api/images/{image_id}/analyses` → list analyses.
   - `GET /api/analyses/{analysis_id}` → detail with annotations.
   - `GET /api/analyses/{analysis_id}/annotations` → annotations only (pagination ready).
4. Feature flag: `ML_ANALYSIS_ENABLED` (config) – endpoints return 404 or 403 when disabled.
5. Audit logging for creation & status changes.

**Note**: The `POST /api/images/{image_id}/analyses` endpoint is designed for external system integration (cron jobs, ML pipelines) and requires API key authentication. End users do not have direct access to trigger ML analyses.

### External Job Acquisition Patterns (Choose One)
| Pattern | Description | Pros | Cons |
|---------|-------------|------|------|
| Pull (Polling) | External worker polls `/api/analyses?status=queued&limit=...` and claims jobs. | Simple, decoupled | Higher latency, wasteful polling |
| Push (Webhook Trigger) | Service sends POST to pipeline with job payload. | Faster start | Outbound connectivity & retry complexity |
| Hybrid (Presigned Fetch) | External pipeline just needs job ID; fetches image via presigned URL. | Flexible | Slightly more moving parts |

**Initial Recommendation**: Implement Pull + presigned URL generation to minimize complexity.

### Claiming a Job (Optional Extension)
- `POST /api/analyses/{analysis_id}/claim` sets `status='processing'` if currently `queued` (atomic update with WHERE clause). Prevents duplicate processing.

---
## Phase 2: External Pipeline Integration (Replace local compute)
**Goals**: Robust, secure ingestion of externally produced outputs.

### Callback Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/analyses/{id}/status` | PATCH | Update status (`processing`, `completed`, `failed`, `canceled`), timestamps. |
| `/api/analyses/{id}/annotations:bulk` | POST | Bulk insert annotations (idempotent key or replace strategy). |
| `/api/analyses/{id}/artifacts/presign` | POST | Request presigned PUT URLs for large artifacts (heatmaps, masks). |
| `/api/analyses/{id}/finalize` | POST | Optional: mark `completed` & return summary counts. |

### Artifact Workflow
1. External pipeline requests presigned upload(s) (declares type: `heatmap`, `mask`, `log`).
2. Service returns `{upload_url, storage_key}`.
3. Pipeline uploads to MinIO directly.
4. Pipeline POSTs annotations referencing `storage_path`.
5. Final status update marks completion.

**Storage Layout**
```
ml_outputs/
  {analysis_id}/
    heatmap.png
    mask.png
    metadata.json (optional aggregate)
```

### Security
- **API Key per pipeline** (scoped to analysis endpoints).
- **HMAC Signature** header (e.g. `X-ML-Signature: sha256=...`) computed over body using shared secret.
- **Replay Protection**: Include `X-ML-Timestamp`; reject if outside skew window.
- **Least Privilege**: Keys cannot access unrelated user CRUD endpoints.
- **Rate Limiting**: Sliding window per key.

### Idempotency
- Provide optional `Idempotency-Key` header for annotation bulk uploads.
- Annotations bulk endpoint can accept `mode=replace|append|upsert`.

### Status State Machine
```
queued -> processing -> completed
queued -> processing -> failed
queued -> canceled
processing -> failed|completed|canceled
```
Reject illegal transitions with 409 Conflict.

---
## Phase 3: Frontend Visualization & Interaction
**Goals**: Expose analyses and overlays in the UI.

### UI Components
| Component | Responsibility |
|-----------|----------------|
| `MLAnalysisPanel` | List analyses, show statuses (read-only). |
| `AnalysisStatusBadge` | Color-coded state indicator. |
| `OverlayLayer` | Canvas/SVG drawing for bounding boxes & keypoints. |
| `HeatmapLayer` | Draw semi-transparent heatmap (lazy load). |
| `MultiViewContainer` | Side-by-side or overlay mode toggling. |
| `OverlayControls` | Toggle layer visibility, opacity slider. |

### Interactions
- **Users CANNOT trigger ML analyses directly**. Analyses are initiated by external services (cron jobs, ML pipelines, or other automated systems).
- Poll or WebSocket updates status in real-time.
- Selecting an analysis loads its annotations → overlays drawn.
- Multi-view: Original (left) vs. Selected Analysis (right) or stacked layering.

### Performance Optimizations
- Debounced resize + memoized scaled coordinates.
- Serve heatmaps as pre-sized PNG with transparency.
- Client-side cache (in-memory Map keyed by `analysis_id`).

### Failure UX
- Show failure badge + tooltip error_message.
- No user re-trigger capability (external systems manage retry logic).

### Implementation Status (Phase 3 - Initial Increment)
Implemented minimal UI integration:
1. Added `frontend/src/components/MLAnalysisPanel.js` listing analyses for an image, status badges, and annotation list (read-only; no user-triggered analysis creation).
2. Injected the panel into the image sidebar within `ImageView` below metadata & comments (non-invasive; gracefully handles 404 or empty states).
3. Kept scope intentionally small (no overlays yet) to ship incremental value and validate API usage patterns.

**Important**: The UI does NOT provide a way for users to trigger new ML analyses. All analyses are created by external systems (scheduled jobs, webhooks, or pipeline services).

Deferred remaining Phase 3 items to sub-phases:
- Overlay rendering (canvas/SVG for boxes, heatmaps) — pending design of annotation type-to-visual mapping.
- Real-time status updates (currently manual refresh; could add polling or WebSocket in Phase 4).
- Multi-view comparison UI and opacity controls.

Next recommended Phase 3 steps:
1. Add lightweight polling (every 5–10s) while any analysis is non-terminal.
2. Implement bounding box overlay renderer using existing annotation `data` shape.
3. Lazy-load heatmap images from `storage_path` once artifact presign + upload path finalized.

Rationale for incremental delivery: ensures backend contract stability and reduces large PR risk while providing immediate visibility into analyses.

---

### Observability
- Log correlation: Include `analysis_id` in all related log events.
- Tracing: Span wrappers around status transitions.
- Metrics: `status_transition_time = completed_at - started_at` for SLO tracking.

### Governance & Reproducibility
- Provenance JSON includes: `git_commit`, `docker_image`, `model_sha256`, `parameters_used`, `pipeline_version`.
- Ability to export full analysis bundle (metadata + annotations + overlay assets manifest) as JSON.

---
## Configuration Additions (`core/config.py`)
```python
ML_ANALYSIS_ENABLED: bool = True
ML_PIPELINE_PULL_ENABLED: bool = True  # If external workers poll
ML_PIPELINE_PUSH_WEBHOOKS_ENABLED: bool = False
ML_CALLBACK_HMAC_SECRET: Optional[str] = None
ML_ALLOWED_MODELS: str = "yolo_v8,resnet50_classifier"
ML_MAX_ANALYSES_PER_IMAGE: int = 50
ML_MAX_PENDING_PER_USER: int = 10
ML_PRESIGNED_URL_EXPIRY_SECONDS: int = 900
```
- Parse `ML_ALLOWED_MODELS` into list at runtime.
- Feature gating ensures safe incremental rollout.

---
## API Contract Summary (Initial Set)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/images/{image_id}/analyses` | (External API) Create analysis (queued; API key required) |
| GET | `/api/images/{image_id}/analyses` | List analyses (users read-only) |
| GET | `/api/analyses/{analysis_id}` | Analysis detail (users read-only) |
| GET | `/api/analyses/{analysis_id}/annotations` | Paginated annotations (users read-only) |
| PATCH | `/api/analyses/{analysis_id}/status` | (Pipeline API) status update |
| POST | `/api/analyses/{analysis_id}/annotations:bulk` | (Pipeline API) bulk insert |
| POST | `/api/analyses/{analysis_id}/artifacts/presign` | (Pipeline API) presigned upload |
| POST | `/api/analyses/{analysis_id}/finalize` | (Pipeline API) finalize |

Optional future: `GET /api/analyses?status=queued&limit=...&claim=true` for worker claiming.

---
## Security Model
- **API Keys**: Distinct prefix (e.g. `mlpip_`) for pipeline keys; stored hashed.
- **HMAC**: `signature = HMAC(secret, timestamp + method + path + body)`; server verifies.
- **Replay Defense**: Reject if `abs(now - timestamp) > 300s` or nonce reused (store short-lived nonce cache).
- **Least Privilege**: RBAC role `pipeline_worker` restricts to certain endpoints.
- **Audit Log Fields**: `{user_or_key_id, action, analysis_id, status_from, status_to, ip, user_agent}`.

---
## Error Handling & Edge Cases
| Scenario | Handling |
|----------|----------|
| Duplicate status update (already completed) | Return 409 with current state snapshot. |
| Large annotation batch | Enforce max items (e.g. 5k) & pagination. |
| Oversized artifact | Validate `Content-Length` vs. configured cap; reject pre-sign. |
| Orphaned analyses (never processed) | Add cleanup job: mark `stale` after TTL. |
| Duplicate analysis creation requests | Allow new analysis; old stays immutable. |
| Pipeline partial failure (some annotations) | Accept incremental bulk uploads; finalize only when ready. |
| Missing image (deleted) | Block new analyses; return 410 Gone. |

---
## Rollout Plan (Incremental)
1. **Deploy Phase 1** (tables + read-safe endpoints; feature flag off).
2. Enable `ML_ANALYSIS_ENABLED` for internal test project.
3. Implement pipeline integration (Phase 2) using a mock script (simulate callbacks).
4. Add frontend (Phase 3) hidden behind UI toggle (only appears if analyses exist or feature flag on).
5. Introduce WebSocket + advanced metrics (Phase 4).

Rollback: Disable feature flag; no code paths invoked. Tables remain (harmless). Re-deploy older image if needed.

---
## Testing Strategy
| Layer | Tests |
|-------|-------|
| Migration | Alembic upgrade/downgrade smoke test in CI. |
| Models | CRUD + cascade delete (analysis deletes annotations). |
| API | AuthZ (API key vs user), state machine transitions, idempotency. |
| Pipeline Simulation | Fixture that posts bulk annotations & artifacts. |
| Frontend | Overlay rendering snapshot, latency resilience, toggle controls. |
| Security | HMAC validation test vectors, replay attempt rejection. |

---
## Minimal Stub Implementation Order
1. Migration + models + schemas.
2. `POST /images/{id}/analyses` + `GET` endpoints (no pipeline callbacks yet).
3. Add pipeline callback endpoints (status + bulk annotations) with API key auth.
4. Frontend basic list + select + JSON overlay debug (no drawing yet).
5. Overlay canvas & bounding boxes; heatmap stub image.
6. Harden security (HMAC) + metrics + docs.

---
## Documentation & Developer Onboarding
Add to README:
```
ML Analysis (Preview)
=====================
This feature enables visualization of ML analysis results. **Users cannot trigger analyses directly** - all ML analyses are initiated by external systems (cron jobs, webhooks, ML pipelines).

For system administrators / pipeline developers:
1. Enable: set ML_ANALYSIS_ENABLED=true
2. Create analysis via API: POST /api/images/{image_id}/analyses {"model_name":"resnet50_classifier","model_version":"1.0.0"} (requires API key)
3. External pipeline polls queued analyses or receives job trigger.
4. Pipeline updates status & uploads artifacts.
5. UI displays analyses and overlays when available (read-only for end users).
```


