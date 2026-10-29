"""P04 JD intelligence, clarification, policy, and approval core

Revision ID: p04_jd_intelligence
Revises: stabilize_p01_p03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p04_jd_intelligence"
down_revision: str | None = "stabilize_p01_p03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


P04_TABLES = (
    "jd_interpretation_revisions",
    "jd_review_corrections",
    "clarification_tasks",
    "eligibility_policy_versions",
    "action_proposals",
    "approval_decisions",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "jd_interpretation_revisions",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("source_artifact_id", sa.UUID(), nullable=False),
        sa.Column("text_extraction_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("adapter_id", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("candidate_facts", postgresql.JSONB(), nullable=False),
        sa.Column("reviewed_facts", postgresql.JSONB(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("validation_findings", postgresql.JSONB(), nullable=False),
        sa.Column("usage_metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_artifact_id"], ["source_artifacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["text_extraction_id"], ["text_extractions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drive_id", "revision_number", name="uq_jd_interpretation_drive_revision"),
        sa.CheckConstraint("status IN ('review_ready','failed','superseded')", name="ck_jd_interpretation_status"),
        sa.CheckConstraint("mode IN ('fixture','manual')", name="ck_jd_interpretation_mode"),
    )
    op.create_index("ix_jd_interpretation_institution_drive", "jd_interpretation_revisions", ["institution_id", "drive_id"])
    op.create_index("ix_jd_interpretation_revisions_status", "jd_interpretation_revisions", ["status"])

    op.create_table(
        "jd_review_corrections",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("interpretation_id", sa.UUID(), nullable=False),
        sa.Column("field_path", sa.String(255), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(), nullable=True),
        sa.Column("corrected_value", postgresql.JSONB(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("corrected_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interpretation_id"], ["jd_interpretation_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["corrected_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "clarification_tasks",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("interpretation_id", sa.UUID(), nullable=False),
        sa.Column("field_path", sa.String(255), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.String(100), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("resolution_value", postgresql.JSONB(), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("resolved_by_membership_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interpretation_id"], ["jd_interpretation_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_membership_id"], ["memberships.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('open','resolved','dismissed')", name="ck_clarification_status"),
    )
    op.create_index("ix_clarifications_interpretation_status", "clarification_tasks", ["interpretation_id", "status"])

    op.create_table(
        "eligibility_policy_versions",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("interpretation_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("engine_contract", sa.String(50), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("policy_payload", postgresql.JSONB(), nullable=False),
        sa.Column("human_summary", sa.Text(), nullable=False),
        sa.Column("canonical_hash", sa.String(64), nullable=False),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        sa.Column("approved_proposal_id", sa.UUID(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interpretation_id"], ["jd_interpretation_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drive_id", "version_number", name="uq_policy_drive_version"),
        sa.CheckConstraint("status IN ('draft','in_review','approved','rejected','superseded')", name="ck_policy_status"),
    )
    op.create_index("ix_policy_institution_drive_status", "eligibility_policy_versions", ["institution_id", "drive_id", "status"])
    op.create_index("ix_eligibility_policy_versions_status", "eligibility_policy_versions", ["status"])

    op.create_table(
        "action_proposals",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("dependencies", postgresql.JSONB(), nullable=False),
        sa.Column("canonical_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("requested_by_membership_id", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "action_type", "target_type", "target_id", "revision_number", name="uq_action_proposal_target_revision"),
        sa.CheckConstraint("state IN ('pending_approval','approved','rejected','revision_requested','stale','expired','cancelled')", name="ck_action_proposal_state"),
    )
    op.create_index("ix_action_proposals_institution_state", "action_proposals", ["institution_id", "state"])

    op.create_table(
        "approval_decisions",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("proposal_id", sa.UUID(), nullable=False),
        sa.Column("proposal_hash", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_by_membership_id", sa.UUID(), nullable=False),
        sa.Column("permission_context", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["action_proposals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", name="uq_approval_decision_proposal"),
        sa.CheckConstraint("decision IN ('approved','rejected','revision_requested')", name="ck_approval_decision"),
    )

    for table in P04_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{table}_institution_scope" ON "{table}" '
            "USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) "
            "WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
        )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO placementos_app")


def downgrade() -> None:
    for table in reversed(P04_TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.drop_table(table)
