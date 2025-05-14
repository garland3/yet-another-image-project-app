from fastapi import Depends, HTTPException, status, Header, Request
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.config import settings
from app.schemas import User, UserCreate
from app.database import get_db
from app import crud

def check_user_in_group(user: User, group_id: str) -> bool:
    return group_id in user.groups

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
    is_member = False
    if settings.CHECK_MOCK_MEMBERSHIP:
        is_member = check_user_in_group(current_user, required_group_id)
    else:
        is_member = required_group_id in current_user.groups
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to group '{required_group_id}'",
        )
    return True
