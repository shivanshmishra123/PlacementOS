"""P09 complete recruitment lifecycle.

Revision ID: p09_complete_lifecycle
Revises: p08_durable_workflows
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p09_complete_lifecycle"
down_revision: str | None = "p08_durable_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "recruitment_rounds",
    "recruitment_sessions",
    "session_revisions",
    "session_assignments",
    "attendance_revisions",
    "outcome_revisions",
    "outcome_gap_acknowledgements",
    "drive_report_revisions",
    "report_export_grants",
)


def cols() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def scoped() -> list[sa.Column]:
    return [
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
    ]


def common_fks() -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
    ]


def upgrade() -> None:
    op.add_column(
        "drives", sa.Column("registration_closed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("drives", sa.Column("latest_report_revision_id", sa.UUID(), nullable=True))
    op.add_column("drives", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("drives", sa.Column("closed_by_membership_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_drives_closed_by",
        "drives",
        "memberships",
        ["closed_by_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "recruitment_rounds",
        *scoped(),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("round_type", sa.String(50), nullable=False),
        sa.Column("requires_previous_round_outcome", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drive_id", "sequence_number", name="uq_round_drive_sequence"),
        sa.CheckConstraint("sequence_number > 0", name="ck_round_sequence_positive"),
        sa.CheckConstraint("status IN ('active','cancelled')", name="ck_round_status"),
    )
    op.create_index(
        "ix_rounds_drive_sequence",
        "recruitment_rounds",
        ["institution_id", "drive_id", "sequence_number"],
    )

    op.create_table(
        "recruitment_sessions",
        *scoped(),
        sa.Column("round_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_revision_id", sa.UUID(), nullable=True),
        sa.Column("published_revision_id", sa.UUID(), nullable=True),
        sa.Column("concurrency_revision", sa.Integer(), nullable=False),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(["round_id"], ["recruitment_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('draft','published','completed','cancelled')", name="ck_session_status"
        ),
    )
    op.create_index(
        "ix_sessions_drive_status", "recruitment_sessions", ["institution_id", "drive_id", "status"]
    )

    op.create_table(
        "session_revisions",
        *scoped(),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("round_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("venue", sa.String(255), nullable=True),
        sa.Column("meeting_url", sa.String(1000), nullable=True),
        sa.Column("panel_members", postgresql.JSONB(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("supersedes_revision_id", sa.UUID(), nullable=True),
        sa.Column("published_proposal_id", sa.UUID(), nullable=True),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(["session_id"], ["recruitment_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["round_id"], ["recruitment_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"], ["session_revisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["published_proposal_id"], ["action_proposals.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "revision_number", name="uq_session_revision_number"),
        sa.CheckConstraint("end_at > start_at", name="ck_session_revision_interval"),
        sa.CheckConstraint(
            "capacity > 0 AND buffer_minutes >= 0", name="ck_session_revision_limits"
        ),
    )
    op.create_index(
        "ix_session_revisions_drive_start",
        "session_revisions",
        ["institution_id", "drive_id", "start_at"],
    )

    op.create_table(
        "session_assignments",
        *scoped(),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("session_revision_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("registration_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("document_override_reason", sa.Text(), nullable=True),
        sa.Column("assigned_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(["session_id"], ["recruitment_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_revision_id"], ["session_revisions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["assigned_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_revision_id", "student_profile_id", name="uq_session_revision_student"
        ),
        sa.CheckConstraint(
            "status IN ('draft','published','cancelled')", name="ck_assignment_status"
        ),
    )
    op.create_index(
        "ix_session_assignments_student",
        "session_assignments",
        ["institution_id", "student_profile_id", "status"],
    )

    op.create_table(
        "attendance_revisions",
        *scoped(),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(["session_id"], ["recruitment_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "student_profile_id", "revision_number", name="uq_attendance_revision"
        ),
        sa.CheckConstraint("status IN ('present','absent','excused')", name="ck_attendance_status"),
    )
    op.create_index(
        "ix_attendance_session_student",
        "attendance_revisions",
        ["session_id", "student_profile_id", "revision_number"],
    )

    op.create_table(
        "outcome_revisions",
        *scoped(),
        sa.Column("round_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column("source_evidence", postgresql.JSONB(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("offer_status", sa.String(32), nullable=False),
        sa.Column("acceptance_status", sa.String(32), nullable=False),
        sa.Column("joining_status", sa.String(32), nullable=False),
        sa.Column("supersedes_revision_id", sa.UUID(), nullable=True),
        sa.Column("published_proposal_id", sa.UUID(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(["round_id"], ["recruitment_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"], ["outcome_revisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["published_proposal_id"], ["action_proposals.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "round_id", "student_profile_id", "revision_number", name="uq_outcome_revision"
        ),
        sa.CheckConstraint(
            "outcome IN ('pending','advanced','rejected','waitlisted','selected','withdrawn')",
            name="ck_outcome_value",
        ),
        sa.CheckConstraint("offer_status IN ('not_recorded','issued')", name="ck_offer_status"),
        sa.CheckConstraint(
            "acceptance_status IN ('not_recorded','accepted','declined')",
            name="ck_acceptance_status",
        ),
        sa.CheckConstraint(
            "joining_status IN ('not_recorded','joined','not_joined','deferred')",
            name="ck_joining_status",
        ),
    )
    op.create_index(
        "ix_outcomes_drive_round_student",
        "outcome_revisions",
        ["institution_id", "drive_id", "round_id", "student_profile_id"],
    )

    op.create_table(
        "outcome_gap_acknowledgements",
        *scoped(),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("acknowledged_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(["session_id"], ["recruitment_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "student_profile_id", name="uq_outcome_gap_session_student"
        ),
    )

    op.create_table(
        "drive_report_revisions",
        *scoped(),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("report_kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("snapshot_payload", postgresql.JSONB(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("supersedes_report_id", sa.UUID(), nullable=True),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(
            ["supersedes_report_id"], ["drive_report_revisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drive_id", "revision_number", name="uq_drive_report_revision"),
        sa.CheckConstraint(
            "report_kind IN ('operational','closure','reopen','cancellation')",
            name="ck_report_kind",
        ),
        sa.CheckConstraint("status IN ('frozen','superseded')", name="ck_report_status"),
    )
    op.create_index(
        "ix_drive_reports_drive_revision",
        "drive_report_revisions",
        ["institution_id", "drive_id", "revision_number"],
    )

    op.create_table(
        "report_export_grants",
        *scoped(),
        sa.Column("report_revision_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *cols(),
        *common_fks(),
        sa.ForeignKeyConstraint(
            ["report_revision_id"], ["drive_report_revisions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_report_export_token_hash"),
    )
    op.create_index(
        "ix_report_exports_expiry", "report_export_grants", ["institution_id", "expires_at"]
    )

    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f"CREATE POLICY \"{table}_institution_scope\" ON \"{table}\" USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
        )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO placementos_app"
    )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.drop_table(table)
    op.drop_constraint("fk_drives_closed_by", "drives", type_="foreignkey")
    for column in (
        "closed_by_membership_id",
        "completed_at",
        "latest_report_revision_id",
        "registration_closed_at",
    ):
        op.drop_column("drives", column)
