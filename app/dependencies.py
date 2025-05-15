from fastapi import Depends, HTTPException, status, Header, Request
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.config import settings
from app.schemas import User, UserCreate
from app.database import get_db
from app import crud, models

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

def check_user_in_group(user: User, group_id: str) -> bool:
    """
    Check if a user is a member of a specific group.
    
    Args:
        user: The user to check
        group_id: The ID of the group to check membership for
        
    Returns:
        True if the user is a member of the group, False otherwise
    """
    if settings.CHECK_MOCK_MEMBERSHIP:
        # Get all members of the group and check if the user's email is in the list
        group_members = get_group_members(group_id)
        is_member = user.email in group_members
        
        # Add debug information
        print(f"DEBUG: Checking if user '{user.email}' is in group '{group_id}'")
        print(f"DEBUG: Group members: {group_members}")
        print(f"DEBUG: User groups: {user.groups}")
        print(f"DEBUG: Is member: {is_member}")
        
        return is_member
    else:
        # Fall back to the original implementation
        is_member = group_id in user.groups
        
        # Add debug information
        print(f"DEBUG: Checking if group '{group_id}' is in user '{user.email}' groups: {user.groups}")
        print(f"DEBUG: Is member: {is_member}")
        
        return is_member

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_user_id: Optional[str] = Header(None),
    x_user_groups: Optional[str] = Header(None)
) -> User:
    if settings.SKIP_HEADER_CHECK:
        # Create a mock user object
        mock_user = User(email=settings.MOCK_USER_EMAIL, groups=settings.MOCK_USER_GROUPS)
        
        # Check if the user exists in the database
        db_user = await crud.get_user_by_email(db=db, email=mock_user.email)
        
        # If the user doesn't exist, create it
        if not db_user:
            user_create = UserCreate(
                email=mock_user.email,
                groups=mock_user.groups,
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
        # Get the user's accessible groups for a more helpful error message
        user_groups = current_user.groups
        available_groups = MOCK_GROUP_MEMBERS.keys() if settings.CHECK_MOCK_MEMBERSHIP else user_groups
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to group '{required_group_id}'. You have access to these groups: {', '.join(user_groups)}. Available groups in the system: {', '.join(available_groups)}.",
        )
    return True
