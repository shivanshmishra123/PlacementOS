"""PlacementOS Storage, Source Artifacts, Text Extractions, and Domain Jobs Models (P03-T02 through P03-T06)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from placementos.core.database import TimestampedUUIDModel


class UploadSession(TimestampedUUIDModel):
    """Owner-bound upload session for private quarantine intake."""

    __tablename__ = "upload_sessions"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # jd_intake, student_document, etc.
    drive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    student_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quarantine_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    accepted_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, validating, completed, rejected, expired
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceArtifact(TimestampedUUIDModel):
    """Immutable recruitment source document (uploaded JD, pasted email text, etc.)."""

    __tablename__ = "source_artifacts"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    upload_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("upload_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_kind: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # jd_upload, pasted_email, manual_entry
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)  # Immutable final key
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scan_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, clean, infected, suspicious, unavailable, development_fixture
    acceptance_status: Mapped[str] = mapped_column(
        String(50), default="validating", nullable=False
    )  # quarantined, validating, accepted, rejected

    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    extractions: Mapped[list[TextExtraction]] = relationship(
        "TextExtraction", back_populates="source_artifact", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_source_artifacts_inst_hash", "institution_id", "hash_sha256"),
    )


class TextExtraction(TimestampedUUIDModel):
    """Extracted text and structural locators derived from a SourceArtifact."""

    __tablename__ = "text_extractions"

    source_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    extraction_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # pdf_extractor, docx_extractor, text_extractor
    text_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_empty_or_scanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    locators: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    source_artifact: Mapped[SourceArtifact] = relationship("SourceArtifact", back_populates="extractions")


class DomainJob(TimestampedUUIDModel):
    """Durable asynchronous job tracking background work idempotently."""

    __tablename__ = "domain_jobs"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    operation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="queued", nullable=False, index=True
    )  # queued, processing, completed, failed_retryable, failed_terminal, cancelled
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("institution_id", "operation_key", name="uq_domain_jobs_inst_operation"),
        Index("ix_domain_jobs_inst_status", "institution_id", "status"),
    )

