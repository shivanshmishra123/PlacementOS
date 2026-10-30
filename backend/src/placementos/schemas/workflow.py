"""Typed P08 contracts for durable workflow operations and baseline cases."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class WorkflowRunCreate(BaseModel):
    source_artifact_id: uuid.UUID | None = None


class WorkflowRunResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    graph_version: str
    state_schema_version: int
    status: str
    current_step: str
    state_references: dict[str, Any]
    pending_proposal_id: uuid.UUID | None
    pending_clarification_id: uuid.UUID | None
    pending_case_id: uuid.UUID | None
    last_event_id: uuid.UUID | None
    last_processed_command_id: uuid.UUID | None
    error_category: str | None
    error_detail: str | None
    concurrency_revision: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowResumeCreate(BaseModel):
    expected_run_revision: int = Field(ge=1)
    reference_type: Literal["decision", "clarification", "event"]
    reference_id: uuid.UUID


class WorkflowCommandResponse(BaseModel):
    id: uuid.UUID
    workflow_run_id: uuid.UUID
    command_type: str
    reference_type: str | None
    reference_id: uuid.UUID | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowEventCreate(BaseModel):
    event_key: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9:._-]+$")
    event_type: Literal[
        "registration_changed",
        "document_changed",
        "policy_changed",
        "deadline_reached",
        "dispatch_changed",
    ]
    resource_type: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$")
    resource_id: uuid.UUID
    resource_revision: str | None = Field(default=None, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime

    @field_validator("payload")
    @classmethod
    def bounded_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 20 or len(str(value)) > 4000:
            raise ValueError("Workflow event payload must be a small reference envelope")
        blocked_fragments = {"token", "secret", "password", "signed_url", "raw_text", "content"}
        for key, item in value.items():
            normalized_key = key.lower()
            if any(fragment in normalized_key for fragment in blocked_fragments):
                raise ValueError("Workflow event payload contains a prohibited sensitive field")
            if not isinstance(item, (str, int, float, bool, type(None))):
                raise ValueError("Workflow event payload values must be scalar references")
        return value

    @field_validator("occurred_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Event occurrence time must include a timezone")
        return value


class WorkflowEventResponse(BaseModel):
    id: uuid.UUID
    workflow_run_id: uuid.UUID
    event_key: str
    event_type: str
    resource_type: str
    resource_id: uuid.UUID
    resource_revision: str | None
    payload: dict[str, Any]
    occurred_at: datetime
    status: str
    processing_result: dict[str, Any]
    command_id: uuid.UUID | None = None
    created: bool = False


class OperationalHoldCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    expected_run_revision: int = Field(ge=1)


class OperationalHoldRelease(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    expected_run_revision: int = Field(ge=1)


class ExceptionCaseResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    workflow_run_id: uuid.UUID | None
    category: str
    severity: str
    status: str
    affected_resources: list[dict[str, Any]]
    evidence: dict[str, Any]
    proposed_next_action: str
    owner_membership_id: uuid.UUID | None
    resolution_history: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExceptionCaseAction(BaseModel):
    action: Literal["acknowledged", "resolved", "dismissed"]
    note: str = Field(min_length=3, max_length=2000)
    expected_run_revision: int | None = Field(default=None, ge=1)
