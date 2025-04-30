from fastapi import Depends, HTTPException, status, Header, Request
from typing import Optional, List
from app.config import settings
from app.schemas import User

def check_mock_user_in_group(user: User, group_id: str) -> bool:
    return group_id in user.groups

async def get_current_user(
    request: Request,
    x_user_id: Optional[str] = Header(None),
    x_user_groups: Optional[str] = Header(None)
) -> User:
    if settings.SKIP_HEADER_CHECK:
        return User(email=settings.MOCK_USER_EMAIL, groups=settings.MOCK_USER_GROUPS)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (mocking disabled)",
        )

async def requires_group_membership(
    required_group_id: str,
    current_user: User = Depends(get_current_user)
) -> bool:
    is_member = False
    if settings.SKIP_HEADER_CHECK:
        is_member = check_mock_user_in_group(current_user, required_group_id)
    else:
        is_member = required_group_id in current_user.groups
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{current_user.email}' does not have access to group '{required_group_id}'",
        )
    return True
