"""Typed P09 scheduling, results, reporting, and closure contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RoundCreate(BaseModel):
    sequence_number: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=150)
    round_type: str = Field(min_length=1, max_length=50)
    requires_previous_round_outcome: bool = True


class SessionCreate(BaseModel):
    start_at: datetime
    end_at: datetime
    timezone: str = Field(min_length=1, max_length=100)
    buffer_minutes: int = Field(default=0, ge=0, le=1440)
    capacity: int = Field(ge=1, le=10000)
    venue: str | None = Field(default=None, max_length=255)
    meeting_url: str | None = Field(default=None, max_length=1000)
    panel_members: list[str] = Field(default_factory=list, max_length=100)
    student_profile_ids: list[uuid.UUID] = Field(min_length=1, max_length=10000)
    document_override_reason: str | None = Field(default=None, min_length=3, max_length=2000)
    change_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_interval(self) -> SessionCreate:
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("Session timestamps must include a timezone offset")
        if self.end_at <= self.start_at:
            raise ValueError("Session end must be after its start")
        if not self.venue and not self.meeting_url:
            raise ValueError("A venue or meeting URL is required")
        if len(set(self.student_profile_ids)) != len(self.student_profile_ids):
            raise ValueError("A student cannot be assigned twice")
        return self


class ProposalDecisionCreate(BaseModel):
    expected_revision: int = Field(ge=1)
    expected_hash: str = Field(min_length=64, max_length=64)
    decision: Literal["approved", "rejected", "revision_requested"]
    comment: str | None = Field(default=None, max_length=2000)


class AttendanceItem(BaseModel):
    student_profile_id: uuid.UUID
    status: Literal["present", "absent", "excused"]
    note: str | None = Field(default=None, max_length=2000)


class AttendanceCreate(BaseModel):
    items: list[AttendanceItem] = Field(min_length=1, max_length=10000)


class OutcomeCreate(BaseModel):
    student_profile_id: uuid.UUID
    outcome: Literal["pending", "advanced", "rejected", "waitlisted", "selected", "withdrawn"]
    source_type: str = Field(min_length=1, max_length=50)
    source_reference: str = Field(min_length=1, max_length=500)
    source_evidence: dict = Field(default_factory=dict)
    note: str | None = Field(default=None, max_length=2000)
    offer_status: Literal["not_recorded", "issued"] = "not_recorded"
    acceptance_status: Literal["not_recorded", "accepted", "declined"] = "not_recorded"
    joining_status: Literal["not_recorded", "joined", "not_joined", "deferred"] = "not_recorded"


class GapAcknowledgementCreate(BaseModel):
    student_profile_id: uuid.UUID
    reason: str = Field(min_length=3, max_length=2000)


class ReasonCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class ReportCreate(ReasonCreate):
    report_kind: Literal["operational"] = "operational"


class RoundResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    sequence_number: int
    name: str
    round_type: str
    requires_previous_round_outcome: bool
    status: str


class SessionResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    round_id: uuid.UUID
    status: str
    current_revision_id: uuid.UUID | None
    published_revision_id: uuid.UUID | None
    revision: dict | None
    assignments: list[dict]


class ProposalResponse(BaseModel):
    id: uuid.UUID
    action_type: str
    target_type: str
    target_id: uuid.UUID
    revision_number: int
    canonical_hash: str
    state: str
    payload: dict
    dependencies: dict


class OutcomeResponse(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID
    student_profile_id: uuid.UUID
    revision_number: int
    outcome: str
    source_type: str
    source_reference: str
    source_evidence: dict
    note: str | None
    offer_status: str
    acceptance_status: str
    joining_status: str
    published_at: datetime | None


class ReportResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    revision_number: int
    report_kind: str
    status: str
    snapshot_payload: dict
    snapshot_hash: str
    reason: str
    created_at: datetime


class ExportGrantResponse(BaseModel):
    download_url: str
    expires_at: datetime
