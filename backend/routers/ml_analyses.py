import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from core import schemas
from core.config import settings
from core.database import get_db
from utils.dependencies import get_current_user, get_image_or_403, verify_hmac_signature_flexible
import utils.crud as crud
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ML Analyses"]) 

@router.post("/images/{image_id}/analyses", response_model=schemas.MLAnalysis, status_code=status.HTTP_201_CREATED)
async def create_ml_analysis(
    image_id: uuid.UUID,
    analysis_in: schemas.MLAnalysisCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if not settings.ML_ANALYSIS_ENABLED:
        raise HTTPException(status_code=404, detail="ML analysis feature disabled")
    # Ensure path image id matches body
    if image_id != analysis_in.image_id:
        raise HTTPException(status_code=400, detail="Image ID mismatch")
    # Access check
    await get_image_or_403(image_id, db, current_user)
    # Basic per-image limit
    existing = await crud.list_ml_analyses_for_image(db, image_id, 0, settings.ML_MAX_ANALYSES_PER_IMAGE + 1)
    if len(existing) >= settings.ML_MAX_ANALYSES_PER_IMAGE:
        raise HTTPException(status_code=400, detail="Analysis limit reached for this image")
    # Model allow-list check
    allowed = [m.strip() for m in settings.ML_ALLOWED_MODELS.split(',') if m.strip()]
    if analysis_in.model_name not in allowed:
        raise HTTPException(status_code=400, detail="Model not allowed")
    db_obj = await crud.create_ml_analysis(db, analysis_in, requested_by_id=current_user.id, status=settings.ML_DEFAULT_STATUS)
    # Audit log
    logger.info("ML_ANALYSIS_CREATE", extra={
        "analysis_id": str(db_obj.id),
        "image_id": str(db_obj.image_id),
        "model": db_obj.model_name,
        "requested_by": str(current_user.id)
    })
    # Reload with annotations empty
    return schemas.MLAnalysis(
        id=db_obj.id,
        image_id=db_obj.image_id,
        model_name=db_obj.model_name,
        model_version=db_obj.model_version,
        status=db_obj.status,
        error_message=db_obj.error_message,
        parameters=db_obj.parameters,
        provenance=db_obj.provenance,
        requested_by_id=db_obj.requested_by_id,
        external_job_id=db_obj.external_job_id,
        priority=db_obj.priority,
        created_at=db_obj.created_at,
        started_at=db_obj.started_at,
        completed_at=db_obj.completed_at,
        updated_at=db_obj.updated_at,
        annotations=[]
    )

@router.get("/images/{image_id}/analyses", response_model=schemas.MLAnalysisList)
async def list_ml_analyses(
    image_id: uuid.UUID,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if not settings.ML_ANALYSIS_ENABLED:
        raise HTTPException(status_code=404, detail="ML analysis feature disabled")
    await get_image_or_403(image_id, db, current_user)
    objs = await crud.list_ml_analyses_for_image(db, image_id, skip, limit)
    # Convert to schemas (annotations excluded for list for performance)
    analyses = [
        schemas.MLAnalysis(
            id=o.id,
            image_id=o.image_id,
            model_name=o.model_name,
            model_version=o.model_version,
            status=o.status,
            error_message=o.error_message,
            parameters=o.parameters,
            provenance=o.provenance,
            requested_by_id=o.requested_by_id,
            external_job_id=o.external_job_id,
            priority=o.priority,
            created_at=o.created_at,
            started_at=o.started_at,
            completed_at=o.completed_at,
            updated_at=o.updated_at,
            annotations=[]
        ) for o in objs
    ]
    return schemas.MLAnalysisList(analyses=analyses, total=len(analyses))

@router.get("/analyses/{analysis_id}", response_model=schemas.MLAnalysis)
async def get_ml_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if not settings.ML_ANALYSIS_ENABLED:
        raise HTTPException(status_code=404, detail="ML analysis feature disabled")
    db_obj = await crud.get_ml_analysis(db, analysis_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # Access via image
    await get_image_or_403(db_obj.image_id, db, current_user)
    # Build response
    annotations = [
        schemas.MLAnnotation(
            id=a.id,
            analysis_id=a.analysis_id,
            annotation_type=a.annotation_type,
            class_name=a.class_name,
            confidence=float(a.confidence) if a.confidence is not None else None,
            data=a.data,
            storage_path=a.storage_path,
            ordering=a.ordering,
            created_at=a.created_at,
        ) for a in db_obj.annotations
    ]
    return schemas.MLAnalysis(
        id=db_obj.id,
        image_id=db_obj.image_id,
        model_name=db_obj.model_name,
        model_version=db_obj.model_version,
        status=db_obj.status,
        error_message=db_obj.error_message,
        parameters=db_obj.parameters,
        provenance=db_obj.provenance,
        requested_by_id=db_obj.requested_by_id,
        external_job_id=db_obj.external_job_id,
        priority=db_obj.priority,
        created_at=db_obj.created_at,
        started_at=db_obj.started_at,
        completed_at=db_obj.completed_at,
        updated_at=db_obj.updated_at,
        annotations=annotations
    )

@router.get("/analyses/{analysis_id}/annotations", response_model=schemas.MLAnnotationList)
async def list_analysis_annotations(
    analysis_id: uuid.UUID,
    skip: int = 0,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if not settings.ML_ANALYSIS_ENABLED:
        raise HTTPException(status_code=404, detail="ML analysis feature disabled")
    db_obj = await crud.get_ml_analysis(db, analysis_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # Access via image
    await get_image_or_403(db_obj.image_id, db, current_user)
    anns = await crud.list_ml_annotations(db, analysis_id, skip, limit)
    items = [
        schemas.MLAnnotation(
            id=a.id,
            analysis_id=a.analysis_id,
            annotation_type=a.annotation_type,
            class_name=a.class_name,
            confidence=float(a.confidence) if a.confidence is not None else None,
            data=a.data,
            storage_path=a.storage_path,
            ordering=a.ordering,
            created_at=a.created_at,
        ) for a in anns
    ]
    return schemas.MLAnnotationList(annotations=items, total=len(items))


class StatusUpdatePayload(schemas.BaseModel):  # type: ignore[attr-defined]
    """Minimal payload for status updates (Phase 1)."""
    status: str
    error_message: Optional[str] = None


VALID_STATUS_TRANSITIONS = {
    "queued": {"processing", "canceled"},
    "processing": {"completed", "failed", "canceled"},
}


@router.patch("/analyses/{analysis_id}/status", response_model=schemas.MLAnalysis)
async def update_ml_analysis_status(
    analysis_id: uuid.UUID,
    payload: StatusUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if not settings.ML_ANALYSIS_ENABLED:
        raise HTTPException(status_code=404, detail="ML analysis feature disabled")
    db_obj = await crud.get_ml_analysis(db, analysis_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # Access via image
    await get_image_or_403(db_obj.image_id, db, current_user)

    new_status = payload.status.lower()
    old_status = (db_obj.status or "").lower()
    if old_status == new_status:
        return await get_ml_analysis(analysis_id, db, current_user)  # No-op
    allowed = VALID_STATUS_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise HTTPException(status_code=409, detail=f"Illegal transition {old_status}->{new_status}")

    # Update timestamps
    if new_status == "processing" and not db_obj.started_at:
        db_obj.started_at = datetime.now(timezone.utc)
    if new_status in {"completed", "failed", "canceled"}:
        db_obj.completed_at = datetime.now(timezone.utc)
    db_obj.status = new_status
    if payload.error_message:
        db_obj.error_message = payload.error_message
    await db.commit()
    await db.refresh(db_obj)
    logger.info("ML_ANALYSIS_STATUS", extra={
        "analysis_id": str(db_obj.id),
        "from": old_status,
        "to": new_status,
        "user": str(current_user.id)
    })
    return await get_ml_analysis(analysis_id, db, current_user)


# ---------------- Phase 2 Callback / Pipeline Endpoints ---------------- #
class BulkAnnotationsPayload(schemas.BaseModel):  # type: ignore[attr-defined]
    annotations: List[schemas.MLAnnotationCreate]
    mode: str = "append"  # append|replace (replace not yet differentiating; future extension)


def _verify_pipeline_hmac(request: Request, body_bytes: bytes):
    if not settings.ML_PIPELINE_REQUIRE_HMAC:
        return
    secret = settings.ML_CALLBACK_HMAC_SECRET
    if not secret:
        # Add debug logging to help diagnose why secret may be missing during tests
        logger.warning(
            "ML_HMAC_SECRET_MISSING",
            extra={
                "require_hmac": settings.ML_PIPELINE_REQUIRE_HMAC,
                "configured_secret": bool(secret),
                "settings_id": id(settings),
            },
        )
        raise HTTPException(status_code=500, detail="HMAC secret not configured")
    sig = request.headers.get("X-ML-Signature", "")
    ts = request.headers.get("X-ML-Timestamp", "0")
    if not verify_hmac_signature_flexible(secret, body_bytes, ts, sig):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")


@router.post("/analyses/{analysis_id}/annotations:bulk", response_model=schemas.MLAnnotationList)
async def bulk_upload_annotations(
    analysis_id: uuid.UUID,
    payload: BulkAnnotationsPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if not settings.ML_ANALYSIS_ENABLED:
        raise HTTPException(status_code=404, detail="ML analysis feature disabled")
    db_obj = await crud.get_ml_analysis(db, analysis_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # Access check (user must have image access)
    await get_image_or_403(db_obj.image_id, db, current_user)
    if len(payload.annotations) > settings.ML_MAX_BULK_ANNOTATIONS:
        raise HTTPException(status_code=400, detail="Too many annotations in one request")
    # HMAC verify using the raw original request body instead of re-serializing the parsed model.
    # Re-serialization can change ordering or add default fields (e.g. 'mode') causing signature mismatches.
    body_bytes = await request.body()
    _verify_pipeline_hmac(request, body_bytes)
    # If mode == replace, we could delete existing first (future). For now always append.
    inserted = await crud.bulk_insert_ml_annotations(db, analysis_id, payload.annotations)
    anns = await crud.list_ml_annotations(db, analysis_id)
    items = [
        schemas.MLAnnotation(
            id=a.id,
            analysis_id=a.analysis_id,
            annotation_type=a.annotation_type,
            class_name=a.class_name,
            confidence=float(a.confidence) if a.confidence is not None else None,
            data=a.data,
            storage_path=a.storage_path,
            ordering=a.ordering,
            created_at=a.created_at,
        ) for a in anns
    ]
    logger.info("ML_BULK_ANNOTATIONS", extra={"analysis_id": str(analysis_id), "count": inserted})
    return schemas.MLAnnotationList(annotations=items, total=len(items))


class PresignRequest(schemas.BaseModel):  # type: ignore[attr-defined]
    artifact_type: str
    filename: Optional[str] = None

class PresignResponse(schemas.BaseModel):  # type: ignore[attr-defined]
    upload_url: str
    storage_path: str


@router.post("/analyses/{analysis_id}/artifacts/presign", response_model=PresignResponse)
async def presign_artifact_upload(
    analysis_id: uuid.UUID,
    req: PresignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if not settings.ML_ANALYSIS_ENABLED:
        raise HTTPException(status_code=404, detail="ML analysis feature disabled")
    db_obj = await crud.get_ml_analysis(db, analysis_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await get_image_or_403(db_obj.image_id, db, current_user)
    # Use raw body for HMAC verification (avoid altering via model_dump which may add defaults / reorder keys)
    body_bytes = await request.body()
    _verify_pipeline_hmac(request, body_bytes)
    # Simple simulated presign (since real S3 client may be disabled in tests)
    # In production: use boto3_client.generate_presigned_url with PUT method.
    artifact_name = req.filename or f"{req.artifact_type}.bin"
    storage_path = f"ml_outputs/{analysis_id}/{artifact_name}"
    fake_url = f"https://example.com/upload/{storage_path}?signature=fake"
    return PresignResponse(upload_url=fake_url, storage_path=storage_path)


class FinalizeRequest(schemas.BaseModel):  # type: ignore[attr-defined]
    status: Optional[str] = None  # typically completed
    error_message: Optional[str] = None

@router.post("/analyses/{analysis_id}/finalize", response_model=schemas.MLAnalysis)
async def finalize_analysis(
    analysis_id: uuid.UUID,
    req: FinalizeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    if not settings.ML_ANALYSIS_ENABLED:
        raise HTTPException(status_code=404, detail="ML analysis feature disabled")
    db_obj = await crud.get_ml_analysis(db, analysis_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await get_image_or_403(db_obj.image_id, db, current_user)
    # Use raw body for HMAC verification
    body_bytes = await request.body()
    _verify_pipeline_hmac(request, body_bytes)
    if req.status:
        # Special case: allow pipeline to finalize directly from queued -> completed|failed without requiring an explicit
        # intermediate PATCH to "processing". This is convenient for fast/atomic analyses and matches test expectations.
        normalized_new = req.status.lower()
        if db_obj.status == "queued" and normalized_new in {"completed", "failed"}:
            now = datetime.now(timezone.utc)
            if not db_obj.started_at:
                db_obj.started_at = now  # treat as if processing started just now
            db_obj.completed_at = now
            db_obj.status = normalized_new
            if req.error_message:
                db_obj.error_message = req.error_message
            await db.commit()
            await db.refresh(db_obj)
            logger.info("ML_ANALYSIS_STATUS", extra={
                "analysis_id": str(db_obj.id),
                "from": "queued",
                "to": normalized_new,
                "user": str(current_user.id)
            })
            return db_obj  # Fast path return
        # Otherwise reuse the stricter status update logic (which enforces valid transitions)
        return await update_ml_analysis_status(analysis_id, StatusUpdatePayload(status=req.status, error_message=req.error_message), db, current_user)  # type: ignore
    return await get_ml_analysis(analysis_id, db, current_user)
