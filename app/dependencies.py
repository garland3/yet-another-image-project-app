from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import httpx
import hashlib
import secrets
from app.config import settings
from app.schemas import User, UserCreate
from app.database import get_db
from app import crud, models
from aiocache import cached, Cache
from aiocache.serializers import JsonSerializer

security = HTTPBearer(auto_error=False)

# Mock AD group membership data
# In a real implementation, this would be replaced with actual AD queries
MOCK_GROUP_MEMBERS: Dict[str, List[str]] = {
    "admin": ["test@example.com", "admin@example.com"],
    "project1": ["test@example.com", "user1@example.com"],
    "project2": ["user2@example.com", "user3@example.com"],
    "admin-group": ["test@example.com", "admin@example.com"],
    "data-scientists": ["test@example.com", "scientist@example.com"],
    "project-alpha-group": ["test@example.com", "alpha@example.com"],
    # Add more mock groups as needed
}

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
        if check_user_in_group(user, project.meta_group_id) and project.meta_group_id not in groups:
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
        if check_user_in_group(user, project.meta_group_id):
            accessible_projects.append(project)
    
    return accessible_projects

def get_group_members(group_id: str) -> List[str]:
    """
    Get all members of a specific group from AD.
    In this mock implementation, returns members from the MOCK_GROUP_MEMBERS dictionary.
    
    Args:
        group_id: The ID of the group to get members for
        
    Returns:
        List of email addresses of users who are members of the group
    """
    # In a real implementation, this would query AD for group members
    return MOCK_GROUP_MEMBERS.get(group_id, [])

async def call_authorization_server(user: User, group_id: str) -> bool:
    """
    Call the external authorization server to check group membership.
    This is the actual implementation that would call an external service.
    """
    try:
        auth_server_url = getattr(settings, 'AUTH_SERVER_URL', None)
        if not auth_server_url:
            raise ValueError("AUTH_SERVER_URL not configured")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{auth_server_url}/check-membership",
                json={"user_email": user.email, "group_id": group_id},
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            return result.get("is_member", False)
    except Exception as e:
        print(f"ERROR: Failed to call authorization server: {e}")
        return False

@cached(ttl=900, cache=Cache.MEMORY, serializer=JsonSerializer())
async def is_user_in_group(user: User, group_id: str) -> bool:
    """
    Check if a user is a member of a specific group with 15-minute caching.
    This is the main function to use for authorization checks.
    
    Args:
        user: The user to check
        group_id: The ID of the group to check membership for
        
    Returns:
        True if the user is a member of the group, False otherwise
    """
    if settings.CHECK_MOCK_MEMBERSHIP:
        # Use mock implementation for testing
        group_members = get_group_members(group_id)
        is_member = user.email in group_members
        
        print(f"DEBUG: [MOCK] Checking if user '{user.email}' is in group '{group_id}'")
        print(f"DEBUG: [MOCK] Group members: {group_members}")
        print(f"DEBUG: [MOCK] Is member: {is_member}")
        
        return is_member
    else:
        # Call the actual authorization server
        print(f"DEBUG: [AUTH_SERVER] Checking if user '{user.email}' is in group '{group_id}'")
        is_member = await call_authorization_server(user, group_id)
        print(f"DEBUG: [AUTH_SERVER] Is member: {is_member}")
        return is_member

def check_user_in_group(user: User, group_id: str) -> bool:
    """
    Legacy synchronous function for backward compatibility.
    This will be replaced by is_user_in_group throughout the codebase.
    """
    if settings.CHECK_MOCK_MEMBERSHIP:
        group_members = get_group_members(group_id)
        is_member = user.email in group_members
        
        print(f"DEBUG: [LEGACY] Checking if user '{user.email}' is in group '{group_id}'")
        print(f"DEBUG: [LEGACY] Group members: {group_members}")
        print(f"DEBUG: [LEGACY] Is member: {is_member}")
        
        return is_member
    else:
        # Since we removed the groups field, always call authorization server for non-mock mode
        print(f"DEBUG: [LEGACY] Non-mock mode - groups field removed, should use async is_user_in_group instead")
        return False

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

async def get_user_from_api_key(
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
    
    # Return the user associated with this API key
    return User(
        id=api_key.user.id,
        email=api_key.user.email,
        username=api_key.user.username,
        is_active=api_key.user.is_active,
        created_at=api_key.user.created_at,
        updated_at=api_key.user.updated_at
    )

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_groups: Optional[str] = Header(None),
    api_user: Optional[User] = Depends(get_user_from_api_key)
) -> User:
    # If API key authentication was successful, return that user
    if api_user:
        return api_user
    
    if settings.SKIP_HEADER_CHECK:
        # Create a mock user object (groups field no longer exists)
        mock_user = User(email=settings.MOCK_USER_EMAIL)
        
        # Check if the user exists in the database
        db_user = await crud.get_user_by_email(db=db, email=mock_user.email)
        
        # If the user doesn't exist, create it
        if not db_user:
            user_create = UserCreate(
                email=mock_user.email,
            )
            db_user = await crud.create_user(db=db, user=user_create)
            
            # Update the mock user with the database user's ID
            mock_user.id = db_user.id
        else:
            # Update the mock user with the database user's ID
            mock_user.id = db_user.id
        
        return mock_user
    else:
        # In a real application, we would validate the user's token/credentials here
        # and retrieve the user from the database
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (mocking disabled)",
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
    is_member = check_user_in_group(current_user, required_group_id)
    
    if not is_member:
        # Get the available groups for a more helpful error message
        available_groups = list(MOCK_GROUP_MEMBERS.keys()) if settings.CHECK_MOCK_MEMBERSHIP else []
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to group '{required_group_id}'. Available groups in the system: {', '.join(available_groups)}.",
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
