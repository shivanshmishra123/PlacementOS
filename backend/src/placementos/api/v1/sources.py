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
from placementos.core.errors import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from placementos.models.storage import DomainJob, SourceArtifact, TextExtraction, UploadSession
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
from placementos.services.audit import record_audit
from placementos.services.authorization import load_authorized_drive
from placementos.services.parsers import DocumentScanner, MalwareScanner, ParseError
from placementos.services.session import AuthContext
from placementos.services.source_jobs import SourceJobService
from placementos.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Source Intake & Extraction"])


def _format_source_artifact(artifact: SourceArtifact) -> SourceArtifactResponse:
    ext = artifact.file_name.split(".")[-1] if "." in artifact.file_name else "txt"
    completed = any(item.status == "completed" for item in artifact.extractions)
    status_str = "extracted" if completed else (
        "failed" if artifact.acceptance_status == "rejected" else "processing"
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
        drive_id=artifact.drive_id,
        source_type=source_type_str,
        original_filename=artifact.file_name,
        file_extension=ext,
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

    await load_authorized_drive(session, auth, payload.drive_id)

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
    record_audit(
        session,
        auth,
        "source:upload_session_created",
        "upload_session",
        upload_session.id,
        {"drive_id": str(payload.drive_id), "purpose": payload.purpose},
    )
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
    if not upload_session or upload_session.owner_membership_id != auth.membership_id:
        raise NotFoundException(f"UploadSession '{session_id}' not found")

    if upload_session.drive_id is None:
        raise BadRequestException("Upload session has no drive scope")
    await load_authorized_drive(session, auth, upload_session.drive_id)

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
    if upload_session.expires_at <= datetime.now(UTC):
        upload_session.status = "expired"
        await session.commit()
        raise ConflictException("Upload session has expired")
    if upload_session.status != "pending":
        raise ConflictException(f"Upload session cannot be completed from state '{upload_session.status}'")

    upload_session.status = "validating"
    await session.flush()

    # Extract extension from filename
    raw_ext = upload_session.file_name.split(".")[-1] if "." in upload_session.file_name else ""
    ext = f".{raw_ext.lower()}" if raw_ext else ""

    try:
        data, actual_content_type, actual_size = storage_service.inspect_quarantine_object(
            upload_session.quarantine_key, auth.institution_id
        )
        if actual_size != upload_session.file_size_bytes:
            raise BadRequestException(
                "Uploaded byte size does not match the declared upload session size",
                details={"declared": upload_session.file_size_bytes, "actual": actual_size},
            )
        if actual_content_type and actual_content_type != upload_session.content_type:
            raise BadRequestException(
                "Uploaded content type does not match the declared upload session type",
                details={"declared": upload_session.content_type, "actual": actual_content_type},
            )
        DocumentScanner.scan_bytes(data, raw_ext)
        scan_status = MalwareScanner.scan(data)
        accepted_key, hash_sha256, actual_size, _ = storage_service.promote_quarantine_to_accepted(
            quarantine_key=upload_session.quarantine_key,
            institution_id=auth.institution_id,
            purpose=upload_session.purpose,
            extension=ext,
            content_type=upload_session.content_type,
            validated_data=data,
        )
    except FileNotFoundError as err:
        upload_session.status = "rejected"
        await session.commit()
        raise BadRequestException(
            f"File was not received in quarantine storage before completion was signaled: {err}"
        ) from err
    except (ParseError, BadRequestException) as err:
        upload_session.status = "rejected"
        record_audit(
            session,
            auth,
            "source:upload_rejected",
            "upload_session",
            upload_session.id,
            {"reason": str(err)},
        )
        await session.commit()
        if isinstance(err, ParseError):
            raise BadRequestException(err.message, details={"error_code": err.code}) from err
        raise

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
        scan_status=scan_status,
        acceptance_status="accepted",
        created_by_membership_id=auth.membership_id,
    )
    session.add(artifact)
    await session.flush()

    # Create DomainJob and run extraction
    await SourceJobService.create_extraction_job(session, artifact)
    record_audit(
        session,
        auth,
        "source:accepted",
        "source_artifact",
        artifact.id,
        {"drive_id": str(upload_session.drive_id), "sha256": hash_sha256},
    )
    await session.commit()
    from placementos.workers.source_tasks import extract_source_text_task

    extract_source_text_task.delay(str(artifact.id), str(auth.institution_id))

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

    await load_authorized_drive(session, auth, drive_id)

    raw_bytes = payload.raw_text.strip().encode("utf-8")
    DocumentScanner.scan_bytes(raw_bytes, "txt")
    scan_status = MalwareScanner.scan(raw_bytes)
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
        scan_status=scan_status,
        acceptance_status="accepted",
        created_by_membership_id=auth.membership_id,
    )
    session.add(artifact)
    await session.flush()

    await SourceJobService.create_extraction_job(session, artifact)
    record_audit(
        session,
        auth,
        "source:accepted",
        "source_artifact",
        artifact.id,
        {"drive_id": str(drive_id), "source_kind": "pasted_email"},
    )
    await session.commit()
    from placementos.workers.source_tasks import extract_source_text_task

    extract_source_text_task.delay(str(artifact.id), str(auth.institution_id))

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
    if artifact.drive_id:
        await load_authorized_drive(session, auth, artifact.drive_id)

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
    artifact = await session.get(SourceArtifact, source_artifact_id)
    if artifact and artifact.drive_id:
        await load_authorized_drive(session, auth, artifact.drive_id)

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
    if artifact.acceptance_status != "accepted":
        raise ForbiddenException("Only validated accepted sources can be downloaded")
    if artifact.drive_id:
        await load_authorized_drive(session, auth, artifact.drive_id)

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
    if artifact.drive_id:
        await load_authorized_drive(session, auth, artifact.drive_id)
    if artifact.acceptance_status != "accepted":
        raise ConflictException("Rejected or unvalidated sources cannot be extracted")

    job = await SourceJobService.create_extraction_job(session, artifact)
    if job.status in {"failed_retryable", "failed_terminal"}:
        job.status = "queued"
        job.error_details = None
    await session.commit()
    from placementos.workers.source_tasks import extract_source_text_task

    extract_source_text_task.delay(str(artifact.id), str(auth.institution_id))

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


@router.get("/jobs/{job_id}", response_model=DomainJobResponse)
async def get_domain_job(
    job_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DomainJobResponse:
    job = (
        await session.execute(
            select(DomainJob).where(
                DomainJob.id == job_id,
                DomainJob.institution_id == auth.institution_id,
            )
        )
    ).scalar_one_or_none()
    if not job:
        raise NotFoundException(f"Job '{job_id}' not found")
    if job.resource_type == "source_artifact":
        artifact = await session.get(SourceArtifact, job.resource_id)
        if artifact and artifact.drive_id:
            await load_authorized_drive(session, auth, artifact.drive_id)
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
        completed_at=job.updated_at if job.status in {"completed", "failed_terminal"} else None,
        created_at=job.created_at,
    )
