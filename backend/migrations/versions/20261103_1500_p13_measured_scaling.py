"""P13 measured scaling indexes and institution operating policies.

Revision ID: p13_measured_scaling
Revises: p12_exception_recovery
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p13_measured_scaling"
down_revision: str | None = "p12_exception_recovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_drives_inst_created_id",
        "drives",
        ["institution_id", "created_at", "id"],
    )
    op.create_index(
        "ix_drives_inst_creator_created",
        "drives",
        ["institution_id", "created_by_membership_id", "created_at"],
    )
    op.create_index(
        "ix_drives_inst_assignee_created",
        "drives",
        ["institution_id", "assigned_coordinator_membership_id", "created_at"],
    )
    op.create_index(
        "ix_drive_assignments_inst_member_drive",
        "drive_assignments",
        ["institution_id", "membership_id", "drive_id"],
    )
    op.create_table(
        "institution_operating_policies",
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("onboarding_status", sa.String(32), nullable=False),
        sa.Column("max_open_drives", sa.Integer(), nullable=False),
        sa.Column("max_students_per_import", sa.Integer(), nullable=False),
        sa.Column("max_export_rows", sa.Integer(), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("created_by_membership_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id",
            "revision_number",
            name="uq_institution_operating_policy_revision",
        ),
        sa.CheckConstraint(
            "status IN ('current','superseded')",
            name="ck_institution_operating_policy_status",
        ),
        sa.CheckConstraint(
            "onboarding_status IN ('configuration_pending','synthetic_ready','pilot_ready')",
            name="ck_institution_operating_policy_onboarding",
        ),
        sa.CheckConstraint(
            "max_open_drives > 0 AND max_students_per_import > 0 AND max_export_rows > 0",
            name="ck_institution_operating_policy_quotas",
        ),
    )
    op.create_index(
        "uq_institution_operating_policy_current",
        "institution_operating_policies",
        ["institution_id"],
        unique=True,
        postgresql_where=sa.text("status = 'current'"),
    )
    op.execute("ALTER TABLE institution_operating_policies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE institution_operating_policies FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY institution_operating_policies_institution_scope "
        "ON institution_operating_policies "
        "USING (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid) "
        "WITH CHECK (institution_id = NULLIF(current_setting('app.institution_id', true), '')::uuid)"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON institution_operating_policies TO placementos_app"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS institution_operating_policies_institution_scope "
        "ON institution_operating_policies"
    )
    op.drop_table("institution_operating_policies")
    op.drop_index("ix_drive_assignments_inst_member_drive", table_name="drive_assignments")
    op.drop_index("ix_drives_inst_assignee_created", table_name="drives")
    op.drop_index("ix_drives_inst_creator_created", table_name="drives")
    op.drop_index("ix_drives_inst_created_id", table_name="drives")
