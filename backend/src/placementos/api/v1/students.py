"""PlacementOS Scoped Student Records and Correction Endpoints (P02-T04 / P02-T05 / P02-T06 / P02-T07)."""

from __future__ import annotations

import decimal
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth, require_capability
from placementos.core.errors import BadRequestException, NotFoundException
from placementos.models.academic import AcademicRecordRevision, StudentCorrectionProposal
from placementos.models.identity import AuditLog, StudentProfile, User
from placementos.services.session import AuthContext
from placementos.services.student_import import StudentImportService

router = APIRouter(tags=["Student Records & Corrections"])


# Schemas
class AcademicRevisionDTO(BaseModel):
    id: uuid.UUID
    revision_number: int
    source: str
    source_reference: str | None = None
    is_verified: bool
    verified_at: datetime | None = None
    branch: str
    cgpa: float
    cgpa_scale: float
    graduation_year: int
    active_backlogs: int | None = None
    history_backlogs: int | None = None
    created_at: datetime


class StudentListItemDTO(BaseModel):
    id: uuid.UUID
    student_identifier: str
    full_name: str
    email: str
    branch: str | None = None
    cgpa: float | None = None
    cgpa_scale: float | None = None
    graduation_year: int | None = None
    active_backlogs: int | None = None
    is_verified: bool = False
    created_at: datetime


class StudentDetailDTO(BaseModel):
    id: uuid.UUID
    student_identifier: str
    full_name: str
    email: str
    institution_id: uuid.UUID
    current_verified_revision: AcademicRevisionDTO | None = None
    revision_history: list[AcademicRevisionDTO] = []


class CSVPreviewRequest(BaseModel):
    csv_content: str


class CSVCommitRequest(BaseModel):
    preview_token: str


class CorrectionProposalCreateRequest(BaseModel):
    proposed_changes: dict[str, Any] = Field(
        ...,
        description="Fields to correct e.g. {'cgpa': '8.75', 'active_backlogs': 0}",
    )
    justification: str = Field(..., min_length=5, max_length=1000)
    supporting_document_url: str | None = None


class CorrectionProposalDTO(BaseModel):
    id: uuid.UUID
    student_profile_id: uuid.UUID
    student_identifier: str
    student_name: str
    proposed_changes: dict[str, Any]
    justification: str
    supporting_document_url: str | None = None
    status: str
    review_notes: str | None = None
    decided_at: datetime | None = None
    created_at: datetime


class CorrectionDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    review_notes: str | None = None


# --- Coordinator Endpoints ---


@router.get("/students", response_model=list[StudentListItemDTO])
async def list_students(
    branch: str | None = Query(None, description="Filter by academic branch"),
    min_cgpa: float | None = Query(None, description="Minimum CGPA filter"),
    graduation_year: int | None = Query(None, description="Graduation cohort filter"),
    auth: AuthContext = Depends(require_capability("student:read")),
    db: AsyncSession = Depends(get_db),
) -> list[StudentListItemDTO]:
    """List student records scoped strictly to coordinator's institution (INV-06)."""
    # Fetch profiles with their user
    query = (
        select(StudentProfile)
        .options(selectinload(StudentProfile.institution))
        .where(StudentProfile.institution_id == auth.institution_id)
        .order_by(StudentProfile.student_identifier)
    )
    res = await db.execute(query)
    profiles = res.scalars().all()

    items: list[StudentListItemDTO] = []
    for profile in profiles:
        # Load user
        user_res = await db.execute(select(User).where(User.id == profile.user_id))
        user = user_res.scalar_one()

        # Load current verified revision if present
        rev: AcademicRecordRevision | None = None
        if profile.current_academic_revision_id:
            rev_res = await db.execute(
                select(AcademicRecordRevision).where(
                    AcademicRecordRevision.id == profile.current_academic_revision_id
                )
            )
            rev = rev_res.scalar_one_or_none()

        # Apply in-memory filters on verified revision
        if branch and (not rev or rev.branch != branch.upper()):
            continue
        if min_cgpa is not None and (not rev or float(rev.cgpa) < min_cgpa):
            continue
        if graduation_year is not None and (not rev or rev.graduation_year != graduation_year):
            continue

        items.append(
            StudentListItemDTO(
                id=profile.id,
                student_identifier=profile.student_identifier,
                full_name=user.full_name,
                email=user.email,
                branch=rev.branch if rev else None,
                cgpa=float(rev.cgpa) if rev else None,
                cgpa_scale=float(rev.cgpa_scale) if rev else None,
                graduation_year=rev.graduation_year if rev else None,
                active_backlogs=rev.active_backlogs if rev else None,
                is_verified=rev.is_verified if rev else False,
                created_at=profile.created_at,
            )
        )

    return items


