"""P04 JD interpretation, policy review, and immutable approval models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from placementos.core.database import TimestampedUUIDModel


class JDInterpretationRevision(TimestampedUUIDModel):
    __tablename__ = "jd_interpretation_revisions"
    __table_args__ = (
        UniqueConstraint("drive_id", "revision_number", name="uq_jd_interpretation_drive_revision"),
        Index("ix_jd_interpretation_institution_drive", "institution_id", "drive_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    source_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    text_extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("text_extractions.id", ondelete="RESTRICT"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="review_ready", nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_facts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reviewed_facts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    validation_findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    usage_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class JDReviewCorrection(TimestampedUUIDModel):
    __tablename__ = "jd_review_corrections"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    interpretation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jd_interpretation_revisions.id", ondelete="CASCADE"), nullable=False
    )
    field_path: Mapped[str] = mapped_column(String(255), nullable=False)
    previous_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    corrected_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    corrected_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )


class ClarificationTask(TimestampedUUIDModel):
    __tablename__ = "clarification_tasks"
    __table_args__ = (Index("ix_clarifications_interpretation_status", "interpretation_id", "status"),)

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    interpretation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jd_interpretation_revisions.id", ondelete="CASCADE"), nullable=False
    )
    field_path: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    blocking: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    resolution_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EligibilityPolicyVersion(TimestampedUUIDModel):
    __tablename__ = "eligibility_policy_versions"
    __table_args__ = (
        UniqueConstraint("drive_id", "version_number", name="uq_policy_drive_version"),
        Index("ix_policy_institution_drive_status", "institution_id", "drive_id", "status"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    interpretation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jd_interpretation_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    engine_contract: Mapped[str] = mapped_column(String(50), default="eligibility-v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    policy_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    human_summary: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )
    approved_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ActionProposal(TimestampedUUIDModel):
    __tablename__ = "action_proposals"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "action_type", "target_type", "target_id", "revision_number",
            name="uq_action_proposal_target_revision",
        ),
        Index("ix_action_proposals_institution_state", "institution_id", "state"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    drive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dependencies: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    canonical_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="pending_approval", nullable=False)
    requested_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    earliest_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_bounds: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    sender_connection_revision: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ApprovalDecision(TimestampedUUIDModel):
    __tablename__ = "approval_decisions"
    __table_args__ = (UniqueConstraint("proposal_id", name="uq_approval_decision_proposal"),)

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("action_proposals.id", ondelete="RESTRICT"), nullable=False
    )
    proposal_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="RESTRICT"), nullable=False
    )
    permission_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
