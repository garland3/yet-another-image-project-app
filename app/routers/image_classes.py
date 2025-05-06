import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user, check_mock_user_in_group
from app.config import settings
from app.routers.images import check_project_access

router = APIRouter(
    tags=["Image Classes"],
)

# Image Classes endpoints
@router.post("/projects/{project_id}/classes", response_model=schemas.ImageClass, status_code=status.HTTP_201_CREATED)
async def create_image_class(
    project_id: uuid.UUID,
    image_class: schemas.ImageClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if the user has access to the project
    await check_project_access(project_id, db, current_user)
    
    # Ensure the project_id in the path matches the one in the request body
    if project_id != image_class.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID in the path must match the project_id in the request body",
        )
    
    # Create the image class
    return await crud.create_image_class(db=db, image_class=image_class)

@router.get("/projects/{project_id}/classes", response_model=List[schemas.ImageClass])
async def list_image_classes(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if the user has access to the project
    await check_project_access(project_id, db, current_user)
    
    # Get all image classes for the project
    return await crud.get_image_classes_for_project(db=db, project_id=project_id)

@router.get("/classes/{class_id}", response_model=schemas.ImageClass)
async def get_image_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Get the image class
    db_class = await crud.get_image_class(db=db, class_id=class_id)
    if db_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image class not found")
    
    # Check if the user has access to the project
    await check_project_access(db_class.project_id, db, current_user)
    
    return db_class

@router.patch("/classes/{class_id}", response_model=schemas.ImageClass)
async def update_image_class(
    class_id: uuid.UUID,
    image_class_data: schemas.ImageClassBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Get the image class
    db_class = await crud.get_image_class(db=db, class_id=class_id)
    if db_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image class not found")
    
    # Check if the user has access to the project
    await check_project_access(db_class.project_id, db, current_user)
    
    # Update the image class
    updated_class = await crud.update_image_class(
        db=db, 
        class_id=class_id, 
        image_class_data=image_class_data.model_dump(exclude_unset=True)
    )
    
    return updated_class

@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Get the image class
    db_class = await crud.get_image_class(db=db, class_id=class_id)
    if db_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image class not found")
    
    # Check if the user has access to the project
    await check_project_access(db_class.project_id, db, current_user)
    
    # Delete the image class
    success = await crud.delete_image_class(db=db, class_id=class_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete image class",
        )
    
    return None

# Image Classifications endpoints
async def check_image_access(image_id: uuid.UUID, db: AsyncSession, current_user: schemas.User) -> models.DataInstance:
    # Get the image
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    
    # Check if the user has access to the project
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, db_image.project.meta_group_id)
    else:
        is_member = db_image.project.meta_group_id in current_user.groups
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )
    
    return db_image

@router.post("/images/{image_id}/classifications", response_model=schemas.ImageClassification, status_code=status.HTTP_201_CREATED)
async def classify_image(
    image_id: uuid.UUID,
    classification: schemas.ImageClassificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if the user has access to the image
    db_image = await check_image_access(image_id, db, current_user)
    
    # Ensure the image_id in the path matches the one in the request body
    if image_id != classification.image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image ID in the path must match the image_id in the request body",
        )
    
    # Get the image class to ensure it exists and belongs to the same project
    db_class = await crud.get_image_class(db=db, class_id=classification.class_id)
    if db_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image class not found")
    
    if db_class.project_id != db_image.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image class must belong to the same project as the image",
        )
    
    # Set the created_by_id to the current user's ID
    if current_user.id:
        classification.created_by_id = current_user.id
    else:
        # If the current user doesn't have an ID (e.g., it's a mock user),
        # we need to find or create a user record for them
        db_user = await crud.get_user_by_email(db=db, email=current_user.email)
        if not db_user:
            # Create a new user
            user_create = schemas.UserCreate(
                email=current_user.email,
                groups=current_user.groups,
            )
            db_user = await crud.create_user(db=db, user=user_create)
        
        classification.created_by_id = db_user.id
    
    # Create the classification
    return await crud.create_image_classification(db=db, classification=classification)

@router.get("/images/{image_id}/classifications", response_model=List[schemas.ImageClassification])
async def list_image_classifications(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if the user has access to the image
    await check_image_access(image_id, db, current_user)
    
    # Get all classifications for the image
    return await crud.get_classifications_for_image(db=db, image_id=image_id)

@router.delete("/classifications/{classification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_classification(
    classification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Get the classification
    db_classification = await crud.get_image_classification(db=db, classification_id=classification_id)
    if db_classification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classification not found")
    
    # Check if the user has access to the image
    await check_image_access(db_classification.image_id, db, current_user)
    
    # Only allow the user who created the classification or admin users to delete it
    if (current_user.id and str(db_classification.created_by_id) != str(current_user.id)) and "admin" not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this classification",
        )
    
    # Delete the classification
    success = await crud.delete_image_classification(db=db, classification_id=classification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete classification",
        )
    
    return None
