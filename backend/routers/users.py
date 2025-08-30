import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import utils.crud as crud
from core import schemas
from core.database import get_db
from core.group_auth_helper import is_user_in_group
from utils.dependencies import get_current_user

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)



@router.get("/me", response_model=schemas.User)
async def read_current_user(
    current_user: schemas.User = Depends(get_current_user),
):
    return current_user

@router.get("/me/groups", response_model=List[str])
async def read_current_user_groups(
    current_user: schemas.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all groups that the current user has access to.
    This includes groups they have access to through projects.
    """
    # Get all projects from the database
    all_projects = await crud.get_all_projects(db)
    
    # Initialize empty list for accessible groups
    user_groups = []
    
    # For each project, check if the user is a member of the project's group
    for project in all_projects:
        if is_user_in_group(current_user.email, project.meta_group_id) and project.meta_group_id not in user_groups:
            user_groups.append(project.meta_group_id)
    
    return user_groups

@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Create a new user - restricted to admin group only"""
    # Only allow admin users to create new users
    is_admin = is_user_in_group(current_user.email, "admin")
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create users - admin access required",
        )
    
    # Check if user already exists
    existing_user = await crud.get_user_by_email(db=db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )
    
    # Create the user
    db_user = await crud.create_user(db=db, user=user_data, created_by=current_user.email)
    return db_user

@router.get("/{user_id}", response_model=schemas.User)
async def read_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Only allow admin users to read other users
    is_admin = is_user_in_group(current_user.email, "admin")
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to read user information",
        )
    db_user = await crud.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

@router.patch("/{user_id}", response_model=schemas.User)
async def update_user(
    user_id: uuid.UUID,
    user_data: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Only allow users to update their own profile or admin users
    is_admin = is_user_in_group(current_user.email, "admin")
    if str(user_id) != str(current_user.id) and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )
    
    # Update the user
    db_user = await crud.update_user(db=db, user_id=user_id, user_data=user_data.model_dump(exclude_unset=True))
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return db_user
