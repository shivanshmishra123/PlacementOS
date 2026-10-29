"""FastAPI Authentication and Authorization Dependencies."""

import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.database import get_db
from placementos.core.errors import ForbiddenException, UnauthorizedException
from placementos.models.identity import Institution, Membership, User
from placementos.services.session import AuthContext, SessionManager


async def get_current_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
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

    membership = (
        await db.execute(
            select(Membership, User, Institution)
            .join(User, User.id == Membership.user_id)
            .join(Institution, Institution.id == Membership.institution_id)
            .where(
                Membership.id == auth.membership_id,
                Membership.user_id == auth.user_id,
                Membership.institution_id == auth.institution_id,
            )
        )
    ).one_or_none()
    if not membership:
        raise UnauthorizedException("Institutional membership no longer exists")
    current_membership, current_user, institution = membership
    if not current_membership.is_active or not current_user.is_active or not institution.is_active:
        raise UnauthorizedException("Session membership has been revoked")

    auth = AuthContext(
        session_id=auth.session_id,
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        institution_id=institution.id,
        institution_slug=institution.slug,
        membership_id=current_membership.id,
        role=current_membership.role,
        capabilities=list(current_membership.capabilities),
    )
    db.info["institution_id"] = auth.institution_id
    await db.execute(
        text("SELECT set_config('app.institution_id', :institution_id, true)"),
        {"institution_id": str(auth.institution_id)},
    )

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
