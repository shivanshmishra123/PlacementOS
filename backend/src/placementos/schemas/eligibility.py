"""P05 eligibility API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvaluationRunCreate(BaseModel):
    policy_id: uuid.UUID | None = None


class PredicateFindingResponse(BaseModel):
    predicate: str
    outcome: Literal["true", "false", "unknown"]
    reason_code: str
    expected: Any
    actual: Any
    evidence_status: str
    explanation: str


class EligibilityResultResponse(BaseModel):
    id: uuid.UUID
    evaluation_run_id: uuid.UUID
    student_profile_id: uuid.UUID
    student_identifier: str
    student_name: str
    academic_revision_id: uuid.UUID | None
    outcome: Literal["eligible", "ineligible", "needs_review"]
    predicate_results: list[PredicateFindingResponse]
    reason_codes: list[str]
    student_explanation: str
    input_fingerprint: str
    created_at: datetime


class EvaluationRunResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    policy_id: uuid.UUID
    policy_version: int
    policy_hash: str
    engine_version: str
    normalization_version: str
    cohort_fingerprint: str
    status: str
    is_stale: bool
    stale_reason: str | None
    total_count: int
    eligible_count: int
    ineligible_count: int
    needs_review_count: int
    duration_ms: int | None
    error_code: str | None
    error_detail: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    results: list[EligibilityResultResponse] = Field(default_factory=list)


class StudentEligibilityResponse(BaseModel):
    result_id: uuid.UUID
    evaluation_run_id: uuid.UUID
    drive_id: uuid.UUID
    drive_title: str
    company_name: str
    policy_version: int
    outcome: Literal["eligible", "ineligible", "needs_review"]
    predicate_results: list[PredicateFindingResponse]
    reason_codes: list[str]
    student_explanation: str
    is_stale: bool
    stale_reason: str | None
    evaluated_at: datetime


class ReviewRequestCreate(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class ReviewRequestResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    eligibility_result_id: uuid.UUID
    student_profile_id: uuid.UUID
    student_identifier: str
    student_name: str
    reason: str
    status: str
    created_at: datetime
