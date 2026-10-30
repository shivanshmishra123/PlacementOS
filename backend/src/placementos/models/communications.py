"""P07 immutable communication audiences, renders, outbox, and dispatch history."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from placementos.core.database import TimestampedUUIDModel


class CommunicationDraft(TimestampedUUIDModel):
    __tablename__ = "communication_drafts"
    __table_args__ = (
        UniqueConstraint(
            "drive_id",
            "communication_kind",
            "revision_number",
            name="uq_communication_draft_revision",
        ),
        Index("ix_communication_drafts_drive_state", "institution_id", "drive_id", "state"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    communication_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    audience_type: Mapped[str] = mapped_column(String(50), nullable=False)
    template_version: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_template: Mapped[str] = mapped_column(String(500), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    reply_to: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="email", nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    supersedes_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communication_drafts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class AudienceSnapshot(TimestampedUUIDModel):
    __tablename__ = "audience_snapshots"
    __table_args__ = (
        UniqueConstraint("communication_draft_id", name="uq_audience_snapshot_draft"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    communication_draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communication_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    audience_type: Mapped[str] = mapped_column(String(50), nullable=False)
    query_spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    included_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unresolved_count: Mapped[int] = mapped_column(Integer, nullable=False)
    exclusion_summary: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    canonical_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class AudienceRecipient(TimestampedUUIDModel):
    __tablename__ = "audience_recipients"
    __table_args__ = (
        UniqueConstraint(
            "audience_snapshot_id", "normalized_email", name="uq_audience_recipient_email"
        ),
        Index("ix_audience_recipient_student", "institution_id", "student_profile_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    audience_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audience_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    inclusion_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_revision: Mapped[str] = mapped_column(String(100), nullable=False)
    merge_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rendered_subject: Mapped[str] = mapped_column(String(500), nullable=False)
    rendered_body: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DispatchBatch(TimestampedUUIDModel):
    __tablename__ = "dispatch_batches"
    __table_args__ = (
        UniqueConstraint("proposal_id", name="uq_dispatch_batch_proposal"),
        Index("ix_dispatch_batches_drive_status", "institution_id", "drive_id", "status"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_proposals.id", ondelete="RESTRICT"), nullable=False
    )
    communication_draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communication_drafts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    audience_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audience_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pending_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unknown_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    execution_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DispatchOperation(TimestampedUUIDModel):
    __tablename__ = "dispatch_operations"
    __table_args__ = (
        UniqueConstraint("institution_id", "operation_key", name="uq_dispatch_operation_key"),
        UniqueConstraint(
            "dispatch_batch_id", "audience_recipient_id", name="uq_dispatch_batch_recipient"
        ),
        Index("ix_dispatch_operations_batch_status", "dispatch_batch_id", "status"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    dispatch_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dispatch_batches.id", ondelete="CASCADE"), nullable=False
    )
    audience_recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audience_recipients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    operation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class DispatchAttempt(TimestampedUUIDModel):
    __tablename__ = "dispatch_attempts"
    __table_args__ = (
        UniqueConstraint(
            "dispatch_operation_id", "attempt_number", name="uq_dispatch_attempt_number"
        ),
        Index("ix_dispatch_attempts_operation", "dispatch_operation_id", "attempt_number"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    dispatch_operation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dispatch_operations.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class OutboxEvent(TimestampedUUIDModel):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("institution_id", "event_key", name="uq_outbox_event_key"),
        Index("ix_outbox_events_status_due", "status", "next_attempt_at"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    event_key: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    publish_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
