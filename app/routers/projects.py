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
