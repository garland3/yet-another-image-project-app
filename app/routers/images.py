import uuid
import io
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user, check_mock_user_in_group
from app.minio_client import upload_file_to_minio, get_presigned_download_url
from app.config import settings
import json

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
    parsed_metadata: Optional[Dict[str, Any]] = None
    if metadata_json:
        try:
            parsed_metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format for metadata")
    # If metadata_json is None or empty string, parsed_metadata remains None
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
    # Create a dictionary from the SQLAlchemy model
    db_dict = {}
    for c in db_data_instance.__table__.columns:
        if c.name == "metadata_":
                # Special handling for metadata
                if db_data_instance.metadata_ is not None:
                    try:
                        # Try to get the raw value from the SQLAlchemy JSON type
                        if hasattr(db_data_instance.metadata_, "_asdict"):
                            db_dict["metadata_"] = db_data_instance.metadata_._asdict()
                        elif hasattr(db_data_instance.metadata_, "items"):
                            db_dict["metadata_"] = dict(db_data_instance.metadata_.items())
                        elif hasattr(db_data_instance.metadata_, "__class__") and db_data_instance.metadata_.__class__.__name__ == "MetaData":
                            # Handle MetaData object by converting it to an empty dict
                            db_dict["metadata_"] = {}
                        # Check if it's a string that can be parsed as JSON
                        elif isinstance(db_data_instance.metadata_, str):
                            try:
                                import json
                                db_dict["metadata_"] = json.loads(db_data_instance.metadata_)
                            except json.JSONDecodeError:
                                db_dict["metadata_"] = {"value": db_data_instance.metadata_}
                        else:
                            # If it's already a dict or can be converted to one
                            try:
                                db_dict["metadata_"] = dict(db_data_instance.metadata_) if db_data_instance.metadata_ else None
                            except (TypeError, ValueError):
                                # If conversion to dict fails, use an empty dict
                                db_dict["metadata_"] = {}
                    except (TypeError, ValueError, AttributeError) as e:
                        print(f"Error converting metadata to dict: {e}")
                        db_dict["metadata_"] = {}
                else:
                    db_dict["metadata_"] = None
        else:
            # Normal column handling
            db_dict[c.name] = getattr(db_data_instance, c.name)
    
    try:
        # Validate with Pydantic
        response_data = schemas.DataInstance.model_validate(db_dict)
    except Exception as e:
        print(f"Error validating DataInstance: {e}")
        print(f"Input data: {db_dict}")
        raise
    return response_data

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
                                import json
                                img_dict["metadata_"] = json.loads(img.metadata_)
                            except json.JSONDecodeError:
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
async def get_image_metadata(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
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
    # Create a dictionary from the SQLAlchemy model
    db_dict = {}
    for c in db_image.__table__.columns:
        if c.name == "metadata_":
                # Special handling for metadata
                if db_image.metadata_ is not None:
                    try:
                        # Try to get the raw value from the SQLAlchemy JSON type
                        if hasattr(db_image.metadata_, "_asdict"):
                            db_dict["metadata_"] = db_image.metadata_._asdict()
                        elif hasattr(db_image.metadata_, "items"):
                            db_dict["metadata_"] = dict(db_image.metadata_.items())
                        elif hasattr(db_image.metadata_, "__class__") and db_image.metadata_.__class__.__name__ == "MetaData":
                            # Handle MetaData object by converting it to an empty dict
                            db_dict["metadata_"] = {}
                        # Check if it's a string that can be parsed as JSON
                        elif isinstance(db_image.metadata_, str):
                            try:
                                import json
                                db_dict["metadata_"] = json.loads(db_image.metadata_)
                            except json.JSONDecodeError:
                                db_dict["metadata_"] = {"value": db_image.metadata_}
                        else:
                            # If it's already a dict or can be converted to one
                            try:
                                db_dict["metadata_"] = dict(db_image.metadata_) if db_image.metadata_ else None
                            except (TypeError, ValueError):
                                # If conversion to dict fails, use an empty dict
                                db_dict["metadata_"] = {}
                    except (TypeError, ValueError, AttributeError) as e:
                        print(f"Error converting metadata to dict: {e}")
                        db_dict["metadata_"] = {}
                else:
                    db_dict["metadata_"] = None
        else:
            # Normal column handling
            db_dict[c.name] = getattr(db_image, c.name)
    
    try:
        # Validate with Pydantic
        response_data = schemas.DataInstance.model_validate(db_dict)
    except Exception as e:
        print(f"Error validating DataInstance: {e}")
        print(f"Input data: {db_dict}")
        raise
    return response_data

import httpx
from fastapi.responses import StreamingResponse

@router.get("/images/{image_id}/download", response_model=schemas.PresignedUrlResponse)
async def get_image_download_url(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
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
    db_image = await crud.get_data_instance(db=db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    
    # Check access permissions
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
