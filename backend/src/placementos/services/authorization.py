"""Object-scope authorization helpers shared by API and workers."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.errors import NotFoundException
from placementos.models.identity import DriveAssignment
from placementos.models.recruitment import Drive
from placementos.services.session import AuthContext


async def load_authorized_drive(
    session: AsyncSession,
    auth: AuthContext,
    drive_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Drive:
    """Load a drive only when the current coordinator is explicitly assigned to it."""
    auth.require_coordinator()
    statement = (
        select(Drive)
        .outerjoin(
            DriveAssignment,
            (DriveAssignment.drive_id == Drive.id)
            & (DriveAssignment.institution_id == Drive.institution_id),
        )
        .where(
            Drive.id == drive_id,
            Drive.institution_id == auth.institution_id,
            or_(
                Drive.created_by_membership_id == auth.membership_id,
                Drive.assigned_coordinator_membership_id == auth.membership_id,
                DriveAssignment.membership_id == auth.membership_id,
            ),
        )
    )
    if for_update:
        statement = statement.with_for_update(of=Drive)
    drive = (await session.execute(statement)).scalars().first()
    if not drive:
        raise NotFoundException(f"Drive '{drive_id}' not found")
    return drive
