"""Typed P06 API contracts for documents, publication, and registration."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DocumentType = Literal["resume", "marksheet", "college_id"]
ReadinessStatus = Literal["ready", "pending", "blocked", "needs_review"]


class RequirementCreate(BaseModel):
    document_type: DocumentType
    display_label: str = Field(min_length=1, max_length=100)
    allowed_extensions: list[Literal["pdf", "docx"]] = Field(min_length=1)
    max_size_bytes: int = Field(default=10 * 1024 * 1024, gt=0, le=10 * 1024 * 1024)
    filename_pattern: str | None = Field(default=None, max_length=255)
    required_stage: Literal["registration", "scheduling"]
    due_at: datetime | None = None


class RequirementSetCreate(BaseModel):
    expected_drive_revision: int = Field(ge=1)
    requirements: list[RequirementCreate] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_document_types(self) -> RequirementSetCreate:
        types = [item.document_type for item in self.requirements]
        if len(types) != len(set(types)):
            raise ValueError("Document types must be unique within a requirement set")
        return self


class RequirementResponse(RequirementCreate):
    id: uuid.UUID
    drive_id: uuid.UUID
    drive_revision_id: uuid.UUID
    created_at: datetime


class PublicationProposalCreate(BaseModel):
    expected_drive_revision: int = Field(ge=1)
    evaluation_run_id: uuid.UUID
    registration_start_at: datetime
    registration_end_at: datetime
    withdrawal_end_at: datetime | None = None

    @model_validator(mode="after")
    def valid_window(self) -> PublicationProposalCreate:
        if self.registration_start_at.tzinfo is None or self.registration_end_at.tzinfo is None:
            raise ValueError("Registration timestamps must include a timezone")
        if self.registration_start_at >= self.registration_end_at:
            raise ValueError("Registration start must be before the exclusive deadline")
        if self.withdrawal_end_at and self.withdrawal_end_at.tzinfo is None:
            raise ValueError("Withdrawal deadline must include a timezone")
        return self


class PublicationDecisionCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    expected_hash: str = Field(min_length=64, max_length=64)
    decision: Literal["approved", "rejected", "revision_requested"]
    comment: str | None = Field(default=None, max_length=1000)


class PublicationProposalResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    drive_revision_id: uuid.UUID
    evaluation_run_id: uuid.UUID
    revision_number: int
    canonical_hash: str
    state: str
    payload: dict
    dependencies: dict
    created_at: datetime


class DocumentUploadSessionCreate(BaseModel):
    document_type: DocumentType
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    byte_size: int = Field(gt=0, le=10 * 1024 * 1024)


class DocumentUploadSessionResponse(BaseModel):
    id: uuid.UUID
    document_type: DocumentType
    original_filename: str
    upload_url: str
    expires_at: datetime
    status: str


class FindingResponse(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    required_action: str | None = None


class DocumentRevisionResponse(BaseModel):
    id: uuid.UUID
    document_type: DocumentType
    revision_number: int
    original_filename: str
    media_type: str
    file_size_bytes: int
    hash_sha256: str
    scan_status: str
    structure_status: str
    text_status: str
    created_at: datetime


class RequirementReadinessResponse(BaseModel):
    requirement_id: uuid.UUID
    document_type: DocumentType
    display_label: str
    required_stage: Literal["registration", "scheduling"]
    due_at: datetime | None
    status: ReadinessStatus
    findings: list[FindingResponse]
    current_document: DocumentRevisionResponse | None = None


class ReadinessResponse(BaseModel):
    status: ReadinessStatus
    requirements: list[RequirementReadinessResponse]


class RegistrationResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    student_profile_id: uuid.UUID
    state: Literal["draft", "submitted", "withdrawn", "eligibility_hold"]
    submitted_at: datetime | None
    withdrawn_at: datetime | None
    hold_reason: str | None
    concurrency_revision: int


class WithdrawalCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class CoordinatorRegistrationAction(BaseModel):
    expected_revision: int = Field(ge=1)
    action: Literal["restore", "withdraw"]
    reason: str = Field(min_length=3, max_length=500)


class StudentDriveResponse(BaseModel):
    drive_id: uuid.UUID
    company_name: str
    role_title: str
    location: str | None
    work_mode: str
    employment_type: str
    compensation_details: dict | None
    registration_start_at: datetime
    registration_end_at: datetime
    withdrawal_end_at: datetime | None
    eligibility_status: Literal["eligible", "ineligible", "needs_review"]
    eligibility_reasons: list[str]
    document_readiness: ReadinessResponse
    registration: RegistrationResponse | None


class ParticipantResponse(BaseModel):
    student_profile_id: uuid.UUID
    student_identifier: str
    student_name: str
    eligibility_status: str
    readiness_status: ReadinessStatus
    registration_state: str | None
    registration_id: uuid.UUID | None
    registration_revision: int | None


class ParticipantListResponse(BaseModel):
    items: list[ParticipantResponse]
    total: int
    counts: dict[str, int]