@router.get("/students/{student_id}", response_model=StudentDetailDTO)
async def get_student_detail(
    student_id: uuid.UUID,
    auth: AuthContext = Depends(require_capability("student:read")),
    db: AsyncSession = Depends(get_db),
) -> StudentDetailDTO:
    """Get complete student detail with full audit revision history within institution scope."""
    profile_res = await db.execute(
        select(StudentProfile).where(
            StudentProfile.id == student_id,
            StudentProfile.institution_id == auth.institution_id,
        )
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise NotFoundException(f"Student record {student_id} not found in this institution")

    user_res = await db.execute(select(User).where(User.id == profile.user_id))
    user = user_res.scalar_one()

    # Load all revisions
    rev_res = await db.execute(
        select(AcademicRecordRevision)
        .where(AcademicRecordRevision.student_profile_id == profile.id)
        .order_by(desc(AcademicRecordRevision.revision_number))
    )
    revisions = rev_res.scalars().all()

    rev_dtos = [
        AcademicRevisionDTO(
            id=r.id,
            revision_number=r.revision_number,
            source=r.source,
            source_reference=r.source_reference,
            is_verified=r.is_verified,
            verified_at=r.verified_at,
            branch=r.branch,
            cgpa=float(r.cgpa),
            cgpa_scale=float(r.cgpa_scale),
            graduation_year=r.graduation_year,
            active_backlogs=r.active_backlogs,
            history_backlogs=r.history_backlogs,
            created_at=r.created_at,
        )
        for r in revisions
    ]

    curr_dto = next((r for r in rev_dtos if r.id == profile.current_academic_revision_id), None)

    return StudentDetailDTO(
        id=profile.id,
        student_identifier=profile.student_identifier,
        full_name=user.full_name,
        email=user.email,
        institution_id=profile.institution_id,
        current_verified_revision=curr_dto,
        revision_history=rev_dtos,
    )


@router.post("/students/import-preview")
async def import_preview(
    req: CSVPreviewRequest,
    auth: AuthContext = Depends(require_capability("student:import")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Parse and validate student CSV upload without making mutations."""
    report = await StudentImportService.preview_csv(
        institution_id=auth.institution_id,
        csv_text=req.csv_content,
        db=db,
    )
    return {
        "preview_token": report.preview_token,
        "total_rows": report.total_rows,
        "valid_rows_count": report.valid_rows_count,
        "invalid_rows_count": report.invalid_rows_count,
        "new_students_count": report.new_students_count,
        "updating_students_count": report.updating_students_count,
        "sample_rows": report.sample_rows,
        "invalid_rows": report.invalid_rows,
    }


@router.post("/students/import-commit")
async def import_commit(
    req: CSVCommitRequest,
    auth: AuthContext = Depends(require_capability("student:import")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Commit verified previewed students into database with immutable revisions."""
    return await StudentImportService.commit_preview(
        preview_token=req.preview_token,
        institution_id=auth.institution_id,
        committer_membership_id=auth.membership_id,
        committer_user_id=auth.user_id,
        db=db,
    )


# --- Student Self-Service Portal Endpoints ---


@router.get("/student/me", response_model=StudentDetailDTO)
async def get_my_student_profile(
    auth: AuthContext = Depends(get_current_auth),
    db: AsyncSession = Depends(get_db),
) -> StudentDetailDTO:
    """Student self-service view returning own verified record and history."""
    profile_res = await db.execute(
        select(StudentProfile).where(
            StudentProfile.institution_id == auth.institution_id,
            StudentProfile.user_id == auth.user_id,
        )
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise NotFoundException("Student profile not found for this account")

    rev_res = await db.execute(
        select(AcademicRecordRevision)
        .where(AcademicRecordRevision.student_profile_id == profile.id)
        .order_by(desc(AcademicRecordRevision.revision_number))
    )
    revisions = rev_res.scalars().all()

    rev_dtos = [
        AcademicRevisionDTO(
            id=r.id,
            revision_number=r.revision_number,
            source=r.source,
            source_reference=r.source_reference,
            is_verified=r.is_verified,
            verified_at=r.verified_at,
            branch=r.branch,
            cgpa=float(r.cgpa),
            cgpa_scale=float(r.cgpa_scale),
            graduation_year=r.graduation_year,
            active_backlogs=r.active_backlogs,
            history_backlogs=r.history_backlogs,
            created_at=r.created_at,
        )
        for r in revisions
    ]

    curr_dto = next((r for r in rev_dtos if r.id == profile.current_academic_revision_id), None)

    return StudentDetailDTO(
        id=profile.id,
        student_identifier=profile.student_identifier,
        full_name=auth.full_name,
        email=auth.email,
        institution_id=profile.institution_id,
        current_verified_revision=curr_dto,
        revision_history=rev_dtos,
    )


@router.post("/student/corrections", response_model=CorrectionProposalDTO)
async def submit_correction_proposal(
    req: CorrectionProposalCreateRequest,
    auth: AuthContext = Depends(get_current_auth),
    db: AsyncSession = Depends(get_db),
) -> CorrectionProposalDTO:
    """Student submits a correction proposal for academic facts (P02-T06)."""
    profile_res = await db.execute(
        select(StudentProfile).where(
            StudentProfile.institution_id == auth.institution_id,
            StudentProfile.user_id == auth.user_id,
        )
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise NotFoundException("Student profile not found for this account")

    proposal = StudentCorrectionProposal(
        institution_id=auth.institution_id,
        student_profile_id=profile.id,
        proposed_by_user_id=auth.user_id,
        proposed_changes=req.proposed_changes,
        justification=req.justification,
        supporting_document_url=req.supporting_document_url,
        status="pending",
    )
    db.add(proposal)
    await db.flush()

    audit = AuditLog(
        institution_id=auth.institution_id,
        actor_user_id=auth.user_id,
        actor_membership_id=auth.membership_id,
        action="student:correction_submitted",
        target_type="correction_proposal",
        target_id=str(proposal.id),
        payload={"proposed_changes": req.proposed_changes},
    )
    db.add(audit)
    await db.commit()

    return CorrectionProposalDTO(
        id=proposal.id,
        student_profile_id=profile.id,
        student_identifier=profile.student_identifier,
        student_name=auth.full_name,
        proposed_changes=proposal.proposed_changes,
        justification=proposal.justification,
        supporting_document_url=proposal.supporting_document_url,
        status=proposal.status,
        review_notes=proposal.review_notes,
        decided_at=proposal.decided_at,
        created_at=proposal.created_at,
    )


@router.get("/student/corrections", response_model=list[CorrectionProposalDTO])
async def list_my_corrections(
    auth: AuthContext = Depends(get_current_auth),
    db: AsyncSession = Depends(get_db),
) -> list[CorrectionProposalDTO]:
    """Student self-service view to track status of their own correction proposals."""
    profile_res = await db.execute(
        select(StudentProfile).where(
            StudentProfile.institution_id == auth.institution_id,
            StudentProfile.user_id == auth.user_id,
        )
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return []

    res = await db.execute(
        select(StudentCorrectionProposal)
        .where(
            StudentCorrectionProposal.institution_id == auth.institution_id,
            StudentCorrectionProposal.student_profile_id == profile.id,
        )
        .order_by(desc(StudentCorrectionProposal.created_at))
    )
    proposals = res.scalars().all()

    return [
        CorrectionProposalDTO(
            id=prop.id,
            student_profile_id=profile.id,
            student_identifier=profile.student_identifier,
            student_name=auth.full_name,
            proposed_changes=prop.proposed_changes,
            justification=prop.justification,
            supporting_document_url=prop.supporting_document_url,
            status=prop.status,
            review_notes=prop.review_notes,
            decided_at=prop.decided_at,
            created_at=prop.created_at,
        )
        for prop in proposals
    ]


@router.get("/students/corrections/pending", response_model=list[CorrectionProposalDTO])
async def list_pending_corrections(
    auth: AuthContext = Depends(require_capability("student:read")),
    db: AsyncSession = Depends(get_db),
) -> list[CorrectionProposalDTO]:
    """Coordinator view of pending correction proposals awaiting decision."""
    query = (
        select(StudentCorrectionProposal)
        .where(
            StudentCorrectionProposal.institution_id == auth.institution_id,
            StudentCorrectionProposal.status == "pending",
        )
        .order_by(StudentCorrectionProposal.created_at)
    )
    res = await db.execute(query)
    proposals = res.scalars().all()

    dtos: list[CorrectionProposalDTO] = []
    for prop in proposals:
        prof_res = await db.execute(
            select(StudentProfile).where(StudentProfile.id == prop.student_profile_id)
        )
        profile = prof_res.scalar_one()

        user_res = await db.execute(select(User).where(User.id == profile.user_id))
        user = user_res.scalar_one()

        dtos.append(
            CorrectionProposalDTO(
                id=prop.id,
                student_profile_id=profile.id,
                student_identifier=profile.student_identifier,
                student_name=user.full_name,
                proposed_changes=prop.proposed_changes,
                justification=prop.justification,
                supporting_document_url=prop.supporting_document_url,
                status=prop.status,
                review_notes=prop.review_notes,
                decided_at=prop.decided_at,
                created_at=prop.created_at,
            )
        )

    return dtos


@router.post("/students/corrections/{proposal_id}/decide", response_model=CorrectionProposalDTO)
async def decide_correction_proposal(
    proposal_id: uuid.UUID,
    req: CorrectionDecisionRequest,
    auth: AuthContext = Depends(require_capability("student:read")),
    db: AsyncSession = Depends(get_db),
) -> CorrectionProposalDTO:
    """Coordinator accepts or rejects correction proposal with evidence (P02-T06)."""
    prop_res = await db.execute(
        select(StudentCorrectionProposal).where(
            StudentCorrectionProposal.id == proposal_id,
            StudentCorrectionProposal.institution_id == auth.institution_id,
        )
    )
    proposal = prop_res.scalar_one_or_none()
    if not proposal:
        raise NotFoundException(f"Correction proposal {proposal_id} not found")

    if proposal.status != "pending":
        raise BadRequestException(f"Proposal has already been {proposal.status}")

    prof_res = await db.execute(
        select(StudentProfile).where(StudentProfile.id == proposal.student_profile_id)
    )
    profile = prof_res.scalar_one()

    user_res = await db.execute(select(User).where(User.id == profile.user_id))
    user = user_res.scalar_one()

    now = datetime.now(UTC)
    proposal.status = req.decision
    proposal.review_notes = req.review_notes
    proposal.decided_at = now
    proposal.decided_by_membership_id = auth.membership_id

    if req.decision == "approved":
        # Load current verified revision to carry forward unchanged fields
        curr_rev_res = await db.execute(
            select(AcademicRecordRevision).where(
                AcademicRecordRevision.id == profile.current_academic_revision_id
            )
        )
        curr_rev = curr_rev_res.scalar_one_or_none()

        branch = proposal.proposed_changes.get("branch", curr_rev.branch if curr_rev else "CSE")
        cgpa_raw = proposal.proposed_changes.get("cgpa", str(curr_rev.cgpa) if curr_rev else "0.00")
        scale_raw = proposal.proposed_changes.get(
            "scale", str(curr_rev.cgpa_scale) if curr_rev else "10.00"
        )
        grad_year = proposal.proposed_changes.get(
            "graduation_year", curr_rev.graduation_year if curr_rev else 2027
        )
        backlog = proposal.proposed_changes.get(
            "active_backlogs", curr_rev.active_backlogs if curr_rev else None
        )

        latest_num_res = await db.execute(
            select(AcademicRecordRevision.revision_number)
            .where(AcademicRecordRevision.student_profile_id == profile.id)
            .order_by(desc(AcademicRecordRevision.revision_number))
            .limit(1)
        )
        latest_num = latest_num_res.scalar_one_or_none() or 0

        new_revision = AcademicRecordRevision(
            institution_id=auth.institution_id,
            student_profile_id=profile.id,
            revision_number=latest_num + 1,
            source="correction_request",
            source_reference=str(proposal.id),
            is_verified=True,
            verified_at=now,
            verified_by_membership_id=auth.membership_id,
            branch=branch.upper(),
            cgpa=decimal.Decimal(str(cgpa_raw)),
            cgpa_scale=decimal.Decimal(str(scale_raw)),
            graduation_year=int(grad_year),
            active_backlogs=int(backlog) if backlog is not None else None,
        )
        db.add(new_revision)
        await db.flush()

        profile.current_academic_revision_id = new_revision.id
        proposal.resulting_revision_id = new_revision.id
        await db.flush()

    audit = AuditLog(
        institution_id=auth.institution_id,
        actor_user_id=auth.user_id,
        actor_membership_id=auth.membership_id,
        action=f"student:correction_{req.decision}",
        target_type="correction_proposal",
        target_id=str(proposal.id),
        payload={"decision": req.decision, "review_notes": req.review_notes},
    )
    db.add(audit)
    await db.commit()

    return CorrectionProposalDTO(
        id=proposal.id,
        student_profile_id=profile.id,
        student_identifier=profile.student_identifier,
        student_name=user.full_name,
        proposed_changes=proposal.proposed_changes,
        justification=proposal.justification,
        supporting_document_url=proposal.supporting_document_url,
        status=proposal.status,
        review_notes=proposal.review_notes,
        decided_at=proposal.decided_at,
        created_at=proposal.created_at,
    )
