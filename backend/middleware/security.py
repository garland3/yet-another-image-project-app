"""
Simple authentication middleware.
Handles protocol-specific authentication logic.
"""

import logging
from typing import Optional
from fastapi import Request
from core.config import settings
from core.security import security_validator

logger = logging.getLogger(__name__)


def get_user_from_header(header_value: Optional[str]) -> Optional[str]:
    """Extract clean user email from header value."""
    if not header_value:
        return None
    
    # Clean up the header value
    email = header_value.strip()
    if not email or '@' not in email:
        return None
    
    return email.lower()


# Simple auth middleware
async def auth_middleware(request: Request, call_next):
    """
    Simple authentication middleware.
    Extracts user email and adds it to request state.
    """
    try:
        # Use SKIP_HEADER_CHECK as debug mode flag
        debug_mode = settings.SKIP_HEADER_CHECK
        
        user_email = None
        
        if debug_mode:
            # Debug mode - use header if present, otherwise use mock user
            x_email_header = request.headers.get(settings.X_USER_ID_HEADER) or request.headers.get(settings.X_USER_ID_HEADER.lower())
            if x_email_header:
                user_email = get_user_from_header(x_email_header)
            else:
                user_email = settings.MOCK_USER_EMAIL
            
            logger.debug(f"DEBUG MODE: Authenticated user: {user_email}")
        else:
            # Production mode - require valid header
            x_email_header = request.headers.get(settings.X_USER_ID_HEADER) or request.headers.get(settings.X_USER_ID_HEADER.lower())
            user_email = get_user_from_header(x_email_header)
            
            if user_email:
                logger.debug(f"Authenticated user: {user_email}")
            else:
                logger.warning(f"Missing or empty {settings.X_USER_ID_HEADER} header")
        
        # Add user to request state (can be None)
        request.state.user_email = user_email

        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.error(f"Auth middleware error: {e}", exc_info=True)
        # Don't fail the request, just continue without auth
        request.state.user_email = None
        response = await call_next(request)
        return response


def is_user_in_group(user_email: str, group_id: str) -> bool:
    """
    Convenience function for group membership checks.
    Delegates to the core security validator.
    """
    return security_validator.is_user_in_group(user_email, group_id)

import time
import logging
from typing import Dict, Tuple, Optional
from fastapi import Request
from core.config import settings

logger = logging.getLogger(__name__)

# Simple in-memory cache for group membership checks
# Format: {(user_email, group_id): (is_member, timestamp)}
_group_membership_cache: Dict[Tuple[str, str], Tuple[bool, float]] = {}
_CACHE_TTL = 300  # 5 minutes


def get_user_from_header(header_value: Optional[str]) -> Optional[str]:
    """Extract clean user email from header value."""
    if not header_value:
        return None
    
    # Clean up the header value
    email = header_value.strip()
    if not email or '@' not in email:
        return None
    
    return email.lower()


class SecurityValidator:
    """Centralized security validation for authentication and authorization."""

    def __init__(self):
        pass

    async def validate_authentication(
        self, headers: Dict[str, str], debug_mode: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate authentication for both HTTP and WebSocket requests.

        Returns:
            (is_valid, user_email, error_message)
        """
        try:
            # Use configured header name instead of hardcoded values
            x_email_header = headers.get(settings.X_USER_ID_HEADER) or headers.get(settings.X_USER_ID_HEADER.lower())

            if debug_mode:
                if x_email_header:
                    user_email = get_user_from_header(x_email_header)
                else:
                    user_email = settings.MOCK_USER_EMAIL

                return True, user_email or settings.MOCK_USER_EMAIL, None
            else:
                # Production mode - require valid header
                user_email = get_user_from_header(x_email_header)
                if not user_email:
                    return False, None, f"Missing or empty {settings.X_USER_ID_HEADER} header"

                return True, user_email, None

        except Exception as e:
            logger.error(f"Authentication validation error: {e}", exc_info=True)
            return False, None, f"Authentication error: {str(e)}"

    def is_user_in_group(self, user_email: str, group_id: str) -> bool:
        """
        Single source of truth for group membership checks.
        Includes caching for performance.
        
        Args:
            user_email: The user's email address
            group_id: The group ID to check membership for
            
        Returns:
            True if user is in the group, False otherwise
        """
        if not user_email or not group_id:
            return False
        
        # In debug mode, always allow access
        if settings.DEBUG or settings.SKIP_HEADER_CHECK:
            logger.debug(f"DEBUG MODE: Allowing {user_email} access to group {group_id}")
            return True
        
        # Normalize inputs
        user_email = user_email.lower().strip()
        group_id = group_id.strip()
        
        cache_key = (user_email, group_id)
        current_time = time.time()
        
        # Check cache first
        if cache_key in _group_membership_cache:
            is_member, cached_time = _group_membership_cache[cache_key]
            if current_time - cached_time < _CACHE_TTL:
                logger.debug(f"Cache hit: {user_email} in {group_id} = {is_member}")
                return is_member
            else:
                # Cache expired, remove entry
                del _group_membership_cache[cache_key]
        
        # Look up group membership
        is_member = self._check_group_membership(user_email, group_id)
        
        # Cache the result
        _group_membership_cache[cache_key] = (is_member, current_time)
        
        logger.info(f"Group membership check: {user_email} in {group_id} = {is_member}")
        return is_member
    
    def _check_group_membership(self, user_email: str, group_id: str) -> bool:
        """
        Internal method to check group membership.
        Replace this with your actual auth system integration.
        """
        # TODO: Replace with actual auth system lookup
        # Examples:
        # - Query LDAP/Active Directory
        # - Call external auth service API
        # - Query database with user roles
        # - Call OAuth2 userinfo endpoint
        
        # For development, simple user-to-group mapping
        user_group_mapping = {
            "admin@example.com": ["admin", "data-scientists", "project-alpha-group"],
            "scientist@example.com": ["data-scientists", "project-alpha-group"],
            "user@example.com": ["project-alpha-group"],
            settings.MOCK_USER_EMAIL: settings.MOCK_USER_GROUPS,
        }
        
        user_groups = user_group_mapping.get(user_email, [])
        return group_id in user_groups



# Global instance - single source of truth
security_validator = SecurityValidator()


# Simple auth middleware
async def auth_middleware(request: Request, call_next):
    """
    Simple authentication middleware.
    Extracts user email and adds it to request state.
    """
    try:
        # Convert headers to dict for the validator
        headers = dict(request.headers)
        
        # Use SKIP_HEADER_CHECK as debug mode flag
        debug_mode = settings.SKIP_HEADER_CHECK
        
        # Validate authentication
        is_valid, user_email, error_message = await security_validator.validate_authentication(
            headers, debug_mode
        )
        
        if is_valid and user_email:
            # Add user to request state
            request.state.user_email = user_email
            logger.debug(f"Authenticated user: {user_email}")
        else:
            # No user authenticated - endpoints can still handle API key auth
            request.state.user_email = None
            if error_message:
                logger.warning(f"Authentication failed: {error_message}")

        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.error(f"Auth middleware error: {e}", exc_info=True)
        # Don't fail the request, just continue without auth
        request.state.user_email = None
        response = await call_next(request)
        return response
