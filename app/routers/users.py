import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app import crud, schemas
from app.database import get_db
from app.dependencies import get_current_user, get_user_accessible_groups, MOCK_GROUP_MEMBERS
from app.config import settings
from app.config import settings

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)

@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    # Check if the user already exists
    db_user = await crud.get_user_by_email(db=db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user.email}' already exists",
        )
    
    # Create the user
    return await crud.create_user(db=db, user=user)

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
    This includes both the user's direct groups and groups they have access to through projects.
    """
    # If using mock membership, return all groups the user is a member of
    if settings.CHECK_MOCK_MEMBERSHIP:
        # Get all groups where the user is a member
        user_groups = []
        for group_id, members in MOCK_GROUP_MEMBERS.items():
            if current_user.email in members and group_id not in user_groups:
                user_groups.append(group_id)
        return user_groups
    else:
        # Otherwise, return the user's groups from their profile
        return current_user.groups

@router.get("/{user_id}", response_model=schemas.User)
async def read_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
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
    if str(user_id) != str(current_user.id) and "admin" not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )
    
    # Update the user
    db_user = await crud.update_user(db=db, user_id=user_id, user_data=user_data.model_dump(exclude_unset=True))
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return db_user
