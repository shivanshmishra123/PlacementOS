"""P13 institution-scoped operating policy and quota models."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from placementos.core.database import TimestampedUUIDModel


class InstitutionOperatingPolicy(TimestampedUUIDModel):
    __tablename__ = "institution_operating_policies"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "revision_number",
            name="uq_institution_operating_policy_revision",
        ),
        Index(
            "uq_institution_operating_policy_current",
            "institution_id",
            unique=True,
            postgresql_where=text("status = 'current'"),
        ),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="current")
    onboarding_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="configuration_pending"
    )
    max_open_drives: Mapped[int] = mapped_column(Integer, nullable=False)
    max_students_per_import: Mapped[int] = mapped_column(Integer, nullable=False)
    max_export_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )
