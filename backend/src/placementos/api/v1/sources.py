"""Source Intake, Upload Sessions, and Text Extraction Endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import BadRequestException, ConflictException, NotFoundException
from placementos.models.recruitment import Drive
from placementos.models.storage import SourceArtifact, TextExtraction, UploadSession
from placementos.schemas.storage import (
    DomainJobResponse,
    DownloadUrlResponse,
    PastedSourceCreate,
    SourceArtifactResponse,
    TextExtractionResponse,
    TextLocatorSchema,
    UploadSessionCreate,
    UploadSessionResponse,
)
from placementos.services.parsers import ParseError
from placementos.services.session import AuthContext
from placementos.services.source_jobs import SourceJobService
from placementos.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Source Intake & Extraction"])


def _format_source_artifact(artifact: SourceArtifact) -> SourceArtifactResponse:
    ext = artifact.file_name.split(".")[-1] if "." in artifact.file_name else "txt"
    status_str = "extracted" if artifact.acceptance_status == "accepted" else (
        "failed" if artifact.acceptance_status == "rejected" else "pending"
    )

    source_type_str = "pasted_text" if artifact.source_kind in ("pasted_email", "pasted_text") else "file_upload"

    error_code = None
    error_message = None
    if artifact.extractions:
        for ext_rec in artifact.extractions:
            if ext_rec.status == "failed":
                error_code = "MIMETYPE_MISMATCH" if "header" in (ext_rec.error_message or "").lower() or "executable" in (ext_rec.error_message or "").lower() or "extension" in (ext_rec.error_message or "").lower() else "CORRUPT_FILE"
                error_message = ext_rec.error_message

    return SourceArtifactResponse(
        id=artifact.id,
        institution_id=artifact.institution_id,
        drive_id=artifact.drive_id or uuid.uuid4(),
        source_type=source_type_str,
        original_filename=artifact.file_name,
        file_extension=ext,
        storage_key=artifact.object_key,
        hash_sha256=artifact.hash_sha256,
        byte_size=artifact.file_size_bytes,
        status=status_str,
        metadata_json={
            "scan_status": artifact.scan_status,
            "acceptance_status": artifact.acceptance_status,
            "error_code": error_code,
            "error_message": error_message,
        },
        created_at=artifact.created_at,
        extracted_at=artifact.updated_at,
    )


@router.post("/uploads/sessions", response_model=UploadSessionResponse, status_code=201)
async def create_upload_session(
    payload: UploadSessionCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> UploadSessionResponse:
    """Create an isolated quarantine upload session with presigned S3 upload URL."""
    auth.require_coordinator()

    # Validate drive exists and belongs to active institution
    drive_stmt = select(Drive).where(
        Drive.id == payload.drive_id,
        Drive.institution_id == auth.institution_id,
    )
    drive = (await session.execute(drive_stmt)).scalar_one_or_none()
    if not drive:
        raise NotFoundException(f"Drive '{payload.drive_id}' not found in active institution")

    session_id = uuid.uuid4()
    storage_key = storage_service.build_quarantine_key(
        institution_id=auth.institution_id,
        purpose=payload.purpose,
        session_id=session_id,
        filename=payload.original_filename,
    )
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    # Generate presigned PUT URL
    upload_url = storage_service.generate_presigned_upload_url(
        storage_key=storage_key,
        institution_id=auth.institution_id,
        expires_in=900,
    )

    upload_session = UploadSession(
        id=session_id,
        institution_id=auth.institution_id,
        owner_user_id=auth.user_id,
        owner_membership_id=auth.membership_id,
        purpose=payload.purpose,
        drive_id=payload.drive_id,
        quarantine_key=storage_key,
        file_name=payload.original_filename,
        file_size_bytes=payload.byte_size,
        content_type=payload.content_type,
        status="pending",
        expires_at=expires_at,
    )
    session.add(upload_session)
    await session.commit()
    await session.refresh(upload_session)

    return UploadSessionResponse(
        id=upload_session.id,
        drive_id=upload_session.drive_id,
        purpose=upload_session.purpose,
        original_filename=upload_session.file_name,
        storage_key=upload_session.quarantine_key,
        upload_url=upload_url,
        expires_at=upload_session.expires_at,
        status=upload_session.status,
        created_at=upload_session.created_at,
    )


@router.post("/uploads/sessions/{session_id}/complete", response_model=SourceArtifactResponse, status_code=201)
async def complete_upload_session(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> SourceArtifactResponse:
    """Promote quarantine bytes to accepted storage, hash content, and trigger text extraction."""
    auth.require_coordinator()

    stmt = (
        select(UploadSession)
        .where(
            UploadSession.id == session_id,
            UploadSession.institution_id == auth.institution_id,
        )
        .with_for_update()
    )
    upload_session = (await session.execute(stmt)).scalar_one_or_none()
    if not upload_session:
        raise NotFoundException(f"UploadSession '{session_id}' not found")

    if upload_session.status == "completed":
        art_stmt = (
            select(SourceArtifact)
            .where(SourceArtifact.upload_session_id == session_id)
            .options(selectinload(SourceArtifact.extractions))
        )
        existing = (await session.execute(art_stmt)).scalar_one_or_none()
        if existing:
            return _format_source_artifact(existing)
        raise ConflictException("Upload session is already completed")

    # Extract extension from filename
    raw_ext = upload_session.file_name.split(".")[-1] if "." in upload_session.file_name else ""
    ext = f".{raw_ext.lower()}" if raw_ext else ""

    # Promote bytes: read quarantine, compute hash, save to accepted storage, delete quarantine
    try:
        accepted_key, hash_sha256, actual_size, _ = storage_service.promote_quarantine_to_accepted(
            quarantine_key=upload_session.quarantine_key,
            institution_id=auth.institution_id,
            purpose=upload_session.purpose,
            extension=ext,
            content_type=upload_session.content_type,
        )
    except FileNotFoundError as err:
        raise BadRequestException(
            f"File was not received in quarantine storage before completion was signaled: {err}"
        ) from err

    upload_session.status = "completed"
    upload_session.accepted_key = accepted_key

    artifact = SourceArtifact(
        institution_id=auth.institution_id,
        drive_id=upload_session.drive_id,
        upload_session_id=upload_session.id,
        source_kind="jd_upload",
        object_key=accepted_key,
        file_name=upload_session.file_name,
        media_type=upload_session.content_type,
        file_size_bytes=actual_size,
        hash_sha256=hash_sha256,
        scan_status="clean",
        acceptance_status="accepted",
        created_by_membership_id=auth.membership_id,
    )
    session.add(artifact)
    await session.flush()

    # Create DomainJob and run extraction
    await SourceJobService.create_extraction_job(session, artifact)
    await session.commit()

    # Run extraction synchronously
    try:
        await SourceJobService.run_extraction(
            source_artifact_id=artifact.id,
            institution_id=auth.institution_id,
            session=session,
        )
        await session.commit()
    except ParseError as parse_err:
        logger.warning("Document parsing failed with error code %s: %s", parse_err.code, parse_err.message)
        await session.commit()
    except Exception as exc:
        logger.error("Unexpected error during text extraction: %s", exc)
        await session.commit()

    # Fetch updated artifact with extractions
    art_stmt = (
        select(SourceArtifact)
        .where(SourceArtifact.id == artifact.id)
        .options(selectinload(SourceArtifact.extractions))
    )
    fresh_artifact = (await session.execute(art_stmt)).scalar_one()
    return _format_source_artifact(fresh_artifact)


@router.post("/drives/{drive_id}/sources/pasted", response_model=SourceArtifactResponse, status_code=201)
async def create_pasted_source(
    drive_id: uuid.UUID,
    payload: PastedSourceCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> SourceArtifactResponse:
    """Intake raw pasted job description or email text into accepted storage and run extraction."""
    auth.require_coordinator()

    # Validate drive exists and belongs to active institution
    drive_stmt = select(Drive).where(
        Drive.id == drive_id,
        Drive.institution_id == auth.institution_id,
    )
    drive = (await session.execute(drive_stmt)).scalar_one_or_none()
    if not drive:
        raise NotFoundException(f"Drive '{drive_id}' not found in active institution")

    raw_bytes = payload.raw_text.strip().encode("utf-8")
    accepted_key, hash_sha256, byte_size = storage_service.store_accepted_bytes(
        data=raw_bytes,
        institution_id=auth.institution_id,
        purpose="jd_intake",
        extension=".txt",
        content_type="text/plain; charset=utf-8",
    )

    artifact = SourceArtifact(
        institution_id=auth.institution_id,
        drive_id=drive_id,
        source_kind="pasted_email",
        object_key=accepted_key,
        file_name=payload.title.strip(),
        media_type="text/plain",
        file_size_bytes=byte_size,
        hash_sha256=hash_sha256,
        scan_status="clean",
        acceptance_status="accepted",
        created_by_membership_id=auth.membership_id,
    )
    session.add(artifact)
    await session.flush()

    await SourceJobService.create_extraction_job(session, artifact)
    await session.commit()

    # Execute extraction
    try:
        await SourceJobService.run_extraction(
            source_artifact_id=artifact.id,
            institution_id=auth.institution_id,
            session=session,
        )
        await session.commit()
    except ParseError as parse_err:
        logger.warning("Pasted text extraction encountered ParseError %s: %s", parse_err.code, parse_err.message)
        await session.commit()

    # Fetch updated artifact with extractions
    art_stmt = (
        select(SourceArtifact)
        .where(SourceArtifact.id == artifact.id)
        .options(selectinload(SourceArtifact.extractions))
    )
    fresh_artifact = (await session.execute(art_stmt)).scalar_one()
    return _format_source_artifact(fresh_artifact)


@router.get("/sources/{source_artifact_id}", response_model=SourceArtifactResponse)
async def get_source_artifact(
    source_artifact_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> SourceArtifactResponse:
    """Retrieve metadata and extraction status for a source artifact."""
    stmt = (
        select(SourceArtifact)
        .where(
            SourceArtifact.id == source_artifact_id,
            SourceArtifact.institution_id == auth.institution_id,
        )
        .options(selectinload(SourceArtifact.extractions))
    )
    artifact = (await session.execute(stmt)).scalar_one_or_none()
    if not artifact:
        raise NotFoundException(f"Source artifact '{source_artifact_id}' not found")

    return _format_source_artifact(artifact)


@router.get("/sources/{source_artifact_id}/extractions", response_model=TextExtractionResponse)
async def get_text_extraction(
    source_artifact_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> TextExtractionResponse:
    """Retrieve extracted text and precise page/paragraph locators for a source artifact."""
    stmt = select(TextExtraction).where(
        TextExtraction.source_artifact_id == source_artifact_id,
        TextExtraction.institution_id == auth.institution_id,
    )
    extraction = (await session.execute(stmt)).scalar_one_or_none()
    if not extraction:
        raise NotFoundException(f"Extraction not found for source artifact '{source_artifact_id}'")

    loc_schemas = [
        TextLocatorSchema(
            locator_type=loc.get("locator_type", "paragraph"),
            page_number=loc.get("page_number"),
            paragraph_index=loc.get("paragraph_index", 0),
            char_offset_start=loc.get("char_offset_start", 0),
            char_offset_end=loc.get("char_offset_end", 0),
            preview=loc.get("preview", ""),
        )
        for loc in (extraction.locators or [])
    ]

    return TextExtractionResponse(
        id=extraction.id,
        source_artifact_id=extraction.source_artifact_id,
        institution_id=extraction.institution_id,
        extracted_text=extraction.extracted_text,
        char_count=len(extraction.extracted_text),
        locators=loc_schemas,
        page_count=extraction.page_count,
        paragraph_count=len(loc_schemas),
        parser_version=extraction.parser_version,
        is_empty_or_scanned=extraction.is_empty_or_scanned,
        created_at=extraction.created_at,
    )


@router.get("/sources/{source_artifact_id}/download-url", response_model=DownloadUrlResponse)
async def get_download_url(
    source_artifact_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DownloadUrlResponse:
    """Generate a temporary presigned download URL for accepted source file bytes (5-min TTL)."""
    stmt = select(SourceArtifact).where(
        SourceArtifact.id == source_artifact_id,
        SourceArtifact.institution_id == auth.institution_id,
    )
    artifact = (await session.execute(stmt)).scalar_one_or_none()
    if not artifact:
        raise NotFoundException(f"Source artifact '{source_artifact_id}' not found")

    download_url = storage_service.generate_presigned_download_url(
        storage_key=artifact.object_key,
        institution_id=auth.institution_id,
        filename=artifact.file_name,
        expires_in=300,
    )

    return DownloadUrlResponse(
        download_url=download_url,
        expires_in=300,
        filename=artifact.file_name,
    )


@router.post("/sources/{source_artifact_id}/extract", response_model=DomainJobResponse)
async def retrigger_extraction(
    source_artifact_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DomainJobResponse:
    """Trigger or retry text extraction job for a source artifact."""
    auth.require_coordinator()

    stmt = select(SourceArtifact).where(
        SourceArtifact.id == source_artifact_id,
        SourceArtifact.institution_id == auth.institution_id,
    )
    artifact = (await session.execute(stmt)).scalar_one_or_none()
    if not artifact:
        raise NotFoundException(f"Source artifact '{source_artifact_id}' not found")

    job = await SourceJobService.create_extraction_job(session, artifact)
    await session.commit()

    # Run extraction
    try:
        await SourceJobService.run_extraction(
            source_artifact_id=artifact.id,
            institution_id=auth.institution_id,
            session=session,
        )
        await session.commit()
    except Exception as exc:
        logger.warning("Extraction re-trigger failed: %s", exc)
        await session.commit()

    await session.refresh(job)
    return DomainJobResponse(
        id=job.id,
        institution_id=job.institution_id,
        job_kind=job.job_kind,
        operation_key=job.operation_key,
        resource_id=job.resource_id,
        status=job.status,
        error_code=job.error_details.get("error_code") if job.error_details else None,
        error_detail=job.error_details.get("error_message") if job.error_details else None,
        attempt_count=job.attempts,
        started_at=job.created_at,
        completed_at=job.updated_at if job.status in ("completed", "failed") else None,
        created_at=job.created_at,
    )
