"""P07 immutable communications, transactional outbox, and safe dispatch.

Revision ID: p07_safe_dispatch
Revises: p06_participation
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p07_safe_dispatch"
down_revision: str | None = "p06_participation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

P07_TABLES = (
    "communication_drafts",
    "audience_snapshots",
    "audience_recipients",
    "dispatch_batches",
    "dispatch_operations",
    "dispatch_attempts",
    "outbox_events",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column(
        "action_proposals",
        sa.Column("earliest_execution_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "action_proposals",
        sa.Column("execution_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "action_proposals",
        sa.Column(
            "execution_bounds",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "action_proposals", sa.Column("sender_connection_revision", sa.String(100), nullable=True)
    )

    op.create_table(
        "communication_drafts",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("communication_kind", sa.String(50), nullable=False),
        sa.Column("audience_type", sa.String(50), nullable=False),
        sa.Column("template_version", sa.String(50), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("sender_email", sa.String(255), nullable=False),
        sa.Column("reply_to", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("supersedes_draft_id", sa.UUID(), nullable=True),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["supersedes_draft_id"], ["communication_drafts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "drive_id",
            "communication_kind",
            "revision_number",
            name="uq_communication_draft_revision",
        ),
        sa.CheckConstraint(
            "communication_kind IN ('drive_announcement','missing_document_reminder','registration_deadline_reminder','interview_schedule','schedule_correction','result_notice','clarification')",
            name="ck_communication_kind",
        ),
        sa.CheckConstraint(
            "audience_type IN ('current_eligible','submitted_registrants','required_document_findings','explicit_recipients','session_participants')",
            name="ck_communication_audience_type",
        ),
        sa.CheckConstraint(
            "state IN ('draft','in_review','approved','rejected','revision_requested','stale','cancelled')",
            name="ck_communication_draft_state",
        ),
    )
    op.create_index(
        "ix_communication_drafts_drive_state",
        "communication_drafts",
        ["institution_id", "drive_id", "state"],
    )

    op.create_table(
        "audience_snapshots",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("communication_draft_id", sa.UUID(), nullable=False),
        sa.Column("audience_type", sa.String(50), nullable=False),
        sa.Column("query_spec", postgresql.JSONB(), nullable=False),
        sa.Column("included_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("unresolved_count", sa.Integer(), nullable=False),
        sa.Column("exclusion_summary", postgresql.JSONB(), nullable=False),
        sa.Column("canonical_hash", sa.String(64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["communication_draft_id"], ["communication_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("communication_draft_id", name="uq_audience_snapshot_draft"),
    )

    op.create_table(
        "audience_recipients",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("audience_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("normalized_email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("inclusion_reason", sa.String(255), nullable=False),
        sa.Column("contact_revision", sa.String(100), nullable=False),
        sa.Column("merge_data", postgresql.JSONB(), nullable=False),
        sa.Column("rendered_subject", sa.String(500), nullable=False),
        sa.Column("rendered_body", sa.Text(), nullable=False),
        sa.Column("rendered_hash", sa.String(64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["audience_snapshot_id"], ["audience_snapshots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "audience_snapshot_id", "normalized_email", name="uq_audience_recipient_email"
        ),
    )
    op.create_index(
        "ix_audience_recipient_student",
        "audience_recipients",
        ["institution_id", "student_profile_id"],
    )

    op.create_table(
        "dispatch_batches",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("proposal_id", sa.UUID(), nullable=False),
        sa.Column("communication_draft_id", sa.UUID(), nullable=False),
        sa.Column("audience_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("pending_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("delivered_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("unknown_count", sa.Integer(), nullable=False),
        sa.Column("cancelled_count", sa.Integer(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_expires_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["action_proposals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["communication_draft_id"], ["communication_drafts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["audience_snapshot_id"], ["audience_snapshots.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_dispatch_batch_proposal"),
        sa.CheckConstraint(
            "status IN ('queued','processing','completed','partial','cancelled','stale')",
            name="ck_dispatch_batch_status",
        ),
    )
    op.create_index(
        "ix_dispatch_batches_drive_status",
        "dispatch_batches",
        ["institution_id", "drive_id", "status"],
    )

    op.create_table(
        "dispatch_operations",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("dispatch_batch_id", sa.UUID(), nullable=False),
        sa.Column("audience_recipient_id", sa.UUID(), nullable=False),
        sa.Column("operation_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        sa.Column("last_error_detail", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dispatch_batch_id"], ["dispatch_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["audience_recipient_id"], ["audience_recipients.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "operation_key", name="uq_dispatch_operation_key"),
        sa.UniqueConstraint(
            "dispatch_batch_id", "audience_recipient_id", name="uq_dispatch_batch_recipient"
        ),
        sa.CheckConstraint(
            "status IN ('pending','claimed','provider_accepted','delivered','failed','unknown','cancelled','stale')",
            name="ck_dispatch_operation_status",
        ),
    )
    op.create_index(
        "ix_dispatch_operations_batch_status",
        "dispatch_operations",
        ["dispatch_batch_id", "status"],
    )

    op.create_table(
        "dispatch_attempts",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("dispatch_operation_id", sa.UUID(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("adapter_id", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("provider_evidence", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["dispatch_operation_id"], ["dispatch_operations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dispatch_operation_id", "attempt_number", name="uq_dispatch_attempt_number"
        ),
    )
    op.create_index(
        "ix_dispatch_attempts_operation",
        "dispatch_attempts",
        ["dispatch_operation_id", "attempt_number"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("event_key", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("publish_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "event_key", name="uq_outbox_event_key"),
        sa.CheckConstraint(
            "status IN ('pending','published','failed')", name="ck_outbox_event_status"
        ),
    )
    op.create_index("ix_outbox_events_status_due", "outbox_events", ["status", "next_attempt_at"])

    for table in P07_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{table}_institution_scope" ON "{table}" '
            "USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) "
            "WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
        )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO placementos_app"
    )


def downgrade() -> None:
    for table in reversed(P07_TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.drop_table(table)
    for column in (
        "sender_connection_revision",
        "execution_bounds",
        "execution_expires_at",
        "earliest_execution_at",
    ):
        op.drop_column("action_proposals", column)
