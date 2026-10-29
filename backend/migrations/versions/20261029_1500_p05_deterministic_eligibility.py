"""P05 deterministic eligibility evaluations and frozen cohorts

Revision ID: p05_eligibility
Revises: p04_jd_intelligence
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p05_eligibility"
down_revision: str | None = "p04_jd_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

P05_TABLES = (
    "evaluation_runs",
    "evaluation_cohort_members",
    "eligibility_results",
    "eligibility_review_requests",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    # Composite keys make tenant ownership part of every P05 relationship (INV-06).
    op.create_unique_constraint(
        "uq_policy_id_institution",
        "eligibility_policy_versions",
        ["id", "institution_id"],
    )
    op.create_unique_constraint(
        "uq_academic_revision_id_institution",
        "academic_record_revisions",
        ["id", "institution_id"],
    )
    op.create_table(
        "evaluation_runs",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("policy_id", sa.UUID(), nullable=False),
        sa.Column("policy_hash", sa.String(64), nullable=False),
        sa.Column("engine_version", sa.String(50), nullable=False),
        sa.Column("normalization_version", sa.String(100), nullable=False),
        sa.Column("cohort_fingerprint", sa.String(64), nullable=False),
        sa.Column("run_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("is_stale", sa.Boolean(), nullable=False),
        sa.Column("stale_reason", sa.String(255), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("eligible_count", sa.Integer(), nullable=False),
        sa.Column("ineligible_count", sa.Integer(), nullable=False),
        sa.Column("needs_review_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["eligibility_policy_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["drive_id", "institution_id"], ["drives.id", "drives.institution_id"], ondelete="CASCADE", name="fk_evaluation_run_drive_scope"),
        sa.ForeignKeyConstraint(["policy_id", "institution_id"], ["eligibility_policy_versions.id", "eligibility_policy_versions.institution_id"], ondelete="RESTRICT", name="fk_evaluation_run_policy_scope"),
        sa.ForeignKeyConstraint(["created_by_membership_id", "institution_id"], ["memberships.id", "memberships.institution_id"], ondelete="RESTRICT", name="fk_evaluation_run_creator_scope"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "run_fingerprint", name="uq_evaluation_run_fingerprint"),
        sa.UniqueConstraint("id", "institution_id", name="uq_evaluation_run_id_institution"),
        sa.CheckConstraint("status IN ('queued','processing','completed','failed','cancelled')", name="ck_evaluation_run_status"),
        sa.CheckConstraint("total_count >= 0 AND eligible_count >= 0 AND ineligible_count >= 0 AND needs_review_count >= 0", name="ck_evaluation_counts_nonnegative"),
    )
    op.create_index("ix_evaluation_runs_drive_created", "evaluation_runs", ["institution_id", "drive_id", "created_at"])
    op.create_index("ix_evaluation_runs_status", "evaluation_runs", ["institution_id", "status"])

    op.create_table(
        "evaluation_cohort_members",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("evaluation_run_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("membership_id", sa.UUID(), nullable=True),
        sa.Column("academic_revision_id", sa.UUID(), nullable=True),
        sa.Column("member_fingerprint", sa.String(64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["academic_revision_id"], ["academic_record_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluation_run_id", "institution_id"], ["evaluation_runs.id", "evaluation_runs.institution_id"], ondelete="CASCADE", name="fk_evaluation_member_run_scope"),
        sa.ForeignKeyConstraint(["student_profile_id", "institution_id"], ["student_profiles.id", "student_profiles.institution_id"], ondelete="RESTRICT", name="fk_evaluation_member_student_scope"),
        sa.ForeignKeyConstraint(["membership_id", "institution_id"], ["memberships.id", "memberships.institution_id"], ondelete="RESTRICT", name="fk_evaluation_member_membership_scope"),
        sa.ForeignKeyConstraint(["academic_revision_id", "institution_id"], ["academic_record_revisions.id", "academic_record_revisions.institution_id"], ondelete="RESTRICT", name="fk_evaluation_member_academic_scope"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_run_id", "student_profile_id", name="uq_evaluation_member_student"),
        sa.UniqueConstraint("id", "institution_id", name="uq_evaluation_member_id_institution"),
    )
    op.create_index("ix_evaluation_members_student", "evaluation_cohort_members", ["institution_id", "student_profile_id"])

    op.create_table(
        "eligibility_results",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("evaluation_run_id", sa.UUID(), nullable=False),
        sa.Column("cohort_member_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("academic_revision_id", sa.UUID(), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("predicate_results", postgresql.JSONB(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(), nullable=False),
        sa.Column("facts_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("student_explanation", sa.Text(), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_member_id"], ["evaluation_cohort_members.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["academic_revision_id"], ["academic_record_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluation_run_id", "institution_id"], ["evaluation_runs.id", "evaluation_runs.institution_id"], ondelete="CASCADE", name="fk_eligibility_result_run_scope"),
        sa.ForeignKeyConstraint(["cohort_member_id", "institution_id"], ["evaluation_cohort_members.id", "evaluation_cohort_members.institution_id"], ondelete="RESTRICT", name="fk_eligibility_result_member_scope"),
        sa.ForeignKeyConstraint(["student_profile_id", "institution_id"], ["student_profiles.id", "student_profiles.institution_id"], ondelete="RESTRICT", name="fk_eligibility_result_student_scope"),
        sa.ForeignKeyConstraint(["academic_revision_id", "institution_id"], ["academic_record_revisions.id", "academic_record_revisions.institution_id"], ondelete="RESTRICT", name="fk_eligibility_result_academic_scope"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_run_id", "student_profile_id", name="uq_eligibility_result_student"),
        sa.UniqueConstraint("id", "institution_id", name="uq_eligibility_result_id_institution"),
        sa.CheckConstraint("outcome IN ('eligible','ineligible','needs_review')", name="ck_eligibility_result_outcome"),
    )
    op.create_index("ix_eligibility_results_run_outcome", "eligibility_results", ["evaluation_run_id", "outcome"])
    op.create_index("ix_eligibility_results_student", "eligibility_results", ["institution_id", "student_profile_id"])

    op.create_table(
        "eligibility_review_requests",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("eligibility_result_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["eligibility_result_id"], ["eligibility_results.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["drive_id", "institution_id"], ["drives.id", "drives.institution_id"], ondelete="CASCADE", name="fk_eligibility_review_drive_scope"),
        sa.ForeignKeyConstraint(["eligibility_result_id", "institution_id"], ["eligibility_results.id", "eligibility_results.institution_id"], ondelete="RESTRICT", name="fk_eligibility_review_result_scope"),
        sa.ForeignKeyConstraint(["student_profile_id", "institution_id"], ["student_profiles.id", "student_profiles.institution_id"], ondelete="RESTRICT", name="fk_eligibility_review_student_scope"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eligibility_result_id", "student_profile_id", "status", name="uq_open_result_review_request"),
        sa.CheckConstraint("status IN ('open','resolved','dismissed')", name="ck_eligibility_review_status"),
    )
    op.create_index("ix_eligibility_review_drive_status", "eligibility_review_requests", ["institution_id", "drive_id", "status"])

    for table in P05_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{table}_institution_scope" ON "{table}" '
            "USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) "
            "WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
        )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO placementos_app")


def downgrade() -> None:
    for table in reversed(P05_TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.drop_table(table)
    op.drop_constraint(
        "uq_academic_revision_id_institution",
        "academic_record_revisions",
        type_="unique",
    )
    op.drop_constraint(
        "uq_policy_id_institution",
        "eligibility_policy_versions",
        type_="unique",
    )
