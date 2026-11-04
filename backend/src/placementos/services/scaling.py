"""P13 versioned institution operating policy and quota enforcement."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.errors import ConflictException
from placementos.models.identity import Institution
from placementos.models.recruitment import Drive
from placementos.models.scaling import InstitutionOperatingPolicy
from placementos.schemas.scaling import OperatingPolicyRevisionCreate
from placementos.services.audit import record_audit
from placementos.services.session import AuthContext

DEFAULT_MAX_OPEN_DRIVES = 1_000
DEFAULT_MAX_STUDENTS_PER_IMPORT = 10_000
DEFAULT_MAX_EXPORT_ROWS = 10_000
TERMINAL_DRIVE_STATUSES = {"completed", "archived", "cancelled"}


@dataclass(frozen=True)
class OperatingPolicySnapshot:
    institution_id: uuid.UUID
    revision_number: int
    source: str
    onboarding_status: str
    max_open_drives: int
    max_students_per_import: int
    max_export_rows: int
    change_reason: str
    created_by_membership_id: uuid.UUID | None
    created_at: datetime | None


def default_policy(institution_id: uuid.UUID) -> OperatingPolicySnapshot:
    return OperatingPolicySnapshot(
        institution_id=institution_id,
        revision_number=0,
        source="system_default",
        onboarding_status="configuration_pending",
        max_open_drives=DEFAULT_MAX_OPEN_DRIVES,
        max_students_per_import=DEFAULT_MAX_STUDENTS_PER_IMPORT,
        max_export_rows=DEFAULT_MAX_EXPORT_ROWS,
        change_reason="P13 conservative system default; institution review pending",
        created_by_membership_id=None,
        created_at=None,
    )


def _snapshot(item: InstitutionOperatingPolicy) -> OperatingPolicySnapshot:
    return OperatingPolicySnapshot(
        institution_id=item.institution_id,
        revision_number=item.revision_number,
        source="institution_revision",
        onboarding_status=item.onboarding_status,
        max_open_drives=item.max_open_drives,
        max_students_per_import=item.max_students_per_import,
        max_export_rows=item.max_export_rows,
        change_reason=item.change_reason,
        created_by_membership_id=item.created_by_membership_id,
        created_at=item.created_at,
    )


async def current_operating_policy(
    session: AsyncSession,
    institution_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> OperatingPolicySnapshot:
    statement = select(InstitutionOperatingPolicy).where(
        InstitutionOperatingPolicy.institution_id == institution_id,
        InstitutionOperatingPolicy.status == "current",
    )
    if for_update:
        statement = statement.with_for_update()
    item = (await session.execute(statement)).scalar_one_or_none()
    return _snapshot(item) if item else default_policy(institution_id)


async def revise_operating_policy(
    session: AsyncSession,
    auth: AuthContext,
    payload: OperatingPolicyRevisionCreate,
) -> OperatingPolicySnapshot:
    current = (
        await session.execute(
            select(InstitutionOperatingPolicy)
            .where(
                InstitutionOperatingPolicy.institution_id == auth.institution_id,
                InstitutionOperatingPolicy.status == "current",
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    current_revision = current.revision_number if current else 0
    if payload.expected_revision != current_revision:
        raise ConflictException("Institution operating policy revision changed")
    if current:
        current.status = "superseded"
    item = InstitutionOperatingPolicy(
        institution_id=auth.institution_id,
        revision_number=current_revision + 1,
        status="current",
        onboarding_status=payload.onboarding_status,
        max_open_drives=payload.max_open_drives,
        max_students_per_import=payload.max_students_per_import,
        max_export_rows=payload.max_export_rows,
        change_reason=payload.change_reason,
        created_by_membership_id=auth.membership_id,
    )
    session.add(item)
    await session.flush()
    record_audit(
        session,
        auth,
        "institution:operating_policy_revised",
        "institution_operating_policy",
        item.id,
        {
            "revision_number": item.revision_number,
            "onboarding_status": item.onboarding_status,
            "quotas": {
                "max_open_drives": item.max_open_drives,
                "max_students_per_import": item.max_students_per_import,
                "max_export_rows": item.max_export_rows,
            },
        },
    )
    await session.commit()
    return _snapshot(item)


async def enforce_open_drive_quota(
    session: AsyncSession, institution_id: uuid.UUID
) -> None:
    # Serialize count-and-create within an institution so concurrent requests cannot
    # both observe the last available slot. The caller commits the drive mutation.
    await session.execute(
        select(Institution.id)
        .where(Institution.id == institution_id)
        .with_for_update()
    )
    policy = await current_operating_policy(session, institution_id)
    count = int(
        await session.scalar(
            select(func.count())
            .select_from(Drive)
            .where(
                Drive.institution_id == institution_id,
                Drive.status.not_in(TERMINAL_DRIVE_STATUSES),
            )
        )
        or 0
    )
    if count >= policy.max_open_drives:
        raise ConflictException(
            "Institution open-drive quota reached",
            code="INSTITUTION_QUOTA_REACHED",
            details={"quota": "max_open_drives", "limit": policy.max_open_drives},
        )


async def enforce_student_import_quota(
    session: AsyncSession, institution_id: uuid.UUID, row_count: int
) -> None:
    policy = await current_operating_policy(session, institution_id)
    if row_count > policy.max_students_per_import:
        raise ConflictException(
            "Student import exceeds the institution quota",
            code="INSTITUTION_QUOTA_REACHED",
            details={
                "quota": "max_students_per_import",
                "limit": policy.max_students_per_import,
                "requested": row_count,
            },
        )


async def enforce_export_quota(
    session: AsyncSession, institution_id: uuid.UUID, row_count: int
) -> None:
    policy = await current_operating_policy(session, institution_id)
    if row_count > policy.max_export_rows:
        raise ConflictException(
            "Export exceeds the institution quota",
            code="INSTITUTION_QUOTA_REACHED",
            details={
                "quota": "max_export_rows",
                "limit": policy.max_export_rows,
                "requested": row_count,
            },
        )
