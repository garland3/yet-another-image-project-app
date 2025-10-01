import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core import schemas
from core.config import settings
from core.database import get_db
from utils.dependencies import get_current_user, get_image_or_403
import utils.crud as crud

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
