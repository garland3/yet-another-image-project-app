import uuid
import io
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user, check_mock_user_in_group
from app.minio_client import upload_file_to_minio, get_presigned_download_url
from app.config import settings
import httpx
from fastapi.responses import StreamingResponse

router = APIRouter(
    tags=["Images"],
)

async def check_project_access(project_id: uuid.UUID, db: AsyncSession, current_user: schemas.User) -> models.Project:
    db_project = await crud.get_project(db=db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, db_project.meta_group_id)
    else:
        is_member = db_project.meta_group_id in current_user.groups
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to project '{project_id}' (group '{db_project.meta_group_id}')",
        )
    return db_project

async def check_data_instance_access(data_instance_id: uuid.UUID, db: AsyncSession, current_user: schemas.User) -> models.DataInstance:
    db_data_instance = await crud.get_data_instance(db=db, image_id=data_instance_id)
    if db_data_instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    
    # Check if user has access to the project
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, db_data_instance.project.meta_group_id)
    else:
        is_member = db_data_instance.project.meta_group_id in current_user.groups
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{data_instance_id}'",
        )
    return db_data_instance

# --- DataInstance Endpoints ---

@router.post("/projects/{project_id}/images", response_model=schemas.DataInstance, status_code=status.HTTP_201_CREATED)
async def upload_image_to_project(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    metadata_json: Optional[str] = Form(None, alias="metadata"),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_project = await check_project_access(project_id, db, current_user)
    image_id = uuid.uuid4()
    object_storage_key = f"{db_project.id}/{image_id}/{file.filename}"
    
    # Upload file to object storage
    contents = await file.read()
    file_data = io.BytesIO(contents)
    file_size = len(contents)
    success = await upload_file_to_minio(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_storage_key,
        file_data=file_data,
        length=file_size,
        content_type=file.content_type
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload file to object storage")
    
    # Create data instance
    data_instance_create = schemas.DataInstanceCreate(
        project_id=db_project.id,
        filename=file.filename,
        object_storage_key=object_storage_key,
        content_type=file.content_type,
        size_bytes=file_size,
        uploaded_by_user_id=current_user.email,
    )
    db_data_instance = await crud.create_data_instance(db=db, data_instance=data_instance_create)
    
    # Process metadata if provided
    if metadata_json:
        try:
            parsed_metadata = json.loads(metadata_json)
            if isinstance(parsed_metadata, dict):
                for key, value in parsed_metadata.items():
                    metadata_create = schemas.ImageMetadataCreate(
                        data_instance_id=db_data_instance.id,
                        key=key,
                        value=str(value),
                        created_by_user_id=current_user.email
                    )
                    await crud.create_image_metadata(db=db, metadata=metadata_create)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format for metadata")
    
    # Refresh data instance to include metadata
    db_data_instance = await crud.get_data_instance(db=db, image_id=db_data_instance.id)
    
    return db_data_instance

@router.get("/projects/{project_id}/images", response_model=List[schemas.DataInstance])
async def list_images_in_project(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
    try:
        await check_project_access(project_id, db, current_user)
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            # If project doesn't exist, return empty list instead of 404
            return []
        # Re-raise other exceptions (like permission issues)
        raise
        
    # Get images for the project
    images = await crud.get_data_instances_for_project(db=db, project_id=project_id, skip=skip, limit=limit)
    
    # If no images found, return empty list
    if not images:
        return []
    
    return images

@router.get("/images/{image_id}", response_model=schemas.DataInstance)
async def get_image_metadata(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_image = await check_data_instance_access(image_id, db, current_user)
    return db_image

@router.get("/images/{image_id}/download", response_model=schemas.PresignedUrlResponse)
async def get_image_download_url(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_image = await check_data_instance_access(image_id, db, current_user)
    
    # Get the presigned URL for internal use
    internal_url = get_presigned_download_url(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=db_image.object_storage_key
    )
    if not internal_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate download URL")
    
    # Create a proxy URL that goes through our API
    proxy_url = f"/images/{image_id}/content"
    
    return schemas.PresignedUrlResponse(url=proxy_url, object_key=db_image.object_storage_key)

@router.get("/images/{image_id}/content", response_class=StreamingResponse)
async def get_image_content(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Proxy endpoint that streams image content from Minio to the client"""
    db_image = await check_data_instance_access(image_id, db, current_user)
    
    # Get the presigned URL for internal use
    internal_url = get_presigned_download_url(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=db_image.object_storage_key
    )
    if not internal_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate download URL")
    
    # Use httpx to fetch the image from Minio
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(internal_url)
            response.raise_for_status()
            
            # Create a streaming response with the same content type
            return StreamingResponse(
                content=response.iter_bytes(),
                media_type=db_image.content_type or "application/octet-stream",
                headers={
                    "Content-Disposition": f'inline; filename="{db_image.filename}"'
                }
            )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching image from storage: {str(e)}"
            )

@router.get("/images/{image_id}/thumbnail/", response_class=StreamingResponse)
async def get_image_thumbnail(
    image_id: uuid.UUID,
    width: int = 300,
    height: int = 300,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Endpoint that generates and returns a thumbnail of the image"""
    try:
        from PIL import Image
    except ImportError:
        # If Pillow is not installed, return a 501 Not Implemented
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Image resizing is not available. Please install Pillow."
        )
    
    db_image = await check_data_instance_access(image_id, db, current_user)
    
    # Check if the content type is an image
    if not db_image.content_type or not db_image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The requested file is not an image"
        )
    
    # Get the presigned URL for internal use
    internal_url = get_presigned_download_url(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=db_image.object_storage_key
    )
    if not internal_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate download URL")
    
    # Use httpx to fetch the image from Minio
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(internal_url)
            response.raise_for_status()
            
            # Get the image data
            image_data = await response.aread()
            
            # Create a BytesIO object from the image data
            from io import BytesIO
            image_stream = BytesIO(image_data)
            
            # Open the image with Pillow
            img = Image.open(image_stream)
            
            # Resize the image while maintaining aspect ratio
            img.thumbnail((width, height))
            
            # Save the resized image to a new BytesIO object
            output_stream = BytesIO()
            
            # Determine the format to save as
            save_format = 'JPEG'
            if db_image.content_type == 'image/png':
                save_format = 'PNG'
            elif db_image.content_type == 'image/gif':
                save_format = 'GIF'
            elif db_image.content_type == 'image/webp':
                save_format = 'WEBP'
            
            # Save the image to the output stream
            img.save(output_stream, format=save_format)
            output_stream.seek(0)
            
            # Create a streaming response with the resized image
            return StreamingResponse(
                content=output_stream,
                media_type=db_image.content_type,
                headers={
                    "Content-Disposition": f'inline; filename="thumb_{db_image.filename}"',
                    "Cache-Control": "public, max-age=86400"  # Cache for 24 hours
                }
            )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching image from storage: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating thumbnail: {str(e)}"
            )

# --- Image Metadata Endpoints ---

@router.get("/images/{image_id}/metadata", response_model=List[schemas.ImageMetadata])
async def get_image_metadata_list(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Get all metadata for the image
    image_metadata = await crud.get_image_metadata_all(db=db, data_instance_id=image_id)
    return image_metadata

@router.post("/images/{image_id}/metadata", response_model=schemas.ImageMetadata, status_code=status.HTTP_201_CREATED)
async def create_image_metadata(
    image_id: uuid.UUID,
    metadata: schemas.ImageMetadataBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Check if metadata with this key already exists
    existing_metadata = await crud.get_image_metadata_by_key(db=db, data_instance_id=image_id, key=metadata.key)
    if existing_metadata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Metadata with key '{metadata.key}' already exists for this image"
        )
    
    # Create the metadata
    metadata_create = schemas.ImageMetadataCreate(
        **metadata.model_dump(),
        data_instance_id=image_id,
        created_by_user_id=current_user.email
    )
    
    db_metadata = await crud.create_image_metadata(db=db, metadata=metadata_create)
    return db_metadata

@router.put("/images/{image_id}/metadata/{metadata_id}", response_model=schemas.ImageMetadata)
async def update_image_metadata(
    image_id: uuid.UUID,
    metadata_id: uuid.UUID,
    metadata_update: schemas.ImageMetadataUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Check if the metadata exists
    db_metadata = await crud.get_image_metadata(db=db, metadata_id=metadata_id)
    if db_metadata is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadata not found")
    
    # Check if the metadata belongs to the image
    if db_metadata.data_instance_id != image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata does not belong to the specified image"
        )
    
    # Set the updater user ID
    if not metadata_update.updated_by_user_id:
        metadata_update.updated_by_user_id = current_user.email
    
    updated_metadata = await crud.update_image_metadata(db=db, metadata_id=metadata_id, metadata_update=metadata_update)
    return updated_metadata

@router.delete("/images/{image_id}/metadata/{metadata_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_metadata(
    image_id: uuid.UUID,
    metadata_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Check if the metadata exists
    db_metadata = await crud.get_image_metadata(db=db, metadata_id=metadata_id)
    if db_metadata is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadata not found")
    
    # Check if the metadata belongs to the image
    if db_metadata.data_instance_id != image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata does not belong to the specified image"
        )
    
    success = await crud.delete_image_metadata(db=db, metadata_id=metadata_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete metadata"
        )
    
    return None

# --- Comment Endpoints ---

@router.get("/images/{image_id}/comments", response_model=List[schemas.Comment])
async def get_image_comments(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Get all comments for the image
    comments = await crud.get_comments_for_data_instance(db=db, data_instance_id=image_id)
    return comments

@router.post("/images/{image_id}/comments", response_model=schemas.Comment, status_code=status.HTTP_201_CREATED)
async def create_image_comment(
    image_id: uuid.UUID,
    comment: schemas.CommentBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Create the comment
    comment_create = schemas.CommentCreate(
        **comment.model_dump(),
        data_instance_id=image_id,
        user_id=current_user.email
    )
    
    db_comment = await crud.create_comment(db=db, comment=comment_create)
    return db_comment

@router.put("/images/{image_id}/comments/{comment_id}", response_model=schemas.Comment)
async def update_image_comment(
    image_id: uuid.UUID,
    comment_id: uuid.UUID,
    comment_update: schemas.CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Check if the comment exists
    db_comment = await crud.get_comment(db=db, comment_id=comment_id)
    if db_comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    
    # Check if the comment belongs to the image
    if db_comment.data_instance_id != image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment does not belong to the specified image"
        )
    
    # Check if the user is the owner of the comment
    if db_comment.user_id != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own comments"
        )
    
    updated_comment = await crud.update_comment(db=db, comment_id=comment_id, comment_update=comment_update)
    return updated_comment

@router.delete("/images/{image_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_comment(
    image_id: uuid.UUID,
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Check if the comment exists
    db_comment = await crud.get_comment(db=db, comment_id=comment_id)
    if db_comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    
    # Check if the comment belongs to the image
    if db_comment.data_instance_id != image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment does not belong to the specified image"
        )
    
    # Check if the user is the owner of the comment
    if db_comment.user_id != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )
    
    success = await crud.delete_comment(db=db, comment_id=comment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        )
    
    return None

# --- Bounding Box Endpoints ---

@router.get("/images/{image_id}/boxes", response_model=List[schemas.BoundingBox])
async def get_image_bounding_boxes(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Get all bounding boxes for the image
    boxes = await crud.get_bounding_boxes_for_data_instance(db=db, data_instance_id=image_id)
    return boxes

@router.post("/images/{image_id}/boxes", response_model=schemas.BoundingBox, status_code=status.HTTP_201_CREATED)
async def create_bounding_box(
    image_id: uuid.UUID,
    box: schemas.BoundingBoxBase,
    image_class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    db_image = await check_data_instance_access(image_id, db, current_user)
    
    # Check if the image class exists and belongs to the same project as the image
    db_class = await crud.get_image_class(db=db, class_id=image_class_id)
    if db_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image class not found")
    
    if db_class.project_id != db_image.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image class does not belong to the same project as the image"
        )
    
    # Create the bounding box
    box_create = schemas.BoundingBoxCreate(
        **box.model_dump(),
        data_instance_id=image_id,
        image_class_id=image_class_id,
        created_by_user_id=current_user.email
    )
    
    db_box = await crud.create_bounding_box(db=db, box=box_create)
    return db_box

@router.put("/images/{image_id}/boxes/{box_id}", response_model=schemas.BoundingBox)
async def update_bounding_box(
    image_id: uuid.UUID,
    box_id: uuid.UUID,
    box_update: schemas.BoundingBoxUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    db_image = await check_data_instance_access(image_id, db, current_user)
    
    # Check if the bounding box exists
    db_box = await crud.get_bounding_box(db=db, box_id=box_id)
    if db_box is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounding box not found")
    
    # Check if the bounding box belongs to the image
    if db_box.data_instance_id != image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bounding box does not belong to the specified image"
        )
    
    # If image_class_id is provided, check if it exists and belongs to the same project
    if box_update.image_class_id is not None:
        db_class = await crud.get_image_class(db=db, class_id=box_update.image_class_id)
        if db_class is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image class not found")
        
        if db_class.project_id != db_image.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image class does not belong to the same project as the image"
            )
    
    # Set the updater user ID
    if not hasattr(box_update, 'updated_by_user_id') or not box_update.updated_by_user_id:
        box_update.updated_by_user_id = current_user.email
    
    updated_box = await crud.update_bounding_box(db=db, box_id=box_id, box_update=box_update)
    return updated_box

@router.delete("/images/{image_id}/boxes/{box_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bounding_box(
    image_id: uuid.UUID,
    box_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Check if the bounding box exists
    db_box = await crud.get_bounding_box(db=db, box_id=box_id)
    if db_box is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounding box not found")
    
    # Check if the bounding box belongs to the image
    if db_box.data_instance_id != image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bounding box does not belong to the specified image"
        )
    
    success = await crud.delete_bounding_box(db=db, box_id=box_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bounding box"
        )
    
    return None

# --- Category Endpoints ---

@router.get("/categories", response_model=List[schemas.Category])
async def get_all_categories(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    categories = await crud.get_all_categories(db=db, skip=skip, limit=limit)
    return categories

@router.post("/categories", response_model=schemas.Category, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: schemas.CategoryBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if a category with this name already exists
    existing_category = await crud.get_category_by_name(db=db, name=category.name)
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{category.name}' already exists"
        )
    
    # Create the category
    category_create = schemas.CategoryCreate(
        **category.model_dump(),
        created_by_user_id=current_user.email
    )
    
    db_category = await crud.create_category(db=db, category=category_create)
    return db_category

@router.put("/categories/{category_id}", response_model=schemas.Category)
async def update_category(
    category_id: uuid.UUID,
    category_update: schemas.CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if the category exists
    db_category = await crud.get_category(db=db, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # If name is being updated, check if it's unique
    if category_update.name is not None and category_update.name != db_category.name:
        existing_category = await crud.get_category_by_name(db=db, name=category_update.name)
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{category_update.name}' already exists"
            )
    
    updated_category = await crud.update_category(db=db, category_id=category_id, category_update=category_update)
    return updated_category

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if the category exists
    db_category = await crud.get_category(db=db, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    success = await crud.delete_category(db=db, category_id=category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )
    
    return None

@router.get("/images/{image_id}/categories", response_model=List[schemas.Category])
async def get_image_categories(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Get all categories for the image
    categories = await crud.get_categories_for_data_instance(db=db, data_instance_id=image_id)
    return categories

@router.post("/images/{image_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_category_to_image(
    image_id: uuid.UUID,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Check if the category exists
    db_category = await crud.get_category(db=db, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Create the link
    link_create = schemas.DataInstanceCategoryLinkCreate(
        data_instance_id=image_id,
        category_id=category_id,
        assigned_by_user_id=current_user.email
    )
    
    try:
        await crud.link_data_instance_to_category(db=db, link=link_create)
    except Exception as e:
        # If the link already exists, this is fine
        pass
    
    return None

@router.delete("/images/{image_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_category_from_image(
    image_id: uuid.UUID,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if user has access to the image
    await check_data_instance_access(image_id, db, current_user)
    
    # Check if the category exists
    db_category = await crud.get_category(db=db, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    success = await crud.unlink_data_instance_from_category(db=db, data_instance_id=image_id, category_id=category_id)
    if not success:
        # If the link doesn't exist, this is fine
        pass
    
    return None
