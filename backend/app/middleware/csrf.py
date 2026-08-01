"""
CSRF protection middleware for state-changing requests.

Since the app uses httpOnly cookies for authentication, CSRF protection
is required on POST/PUT/PATCH/DELETE endpoints. This middleware validates
the Origin/Referer header against ALLOWED_ORIGINS.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.config import settings
import logging

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFTokenMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware.

    Validates Origin/Referer headers on state-changing requests.
    GET/HEAD/OPTIONS are exempt. Server-to-server calls (no Origin/Referer)
    are allowed for internal service communication.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() not in STATE_CHANGING_METHODS:
            return await call_next(request)

        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        if not origin and not referer:
            return await call_next(request)

        allowed = [o.rstrip("/").lower() for o in settings.ALLOWED_ORIGINS]

        if origin:
            origin_clean = origin.rstrip("/").lower()
            if origin_clean not in allowed:
                logger.warning(
                    f"CSRF blocked: origin={origin} for {request.method} {request.url.path}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": True,
                        "message": "Cross-origin request blocked",
                        "status_code": 403,
                    },
                )
            return await call_next(request)

        if referer:
            from urllib.parse import urlparse
            try:
                referer_host = urlparse(referer).hostname
                if referer_host:
                    allowed_hosts = [urlparse(o).hostname for o in allowed]
                    if referer_host not in allowed_hosts:
                        logger.warning(
                            f"CSRF blocked: referer={referer} for {request.method} {request.url.path}"
                        )
                        return JSONResponse(
                            status_code=403,
                            content={
                                "error": True,
                                "message": "Cross-origin request blocked",
                                "status_code": 403,
                            },
                        )
            except Exception:
                # URL parsing failed — block as safety measure
                logger.warning(
                    f"CSRF blocked: unparseable referer={referer} for {request.method} {request.url.path}"
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": True,
                        "message": "Cross-origin request blocked",
                        "status_code": 403,
                    },
                )

        return await call_next(request)
