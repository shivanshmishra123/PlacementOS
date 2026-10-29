"""Small transactional audit helper for attributable domain changes."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from placementos.models.identity import AuditLog
from placementos.services.session import AuthContext


def record_audit(
    session: AsyncSession,
    auth: AuthContext,
    action: str,
    target_type: str,
    target_id: object,
    payload: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            institution_id=auth.institution_id,
            actor_user_id=auth.user_id,
            actor_membership_id=auth.membership_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            payload=payload or {},
        )
    )
