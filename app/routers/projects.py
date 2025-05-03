import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user, requires_group_membership, check_mock_user_in_group
from app.config import settings

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)

# --- Project Endpoints ---

@router.post("/", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    project: schemas.ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, project.meta_group_id)
    else:
        is_member = project.meta_group_id in current_user.groups
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' cannot create projects in group '{project.meta_group_id}'",
        )
    
    # Set the creator user ID
    if not project.created_by_user_id and hasattr(current_user, 'id'):
        project.created_by_user_id = current_user.email
    
    db_project = await crud.create_project(db=db, project=project)
    return db_project

@router.get("/", response_model=List[schemas.Project])
async def read_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    projects = await crud.get_projects_by_group_ids(db=db, group_ids=current_user.groups, skip=skip, limit=limit)
    return projects

@router.get("/{project_id}", response_model=schemas.Project)
async def read_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
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

@router.put("/{project_id}", response_model=schemas.Project)
async def update_project_details(
    project_id: uuid.UUID,
    project_update: schemas.ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    db_project = await crud.get_project(db=db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check if user has access to the project
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
    
    # Set the updater user ID
    if not project_update.updated_by_user_id and hasattr(current_user, 'id'):
        project_update.updated_by_user_id = current_user.email
    
    updated_project = await crud.update_project(db=db, project_id=project_id, project_update=project_update)
    return updated_project

# --- Project Metadata Endpoints ---

@router.get("/{project_id}/metadata", response_model=List[schemas.ProjectMetadata])
async def read_project_metadata(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
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
            detail=f"User '{current_user.email}' does not have access to project '{project_id}'",
        )
    
    project_metadata = await crud.get_project_metadata_all(db=db, project_id=project_id)
    return project_metadata

@router.post("/{project_id}/metadata", response_model=schemas.ProjectMetadata, status_code=status.HTTP_201_CREATED)
async def create_project_metadata(
    project_id: uuid.UUID,
    metadata: schemas.ProjectMetadataBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
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
            detail=f"User '{current_user.email}' does not have access to project '{project_id}'",
        )
    
    # Check if metadata with this key already exists
    existing_metadata = await crud.get_project_metadata_by_key(db=db, project_id=project_id, key=metadata.key)
    if existing_metadata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Metadata with key '{metadata.key}' already exists for this project"
        )
    
    # Create the metadata
    metadata_create = schemas.ProjectMetadataCreate(
        **metadata.model_dump(),
        project_id=project_id,
        created_by_user_id=current_user.email
    )
    
    db_metadata = await crud.create_project_metadata(db=db, metadata=metadata_create)
    return db_metadata

@router.put("/{project_id}/metadata/{metadata_id}", response_model=schemas.ProjectMetadata)
async def update_project_metadata(
    project_id: uuid.UUID,
    metadata_id: uuid.UUID,
    metadata_update: schemas.ProjectMetadataUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
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
            detail=f"User '{current_user.email}' does not have access to project '{project_id}'",
        )
    
    # Check if the metadata exists
    db_metadata = await crud.get_project_metadata(db=db, metadata_id=metadata_id)
    if db_metadata is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadata not found")
    
    # Check if the metadata belongs to the project
    if db_metadata.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata does not belong to the specified project"
        )
    
    # Set the updater user ID
    if not metadata_update.updated_by_user_id:
        metadata_update.updated_by_user_id = current_user.email
    
    updated_metadata = await crud.update_project_metadata(db=db, metadata_id=metadata_id, metadata_update=metadata_update)
    return updated_metadata

@router.delete("/{project_id}/metadata/{metadata_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_metadata(
    project_id: uuid.UUID,
    metadata_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
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
            detail=f"User '{current_user.email}' does not have access to project '{project_id}'",
        )
    
    # Check if the metadata exists
    db_metadata = await crud.get_project_metadata(db=db, metadata_id=metadata_id)
    if db_metadata is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadata not found")
    
    # Check if the metadata belongs to the project
    if db_metadata.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata does not belong to the specified project"
        )
    
    success = await crud.delete_project_metadata(db=db, metadata_id=metadata_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete metadata"
        )
    
    return None

# --- Image Class Endpoints ---

@router.get("/{project_id}/classes", response_model=List[schemas.ImageClass])
async def read_image_classes(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
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
            detail=f"User '{current_user.email}' does not have access to project '{project_id}'",
        )
    
    classes = await crud.get_image_classes_for_project(db=db, project_id=project_id)
    return classes

@router.post("/{project_id}/classes", response_model=schemas.ImageClass, status_code=status.HTTP_201_CREATED)
async def create_image_class(
    project_id: uuid.UUID,
    image_class: schemas.ImageClassBase,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
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
            detail=f"User '{current_user.email}' does not have access to project '{project_id}'",
        )
    
    # Create the image class
    class_create = schemas.ImageClassCreate(
        **image_class.model_dump(),
        project_id=project_id,
        created_by_user_id=current_user.email
    )
    
    db_class = await crud.create_image_class(db=db, image_class=class_create)
    return db_class

@router.put("/{project_id}/classes/{class_id}", response_model=schemas.ImageClass)
async def update_image_class(
    project_id: uuid.UUID,
    class_id: uuid.UUID,
    class_update: schemas.ImageClassUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
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
            detail=f"User '{current_user.email}' does not have access to project '{project_id}'",
        )
    
    # Check if the class exists
    db_class = await crud.get_image_class(db=db, class_id=class_id)
    if db_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image class not found")
    
    # Check if the class belongs to the project
    if db_class.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image class does not belong to the specified project"
        )
    
    # Set the updater user ID
    if not class_update.updated_by_user_id:
        class_update.updated_by_user_id = current_user.email
    
    updated_class = await crud.update_image_class(db=db, class_id=class_id, class_update=class_update)
    return updated_class

@router.delete("/{project_id}/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_class(
    project_id: uuid.UUID,
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # First check if the project exists and user has access
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
            detail=f"User '{current_user.email}' does not have access to project '{project_id}'",
        )
    
    # Check if the class exists
    db_class = await crud.get_image_class(db=db, class_id=class_id)
    if db_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image class not found")
    
    # Check if the class belongs to the project
    if db_class.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image class does not belong to the specified project"
        )
    
    success = await crud.delete_image_class(db=db, class_id=class_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete image class"
        )
    
    return None
