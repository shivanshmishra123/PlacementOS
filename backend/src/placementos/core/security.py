"""PlacementOS Security and Correlation ID Middleware."""

import hashlib
import secrets
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware attaching a unique correlation ID to every incoming request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


def hash_token(token: str) -> str:
    """Cryptographic SHA-256 hash for session tokens and proposal fingerprints."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generate a high-entropy random CSRF token."""
    return secrets.token_urlsafe(32)
