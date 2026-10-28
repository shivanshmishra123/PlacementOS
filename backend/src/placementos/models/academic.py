"""PlacementOS Academic Record Revisions and Correction Proposals (P02-T04 / P02-T06)."""

from __future__ import annotations

import decimal
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from placementos.core.database import Base, TimestampedUUIDModel
from placementos.models.identity import StudentProfile, User


class AcademicRecordRevision(Base):
    """Immutable, append-only historical academic fact revision for a student."""

    __tablename__ = "academic_record_revisions"
    __table_args__ = (
        UniqueConstraint(
            "student_profile_id", "revision_number", name="uq_academic_student_revision"
        ),
        Index("ix_academic_inst_student", "institution_id", "student_profile_id"),
        Index("ix_academic_branch_cohort", "institution_id", "branch", "graduation_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Provenance and verification
    source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # csv_import, correction_request, registrar_sync
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Core academic facts (exact decimal for CGPA - INV-05)
    branch: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cgpa: Mapped[decimal.Decimal] = mapped_column(Numeric(precision=4, scale=2), nullable=False)
    cgpa_scale: Mapped[decimal.Decimal] = mapped_column(
        Numeric(precision=4, scale=2), default=decimal.Decimal("10.00"), nullable=False
    )
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Backlog facts: None indicates unverified/unknown; 0 indicates clean record (INV-02)
    active_backlogs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    history_backlogs: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    student_profile: Mapped[StudentProfile] = relationship("StudentProfile")


class StudentCorrectionProposal(TimestampedUUIDModel):
    """Student-initiated correction proposal for verified facts, subject to coordinator approval."""

    __tablename__ = "student_correction_proposals"
    __table_args__ = (
        Index("ix_corrections_inst_status", "institution_id", "status"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Proposed changes dictionary e.g. {"cgpa": "8.80", "active_backlogs": 0}
    proposed_changes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    justification: Mapped[str] = mapped_column(String(1000), nullable=False)
    supporting_document_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Review status: pending | approved | rejected
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    review_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="SET NULL"),
        nullable=True,
    )
    resulting_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_record_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    student_profile: Mapped[StudentProfile] = relationship("StudentProfile")
    proposed_by_user: Mapped[User] = relationship("User")
