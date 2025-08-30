"""Security headers middleware with config-based toggles.

Sets common security headers:
 - Content-Security-Policy (CSP)
 - X-Frame-Options (XFO)
 - X-Content-Type-Options: nosniff
 - Referrer-Policy

Each header is individually togglable via settings. HSTS is intentionally omitted.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import Response
from fastapi import Request

from core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # X-Content-Type-Options
        if getattr(settings, "SECURITY_NOSNIFF_ENABLED", True):
            if "X-Content-Type-Options" not in response.headers:
                response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        if getattr(settings, "SECURITY_XFO_ENABLED", True):
            xfo_value = getattr(settings, "SECURITY_XFO_VALUE", "SAMEORIGIN")
            if "X-Frame-Options" not in response.headers:
                response.headers["X-Frame-Options"] = xfo_value

        # Referrer-Policy
        if getattr(settings, "SECURITY_REFERRER_POLICY_ENABLED", True):
            ref_value = getattr(
                settings, "SECURITY_REFERRER_POLICY_VALUE", "no-referrer"
            )
            if "Referrer-Policy" not in response.headers:
                response.headers["Referrer-Policy"] = ref_value

        # Content-Security-Policy
        if getattr(settings, "SECURITY_CSP_ENABLED", True):
            csp_value = getattr(settings, "SECURITY_CSP_VALUE", None)
            if csp_value and "Content-Security-Policy" not in response.headers:
                response.headers["Content-Security-Policy"] = csp_value

        return response