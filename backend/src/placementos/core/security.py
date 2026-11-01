"""PlacementOS Security and Correlation ID Middleware."""

import hashlib
import json
import logging
import re
import secrets
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from placementos.core.config import settings

access_logger = logging.getLogger("placementos.access")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a unique correlation ID to every incoming request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", "")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,100}", correlation_id):
            correlation_id = str(uuid.uuid4())

        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Prevent shared caching/sniffing of authenticated application responses."""

    PUBLIC_PROBES = {"/health", "/ready", "/api/v1/health", "/api/v1/ready"}

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path not in self.PUBLIC_PROBES:
            response.headers["Cache-Control"] = "private, no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Vary"] = "Cookie, Authorization"
        response.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - started) * 1000:.2f}"
        auth = getattr(request.state, "auth", None)
        access_logger.info(
            json.dumps(
                {
                    "event": "http.request.completed",
                    "correlation_id": getattr(request.state, "correlation_id", None),
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "institution_id": str(auth.institution_id) if auth else None,
                    "actor_user_id": str(auth.user_id) if auth else None,
                },
                separators=(",", ":"),
            )
        )
        return response


class BrowserWriteProtectionMiddleware(BaseHTTPMiddleware):
    """Enforce origin and double-submit CSRF checks for cookie-authenticated writes."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    EXEMPT_PATHS = {"/api/v1/auth/dev-login"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in self.SAFE_METHODS or request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if not session_cookie:
            return await call_next(request)

        origin = request.headers.get("origin")
        if (settings.ENVIRONMENT == "production" and not origin) or (
            origin and origin not in settings.ALLOWED_ORIGINS
        ):
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "ORIGIN_REJECTED", "message": "Untrusted request origin", "correlation_id": getattr(request.state, "correlation_id", None), "details": {}}},
            )

        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")
        if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "CSRF_FAILED", "message": "Missing or invalid CSRF token", "correlation_id": getattr(request.state, "correlation_id", None), "details": {}}},
            )
        return await call_next(request)


def hash_token(token: str) -> str:
    """Cryptographic SHA-256 hash for session tokens and proposal fingerprints."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generate a high-entropy random CSRF token."""
    return secrets.token_urlsafe(32)
