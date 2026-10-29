"""P06 student documents, readiness, publication, and registration models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from placementos.core.database import TimestampedUUIDModel


class DriveDocumentRequirement(TimestampedUUIDModel):
    """Immutable validation rule bound to one immutable drive revision."""

    __tablename__ = "drive_document_requirements"
    __table_args__ = (
        UniqueConstraint("drive_revision_id", "document_type", name="uq_requirement_revision_type"),
        Index("ix_requirements_drive_revision", "institution_id", "drive_id", "drive_revision_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    drive_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drive_revisions.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_label: Mapped[str] = mapped_column(String(100), nullable=False)
    allowed_extensions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    max_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    filename_pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    required_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class StudentDocument(TimestampedUUIDModel):
    """Student-owned logical document with an immutable current revision pointer."""

    __tablename__ = "student_documents"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "student_profile_id", "document_type", name="uq_student_document_type"
        ),
        Index("ix_student_documents_owner", "institution_id", "student_profile_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class DocumentRevision(TimestampedUUIDModel):
    """Immutable accepted bytes owned by one student document."""

    __tablename__ = "document_revisions"
    __table_args__ = (
        UniqueConstraint(
            "student_document_id", "revision_number", name="uq_document_revision_number"
        ),
        UniqueConstraint("upload_session_id", name="uq_document_revision_upload_session"),
        Index("ix_document_revisions_owner", "institution_id", "student_profile_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    student_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_documents.id", ondelete="CASCADE"), nullable=False
    )
    upload_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("upload_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    scan_status: Mapped[str] = mapped_column(String(32), nullable=False)
    structure_status: Mapped[str] = mapped_column(String(32), nullable=False)
    text_status: Mapped[str] = mapped_column(String(32), nullable=False)
    supersedes_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_revisions.id", ondelete="RESTRICT"), nullable=True
    )
    uploaded_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class DocumentValidationRun(TimestampedUUIDModel):
    """Validation of exact document bytes against an exact requirement revision."""

    __tablename__ = "document_validation_runs"
    __table_args__ = (
        UniqueConstraint(
            "document_revision_id", "requirement_id", name="uq_document_validation_dependency"
        ),
        Index("ix_document_validations_student", "institution_id", "student_profile_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    document_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drive_document_requirements.id", ondelete="RESTRICT"),
        nullable=False,
    )
    validator_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)


class Registration(TimestampedUUIDModel):
    """Current participation projection; immutable events preserve every transition."""

    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("drive_id", "student_profile_id", name="uq_registration_drive_student"),
        Index("ix_registrations_drive_state", "institution_id", "drive_id", "state"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_drive_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drive_revisions.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eligibility_policy_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    submitted_evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_eligibility_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eligibility_results.id", ondelete="RESTRICT"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    concurrency_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class RegistrationEvent(TimestampedUUIDModel):
    """Append-only evidence for registration transitions."""

    __tablename__ = "registration_events"
    __table_args__ = (
        Index("ix_registration_events_registration", "registration_id", "created_at"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    registration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("registrations.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
