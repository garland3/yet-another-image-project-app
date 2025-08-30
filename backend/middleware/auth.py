"""
Unified authentication middleware.
Single middleware for auth that extracts user info from headers and sets request state.
"""

import logging
import re
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from core.config import settings

logger = logging.getLogger(__name__)


def get_user_from_header(header_value: str) -> str | None:
    """
    Extract and validate user email from header.
    
    Args:
        header_value: Raw header value containing user email
        
    Returns:
        Cleaned user email or None if invalid
    """
    if not header_value:
        return None
    
    # Clean and normalize email
    email = header_value.strip().lower()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return None
    
    return email


async def auth_middleware(request: Request, call_next):
    """
    Unified authentication middleware.
    Extracts user info from headers and sets request state based on config.
    
    Similar to:
        request.state.user_email = user_email
        response = await call_next(request)
        return response
    """
    try:
        # Get headers with case-insensitive lookup
        headers = {k.lower(): v for k, v in request.headers.items()}
        
        # Determine if we're in debug/development mode
        debug_mode = settings.DEBUG or settings.SKIP_HEADER_CHECK
        
        if debug_mode:
            # Debug mode - more permissive auth
            logger.debug("Running in debug mode")
            
            # Try to get user from header first
            user_header_value = (
                headers.get(settings.X_USER_ID_HEADER.lower()) or 
                headers.get("x-user-email")  # Fallback for compatibility
            )
            
            if user_header_value:
                user_email = get_user_from_header(user_header_value)
                if user_email:
                    logger.debug(f"Debug mode: Using header user {user_email}")
                    request.state.user_email = user_email
                else:
                    logger.debug(f"Debug mode: Invalid header email, using mock user {settings.MOCK_USER_EMAIL}")
                    request.state.user_email = settings.MOCK_USER_EMAIL
            else:
                # No header in debug mode - use mock user
                logger.debug(f"Debug mode: No header, using mock user {settings.MOCK_USER_EMAIL}")
                request.state.user_email = settings.MOCK_USER_EMAIL
                
            # Set other user info for debug mode
            request.state.is_authenticated = True
            
        else:
            # Production mode - require valid headers
            logger.debug("Running in production mode")
            
            # Check for proxy secret if required
            if settings.PROXY_SHARED_SECRET:
                proxy_secret = headers.get(settings.X_PROXY_SECRET_HEADER.lower())
                if proxy_secret != settings.PROXY_SHARED_SECRET:
                    logger.warning("Invalid or missing proxy secret")
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid proxy authentication"}
                    )
            
            # Get user email from configured header
            user_header_value = headers.get(settings.X_USER_ID_HEADER.lower())
            user_email = get_user_from_header(user_header_value)
            
            if not user_email:
                logger.warning(f"Missing or invalid {settings.X_USER_ID_HEADER} header")
                return JSONResponse(
                    status_code=401, 
                    content={"detail": f"Missing or invalid {settings.X_USER_ID_HEADER} header"}
                )
            
            # Set user info from headers  
            request.state.user_email = user_email
            request.state.is_authenticated = True
            
            # Groups will always be looked up server-side via auth system
            logger.debug(f"Groups will be looked up server-side for {user_email}")
        
        # Process request
        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.error(f"Authentication middleware error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal authentication error"}
        )

# code shoudl just use the request.state

# def get_authenticated_user_email(request: Request) -> str | None:
#     """
#     Get the authenticated user email from request state.
    
#     Args:
#         request: FastAPI request object
        
#     Returns:
#         User email if authenticated, None otherwise
#     """
#     return getattr(request.state, 'user_email', None)



# Unauthenticated users should never make it to the backend and be rejected by the middleware.
# Code should just use request.state.user_email directly - no wrapper functions needed.