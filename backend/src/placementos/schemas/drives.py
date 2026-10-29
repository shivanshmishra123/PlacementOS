"""Pydantic schemas for Companies, Drives, and Drive Revisions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    industry: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)
    contact_email: str | None = Field(None, max_length=255)


class CompanyResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    name: str
    industry: str | None = None
    website: str | None = None
    contact_email: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriveCreate(BaseModel):
    company_id: uuid.UUID
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{4}$", description="Academic cohort format, e.g. 2026-2027")
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class DriveUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None


class DriveRevisionCreate(BaseModel):
    expected_revision_number: int = Field(..., description="Optimistic concurrency control token")
    change_summary: str = Field(..., min_length=1, max_length=500)
    proposed_changes: dict[str, Any] = Field(default_factory=dict)


class DriveRevisionResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    revision_number: int
    change_summary: str
    proposed_changes: dict[str, Any]
    created_by_user_id: uuid.UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceArtifactSummary(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    source_type: str
    original_filename: str | None
    status: str
    hash_sha256: str
    byte_size: int
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriveResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    academic_year: str
    status: str
    title: str
    description: str | None
    current_revision_number: int
    revisions: list[DriveRevisionResponse] = Field(default_factory=list)
    source_artifacts: list[SourceArtifactSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriveListResponse(BaseModel):
    items: list[DriveResponse]
    total: int
    page: int
    limit: int
