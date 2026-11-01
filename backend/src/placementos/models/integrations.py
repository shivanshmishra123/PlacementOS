"""P11 Google Workspace connection, reconciliation, and controlled-operation models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from placementos.core.database import TimestampedUUIDModel


class IntegrationConnection(TimestampedUUIDModel):
    __tablename__ = "integration_connections"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "provider", "external_account_id", name="uq_integration_account"
        ),
        Index("ix_integration_connections_status", "institution_id", "provider", "status"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    owner_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), default="google", nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    granted_scopes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    access_token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    connection_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OAuthAuthorizationState(TimestampedUUIDModel):
    __tablename__ = "oauth_authorization_states"
    __table_args__ = (UniqueConstraint("state_hash", name="uq_oauth_state_hash"),)

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False
    )
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    code_verifier_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    requested_features: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    requested_scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    redirect_after: Mapped[str] = mapped_column(String(512), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GmailSourceCapture(TimestampedUUIDModel):
    __tablename__ = "gmail_source_captures"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "message_id",
            "attachment_id",
            name="uq_gmail_capture_selection",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_gmail_capture_drive", "institution_id", "drive_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_connections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    source_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    attachment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(998), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_history_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class SheetImportPreview(TimestampedUUIDModel):
    __tablename__ = "sheet_import_previews"
    __table_args__ = (Index("ix_sheet_preview_status", "institution_id", "status", "expires_at"),)

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_connections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    spreadsheet_id: Mapped[str] = mapped_column(String(255), nullable=False)
    selected_range: Mapped[str] = mapped_column(String(255), nullable=False)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_token: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_academic_revisions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="previewed", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class IntegrationOperation(TimestampedUUIDModel):
    __tablename__ = "integration_operations"
    __table_args__ = (
        UniqueConstraint("institution_id", "operation_key", name="uq_integration_operation_key"),
        UniqueConstraint("proposal_id", name="uq_integration_operation_proposal"),
        Index("ix_integration_operation_status", "institution_id", "status", "created_at"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_connections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_proposals.id", ondelete="RESTRICT"), nullable=False
    )
    operation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    exact_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dependency_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    connection_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_resource_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntegrationAttempt(TimestampedUUIDModel):
    __tablename__ = "integration_attempts"
    __table_args__ = (
        UniqueConstraint("operation_id", "attempt_number", name="uq_integration_attempt_number"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    operation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_operations.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class ProviderResourceMapping(TimestampedUUIDModel):
    __tablename__ = "provider_resource_mappings"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "local_resource_type",
            "local_resource_id",
            name="uq_provider_local_mapping",
        ),
        UniqueConstraint(
            "connection_id",
            "provider_resource_type",
            "provider_resource_id",
            name="uq_provider_remote_mapping",
        ),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    local_resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    local_resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider_resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_resource_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    provider_version: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sync_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="current", nullable=False)


class IntegrationWebhookChannel(TimestampedUUIDModel):
    __tablename__ = "integration_webhook_channels"
    __table_args__ = (UniqueConstraint("channel_id", name="uq_integration_channel_id"),)

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), default="google_calendar", nullable=False)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationWebhookEvent(TimestampedUUIDModel):
    __tablename__ = "integration_webhook_events"
    __table_args__ = (
        UniqueConstraint("channel_id", "message_number", name="uq_integration_webhook_message"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    message_number: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    resource_state: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="received", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
