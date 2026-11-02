"""P12 structured exception impact, recovery-plan, and execution models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from placementos.core.database import TimestampedUUIDModel


class ExceptionImpactAnalysis(TimestampedUUIDModel):
    __tablename__ = "exception_impact_analyses"
    __table_args__ = (
        UniqueConstraint("case_id", "revision_number", name="uq_exception_impact_revision"),
        Index("ix_exception_impact_case_status", "institution_id", "case_id", "status"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exception_cases.id", ondelete="CASCADE"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="current")
    input_references: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dependency_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dependency_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    impact_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    affected_students: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    affected_resources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    manual_fallback: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class RecoveryPlan(TimestampedUUIDModel):
    __tablename__ = "recovery_plans"
    __table_args__ = (
        UniqueConstraint("analysis_id", "revision_number", name="uq_recovery_plan_revision"),
        Index("ix_recovery_plan_case_status", "institution_id", "case_id", "status"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exception_cases.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exception_impact_analyses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_proposals.id", ondelete="RESTRICT"), nullable=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    planner_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    planner_id: Mapped[str] = mapped_column(String(100), nullable=False)
    planner_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dependency_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    usage_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class RecoveryPlanStep(TimestampedUUIDModel):
    __tablename__ = "recovery_plan_steps"
    __table_args__ = (
        UniqueConstraint("plan_id", "step_number", name="uq_recovery_plan_step_number"),
        UniqueConstraint("institution_id", "operation_key", name="uq_recovery_step_operation_key"),
        Index("ix_recovery_steps_plan_status", "plan_id", "status"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recovery_plans.id", ondelete="CASCADE"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    exact_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preconditions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dependencies: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    expected_effects: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    approval_type: Mapped[str] = mapped_column(String(64), nullable=False)
    irreversible_effects: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryExecution(TimestampedUUIDModel):
    __tablename__ = "recovery_executions"
    __table_args__ = (
        UniqueConstraint("plan_id", name="uq_recovery_execution_plan"),
        Index("ix_recovery_execution_status", "institution_id", "status", "created_at"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exception_cases.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recovery_plans.id", ondelete="RESTRICT"), nullable=False
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_proposals.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    current_step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_step_count: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    irreversible_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)


class RecoveryStepAttempt(TimestampedUUIDModel):
    __tablename__ = "recovery_step_attempts"
    __table_args__ = (
        UniqueConstraint("step_id", "attempt_number", name="uq_recovery_step_attempt"),
        Index("ix_recovery_attempt_step", "step_id", "attempt_number"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recovery_executions.id", ondelete="CASCADE"), nullable=False
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recovery_plan_steps.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
