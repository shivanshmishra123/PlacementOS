"""Typed P04 API contracts for JD review, policies, and exact decisions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class EvidenceLocator(BaseModel):
    field_path: str = Field(min_length=1, max_length=255)
    locator_type: Literal["page", "paragraph", "human_correction"]
    page_number: int | None = Field(default=None, ge=1)
    paragraph_index: int | None = Field(default=None, ge=0)
    char_offset_start: int | None = Field(default=None, ge=0)
    char_offset_end: int | None = Field(default=None, ge=0)
    excerpt: str = Field(min_length=1, max_length=500)


class InterpretationCreate(BaseModel):
    source_artifact_id: uuid.UUID
    mode: Literal["fixture", "manual"] = "fixture"
    manual_facts: dict[str, Any] | None = None
    manual_evidence: list[EvidenceLocator] = Field(default_factory=list)
    rationale: str | None = Field(default=None, min_length=3, max_length=1000)

    @field_validator("manual_facts")
    @classmethod
    def manual_facts_must_be_object(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None and not value:
            raise ValueError("manual_facts cannot be empty")
        return value


class ClarificationResponse(BaseModel):
    id: uuid.UUID
    field_path: str
    question: str
    reason_code: str
    blocking: bool
    status: str
    resolution_value: Any | None = None
    resolution_reason: str | None = None


class InterpretationResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    source_artifact_id: uuid.UUID
    text_extraction_id: uuid.UUID
    revision_number: int
    schema_version: int
    status: str
    mode: str
    adapter_id: str
    candidate_facts: dict[str, Any]
    reviewed_facts: dict[str, Any]
    evidence: list[dict[str, Any]]
    validation_findings: list[dict[str, Any]]
    clarifications: list[ClarificationResponse]
    created_at: datetime


class InterpretationCorrectionCreate(BaseModel):
    field_path: str = Field(min_length=1, max_length=255)
    corrected_value: Any
    rationale: str = Field(min_length=3, max_length=1000)
    evidence: EvidenceLocator | None = None


class ClarificationResolve(BaseModel):
    value: Any
    rationale: str = Field(min_length=3, max_length=1000)


class PolicyCompileRequest(BaseModel):
    interpretation_id: uuid.UUID
    explicitly_not_required: list[
        Literal["branch", "cgpa", "graduation_year", "active_backlogs"]
    ] = Field(default_factory=list)


class PolicyResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    interpretation_id: uuid.UUID
    version_number: int
    schema_version: int
    engine_contract: str
    status: str
    policy_payload: dict[str, Any]
    human_summary: str
    canonical_hash: str
    approved_proposal_id: uuid.UUID | None
    created_at: datetime


class ProposalResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    action_type: str
    target_type: str
    target_id: uuid.UUID
    revision_number: int
    payload: dict[str, Any]
    dependencies: dict[str, Any]
    canonical_hash: str
    state: str
    expires_at: datetime | None
    created_at: datetime


class ProposalDecisionCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    expected_hash: str = Field(min_length=64, max_length=64)
    decision: Literal["approved", "rejected", "revision_requested"]
    comment: str | None = Field(default=None, max_length=1000)


class DecisionResponse(BaseModel):
    id: uuid.UUID
    proposal_id: uuid.UUID
    decision: str
    comment: str | None
    decided_at: datetime
    proposal_state: str
    policy_status: str
