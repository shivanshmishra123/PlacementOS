"""P08 durable workflow runs, commands, events, cases, and checkpoint boundary.

Revision ID: p08_durable_workflows
Revises: p07_safe_dispatch
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p08_durable_workflows"
down_revision: str | None = "p07_safe_dispatch"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

P08_TABLES = ("workflow_runs", "workflow_commands", "workflow_events", "exception_cases")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'placementos_workflow') THEN
            CREATE ROLE placementos_workflow LOGIN PASSWORD 'placementos_workflow_dev_password'
              NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
          END IF;
        END $$
        """
    )
    database_name = op.get_bind().execute(sa.text("SELECT current_database()"))
    escaped_database_name = database_name.scalar_one().replace('"', '""')
    op.execute(f'GRANT CONNECT ON DATABASE "{escaped_database_name}" TO placementos_workflow')
    op.execute("CREATE SCHEMA IF NOT EXISTS workflow_checkpoints AUTHORIZATION placementos_workflow")
    op.execute("REVOKE ALL ON SCHEMA workflow_checkpoints FROM PUBLIC")

    op.create_table(
        "workflow_runs",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("graph_version", sa.String(50), nullable=False),
        sa.Column("state_schema_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("current_step", sa.String(50), nullable=False),
        sa.Column("state_references", postgresql.JSONB(), nullable=False),
        sa.Column("pending_proposal_id", sa.UUID(), nullable=True),
        sa.Column("pending_clarification_id", sa.UUID(), nullable=True),
        sa.Column("pending_case_id", sa.UUID(), nullable=True),
        sa.Column("last_event_id", sa.UUID(), nullable=True),
        sa.Column("last_processed_command_id", sa.UUID(), nullable=True),
        sa.Column("error_category", sa.String(100), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("concurrency_revision", sa.Integer(), nullable=False),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", name="uq_workflow_run_thread"),
        sa.CheckConstraint(
            "status IN ('queued','running','waiting_clarification','waiting_policy_approval','waiting_publication_approval','waiting_communication_approval','waiting_input','monitoring','held','failed','completed','cancelled','incompatible')",
            name="ck_workflow_run_status",
        ),
    )
    op.create_index("ix_workflow_runs_drive_status", "workflow_runs", ["institution_id", "drive_id", "status"])

    op.create_table(
        "workflow_commands",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("workflow_run_id", sa.UUID(), nullable=False),
        sa.Column("command_key", sa.String(255), nullable=False),
        sa.Column("command_type", sa.String(50), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("expected_run_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("publish_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("requested_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "command_key", name="uq_workflow_command_key"),
        sa.CheckConstraint("status IN ('pending','published','claimed','processed','failed','cancelled')", name="ck_workflow_command_status"),
    )
    op.create_index("ix_workflow_commands_status_due", "workflow_commands", ["institution_id", "status", "next_attempt_at"])

    op.create_table(
        "workflow_events",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("workflow_run_id", sa.UUID(), nullable=False),
        sa.Column("event_key", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=False),
        sa.Column("resource_revision", sa.String(100), nullable=True),
        sa.Column("event_payload", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_result", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "event_key", name="uq_workflow_event_key"),
        sa.CheckConstraint("status IN ('pending','processed','ignored','failed')", name="ck_workflow_event_status"),
    )
    op.create_index("ix_workflow_events_run_created", "workflow_events", ["workflow_run_id", "created_at"])

    op.create_table(
        "exception_cases",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("workflow_run_id", sa.UUID(), nullable=True),
        sa.Column("case_key", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("affected_resources", postgresql.JSONB(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("proposed_next_action", sa.Text(), nullable=False),
        sa.Column("owner_membership_id", sa.UUID(), nullable=True),
        sa.Column("resolution_history", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_membership_id"], ["memberships.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "case_key", name="uq_exception_case_key"),
        sa.CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_exception_case_severity"),
        sa.CheckConstraint("status IN ('open','acknowledged','resolved','dismissed')", name="ck_exception_case_status"),
    )
    op.create_index("ix_exception_cases_drive_status", "exception_cases", ["institution_id", "drive_id", "status"])

    for table in P08_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{table}_institution_scope" ON "{table}" '
            "USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) "
            "WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
        )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO placementos_app")


def downgrade() -> None:
    for table in reversed(P08_TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.drop_table(table)
    op.execute("DROP SCHEMA IF EXISTS workflow_checkpoints CASCADE")
    database_name = op.get_bind().execute(sa.text("SELECT current_database()"))
    escaped_database_name = database_name.scalar_one().replace('"', '""')
    op.execute(f'REVOKE CONNECT ON DATABASE "{escaped_database_name}" FROM placementos_workflow')
    # The role is cluster-scoped infrastructure and may still own checkpoint schemas
    # in another database. A database-local downgrade must not drop it globally.
