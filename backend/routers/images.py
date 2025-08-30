import uuid
import io
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Body
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import utils.crud as crud
from core import schemas, models
from core.database import get_db
from core.config import settings
from core.group_auth_helper import is_user_in_group
from utils.dependencies import get_current_user
from utils.dependencies import get_project_or_403
from utils.boto3_client import upload_file_to_minio, get_presigned_download_url
from utils.serialization import to_data_instance_schema
from utils.file_security import get_content_disposition_header
import json as _json
from PIL import Image

router = APIRouter(
    prefix="/api",
    tags=["Images"],
)

@router.post("/projects/{project_id}/images", response_model=schemas.DataInstance, status_code=status.HTTP_201_CREATED)
async def upload_image_to_project(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    metadata_json: Optional[str] = Form(None, alias="metadata"),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_project = await get_project_or_403(project_id, db, current_user)
    image_id = uuid.uuid4()
    object_storage_key = f"{db_project.id}/{image_id}/{file.filename}"
    parsed_metadata: Optional[Dict[str, Any]] = None
    if metadata_json:
        try:
            parsed_metadata = _json.loads(metadata_json)
        except _json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format for metadata")
    # If metadata_json is None or empty string, parsed_metadata remains None
    # Basic validation
    max_size = int(os.getenv("MAX_UPLOAD_BYTES", "10485760"))  # 10MB default
    # Try to read a small chunk to estimate streaming health, but do not load all into memory
    try:
        file.file.seek(0, io.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size and file_size > max_size:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
    except Exception:
        # If we cannot get size ahead of time, proceed to stream; S3 client will handle
        file_size = None
    success = await upload_file_to_minio(
        bucket_name=settings.S3_BUCKET,
        object_name=object_storage_key,
        file_data=file.file,
        length=file_size or 0,
        content_type=file.content_type
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload file to object storage")
    data_instance_create = schemas.DataInstanceCreate(
        project_id=db_project.id,
        filename=file.filename,
        object_storage_key=object_storage_key,
        content_type=file.content_type,
        size_bytes=file_size,
        metadata=parsed_metadata,
        uploaded_by_user_id=current_user.email,
    )
    db_data_instance = await crud.create_data_instance(db=db, data_instance=data_instance_create)
    
    # Use utility function for consistent metadata serialization
    return to_data_instance_schema(db_data_instance)

@router.get("/projects/{project_id}/images", response_model=List[schemas.DataInstance])
#@cached(ttl=3600, key_builder=lambda *args, **kwargs: f"project_images:{kwargs['project_id']}:skip:{kwargs.get('skip', 0)}:limit:{kwargs.get('limit', 100)}")
async def list_images_in_project(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
    try:
        await get_project_or_403(project_id, db, current_user)
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
        
    # Process images
    response_images = []
    for img in images:
        # Create a dictionary from the SQLAlchemy model
        img_dict = {}
        for c in img.__table__.columns:
            if c.name == "metadata_":
                # Special handling for metadata
                if img.metadata_ is not None:
                    try:
                        # Try to get the raw value from the SQLAlchemy JSON type
                        if hasattr(img.metadata_, "_asdict"):
                            img_dict["metadata_"] = img.metadata_._asdict()
                        elif hasattr(img.metadata_, "items"):
                            img_dict["metadata_"] = dict(img.metadata_.items())
                        elif hasattr(img.metadata_, "__class__") and img.metadata_.__class__.__name__ == "MetaData":
                            # Handle MetaData object by converting it to an empty dict
                            img_dict["metadata_"] = {}
                        # Check if it's a string that can be parsed as JSON
                        elif isinstance(img.metadata_, str):
                            try:
                                import json as _j
                                img_dict["metadata_"] = _j.loads(img.metadata_)
                            except _json.JSONDecodeError:
                                img_dict["metadata_"] = {"value": img.metadata_}
                        else:
                            # If it's already a dict or can be converted to one
                            try:
                                img_dict["metadata_"] = dict(img.metadata_) if img.metadata_ else None
                            except (TypeError, ValueError):
                                # If conversion to dict fails, use an empty dict
                                img_dict["metadata_"] = {}
                    except (TypeError, ValueError, AttributeError) as e:
                        print(f"Error converting metadata to dict: {e}")
                        img_dict["metadata_"] = {}
                else:
                    img_dict["metadata_"] = None
            else:
                # Normal column handling
                img_dict[c.name] = getattr(img, c.name)
        
        try:
            # Validate with Pydantic
            img_schema = schemas.DataInstance.model_validate(img_dict)
            response_images.append(img_schema)
        except Exception as e:
            print(f"Error validating DataInstance: {e}")
            print(f"Input data: {img_dict}")
            # Skip this image but continue processing others
            continue
    
    return response_images

# Add trailing slash version to handle frontend requests
@router.get("/projects/{project_id}/images/", response_model=List[schemas.DataInstance])
# #@cached(ttl=3600, key_builder=lambda *args, **kwargs: f"project_images:{kwargs['project_id']}:skip:{kwargs.get('skip', 0)}:limit:{kwargs.get('limit', 100)}")
async def list_images_in_project_with_slash(
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Same as list_images_in_project but with trailing slash to handle frontend requests."""
    # First check if the project exists and user has access
    try:
        await get_project_or_403(project_id, db, current_user)
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
        
    # Process images
    response_images = []
    for img in images:
        # Create a dictionary from the SQLAlchemy model
        img_dict = {}
        for c in img.__table__.columns:
            if c.name == "metadata_":
                # Special handling for metadata
                if img.metadata_ is not None:
                    try:
                        # Try to get the raw value from the SQLAlchemy JSON type
                        if hasattr(img.metadata_, "_asdict"):
                            img_dict["metadata_"] = img.metadata_._asdict()
                        elif hasattr(img.metadata_, "items"):
                            img_dict["metadata_"] = dict(img.metadata_.items())
                        elif hasattr(img.metadata_, "__class__") and img.metadata_.__class__.__name__ == "MetaData":
                            # Handle MetaData object by converting it to an empty dict
                            img_dict["metadata_"] = {}
                        # Check if it's a string that can be parsed as JSON
                        elif isinstance(img.metadata_, str):
                            try:
                                import json as _j
                                img_dict["metadata_"] = _j.loads(img.metadata_)
                            except _json.JSONDecodeError:
                                img_dict["metadata_"] = {"value": img.metadata_}
                        else:
                            # If it's already a dict or can be converted to one
                            try:
                                img_dict["metadata_"] = dict(img.metadata_) if img.metadata_ else None
                            except (TypeError, ValueError):
                                # If conversion to dict fails, use an empty dict
                                img_dict["metadata_"] = {}
                    except (TypeError, ValueError, AttributeError) as e:
                        print(f"Error converting metadata to dict: {e}")
                        img_dict["metadata_"] = {}
                else:
                    img_dict["metadata_"] = None
            else:
                # Normal column handling
                img_dict[c.name] = getattr(img, c.name)
        
        try:
            # Validate with Pydantic
            img_schema = schemas.DataInstance.model_validate(img_dict)
            response_images.append(img_schema)
        except Exception as e:
            print(f"Error validating DataInstance: {e}")
            print(f"Input data: {img_dict}")
            # Skip this image but continue processing others
            continue
    
    return response_images

@router.get("/images/{image_id}", response_model=schemas.DataInstance)
#@cached(ttl=3600, key_builder=lambda *args, **kwargs: f"image:{kwargs['image_id']}")
async def get_image_metadata(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    is_member = is_user_in_group(current_user.email, db_image.project.meta_group_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )
    
    # Use utility function for consistent metadata serialization
    return to_data_instance_schema(db_image)

import httpx
from fastapi.responses import StreamingResponse

@router.get("/images/{image_id}/download", response_model=schemas.PresignedUrlResponse)
#@cached(ttl=3600, key_builder=lambda *args, **kwargs: f"image_download:{kwargs['image_id']}")
async def get_image_download_url(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    is_member = is_user_in_group(current_user.email, db_image.project.meta_group_id)
    if not is_member:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )
    
    # Get the presigned URL for internal use
    internal_url = get_presigned_download_url(
        bucket_name=settings.S3_BUCKET,
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
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    
    # Check access permissions
    is_member = is_user_in_group(current_user.email, db_image.project.meta_group_id)
    if not is_member:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )
    
    # Get the presigned URL for internal use
    internal_url = get_presigned_download_url(
        bucket_name=settings.S3_BUCKET,
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
                    "Content-Disposition": get_content_disposition_header(db_image.filename, "inline")
                }
            )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching image from storage: {str(e)}"
            )
        except Exception as e:
            # Ensure any unexpected exception is returned as 500 per tests
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error fetching image: {str(e)}"
            )

@router.get("/images/{image_id}/thumbnail", response_class=StreamingResponse)
async def get_image_thumbnail(
    image_id: uuid.UUID,
    width: int = Query(200, description="Thumbnail width in pixels"),
    height: int = Query(200, description="Thumbnail height in pixels"),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Generate and return a thumbnail of the image"""
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Width and height must be positive integers")
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    
    # Check access permissions
    is_member = is_user_in_group(current_user.email, db_image.project.meta_group_id)
    if not is_member:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )
    
    # Get the presigned URL for internal use
    internal_url = get_presigned_download_url(
        bucket_name=settings.S3_BUCKET,
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
            
            # Use PIL to resize the image
            try:
                img = Image.open(io.BytesIO(image_data))
                
                # Resize the image while maintaining aspect ratio
                img.thumbnail((width, height))
                
                # Save the resized image to a bytes buffer
                output_buffer = io.BytesIO()
                img_format = img.format or 'JPEG'  # Default to JPEG if format is unknown
                img.save(output_buffer, format=img_format)
                output_buffer.seek(0)
                
                # Determine the content type based on the image format
                content_type_map = {
                    'JPEG': 'image/jpeg',
                    'PNG': 'image/png',
                    'GIF': 'image/gif',
                    'WEBP': 'image/webp'
                }
                content_type = content_type_map.get(img_format, 'image/jpeg')
                
                # Return the thumbnail
                thumbnail_filename = f"thumbnail_{db_image.filename}" if db_image.filename else "thumbnail"
                return StreamingResponse(
                    content=output_buffer,
                    media_type=content_type,
                    headers={
                        "Content-Disposition": get_content_disposition_header(thumbnail_filename, "inline")
                    }
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error generating thumbnail: {str(e)}"
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching image from storage: {str(e)}"
            )

class MetadataUpdate(BaseModel):
    key: str
    value: Any

@router.put("/images/{image_id}/metadata", response_model=schemas.DataInstance, status_code=status.HTTP_200_OK)
async def update_image_metadata(
    image_id: uuid.UUID,
    metadata: MetadataUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Update metadata for a specific image"""
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    
    # Check access permissions
    is_member = is_user_in_group(current_user.email, db_image.project.meta_group_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )
    
    # Update the metadata
    current_metadata = db_image.metadata_ or {}
    current_metadata[metadata.key] = metadata.value
    
    # Update the database
    await db.execute(
        update(models.DataInstance)
        .where(models.DataInstance.id == image_id)
        .values(metadata_=current_metadata)
    )
    await db.commit()
    
    # Return the updated image; build response dict ensuring updated metadata is present
    await db.refresh(db_image)
    try:
        return schemas.DataInstance(
            id=db_image.id,
            project_id=db_image.project_id,
            filename=db_image.filename,
            object_storage_key=db_image.object_storage_key,
            content_type=db_image.content_type,
            size_bytes=db_image.size_bytes,
            metadata_=current_metadata or {},
            uploaded_by_user_id=db_image.uploaded_by_user_id,
            uploader_id=db_image.uploader_id,
            created_at=db_image.created_at,
            updated_at=db_image.updated_at,
        )
    except Exception as e:
        print(f"Error building DataInstance response: {e}")
        raise

@router.delete("/images/{image_id}/metadata/{key}", response_model=schemas.DataInstance, status_code=status.HTTP_200_OK)
async def delete_image_metadata(
    image_id: uuid.UUID,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Delete metadata for a specific image"""
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    
    # Check access permissions
    is_member = is_user_in_group(current_user.email, db_image.project.meta_group_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to image '{image_id}'",
        )
    
    # Update the metadata
    current_metadata = db_image.metadata_ or {}
    if key in current_metadata:
        del current_metadata[key]
    
    # Update the database
    await db.execute(
        update(models.DataInstance)
        .where(models.DataInstance.id == image_id)
        .values(metadata_=current_metadata)
    )
    await db.commit()
    
    # Return the updated image; build response dict ensuring updated metadata is present
    await db.refresh(db_image)
    try:
        return schemas.DataInstance(
            id=db_image.id,
            project_id=db_image.project_id,
            filename=db_image.filename,
            object_storage_key=db_image.object_storage_key,
            content_type=db_image.content_type,
            size_bytes=db_image.size_bytes,
            metadata_=current_metadata or {},
            uploaded_by_user_id=db_image.uploaded_by_user_id,
            uploader_id=db_image.uploader_id,
            created_at=db_image.created_at,
            updated_at=db_image.updated_at,
        )
    except Exception as e:
        print(f"Error building DataInstance response: {e}")
        raise
