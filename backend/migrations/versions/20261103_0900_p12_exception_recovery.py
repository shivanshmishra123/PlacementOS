"""P12 structured exception recovery.

Revision ID: p12_exception_recovery
Revises: p11_google_connectors
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p12_exception_recovery"
down_revision: str | None = "p11_google_connectors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

P12_TABLES = (
    "exception_impact_analyses",
    "recovery_plans",
    "recovery_plan_steps",
    "recovery_executions",
    "recovery_step_attempts",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "exception_impact_analyses",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_references", postgresql.JSONB(), nullable=False),
        sa.Column("dependency_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("dependency_fingerprint", sa.String(64), nullable=False),
        sa.Column("impact_summary", postgresql.JSONB(), nullable=False),
        sa.Column("affected_students", postgresql.JSONB(), nullable=False),
        sa.Column("affected_resources", postgresql.JSONB(), nullable=False),
        sa.Column("manual_fallback", sa.Text(), nullable=False),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["exception_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "revision_number", name="uq_exception_impact_revision"),
        sa.CheckConstraint(
            "category IN ('criteria_change','academic_correction','deadline_schedule_change','notification_failure')",
            name="ck_exception_impact_category",
        ),
        sa.CheckConstraint(
            "status IN ('current','superseded','stale')", name="ck_exception_impact_status"
        ),
    )
    op.create_index(
        "ix_exception_impact_case_status",
        "exception_impact_analyses",
        ["institution_id", "case_id", "status"],
    )

    op.create_table(
        "recovery_plans",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("proposal_id", sa.UUID(), nullable=True),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("planner_mode", sa.String(32), nullable=False),
        sa.Column("planner_id", sa.String(100), nullable=False),
        sa.Column("planner_version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("canonical_hash", sa.String(64), nullable=False),
        sa.Column("dependency_fingerprint", sa.String(64), nullable=False),
        sa.Column("usage_metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["exception_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["exception_impact_analyses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["proposal_id"], ["action_proposals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "revision_number", name="uq_recovery_plan_revision"),
        sa.CheckConstraint("planner_mode IN ('fixture','manual')", name="ck_recovery_plan_mode"),
        sa.CheckConstraint(
            "status IN ('draft','pending_approval','approved','rejected','revision_requested','stale','queued','executing','partial','succeeded','failed','cancelled')",
            name="ck_recovery_plan_status",
        ),
    )
    op.create_index(
        "ix_recovery_plan_case_status",
        "recovery_plans",
        ["institution_id", "case_id", "status"],
    )

    op.create_table(
        "recovery_plan_steps",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("operation_key", sa.String(255), nullable=False),
        sa.Column("operation_type", sa.String(64), nullable=False),
        sa.Column("exact_payload", postgresql.JSONB(), nullable=False),
        sa.Column("preconditions", postgresql.JSONB(), nullable=False),
        sa.Column("dependencies", postgresql.JSONB(), nullable=False),
        sa.Column("expected_effects", postgresql.JSONB(), nullable=False),
        sa.Column("approval_type", sa.String(64), nullable=False),
        sa.Column("irreversible_effects", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["recovery_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "step_number", name="uq_recovery_plan_step_number"),
        sa.UniqueConstraint(
            "institution_id", "operation_key", name="uq_recovery_step_operation_key"
        ),
        sa.CheckConstraint(
            "operation_type IN ('place_drive_hold','stale_pending_proposals','prepare_correction_draft','mark_external_reconciliation','record_manual_followup')",
            name="ck_recovery_step_operation_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','completed','failed','stale','skipped','cancelled')",
            name="ck_recovery_step_status",
        ),
    )
    op.create_index("ix_recovery_steps_plan_status", "recovery_plan_steps", ["plan_id", "status"])

    op.create_table(
        "recovery_executions",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("proposal_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_step_number", sa.Integer(), nullable=True),
        sa.Column("completed_step_count", sa.Integer(), nullable=False),
        sa.Column("pending_step_count", sa.Integer(), nullable=False),
        sa.Column("failed_step_count", sa.Integer(), nullable=False),
        sa.Column("irreversible_step_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(100), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["exception_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["recovery_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["proposal_id"], ["action_proposals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", name="uq_recovery_execution_plan"),
        sa.CheckConstraint(
            "status IN ('queued','executing','partial','succeeded','failed','stale','cancelled')",
            name="ck_recovery_execution_status",
        ),
    )
    op.create_index(
        "ix_recovery_execution_status",
        "recovery_executions",
        ["institution_id", "status", "created_at"],
    )

    op.create_table(
        "recovery_step_attempts",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("step_id", sa.UUID(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["recovery_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["recovery_plan_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("step_id", "attempt_number", name="uq_recovery_step_attempt"),
    )
    op.create_index(
        "ix_recovery_attempt_step", "recovery_step_attempts", ["step_id", "attempt_number"]
    )

    for table in P12_TABLES:
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
    op.execute("DELETE FROM outbox_events WHERE aggregate_type = 'recovery_execution'")
    for table in reversed(P12_TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.drop_table(table)
