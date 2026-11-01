"""P11 controlled Google Workspace connectors.

Revision ID: p11_google_connectors
Revises: p09_complete_lifecycle
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p11_google_connectors"
down_revision: str | None = "p09_complete_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

P11_TABLES = (
    "integration_connections",
    "oauth_authorization_states",
    "gmail_source_captures",
    "sheet_import_previews",
    "integration_operations",
    "integration_attempts",
    "provider_resource_mappings",
    "integration_webhook_channels",
    "integration_webhook_events",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.drop_constraint("ck_outbox_event_status", "outbox_events", type_="check")
    op.create_check_constraint(
        "ck_outbox_event_status",
        "outbox_events",
        "status IN ('pending','published','processed','failed')",
    )

    op.create_table(
        "integration_connections",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("owner_membership_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_account_id", sa.String(255), nullable=False),
        sa.Column("external_account_email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("granted_scopes", postgresql.JSONB(), nullable=False),
        sa.Column("access_token_ciphertext", sa.Text(), nullable=False),
        sa.Column("refresh_token_ciphertext", sa.Text(), nullable=True),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connection_revision", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id", "provider", "external_account_id", name="uq_integration_account"
        ),
        sa.CheckConstraint(
            "status IN ('active','expired','disconnected','error')",
            name="ck_integration_connection_status",
        ),
    )
    op.create_index(
        "ix_integration_connections_status",
        "integration_connections",
        ["institution_id", "provider", "status"],
    )

    op.create_table(
        "oauth_authorization_states",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("membership_id", sa.UUID(), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("code_verifier_ciphertext", sa.Text(), nullable=False),
        sa.Column("requested_features", postgresql.JSONB(), nullable=False),
        sa.Column("requested_scopes", postgresql.JSONB(), nullable=False),
        sa.Column("redirect_after", sa.String(512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash", name="uq_oauth_state_hash"),
    )

    op.create_table(
        "gmail_source_captures",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("source_artifact_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.String(255), nullable=False),
        sa.Column("attachment_id", sa.String(255), nullable=True),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("sender", sa.String(512), nullable=True),
        sa.Column("subject", sa.String(998), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_history_id", sa.String(255), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("captured_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_artifact_id"], ["source_artifacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["captured_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id",
            "message_id",
            "attachment_id",
            name="uq_gmail_capture_selection",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index("ix_gmail_capture_drive", "gmail_source_captures", ["institution_id", "drive_id"])

    op.create_table(
        "sheet_import_previews",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("spreadsheet_id", sa.String(255), nullable=False),
        sa.Column("selected_range", sa.String(255), nullable=False),
        sa.Column("mapping", postgresql.JSONB(), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("preview_token", sa.String(255), nullable=False),
        sa.Column("expected_academic_revisions", postgresql.JSONB(), nullable=False),
        sa.Column("report", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('previewed','committing','committed','stale','expired')",
            name="ck_sheet_import_preview_status",
        ),
    )
    op.create_index(
        "ix_sheet_preview_status", "sheet_import_previews", ["institution_id", "status", "expires_at"]
    )

    op.create_table(
        "integration_operations",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("proposal_id", sa.UUID(), nullable=False),
        sa.Column("operation_key", sa.String(255), nullable=False),
        sa.Column("operation_kind", sa.String(64), nullable=False),
        sa.Column("exact_payload", postgresql.JSONB(), nullable=False),
        sa.Column("dependency_fingerprint", sa.String(64), nullable=False),
        sa.Column("connection_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_resource_id", sa.String(1024), nullable=True),
        sa.Column("provider_version", sa.String(1024), nullable=True),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("last_error_detail", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["proposal_id"], ["action_proposals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "operation_key", name="uq_integration_operation_key"),
        sa.UniqueConstraint("proposal_id", name="uq_integration_operation_proposal"),
        sa.CheckConstraint(
            "status IN ('queued','claimed','succeeded','failed','unknown','stale','cancelled')",
            name="ck_integration_operation_status",
        ),
    )
    op.create_index(
        "ix_integration_operation_status", "integration_operations", ["institution_id", "status", "created_at"]
    )

    op.create_table(
        "integration_attempts",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("operation_id", sa.UUID(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_request_id", sa.String(255), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("provider_evidence", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operation_id"], ["integration_operations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation_id", "attempt_number", name="uq_integration_attempt_number"),
    )

    op.create_table(
        "provider_resource_mappings",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("local_resource_type", sa.String(64), nullable=False),
        sa.Column("local_resource_id", sa.UUID(), nullable=False),
        sa.Column("provider_resource_type", sa.String(64), nullable=False),
        sa.Column("provider_resource_id", sa.String(1024), nullable=False),
        sa.Column("provider_version", sa.String(1024), nullable=True),
        sa.Column("sync_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "local_resource_type", "local_resource_id", name="uq_provider_local_mapping"),
        sa.UniqueConstraint("connection_id", "provider_resource_type", "provider_resource_id", name="uq_provider_remote_mapping"),
    )

    op.create_table(
        "integration_webhook_channels",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("channel_id", sa.String(255), nullable=False),
        sa.Column("resource_id", sa.String(1024), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", name="uq_integration_channel_id"),
    )

    op.create_table(
        "integration_webhook_events",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("channel_id", sa.String(255), nullable=False),
        sa.Column("message_number", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(1024), nullable=False),
        sa.Column("resource_state", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "message_number", name="uq_integration_webhook_message"),
    )

    for table in P11_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{table}_institution_scope" ON "{table}" '
            "USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) "
            "WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
        )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO placementos_app")


def downgrade() -> None:
    # P09 has no integration operation consumer and does not recognize `processed`.
    # Remove only P11-owned relay rows before restoring the older status contract.
    op.execute("DELETE FROM outbox_events WHERE aggregate_type = 'integration_operation'")
    for table in reversed(P11_TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.drop_table(table)
    op.drop_constraint("ck_outbox_event_status", "outbox_events", type_="check")
    op.create_check_constraint(
        "ck_outbox_event_status",
        "outbox_events",
        "status IN ('pending','published','failed')",
    )
