"""Companies and Recruitment Drives API Endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import ConflictException, NotFoundException
from placementos.models.recruitment import Company, Drive, DriveRevision
from placementos.schemas.drives import (
    CompanyCreate,
    CompanyResponse,
    DriveCreate,
    DriveListResponse,
    DriveResponse,
    DriveRevisionCreate,
    DriveRevisionResponse,
    DriveUpdate,
    SourceArtifactSummary,
)
from placementos.services.session import AuthContext

router = APIRouter(tags=["Recruitment Drives"])


@router.post("/companies", response_model=CompanyResponse, status_code=201)
async def create_company(
    payload: CompanyCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    """Register a new hiring company within the active institution."""
    auth.require_coordinator()

    # Check for duplicate company name within institution
    stmt = select(Company).where(
        Company.institution_id == auth.institution_id,
        func.lower(Company.name) == payload.name.lower().strip(),
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        raise ConflictException(f"Company with name '{payload.name}' already exists in this institution")

    company = Company(
        institution_id=auth.institution_id,
        name=payload.name.strip(),
        industry=payload.industry.strip() if payload.industry else None,
        website=payload.website.strip() if payload.website else None,
        contact_email=payload.contact_email.strip() if payload.contact_email else None,
    )
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return CompanyResponse.model_validate(company)


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[CompanyResponse]:
    """List all registered hiring companies for the active institution."""
    stmt = (
        select(Company)
        .where(Company.institution_id == auth.institution_id)
        .order_by(Company.name.asc())
    )
    result = await session.execute(stmt)
    companies = result.scalars().all()
    return [CompanyResponse.model_validate(c) for c in companies]


@router.post("/drives", response_model=DriveResponse, status_code=201)
async def create_drive(
    payload: DriveCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DriveResponse:
    """Create a new recruitment drive and initialize revision 1."""
    auth.require_coordinator()

    # Validate company exists and belongs to institution
    company_stmt = select(Company).where(
        Company.id == payload.company_id,
        Company.institution_id == auth.institution_id,
    )
    company = (await session.execute(company_stmt)).scalar_one_or_none()
    if not company:
        raise NotFoundException(f"Company '{payload.company_id}' not found in active institution")

    drive = Drive(
        institution_id=auth.institution_id,
        company_id=payload.company_id,
        title=payload.title.strip(),
        status="draft",
        created_by_membership_id=auth.membership_id,
        concurrency_revision=1,
    )
    session.add(drive)
    await session.flush()

    # Initialize Revision 1
    initial_revision = DriveRevision(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        revision_number=1,
        role_title=drive.title,
        job_description_raw=payload.description.strip() if payload.description else None,
        employment_type="full_time",
        compensation_details={"academic_year": payload.academic_year},
        created_by_membership_id=auth.membership_id,
    )
    session.add(initial_revision)
    await session.flush()

    drive.current_drive_revision_id = initial_revision.id
    await session.commit()

    return await _build_drive_response(session, drive.id, auth.institution_id)


@router.get("/drives", response_model=DriveListResponse)
async def list_drives(
    status: str | None = None,
    company_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DriveListResponse:
    """List recruitment drives with optional status filtering and pagination."""
    query = select(Drive).where(Drive.institution_id == auth.institution_id)

    if status:
        query = query.where(Drive.status == status)
    if company_id:
        query = query.where(Drive.company_id == company_id)

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    # Fetch page
    offset = (page - 1) * limit
    paginated_stmt = (
        query.order_by(desc(Drive.created_at))
        .offset(offset)
        .limit(limit)
        .options(
            selectinload(Drive.company),
            selectinload(Drive.revisions),
            selectinload(Drive.source_artifacts),
        )
    )
    drives = (await session.execute(paginated_stmt)).scalars().all()

    items = []
    for d in drives:
        items.append(_format_drive(d))

    return DriveListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/drives/{drive_id}", response_model=DriveResponse)
async def get_drive(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DriveResponse:
    """Fetch single drive detail with all revisions and associated source artifacts."""
    return await _build_drive_response(session, drive_id, auth.institution_id)


@router.patch("/drives/{drive_id}", response_model=DriveResponse)
async def update_drive(
    drive_id: uuid.UUID,
    payload: DriveUpdate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DriveResponse:
    """Update basic metadata or lifecycle status of a drive."""
    auth.require_coordinator()

    stmt = select(Drive).where(
        Drive.id == drive_id,
        Drive.institution_id == auth.institution_id,
    )
    drive = (await session.execute(stmt)).scalar_one_or_none()
    if not drive:
        raise NotFoundException(f"Drive '{drive_id}' not found")

    if payload.title is not None:
        drive.title = payload.title.strip()
    if payload.status is not None:
        drive.status = payload.status

    await session.commit()
    return await _build_drive_response(session, drive_id, auth.institution_id)


@router.post("/drives/{drive_id}/revisions", response_model=DriveRevisionResponse, status_code=201)
async def create_drive_revision(
    drive_id: uuid.UUID,
    payload: DriveRevisionCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DriveRevisionResponse:
    """Create a new versioned revision with optimistic concurrency control."""
    auth.require_coordinator()

    stmt = (
        select(Drive)
        .where(
            Drive.id == drive_id,
            Drive.institution_id == auth.institution_id,
        )
        .with_for_update()
    )
    drive = (await session.execute(stmt)).scalar_one_or_none()
    if not drive:
        raise NotFoundException(f"Drive '{drive_id}' not found")

    if drive.concurrency_revision != payload.expected_revision_number:
        raise ConflictException(
            f"Concurrency conflict: expected revision {payload.expected_revision_number}, "
            f"but current drive revision is {drive.concurrency_revision}"
        )

    next_rev = drive.concurrency_revision + 1
    revision = DriveRevision(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        revision_number=next_rev,
        role_title=drive.title,
        job_description_raw=payload.change_summary.strip(),
        compensation_details=payload.proposed_changes,
        created_by_membership_id=auth.membership_id,
    )
    session.add(revision)
    drive.concurrency_revision = next_rev
    await session.flush()
    drive.current_drive_revision_id = revision.id
    await session.commit()
    await session.refresh(revision)

    return DriveRevisionResponse(
        id=revision.id,
        drive_id=revision.drive_id,
        revision_number=revision.revision_number,
        change_summary=revision.job_description_raw or "",
        proposed_changes=revision.compensation_details or {},
        created_by_user_id=auth.user_id,
        created_at=revision.created_at,
    )


def _format_drive(drive: Drive) -> DriveResponse:
    sorted_revs = sorted(drive.revisions or [], key=lambda r: r.revision_number, reverse=True)
    sorted_artifacts = sorted(drive.source_artifacts or [], key=lambda s: s.created_at, reverse=True)

    academic_year = "2026-2027"
    if sorted_revs and sorted_revs[0].compensation_details:
        academic_year = sorted_revs[0].compensation_details.get("academic_year", "2026-2027")

    rev_responses = [
        DriveRevisionResponse(
            id=r.id,
            drive_id=r.drive_id,
            revision_number=r.revision_number,
            change_summary=r.job_description_raw or "",
            proposed_changes=r.compensation_details or {},
            created_by_user_id=None,
            created_at=r.created_at,
        )
        for r in sorted_revs
    ]

    artifact_summaries = [
        SourceArtifactSummary(
            id=s.id,
            drive_id=s.drive_id,
            source_type=s.source_kind,
            original_filename=s.file_name,
            status="extracted" if s.acceptance_status == "accepted" else ("failed" if s.acceptance_status == "rejected" else "pending"),
            hash_sha256=s.hash_sha256,
            byte_size=s.file_size_bytes,
            metadata_json={"scan_status": s.scan_status, "acceptance_status": s.acceptance_status},
            created_at=s.created_at,
        )
        for s in sorted_artifacts
    ]

    return DriveResponse(
        id=drive.id,
        institution_id=drive.institution_id,
        company_id=drive.company_id,
        company_name=drive.company.name if drive.company else "Unknown Company",
        academic_year=academic_year,
        status=drive.status,
        title=drive.title,
        description=sorted_revs[0].job_description_raw if sorted_revs else None,
        current_revision_number=drive.concurrency_revision,
        revisions=rev_responses,
        source_artifacts=artifact_summaries,
        created_at=drive.created_at,
        updated_at=drive.updated_at,
    )


async def _build_drive_response(
    session: AsyncSession,
    drive_id: uuid.UUID,
    institution_id: uuid.UUID,
) -> DriveResponse:
    """Helper to query and format full drive response with tenant isolation."""
    stmt = (
        select(Drive)
        .where(Drive.id == drive_id, Drive.institution_id == institution_id)
        .options(
            selectinload(Drive.company),
            selectinload(Drive.revisions),
            selectinload(Drive.source_artifacts),
        )
    )
    drive = (await session.execute(stmt)).scalar_one_or_none()
    if not drive:
        raise NotFoundException(f"Drive '{drive_id}' not found")

    return _format_drive(drive)
