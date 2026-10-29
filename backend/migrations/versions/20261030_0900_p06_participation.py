"""P06 documents, publication pointers, readiness, and registrations.

Revision ID: p06_participation
Revises: p05_eligibility
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p06_participation"
down_revision: str | None = "p05_eligibility"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

P06_TABLES = (
    "drive_document_requirements",
    "student_documents",
    "document_revisions",
    "document_validation_runs",
    "registrations",
    "registration_events",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("upload_sessions", sa.Column("student_profile_id", sa.UUID(), nullable=True))
    op.add_column("upload_sessions", sa.Column("document_type", sa.String(32), nullable=True))
    op.create_foreign_key(
        "fk_upload_session_student", "upload_sessions", "student_profiles",
        ["student_profile_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_upload_sessions_student_profile_id", "upload_sessions", ["student_profile_id"])

    op.create_table(
        "drive_document_requirements",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("drive_revision_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("display_label", sa.String(100), nullable=False),
        sa.Column("allowed_extensions", postgresql.JSONB(), nullable=False),
        sa.Column("max_size_bytes", sa.Integer(), nullable=False),
        sa.Column("filename_pattern", sa.String(255), nullable=True),
        sa.Column("required_stage", sa.String(32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_revision_id"], ["drive_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drive_revision_id", "document_type", name="uq_requirement_revision_type"),
        sa.CheckConstraint("document_type IN ('resume','marksheet','college_id')", name="ck_requirement_type"),
        sa.CheckConstraint("required_stage IN ('registration','scheduling')", name="ck_requirement_stage"),
        sa.CheckConstraint("max_size_bytes > 0 AND max_size_bytes <= 10485760", name="ck_requirement_size"),
    )
    op.create_index("ix_requirements_drive_revision", "drive_document_requirements", ["institution_id", "drive_id", "drive_revision_id"])

    op.create_table(
        "student_documents",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("current_revision_id", sa.UUID(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "student_profile_id", "document_type", name="uq_student_document_type"),
        sa.CheckConstraint("document_type IN ('resume','marksheet','college_id')", name="ck_student_document_type"),
    )
    op.create_index("ix_student_documents_owner", "student_documents", ["institution_id", "student_profile_id"])

    op.create_table(
        "document_revisions",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("student_document_id", sa.UUID(), nullable=False),
        sa.Column("upload_session_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("hash_sha256", sa.String(64), nullable=False),
        sa.Column("scan_status", sa.String(32), nullable=False),
        sa.Column("structure_status", sa.String(32), nullable=False),
        sa.Column("text_status", sa.String(32), nullable=False),
        sa.Column("supersedes_revision_id", sa.UUID(), nullable=True),
        sa.Column("uploaded_by_membership_id", sa.UUID(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_document_id"], ["student_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upload_session_id"], ["upload_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["document_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploaded_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_document_id", "revision_number", name="uq_document_revision_number"),
        sa.UniqueConstraint("upload_session_id", name="uq_document_revision_upload_session"),
    )
    op.create_index("ix_document_revisions_owner", "document_revisions", ["institution_id", "student_profile_id"])
    op.create_foreign_key(
        "fk_student_document_current_revision", "student_documents", "document_revisions",
        ["current_revision_id"], ["id"], ondelete="RESTRICT",
    )

    op.create_table(
        "document_validation_runs",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("document_revision_id", sa.UUID(), nullable=False),
        sa.Column("requirement_id", sa.UUID(), nullable=False),
        sa.Column("validator_version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("findings", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_revision_id"], ["document_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requirement_id"], ["drive_document_requirements.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_revision_id", "requirement_id", name="uq_document_validation_dependency"),
        sa.CheckConstraint("status IN ('passed','failed','needs_review')", name="ck_document_validation_status"),
    )
    op.create_index("ix_document_validations_student", "document_validation_runs", ["institution_id", "student_profile_id"])

    op.create_table(
        "registrations",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("drive_id", sa.UUID(), nullable=False),
        sa.Column("student_profile_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("submitted_drive_revision_id", sa.UUID(), nullable=True),
        sa.Column("submitted_policy_id", sa.UUID(), nullable=True),
        sa.Column("submitted_evaluation_run_id", sa.UUID(), nullable=True),
        sa.Column("submitted_eligibility_result_id", sa.UUID(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hold_reason", sa.Text(), nullable=True),
        sa.Column("concurrency_revision", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_drive_revision_id"], ["drive_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_policy_id"], ["eligibility_policy_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_evaluation_run_id"], ["evaluation_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_eligibility_result_id"], ["eligibility_results.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drive_id", "student_profile_id", name="uq_registration_drive_student"),
        sa.CheckConstraint("state IN ('draft','submitted','withdrawn','eligibility_hold')", name="ck_registration_state"),
    )
    op.create_index("ix_registrations_drive_state", "registrations", ["institution_id", "drive_id", "state"])

    op.create_table(
        "registration_events",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("registration_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_membership_id", sa.UUID(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_registration_events_registration", "registration_events", ["registration_id", "created_at"])

    op.add_column("drive_revisions", sa.Column("withdrawal_end_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("drives", sa.Column("published_drive_revision_id", sa.UUID(), nullable=True))
    op.add_column("drives", sa.Column("published_evaluation_run_id", sa.UUID(), nullable=True))
    op.add_column("drives", sa.Column("publication_proposal_id", sa.UUID(), nullable=True))
    op.add_column("drives", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_drive_published_revision", "drives", "drive_revisions", ["published_drive_revision_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_drive_published_evaluation", "drives", "evaluation_runs", ["published_evaluation_run_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_drive_publication_proposal", "drives", "action_proposals", ["publication_proposal_id"], ["id"], ondelete="RESTRICT")

    for table in P06_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{table}_institution_scope" ON "{table}" '
            "USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) "
            "WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
        )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO placementos_app")


def downgrade() -> None:
    for name in ("fk_drive_publication_proposal", "fk_drive_published_evaluation", "fk_drive_published_revision"):
        op.drop_constraint(name, "drives", type_="foreignkey")
    for column in ("published_at", "publication_proposal_id", "published_evaluation_run_id", "published_drive_revision_id"):
        op.drop_column("drives", column)
    op.drop_column("drive_revisions", "withdrawal_end_at")
    op.drop_constraint(
        "fk_student_document_current_revision", "student_documents", type_="foreignkey"
    )
    for table in reversed(P06_TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.drop_table(table)
    op.drop_index("ix_upload_sessions_student_profile_id", table_name="upload_sessions")
    op.drop_constraint("fk_upload_session_student", "upload_sessions", type_="foreignkey")
    op.drop_column("upload_sessions", "document_type")
    op.drop_column("upload_sessions", "student_profile_id")
