"""Typed P11 Google Workspace connector contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

GoogleFeature = Literal["gmail_intake", "sheets_import", "sheets_export", "calendar_events"]


class GoogleAuthorizationCreate(BaseModel):
    features: list[GoogleFeature] = Field(min_length=1)
    redirect_after: str = "/coordinator/integrations"

    @field_validator("features")
    @classmethod
    def unique_features(cls, value: list[GoogleFeature]) -> list[GoogleFeature]:
        return list(dict.fromkeys(value))

    @field_validator("redirect_after")
    @classmethod
    def local_redirect_only(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("redirect_after must be an application-relative path")
        return value


class GoogleAuthorizationResponse(BaseModel):
    authorization_url: str
    expires_at: datetime


class IntegrationConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    external_account_email: str
    status: str
    granted_scopes: list[str]
    connection_revision: int
    access_token_expires_at: datetime | None
    last_error_code: str | None
    disconnected_at: datetime | None
    created_at: datetime


class GmailCaptureCreate(BaseModel):
    connection_id: uuid.UUID
    message_id: str = Field(min_length=1, max_length=255)
    attachment_id: str | None = Field(default=None, max_length=255)


class GmailCaptureResponse(BaseModel):
    id: uuid.UUID
    source_artifact_id: uuid.UUID
    message_id: str
    attachment_id: str | None
    subject: str | None
    sender: str | None
    content_hash: str
    extraction_job_id: uuid.UUID


class SheetImportPreviewCreate(BaseModel):
    connection_id: uuid.UUID
    spreadsheet_id: str = Field(min_length=1, max_length=255)
    selected_range: str = Field(min_length=1, max_length=255)
    mapping: dict[str, str] = Field(default_factory=dict)


class SheetImportPreviewResponse(BaseModel):
    id: uuid.UUID
    spreadsheet_id: str
    selected_range: str
    source_fingerprint: str
    status: str
    expires_at: datetime
    report: dict[str, Any]


class SheetImportCommitResponse(BaseModel):
    preview_id: uuid.UUID
    status: str
    result: dict[str, Any]


class SheetExportProposalCreate(BaseModel):
    connection_id: uuid.UUID
    report_id: uuid.UUID
    spreadsheet_id: str = Field(min_length=1, max_length=255)
    target_range: str = Field(min_length=1, max_length=255)


class CalendarProposalCreate(BaseModel):
    connection_id: uuid.UUID
    calendar_id: str = Field(min_length=1, max_length=1024)
    send_updates: Literal["none", "externalOnly", "all"] = "none"


class IntegrationProposalResponse(BaseModel):
    id: uuid.UUID
    action_type: str
    target_type: str
    target_id: uuid.UUID
    revision_number: int
    state: str
    canonical_hash: str
    payload: dict[str, Any]
    dependencies: dict[str, Any]


class IntegrationDecisionCreate(BaseModel):
    expected_revision: int
    expected_hash: str = Field(min_length=64, max_length=64)
    decision: Literal["approved", "rejected", "revision_requested"]
    comment: str | None = Field(default=None, max_length=2000)


class IntegrationOperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    proposal_id: uuid.UUID
    operation_kind: str
    status: str
    attempt_count: int
    provider_resource_id: str | None
    provider_version: str | None
    last_error_code: str | None
    last_error_detail: str | None
    created_at: datetime
    completed_at: datetime | None


class CalendarWatchCreate(BaseModel):
    calendar_id: str = Field(min_length=1, max_length=1024)


class CalendarChannelResponse(BaseModel):
    id: uuid.UUID
    channel_id: str
    resource_id: str
    status: str
    expires_at: datetime | None
