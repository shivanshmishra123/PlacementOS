"""Pydantic schemas for structured LLM extraction and model contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CompensationDetails(BaseModel):
    source_wording: str | None = Field(
        default=None,
        description="Exact compensation wording from the source (e.g. '18.5 LPA' or '12-15 LPA').",
    )
    annual_ctc_minor_units: int | None = Field(
        default=None,
        description="Annual CTC in minor currency units if clearly stated (e.g. 185000000 for 18.5 LPA INR).",
    )
    currency: str | None = Field(default="INR", description="Currency code (e.g. INR).")


class EligibilityDraft(BaseModel):
    allowed_branches: list[str] | None = Field(
        default=None,
        description="List of allowed branches/disciplines (e.g. ['CSE', 'IT', 'ECE']).",
    )
    minimum_cgpa: str | None = Field(
        default=None,
        description="Minimum CGPA cutoff as decimal string (e.g. '7.50' or '8.00').",
    )
    cgpa_scale: str | None = Field(
        default="10.0",
        description="CGPA scale basis (e.g. '10.0' or '4.0').",
    )
    graduation_years: list[int] | None = Field(
        default=None,
        description="Eligible graduation cohort years (e.g. [2027]).",
    )
    maximum_active_backlogs: int | None = Field(
        default=None,
        description="Maximum permitted active backlogs (e.g. 0).",
    )


class ExtractedCitation(BaseModel):
    field_path: str = Field(
        description="The field this excerpt supports (e.g. 'eligibility_draft.minimum_cgpa', 'role_title', 'compensation')."
    )
    paragraph_index: int = Field(
        description="Zero-based paragraph index (§) from the source document where this fact was found."
    )
    excerpt: str = Field(
        description="Verbatim exact quote/excerpt from that paragraph proving the fact."
    )


class ClarificationFinding(BaseModel):
    field_path: str = Field(
        description="Field with ambiguity or missing required specification (e.g. 'registration_deadline', 'minimum_cgpa')."
    )
    reason_code: str = Field(
        description="Standard reason code (e.g. 'DEADLINE_TIMEZONE_MISSING', 'AMBIGUOUS_CGPA_SCALE', 'CONTRADICTORY_ATTACHMENT')."
    )
    explanation: str = Field(
        description="Actionable explanation describing the ambiguity requiring coordinator review."
    )


class JDExtractionResult(BaseModel):
    """Strict structured output contract for Job Description extraction."""

    company_name: str | None = Field(default=None, description="Name of hiring organization.")
    role_title: str | None = Field(default=None, description="Job title / position name.")
    employment_type: str | None = Field(
        default=None,
        description="Type of employment: 'full_time', 'internship', or 'internship_then_full_time'.",
    )
    location: str | None = Field(default=None, description="Work location (e.g. 'Bengaluru / Hyderabad').")
    work_mode: str | None = Field(
        default=None,
        description="Work arrangement: 'on_site', 'hybrid', or 'remote'.",
    )
    compensation: CompensationDetails = Field(default_factory=CompensationDetails)
    eligibility_draft: EligibilityDraft = Field(default_factory=EligibilityDraft)
    registration_deadline: str | None = Field(
        default=None,
        description="Registration deadline date in YYYY-MM-DD or ISO-8601 format if mentioned.",
    )
    citations: list[ExtractedCitation] = Field(
        default_factory=list,
        description="List of verifiable citations with paragraph locators proving each extracted fact.",
    )
    clarifications: list[ClarificationFinding] = Field(
        default_factory=list,
        description="Ambiguities or unverified details flagged for human coordinator clarification.",
    )
