"""stabilize P01-P03 authorization, integrity, and row-scope boundaries

Revision ID: stabilize_p01_p03
Revises: 1eec380a58a7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "stabilize_p01_p03"
down_revision: str | None = "1eec380a58a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCOPED_TABLES = (
    "audit_logs",
    "student_profiles",
    "academic_record_revisions",
    "student_correction_proposals",
    "companies",
    "drives",
    "drive_revisions",
    "upload_sessions",
    "source_artifacts",
    "text_extractions",
    "domain_jobs",
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'placementos_app') THEN
                CREATE ROLE placementos_app LOGIN PASSWORD 'placementos_app_dev_password'
                    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
            END IF;
        END
        $$
        """
    )
    op.execute("GRANT CONNECT ON DATABASE placementos TO placementos_app")
    op.execute("GRANT USAGE ON SCHEMA public TO placementos_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO placementos_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO placementos_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE placementos IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO placementos_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE placementos IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO placementos_app"
    )

    # Normalize legacy P02/P03 prototype values before enforcing canonical state contracts.
    op.execute("UPDATE drives SET status = 'published' WHERE status = 'active'")
    op.execute("UPDATE drives SET status = 'draft', operational_hold = true WHERE status = 'on_hold'")
    op.execute("UPDATE upload_sessions SET status = 'completed' WHERE status IN ('uploaded', 'accepted')")
    op.execute("UPDATE source_artifacts SET scan_status = 'development_fixture' WHERE scan_status = 'skipped'")
    op.execute("UPDATE domain_jobs SET status = 'failed_terminal' WHERE status = 'failed'")

    op.create_check_constraint(
        "ck_drives_status",
        "drives",
        "status IN ('draft','published','registration_closed','in_progress','completed','archived','cancelled')",
    )
    op.create_check_constraint(
        "ck_upload_sessions_status",
        "upload_sessions",
        "status IN ('pending','validating','completed','rejected','expired')",
    )
    op.create_check_constraint(
        "ck_source_acceptance_status",
        "source_artifacts",
        "acceptance_status IN ('quarantined','validating','accepted','rejected')",
    )
    op.create_check_constraint(
        "ck_source_scan_status",
        "source_artifacts",
        "scan_status IN ('pending','clean','infected','suspicious','unavailable','development_fixture')",
    )
    op.create_check_constraint(
        "ck_domain_jobs_status",
        "domain_jobs",
        "status IN ('queued','processing','completed','failed_retryable','failed_terminal','cancelled')",
    )
    op.create_unique_constraint("uq_companies_id_institution", "companies", ["id", "institution_id"])
    op.create_unique_constraint("uq_drives_id_institution", "drives", ["id", "institution_id"])
    op.create_unique_constraint("uq_memberships_id_institution", "memberships", ["id", "institution_id"])
    op.create_unique_constraint(
        "uq_student_profiles_id_institution", "student_profiles", ["id", "institution_id"]
    )
    op.create_unique_constraint(
        "uq_source_artifacts_id_institution", "source_artifacts", ["id", "institution_id"]
    )
    op.create_foreign_key(
        "fk_drives_company_same_institution",
        "drives",
        "companies",
        ["company_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_drive_revisions_drive_same_institution",
        "drive_revisions",
        "drives",
        ["drive_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_drives_creator_same_institution",
        "drives",
        "memberships",
        ["created_by_membership_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_drives_assignee_same_institution",
        "drives",
        "memberships",
        ["assigned_coordinator_membership_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_drive_assignments_membership_same_institution",
        "drive_assignments",
        "memberships",
        ["membership_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_drive_assignments_drive_same_institution",
        "drive_assignments",
        "drives",
        ["drive_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_academic_student_same_institution",
        "academic_record_revisions",
        "student_profiles",
        ["student_profile_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_corrections_student_same_institution",
        "student_correction_proposals",
        "student_profiles",
        ["student_profile_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_upload_owner_same_institution",
        "upload_sessions",
        "memberships",
        ["owner_membership_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_upload_drive_same_institution",
        "upload_sessions",
        "drives",
        ["drive_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_source_creator_same_institution",
        "source_artifacts",
        "memberships",
        ["created_by_membership_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_sources_drive_same_institution",
        "source_artifacts",
        "drives",
        ["drive_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_extractions_source_same_institution",
        "text_extractions",
        "source_artifacts",
        ["source_artifact_id", "institution_id"],
        ["id", "institution_id"],
        ondelete="CASCADE",
    )

    for table in SCOPED_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f'CREATE POLICY "{table}_institution_scope" ON "{table}" '
            "USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) "
            "WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
        )


def downgrade() -> None:
    for table in reversed(SCOPED_TABLES):
        op.execute(f'DROP POLICY IF EXISTS "{table}_institution_scope" ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    op.drop_constraint("fk_extractions_source_same_institution", "text_extractions", type_="foreignkey")
    op.drop_constraint("fk_source_creator_same_institution", "source_artifacts", type_="foreignkey")
    op.drop_constraint("fk_upload_drive_same_institution", "upload_sessions", type_="foreignkey")
    op.drop_constraint("fk_upload_owner_same_institution", "upload_sessions", type_="foreignkey")
    op.drop_constraint("fk_corrections_student_same_institution", "student_correction_proposals", type_="foreignkey")
    op.drop_constraint("fk_academic_student_same_institution", "academic_record_revisions", type_="foreignkey")
    op.drop_constraint("fk_drive_assignments_drive_same_institution", "drive_assignments", type_="foreignkey")
    op.drop_constraint("fk_drive_assignments_membership_same_institution", "drive_assignments", type_="foreignkey")
    op.drop_constraint("fk_drives_assignee_same_institution", "drives", type_="foreignkey")
    op.drop_constraint("fk_drives_creator_same_institution", "drives", type_="foreignkey")
    op.drop_constraint("fk_sources_drive_same_institution", "source_artifacts", type_="foreignkey")
    op.drop_constraint("fk_drive_revisions_drive_same_institution", "drive_revisions", type_="foreignkey")
    op.drop_constraint("fk_drives_company_same_institution", "drives", type_="foreignkey")
    op.drop_constraint("uq_source_artifacts_id_institution", "source_artifacts", type_="unique")
    op.drop_constraint("uq_memberships_id_institution", "memberships", type_="unique")
    op.drop_constraint("uq_student_profiles_id_institution", "student_profiles", type_="unique")
    op.drop_constraint("uq_drives_id_institution", "drives", type_="unique")
    op.drop_constraint("uq_companies_id_institution", "companies", type_="unique")
    op.drop_constraint("ck_domain_jobs_status", "domain_jobs", type_="check")
    op.drop_constraint("ck_source_scan_status", "source_artifacts", type_="check")
    op.drop_constraint("ck_source_acceptance_status", "source_artifacts", type_="check")
    op.drop_constraint("ck_upload_sessions_status", "upload_sessions", type_="check")
    op.drop_constraint("ck_drives_status", "drives", type_="check")
