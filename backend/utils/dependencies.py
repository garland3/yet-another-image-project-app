from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import hashlib
import secrets
from core.config import settings
from core.schemas import User, UserCreate
from core.database import get_db
from core.group_auth_helper import is_user_in_group
# Direct access to request.state - no need for wrapper functions
import utils.crud as crud
from core import models

security = HTTPBearer(auto_error=False)

# Function to get a user's accessible groups
async def get_user_accessible_groups(
    db: AsyncSession,
    user: User
) -> List[str]:
    """
    Get all groups that a user has access to by checking membership for each project's group.
    This implements the new approach of iterating through projects and checking if the user
    is a member of each project's group.
    
    Args:
        db: Database session
        user: The user to get accessible groups for
        
    Returns:
        List of group IDs the user has access to
    """
    # Get all projects
    all_projects = await crud.get_all_projects(db)
    
    # Initialize empty list for accessible groups
    groups = []
    
    # For each project, check if the user is a member of the project's group
    for project in all_projects:
        if is_user_in_group(user.email, project.meta_group_id) and project.meta_group_id not in groups:
            groups.append(project.meta_group_id)
    
    return groups

# Function to get accessible projects for a user
async def get_accessible_projects_for_user(
    db: AsyncSession,
    user: User,
    skip: int = 0,
    limit: int = 100
) -> List[models.Project]:
    """
    Get all projects that a user has access to by checking membership for each project.
    This implements the new approach of iterating through projects and checking if the user
    is a member of each project's group.
    
    Args:
        db: Database session
        user: The user to get accessible projects for
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of projects the user has access to
    """
    # Get all projects
    all_projects = await crud.get_all_projects(db, skip, limit)
    
    # Initialize empty list for accessible projects
    accessible_projects = []
    
    # For each project, check if the user is a member of the project's group
    for project in all_projects:
        if is_user_in_group(user.email, project.meta_group_id):
            accessible_projects.append(project)
    
    return accessible_projects


async def get_project_or_403(project_id: uuid.UUID, db: AsyncSession, current_user: User) -> models.Project:
    """
    Get a project and check if the current user has access to it.
    Raises 403 if user doesn't have access.
    
    Args:
        project_id: The ID of the project to retrieve
        db: Database session
        current_user: The current authenticated user
        
    Returns:
        The project if user has access
        
    Raises:
        HTTPException: 404 if project doesn't exist, 403 if user doesn't have access
    """
    db_project = await crud.get_project(db, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    is_member = is_user_in_group(current_user.email, db_project.meta_group_id)
    if not is_member:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    return db_project


async def get_image_or_403(image_id: uuid.UUID, db: AsyncSession, current_user: User) -> models.DataInstance:
    """
    Get an image and check if the current user has access to it.
    Raises 403 if user doesn't have access.
    
    Args:
        image_id: The ID of the image to retrieve
        db: Database session
        current_user: The current authenticated user
        
    Returns:
        The image if user has access
        
    Raises:
        HTTPException: 404 if image doesn't exist, 403 if user doesn't have access
    """
    db_image = await crud.get_image(db, image_id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    is_member = is_user_in_group(current_user.email, db_image.project.meta_group_id)
    if not is_member:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    return db_image

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

async def get_user_from_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get user from API key if provided"""
    if not credentials:
        return None
    
    # Hash the provided API key
    key_hash = hash_api_key(credentials.credentials)
    
    # Look up the API key in the database
    api_key = await crud.get_api_key_by_hash(db, key_hash)
    if not api_key or not api_key.is_active:
        return None
    
    # Update last used timestamp
    await crud.update_api_key_last_used(db, api_key.id)
    
    # For API key users, groups will be looked up server-side by the auth system
    # We don't need to parse headers for API key authentication
    user_groups = []  # Will be populated by auth system lookup

    # Return the user associated with this API key
    return User(
        id=api_key.user.id,
        email=api_key.user.email,
        username=api_key.user.username,
        is_active=api_key.user.is_active,
        created_at=api_key.user.created_at,
        updated_at=api_key.user.updated_at,
        groups=user_groups
    )

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_user: Optional[User] = Depends(get_user_from_api_key)
) -> User:
    """
    Get the current authenticated user from multiple sources:
    1. API key authentication (if provided)
    2. Proxy authentication middleware (if user was set in request.state.auth)
    3. Otherwise raise 401 Unauthorized
    
    This is much simpler than the previous implementation.
    """
    # If API key authentication was successful, return that user
    if api_user:
        return api_user
    
    # Check if auth middleware set a user
    user_email = getattr(request.state, 'user_email', None)
    if user_email:
            # Ensure user exists in database for API key operations
            db_user = await crud.get_user_by_email(db=db, email=user_email)
            if not db_user:
                user_create = UserCreate(email=user_email)
                db_user = await crud.create_user(db=db, user=user_create)
            
            # Return user with database ID
            return User(
                id=db_user.id,
                email=db_user.email,
                username=db_user.username,
                is_active=db_user.is_active,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at,
                groups=[]  # Groups handled by auth system
            )
    
    # No authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide API key or ensure proxy auth headers are present.",
    )

async def requires_group_membership(
    required_group_id: str,
    current_user: User = Depends(get_current_user)
) -> bool:
    """
    Check if the current user is a member of the required group.
    Raises an HTTPException if the user is not a member.
    
    Args:
        required_group_id: The ID of the group to check membership for
        current_user: The current user
        
    Returns:
        True if the user is a member of the group
        
    Raises:
        HTTPException: If the user is not a member of the group
    """
    is_member = is_user_in_group(current_user.email, required_group_id)
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to group '{required_group_id}'.",
        )
    return True

async def resolve_user_id(user: User, db: AsyncSession) -> uuid.UUID:
    """
    Resolve a user's ID, creating the user in the database if they don't exist.
    This provides automatic mapping for user resolution.
    """
    if user.id is not None:
        return user.id
    
    # Look up user by email
    db_user = await crud.get_user_by_email(db=db, email=user.email)
    if db_user:
        user.id = db_user.id
        return db_user.id
    
    # Create user if they don't exist
    user_create = UserCreate(email=user.email, username=user.username, is_active=user.is_active)
    db_user = await crud.create_user(db=db, user=user_create, created_by=user.email)
    user.id = db_user.id
    return db_user.id

class UserContext:
    """
    Automatic user context injection for CRUD operations.
    This provides automatic mapping for user information.
    """
    def __init__(self, user: User):
        self.user = user
        self.email = user.email
        self.id = user.id

async def get_user_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserContext:
    """
    Get resolved user context with automatic ID resolution.
    This dependency provides automatic mapping for user operations.
    """
    # Ensure user ID is resolved
    await resolve_user_id(current_user, db)
    return UserContext(current_user)
