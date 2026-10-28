"""FastAPI Authentication and Authorization Dependencies."""

import uuid
from collections.abc import Callable

from fastapi import Depends, Request

from placementos.core.config import settings
from placementos.core.errors import ForbiddenException, UnauthorizedException
from placementos.services.session import AuthContext, SessionManager


async def get_current_auth(request: Request) -> AuthContext:
    """Resolve authenticated user and active institutional context from session cookie or bearer token."""
    # 1. Check session cookie first
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)

    # 2. Check Bearer token fallback for API clients
    if not raw_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.removeprefix("Bearer ").strip()

    if not raw_token:
        raise UnauthorizedException("Authentication required: missing session token")

    auth = await SessionManager.get_session(raw_token)
    if not auth:
        raise UnauthorizedException("Invalid or expired session. Please sign in again.")

    # Attach to request state for downstream handlers and audit logging
    request.state.auth = auth
    return auth


async def get_optional_auth(request: Request) -> AuthContext | None:
    """Optionally resolve authenticated user if token is provided."""
    try:
        return await get_current_auth(request)
    except UnauthorizedException:
        return None


def require_capability(capability: str) -> Callable[[AuthContext], AuthContext]:
    """Dependency factory enforcing specific capability assignment."""

    def capability_checker(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
        auth.require_capability(capability)
        return auth

    return capability_checker


def require_role(roles: list[str]) -> Callable[[AuthContext], AuthContext]:
    """Dependency factory enforcing specific role assignment."""

    def role_checker(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
        if auth.role not in roles and auth.role != "super_admin":
            raise ForbiddenException(
                message=f"Access denied: requires one of roles {roles}",
                details={"required_roles": roles, "current_role": auth.role},
            )
        return auth

    return role_checker


def require_institution(target_institution_id: uuid.UUID, auth: AuthContext) -> None:
    """Enforce tenant isolation boundary (INV-06)."""
    auth.require_institution(target_institution_id)
