"""Typed P12 adaptive exception recovery contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CriteriaChangeImpactCreate(BaseModel):
    category: Literal["criteria_change"]
    old_evaluation_run_id: uuid.UUID
    new_evaluation_run_id: uuid.UUID


class AcademicCorrectionImpactCreate(BaseModel):
    category: Literal["academic_correction"]
    student_profile_id: uuid.UUID
    old_academic_revision_id: uuid.UUID
    new_academic_revision_id: uuid.UUID
    old_evaluation_run_id: uuid.UUID
    new_evaluation_run_id: uuid.UUID


class DeadlineScheduleImpactCreate(BaseModel):
    category: Literal["deadline_schedule_change"]
    change_kind: Literal["deadline", "schedule"]
    old_revision_id: uuid.UUID
    new_revision_id: uuid.UUID


class NotificationFailureImpactCreate(BaseModel):
    category: Literal["notification_failure"]
    dispatch_operation_id: uuid.UUID


ExceptionImpactCreate = Annotated[
    CriteriaChangeImpactCreate
    | AcademicCorrectionImpactCreate
    | DeadlineScheduleImpactCreate
    | NotificationFailureImpactCreate,
    Field(discriminator="category"),
]


RecoveryOperationType = Literal[
    "place_drive_hold",
    "stale_pending_proposals",
    "prepare_correction_draft",
    "mark_external_reconciliation",
    "record_manual_followup",
]


class RecoveryStepCreate(BaseModel):
    operation_type: RecoveryOperationType
    exact_payload: dict[str, Any]
    dependencies: list[int] = Field(default_factory=list, max_length=10)
    expected_effects: list[str] = Field(min_length=1, max_length=10)
    approval_type: Literal["recovery_plan", "separate_action_approval", "manual_evidence"]
    irreversible_effects: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("exact_payload")
    @classmethod
    def bounded_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 20 or len(str(value)) > 12_000:
            raise ValueError("Recovery step payload exceeds the bounded command envelope")
        blocked = {"token", "password", "secret", "raw_document", "signed_url"}
        if any(any(fragment in key.lower() for fragment in blocked) for key in value):
            raise ValueError("Recovery step payload contains a prohibited field")
        return value


class RecoveryPlanCreate(BaseModel):
    planner_mode: Literal["fixture", "manual"]
    rationale: str = Field(min_length=3, max_length=4000)
    manual_steps: list[RecoveryStepCreate] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def manual_mode_requires_steps(self) -> RecoveryPlanCreate:
        if self.planner_mode == "manual" and not self.manual_steps:
            raise ValueError("Manual recovery planning requires at least one typed step")
        if self.planner_mode == "fixture" and self.manual_steps:
            raise ValueError("Fixture planning does not accept caller-supplied steps")
        return self


class RecoveryDecisionCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    expected_hash: str = Field(min_length=64, max_length=64)
    decision: Literal["approved", "rejected", "revision_requested"]
    comment: str | None = Field(default=None, max_length=2000)


class RecoveryCancellationCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class ExceptionImpactResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    drive_id: uuid.UUID
    revision_number: int
    category: str
    status: str
    input_references: dict[str, Any]
    dependency_fingerprint: str
    impact_summary: dict[str, Any]
    affected_students: list[dict[str, Any]]
    affected_resources: list[dict[str, Any]]
    manual_fallback: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RecoveryPlanStepResponse(BaseModel):
    id: uuid.UUID
    step_number: int
    operation_type: str
    exact_payload: dict[str, Any]
    preconditions: dict[str, Any]
    dependencies: list[int]
    expected_effects: list[str]
    approval_type: str
    irreversible_effects: list[str]
    status: str
    attempt_count: int
    result: dict[str, Any]
    error_code: str | None
    error_detail: str | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class RecoveryPlanResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    analysis_id: uuid.UUID
    proposal_id: uuid.UUID | None
    revision_number: int
    planner_mode: str
    planner_id: str
    planner_version: str
    status: str
    rationale: str
    canonical_hash: str
    approval_hash: str
    dependency_fingerprint: str
    usage_metadata: dict[str, Any]
    steps: list[RecoveryPlanStepResponse]
    created_at: datetime


class RecoveryExecutionResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    proposal_id: uuid.UUID
    status: str
    current_step_number: int | None
    completed_step_count: int
    pending_step_count: int
    failed_step_count: int
    irreversible_step_count: int
    last_error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
