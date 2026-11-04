"""P13 operating-policy and optimized drive-summary contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DriveSummaryResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    academic_year: str
    status: str
    title: str
    current_revision_number: int
    source_artifact_count: int
    created_at: datetime
    updated_at: datetime


class DriveSummaryListResponse(BaseModel):
    items: list[DriveSummaryResponse]
    total: int
    page: int
    limit: int


class OperatingPolicyRevisionCreate(BaseModel):
    expected_revision: int = Field(ge=0)
    onboarding_status: Literal["configuration_pending", "synthetic_ready", "pilot_ready"]
    max_open_drives: int = Field(ge=1, le=100_000)
    max_students_per_import: int = Field(ge=1, le=1_000_000)
    max_export_rows: int = Field(ge=1, le=1_000_000)
    change_reason: str = Field(min_length=3, max_length=2000)


class OperatingPolicyResponse(BaseModel):
    institution_id: uuid.UUID
    revision_number: int
    source: Literal["system_default", "institution_revision"]
    onboarding_status: str
    max_open_drives: int
    max_students_per_import: int
    max_export_rows: int
    change_reason: str
    created_by_membership_id: uuid.UUID | None
    created_at: datetime | None
