"""Typed P07 contracts for exact communication approval and dispatch."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

CommunicationKind = Literal[
    "drive_announcement",
    "missing_document_reminder",
    "registration_deadline_reminder",
    "clarification",
]
AudienceType = Literal[
    "current_eligible",
    "submitted_registrants",
    "required_document_findings",
    "explicit_recipients",
]


class CommunicationDraftCreate(BaseModel):
    communication_kind: CommunicationKind
    audience_type: AudienceType
    explicit_student_ids: list[uuid.UUID] = Field(default_factory=list, max_length=5000)
    subject_template: str | None = Field(default=None, min_length=1, max_length=500)
    body_template: str | None = Field(default=None, min_length=1, max_length=20_000)
    sender_email: str | None = Field(default=None, max_length=255)
    reply_to: str = Field(min_length=3, max_length=255)

    @field_validator("sender_email", "reply_to")
    @classmethod
    def valid_email(cls, value: str | None) -> str | None:
        if value is not None and ("@" not in value or value.startswith("@") or value.endswith("@")):
            raise ValueError("A valid email address is required")
        return value

    @model_validator(mode="after")
    def explicit_audience_requires_ids(self) -> CommunicationDraftCreate:
        if self.audience_type == "explicit_recipients" and not self.explicit_student_ids:
            raise ValueError("Explicit recipient audiences require at least one reviewed student")
        if self.audience_type != "explicit_recipients" and self.explicit_student_ids:
            raise ValueError("Student IDs are only accepted for an explicit recipient audience")
        return self


class AudienceRecipientResponse(BaseModel):
    id: uuid.UUID
    student_profile_id: uuid.UUID
    email: str
    display_name: str
    inclusion_reason: str
    rendered_subject: str
    rendered_body: str
    rendered_hash: str


class CommunicationDraftResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    revision_number: int
    communication_kind: str
    audience_type: str
    subject_template: str
    body_template: str
    sender_email: str
    reply_to: str
    state: str
    content_hash: str
    audience_snapshot_id: uuid.UUID
    audience_hash: str
    included_count: int
    excluded_count: int
    duplicate_count: int
    unresolved_count: int
    exclusion_summary: dict[str, int]
    recipients: list[AudienceRecipientResponse]
    created_at: datetime


class CommunicationProposalCreate(BaseModel):
    execution_expires_at: datetime

    @model_validator(mode="after")
    def timezone_required(self) -> CommunicationProposalCreate:
        if self.execution_expires_at.tzinfo is None:
            raise ValueError("Execution expiry must include a timezone")
        return self


class CommunicationProposalResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    draft: CommunicationDraftResponse
    revision_number: int
    canonical_hash: str
    state: str
    payload: dict
    dependencies: dict
    execution_expires_at: datetime | None
    sender_connection_revision: str | None
    decision: dict | None = None
    created_at: datetime


class CommunicationDecisionCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    expected_hash: str = Field(min_length=64, max_length=64)
    decision: Literal["approved", "rejected", "revision_requested"]
    comment: str | None = Field(default=None, max_length=1000)


class DispatchOperationResponse(BaseModel):
    id: uuid.UUID
    operation_key: str
    recipient: str
    recipient_name: str
    status: str
    attempt_count: int
    provider_message_id: str | None
    last_error_code: str | None


class DispatchBatchResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    proposal_id: uuid.UUID
    communication_draft_id: uuid.UUID
    status: str
    total_count: int
    pending_count: int
    accepted_count: int
    delivered_count: int
    failed_count: int
    unknown_count: int
    cancelled_count: int
    execution_expires_at: datetime
    operations: list[DispatchOperationResponse]
    created_at: datetime


class UnknownOutcomeResolution(BaseModel):
    resolution: Literal["provider_accepted", "confirmed_not_accepted"]
    evidence: str = Field(min_length=3, max_length=2000)


class CancellationCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
