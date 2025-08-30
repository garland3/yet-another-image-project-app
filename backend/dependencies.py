from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import hashlib
import secrets
from config import settings
from schemas import User, UserCreate
from database import get_db
import crud, models

security = HTTPBearer(auto_error=False)

# Helpers for trusting proxy headers and parsing user groups
def _headers_trusted(request: Request) -> bool:
    """Return True if we should trust X-User-* headers on this request."""
    if not settings.TRUST_X_USER_GROUPS_HEADERS:
        return False
    secret = settings.PROXY_SHARED_SECRET
    if not secret:
        return True
    header_name = getattr(settings, "X_PROXY_SECRET_HEADER", "X-Proxy-Secret")
    return request.headers.get(header_name) == secret

def _parse_groups_header(raw: Optional[str]):
    if not raw:
        return None
    raw = raw.strip()
    # Try JSON list first
    try:
        import json
        data = json.loads(raw)
        if isinstance(data, list):
            groups = [str(x).strip() for x in data if str(x).strip()]
            # Dedupe preserving order
            seen = set()
            uniq = []
            for g in groups:
                if g not in seen:
                    seen.add(g)
                    uniq.append(g)
            return uniq
    except Exception:
        pass
    # Fallback: comma-separated list
    parts = [p.strip() for p in raw.split(",")]
    groups = [p for p in parts if p]
    if not groups:
        return None
    seen = set()
    uniq = []
    for g in groups:
        if g not in seen:
            seen.add(g)
            uniq.append(g)
    return uniq

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
        if is_user_in_group(user, project.meta_group_id) and project.meta_group_id not in groups:
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
        if is_user_in_group(user, project.meta_group_id):
            accessible_projects.append(project)
    
    return accessible_projects




def is_user_in_group(user: User, group_id: str) -> bool:
    """
    Check if a user is a member of a specific group.
    In DEBUG, we mock and return True; in non-DEBUG, deny by default until real provider is implemented.
    
    Args:
        user: The user to check
        group_id: The ID of the group to check membership for
        
    Returns:
        True if the user is a member of the group (always True in mock mode)
    """
    if settings.DEBUG:
        print(f"MOCKING: Checking if user '{user.email}' is in group '{group_id}' - returning True")
        return True
    # Use groups attached to the user, if present
    if getattr(user, "groups", None):
        return group_id in user.groups
    return False

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
    
    # Optionally attach groups from trusted headers
    user_groups = None
    if _headers_trusted(request):
        user_groups = _parse_groups_header(request.headers.get(settings.X_USER_GROUPS_HEADER))

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
    # If API key authentication was successful, return that user
    if api_user:
        return api_user
    
    if settings.DEBUG and settings.SKIP_HEADER_CHECK:
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
    # If behind a trusted proxy, accept headers for auth
    if _headers_trusted(request):
        user_email = request.headers.get(settings.X_USER_ID_HEADER)
        if not user_email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user header")
        groups = _parse_groups_header(request.headers.get(settings.X_USER_GROUPS_HEADER)) or []
        # Ensure user exists
        db_user = await crud.get_user_by_email(db=db, email=user_email)
        if not db_user:
            db_user = await crud.create_user(db=db, user=UserCreate(email=user_email))
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            groups=groups
        )
    # In a real application, validate headers or other auth here.
    # For now, require API key auth if mocking is disabled.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
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
    is_member = is_user_in_group(current_user, required_group_id)
    
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
