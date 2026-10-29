"""PlacementOS Recruitment Drives and Company Domain Models (P03-T01)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from placementos.core.database import TimestampedUUIDModel


class Company(TimestampedUUIDModel):
    """Institution-scoped employer record."""

    __tablename__ = "companies"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    drives: Mapped[list[Drive]] = relationship(
        "Drive", back_populates="company", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("institution_id", "name", name="uq_companies_institution_name"),
        Index("ix_companies_institution_name", "institution_id", "name"),
    )


class Drive(TimestampedUUIDModel):
    """Recruitment drive entity scoped to an institution and employer."""

    __tablename__ = "drives"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False, index=True
    )  # canonical lifecycle from PROJ_SPECIFICATION.md section 7
    operational_hold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_coordinator_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_drive_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    published_drive_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    published_evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    publication_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concurrency_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="drives")
    revisions: Mapped[list[DriveRevision]] = relationship(
        "DriveRevision", back_populates="drive", cascade="all, delete-orphan"
    )
    source_artifacts: Mapped[list[Any]] = relationship(
        "SourceArtifact",
        primaryjoin="Drive.id == foreign(SourceArtifact.drive_id)",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_drives_institution_status", "institution_id", "status"),
    )


class DriveRevision(TimestampedUUIDModel):
    """Immutable version of drive specifications and requirements."""

    __tablename__ = "drive_revisions"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_description_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_type: Mapped[str] = mapped_column(
        String(50), default="full_time", nullable=False
    )  # full_time, internship, internship_plus_ft
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[str] = mapped_column(
        String(50), default="on_site", nullable=False
    )  # on_site, hybrid, remote
    compensation_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    registration_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registration_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawal_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    drive: Mapped[Drive] = relationship("Drive", back_populates="revisions")

    __table_args__ = (
        UniqueConstraint("drive_id", "revision_number", name="uq_drive_revisions_drive_rev"),
        Index("ix_drive_revisions_drive_num", "drive_id", "revision_number"),
    )

