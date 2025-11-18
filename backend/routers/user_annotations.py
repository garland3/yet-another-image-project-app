import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import utils.crud as crud
from core import schemas
from core.database import get_db
from utils.dependencies import get_current_user, get_user_context, UserContext, get_image_or_403

router = APIRouter(
    tags=["User Annotations"],
)

@router.post("/images/{image_id}/annotations", response_model=schemas.UserAnnotation, status_code=status.HTTP_201_CREATED)
async def create_user_annotation(
    image_id: uuid.UUID,
    annotation: schemas.UserAnnotationBase,
    db: AsyncSession = Depends(get_db),
    user_context: UserContext = Depends(get_user_context),
):
    await get_image_or_403(image_id, db, user_context.user)
    
    annotation_create = schemas.UserAnnotationCreate(
        image_id=image_id,
        annotation_type=annotation.annotation_type,
        label=annotation.label,
        data=annotation.data
    )
    
    return await crud.create_user_annotation(db=db, annotation=annotation_create, created_by_id=user_context.id)

@router.get("/images/{image_id}/annotations", response_model=schemas.UserAnnotationList)
async def list_user_annotations(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    await get_image_or_403(image_id, db, current_user)
    
    annotations = await crud.get_user_annotations_for_image(db=db, image_id=image_id)
    return schemas.UserAnnotationList(annotations=annotations, total=len(annotations))

@router.get("/annotations/{annotation_id}", response_model=schemas.UserAnnotation)
async def get_user_annotation(
    annotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_annotation = await crud.get_user_annotation(db=db, annotation_id=annotation_id)
    if db_annotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    
    await get_image_or_403(db_annotation.image_id, db, current_user)
    
    return db_annotation

@router.patch("/annotations/{annotation_id}", response_model=schemas.UserAnnotation)
async def update_user_annotation(
    annotation_id: uuid.UUID,
    annotation_data: schemas.UserAnnotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_annotation = await crud.get_user_annotation(db=db, annotation_id=annotation_id)
    if db_annotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    
    await get_image_or_403(db_annotation.image_id, db, current_user)
    
    if current_user.id and str(db_annotation.created_by_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this annotation",
        )
    
    updated_annotation = await crud.update_user_annotation(
        db=db, 
        annotation_id=annotation_id, 
        annotation_data=annotation_data.model_dump(exclude_unset=True)
    )
    
    return updated_annotation

@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_annotation(
    annotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_context: UserContext = Depends(get_user_context),
):
    db_annotation = await crud.get_user_annotation(db=db, annotation_id=annotation_id)
    if db_annotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    
    await get_image_or_403(db_annotation.image_id, db, user_context.user)
    
    if user_context.id and str(db_annotation.created_by_id) != str(user_context.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this annotation",
        )
    
    success = await crud.delete_user_annotation(db=db, annotation_id=annotation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete annotation",
        )
    
    return None
