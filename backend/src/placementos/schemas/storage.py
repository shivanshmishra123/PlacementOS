"""Pydantic schemas for Upload Sessions, Source Artifacts, Locators, and Extractions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UploadSessionCreate(BaseModel):
    drive_id: uuid.UUID
    purpose: Literal["jd_intake"] = "jd_intake"
    original_filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    byte_size: int = Field(..., gt=0, le=15 * 1024 * 1024, description="File size up to 15MB")


class UploadSessionResponse(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID | None = None
    purpose: str
    original_filename: str
    storage_key: str
    upload_url: str
    expires_at: datetime
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PastedSourceCreate(BaseModel):
    title: str = Field(default="Pasted Job Description", min_length=1, max_length=255)
    raw_text: str = Field(..., min_length=10, description="Pasted job description or intake text")


class SourceArtifactResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    drive_id: uuid.UUID | None
    source_type: str
    original_filename: str | None
    file_extension: str | None
    hash_sha256: str
    byte_size: int
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    extracted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TextLocatorSchema(BaseModel):
    locator_type: str
    page_number: int | None = None
    paragraph_index: int
    char_offset_start: int
    char_offset_end: int
    preview: str


class TextExtractionResponse(BaseModel):
    id: uuid.UUID
    source_artifact_id: uuid.UUID
    institution_id: uuid.UUID
    extracted_text: str
    char_count: int
    locators: list[TextLocatorSchema]
    page_count: int | None
    paragraph_count: int
    parser_version: str
    is_empty_or_scanned: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int
    filename: str | None = None


class DomainJobResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    job_kind: str
    operation_key: str
    resource_id: uuid.UUID | None
    status: str
    error_code: str | None
    error_detail: str | None
    attempt_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

