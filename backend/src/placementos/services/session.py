"""PlacementOS Session Management and Authentication Context."""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from placementos.core.config import settings
from placementos.core.errors import ForbiddenException
from placementos.core.redis import get_redis_client
from placementos.core.security import hash_token


@dataclass
class AuthContext:
    """Authoritative actor context resolved from an authenticated session."""

    session_id: str
    user_id: uuid.UUID
    email: str
    full_name: str
    institution_id: uuid.UUID
    institution_slug: str
    membership_id: uuid.UUID
    role: str
    capabilities: list[str]

    def has_capability(self, capability: str) -> bool:
        """Check if actor possesses specific capability."""
        if self.role in ("super_admin", "institution_admin"):
            return True
        return capability in self.capabilities

    def require_capability(self, capability: str) -> None:
        """Enforce capability check or raise 403 Forbidden."""
        if not self.has_capability(capability):
            raise ForbiddenException(
                message=f"Missing required capability: {capability}",
                details={"required_capability": capability, "role": self.role},
            )

    def require_role(self, *roles: str) -> None:
        """Enforce role check or raise 403 Forbidden."""
        if self.role in ("super_admin", "institution_admin"):
            return
        if self.role not in roles:
            raise ForbiddenException(
                message=f"Access restricted to roles: {', '.join(roles)}",
                details={"allowed_roles": list(roles), "user_role": self.role},
            )

    def require_coordinator(self) -> None:
        """Enforce coordinator or admin role."""
        self.require_role("placement_coordinator", "coordinator", "institution_admin")

    def require_institution(self, target_institution_id: uuid.UUID) -> None:
        """Enforce tenant isolation boundary (INV-06)."""
        if self.role == "super_admin":
            return
        if self.institution_id != target_institution_id:
            raise ForbiddenException(
                message="Cross-institution access denied",
                details={
                    "actor_institution_id": str(self.institution_id),
                    "target_institution_id": str(target_institution_id),
                },
            )


class SessionManager:
    """Redis-backed opaque session manager."""

    @staticmethod
    def _key(token_hash: str) -> str:
        return f"session:{token_hash}"

    @classmethod
    async def create_session(
        cls,
        user_id: uuid.UUID,
        email: str,
        full_name: str,
        institution_id: uuid.UUID,
        institution_slug: str,
        membership_id: uuid.UUID,
        role: str,
        capabilities: list[str],
    ) -> tuple[str, AuthContext]:
        """Create a new opaque session and store in Redis."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_token(raw_token)
        session_id = str(uuid.uuid4())

        context = AuthContext(
            session_id=session_id,
            user_id=user_id,
            email=email,
            full_name=full_name,
            institution_id=institution_id,
            institution_slug=institution_slug,
            membership_id=membership_id,
            role=role,
            capabilities=capabilities,
        )

        data = {
            "session_id": session_id,
            "user_id": str(user_id),
            "email": email,
            "full_name": full_name,
            "institution_id": str(institution_id),
            "institution_slug": institution_slug,
            "membership_id": str(membership_id),
            "role": role,
            "capabilities": capabilities,
            "created_at": datetime.now(UTC).isoformat(),
        }

        redis = get_redis_client()
        key = cls._key(token_hash)
        await redis.set(key, json.dumps(data), ex=settings.SESSION_MAX_AGE_SECONDS)

        # Index session under user for revocation
        user_sessions_key = f"user_sessions:{user_id}"
        await redis.sadd(user_sessions_key, token_hash)
        await redis.expire(user_sessions_key, settings.SESSION_MAX_AGE_SECONDS)

        return raw_token, context

    @classmethod
    async def get_session(cls, raw_token: str) -> AuthContext | None:
        """Validate and resolve an active session from raw cookie token."""
        if not raw_token:
            return None

        token_hash = hash_token(raw_token)
        redis = get_redis_client()
        raw_data = await redis.get(cls._key(token_hash))
        if not raw_data:
            return None

        data = json.loads(raw_data)
        return AuthContext(
            session_id=data["session_id"],
            user_id=uuid.UUID(data["user_id"]),
            email=data["email"],
            full_name=data["full_name"],
            institution_id=uuid.UUID(data["institution_id"]),
            institution_slug=data["institution_slug"],
            membership_id=uuid.UUID(data["membership_id"]),
            role=data["role"],
            capabilities=data.get("capabilities", []),
        )

    @classmethod
    async def revoke_session(cls, raw_token: str) -> bool:
        """Revoke a single session by its raw token."""
        if not raw_token:
            return False
        token_hash = hash_token(raw_token)
        redis = get_redis_client()
        key = cls._key(token_hash)
        raw_data = await redis.get(key)
        if raw_data:
            data = json.loads(raw_data)
            user_id = data.get("user_id")
            if user_id:
                await redis.srem(f"user_sessions:{user_id}", token_hash)
        deleted = await redis.delete(key)
        return bool(deleted)

    @classmethod
    async def revoke_all_user_sessions(cls, user_id: uuid.UUID) -> int:
        """Revoke all active sessions for a user."""
        redis = get_redis_client()
        user_sessions_key = f"user_sessions:{user_id}"
        token_hashes = await redis.smembers(user_sessions_key)
        count = 0
        for th in token_hashes:
            count += await redis.delete(cls._key(str(th)))
        await redis.delete(user_sessions_key)
        return count
