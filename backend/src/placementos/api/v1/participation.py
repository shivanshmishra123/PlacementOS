"""P06 student document, publication, readiness, and registration endpoints."""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import BadRequestException, ConflictException, NotFoundException
from placementos.models.eligibility import EligibilityResult, EvaluationRun
from placementos.models.identity import StudentProfile, User
from placementos.models.intelligence import ActionProposal, ApprovalDecision
from placementos.models.participation import (
    DocumentRevision,
    DriveDocumentRequirement,
    Registration,
    RegistrationEvent,
    StudentDocument,
)
from placementos.models.recruitment import Company, Drive, DriveRevision
from placementos.models.storage import UploadSession
from placementos.schemas.participation import (
    CoordinatorRegistrationAction,
    DocumentRevisionResponse,
    DocumentType,
    DocumentUploadSessionCreate,
    DocumentUploadSessionResponse,
    ParticipantListResponse,
    ParticipantResponse,
    PublicationDecisionCreate,
    PublicationProposalCreate,
    PublicationProposalResponse,
    ReadinessResponse,
    RegistrationResponse,
    RequirementReadinessResponse,
    RequirementResponse,
    RequirementSetCreate,
    StudentDriveResponse,
    WithdrawalCreate,
)
from placementos.schemas.storage import DownloadUrlResponse
from placementos.services.audit import record_audit
from placementos.services.authorization import load_authorized_drive
from placementos.services.eligibility_engine import canonical_hash
from placementos.services.parsers import DocumentScanner, MalwareScanner, ParseError, TextExtractor
from placementos.services.participation import (
    compute_readiness,
    current_published_result,
    load_student_profile,
    reconcile_registration_holds,
    registration_window_is_open,
    validate_current_documents_for_drive,
    validate_document_against_requirement,
)
from placementos.services.session import AuthContext
from placementos.services.storage import StorageSecurityError, storage_service

router = APIRouter(tags=["Participation and Documents"])


def _requirement_response(item: DriveDocumentRequirement) -> RequirementResponse:
    return RequirementResponse(
        id=item.id,
        drive_id=item.drive_id,
        drive_revision_id=item.drive_revision_id,
        document_type=cast(DocumentType, item.document_type),
        display_label=item.display_label,
        allowed_extensions=cast(list[Literal["pdf", "docx"]], item.allowed_extensions),
        max_size_bytes=item.max_size_bytes,
        filename_pattern=item.filename_pattern,
        required_stage=cast(Literal["registration", "scheduling"], item.required_stage),
        due_at=item.due_at,
        created_at=item.created_at,
    )


def _document_response(item: DocumentRevision, document_type: str) -> DocumentRevisionResponse:
    return DocumentRevisionResponse(
        id=item.id,
        document_type=cast(DocumentType, document_type),
        revision_number=item.revision_number,
        original_filename=item.original_filename,
        media_type=item.media_type,
        file_size_bytes=item.file_size_bytes,
        hash_sha256=item.hash_sha256,
        scan_status=item.scan_status,
        structure_status=item.structure_status,
        text_status=item.text_status,
        created_at=item.created_at,
    )


def _registration_response(item: Registration) -> RegistrationResponse:
    return RegistrationResponse(
        id=item.id,
        drive_id=item.drive_id,
        student_profile_id=item.student_profile_id,
        state=cast(Literal["draft", "submitted", "withdrawn", "eligibility_hold"], item.state),
        submitted_at=item.submitted_at,
        withdrawn_at=item.withdrawn_at,
        hold_reason=item.hold_reason,
        concurrency_revision=item.concurrency_revision,
    )


def _readiness_response(data: dict) -> ReadinessResponse:
    requirements = []
    for row in data["requirements"]:
        revision = row["current_document"]
        requirements.append(
            RequirementReadinessResponse(
                requirement_id=row["requirement_id"],
                document_type=row["document_type"],
                display_label=row["display_label"],
                required_stage=row["required_stage"],
                due_at=row["due_at"],
                status=row["status"],
                findings=row["findings"],
                current_document=(
                    _document_response(revision, row["document_type"]) if revision else None
                ),
            )
        )
    return ReadinessResponse(status=data["status"], requirements=requirements)


@router.put("/drives/{drive_id}/document-requirements", response_model=list[RequirementResponse])
async def set_document_requirements(
    drive_id: uuid.UUID,
    payload: RequirementSetCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[RequirementResponse]:
    auth.require_capability("drive:edit")
    drive = await load_authorized_drive(session, auth, drive_id, for_update=True)
    if drive.status != "draft":
        raise ConflictException("Document requirements can only be edited on a draft drive")
    if drive.concurrency_revision != payload.expected_drive_revision:
        raise ConflictException("The drive changed; reload before editing requirements")
    existing = (
        (
            await session.execute(
                select(DriveDocumentRequirement).where(
                    DriveDocumentRequirement.drive_revision_id == drive.current_drive_revision_id
                )
            )
        )
        .scalars()
        .all()
    )
    if existing:
        raise ConflictException("This immutable drive revision already has document requirements")
    created = []
    for requirement in payload.requirements:
        if requirement.filename_pattern:
            try:
                re.compile(requirement.filename_pattern)
            except re.error as exc:
                raise BadRequestException(f"Invalid filename pattern: {exc}") from exc
        item = DriveDocumentRequirement(
            institution_id=auth.institution_id,
            drive_id=drive.id,
            drive_revision_id=drive.current_drive_revision_id,
            created_by_membership_id=auth.membership_id,
            **requirement.model_dump(),
        )
        session.add(item)
        created.append(item)
    await session.flush()
    record_audit(
        session,
        auth,
        "drive:document_requirements_created",
        "drive",
        drive.id,
        {
            "drive_revision_id": str(drive.current_drive_revision_id),
            "document_types": [item.document_type for item in created],
        },
    )
    await session.commit()
    return [_requirement_response(item) for item in created]


@router.get("/drives/{drive_id}/document-requirements", response_model=list[RequirementResponse])
async def list_document_requirements(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[RequirementResponse]:
    drive = await load_authorized_drive(session, auth, drive_id)
    revision_id = drive.published_drive_revision_id or drive.current_drive_revision_id
    items = (
        (
            await session.execute(
                select(DriveDocumentRequirement).where(
                    DriveDocumentRequirement.drive_revision_id == revision_id
                )
            )
        )
        .scalars()
        .all()
    )
    return [_requirement_response(item) for item in items]


@router.post(
    "/drives/{drive_id}/publication-proposals",
    response_model=PublicationProposalResponse,
    status_code=201,
)
async def create_publication_proposal(
    drive_id: uuid.UUID,
    payload: PublicationProposalCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> PublicationProposalResponse:
    auth.require_capability("drive:edit")
    drive = await load_authorized_drive(session, auth, drive_id, for_update=True)
    if drive.concurrency_revision != payload.expected_drive_revision:
        raise ConflictException("The drive changed; reload before proposing publication")
    evaluation = (
        await session.execute(
            select(EvaluationRun).where(
                EvaluationRun.id == payload.evaluation_run_id,
                EvaluationRun.institution_id == auth.institution_id,
                EvaluationRun.drive_id == drive.id,
            )
        )
    ).scalar_one_or_none()
    if not evaluation or evaluation.status != "completed" or evaluation.is_stale:
        raise ConflictException("Publication requires a current completed evaluation")
    current_revision = await session.get(DriveRevision, drive.current_drive_revision_id)
    if current_revision is None:
        raise ConflictException("Drive has no current revision")
    requirements = (
        (
            await session.execute(
                select(DriveDocumentRequirement).where(
                    DriveDocumentRequirement.drive_revision_id == current_revision.id
                )
            )
        )
        .scalars()
        .all()
    )
    if not requirements:
        raise ConflictException("Configure document requirements before publication")

    next_number = drive.concurrency_revision + 1
    publication_revision = DriveRevision(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        revision_number=next_number,
        role_title=current_revision.role_title,
        job_description_raw=current_revision.job_description_raw,
        employment_type=current_revision.employment_type,
        location=current_revision.location,
        work_mode=current_revision.work_mode,
        compensation_details=current_revision.compensation_details,
        registration_start_at=payload.registration_start_at,
        registration_end_at=payload.registration_end_at,
        withdrawal_end_at=payload.withdrawal_end_at or payload.registration_end_at,
        created_by_membership_id=auth.membership_id,
    )
    session.add(publication_revision)
    await session.flush()
    copied_requirements = []
    for old in requirements:
        copied = DriveDocumentRequirement(
            institution_id=old.institution_id,
            drive_id=old.drive_id,
            drive_revision_id=publication_revision.id,
            document_type=old.document_type,
            display_label=old.display_label,
            allowed_extensions=old.allowed_extensions,
            max_size_bytes=old.max_size_bytes,
            filename_pattern=old.filename_pattern,
            required_stage=old.required_stage,
            due_at=old.due_at,
            created_by_membership_id=auth.membership_id,
        )
        session.add(copied)
        copied_requirements.append(copied)

    drive.current_drive_revision_id = publication_revision.id
    drive.concurrency_revision = next_number
    exact_payload = {
        "drive_revision_id": str(publication_revision.id),
        "evaluation_run_id": str(evaluation.id),
        "registration_start_at": payload.registration_start_at.isoformat(),
        "registration_end_at": payload.registration_end_at.isoformat(),
        "withdrawal_end_at": (payload.withdrawal_end_at or payload.registration_end_at).isoformat(),
        "student_visible": {
            "role_title": publication_revision.role_title,
            "location": publication_revision.location,
            "work_mode": publication_revision.work_mode,
            "employment_type": publication_revision.employment_type,
            "compensation_details": publication_revision.compensation_details,
        },
        "requirements": [
            {
                "document_type": item.document_type,
                "allowed_extensions": item.allowed_extensions,
                "max_size_bytes": item.max_size_bytes,
                "required_stage": item.required_stage,
                "due_at": item.due_at.isoformat() if item.due_at else None,
            }
            for item in copied_requirements
        ],
    }
    dependencies = {
        "drive_concurrency_revision": next_number,
        "drive_revision_id": str(publication_revision.id),
        "evaluation_run_id": str(evaluation.id),
        "evaluation_run_fingerprint": evaluation.run_fingerprint,
        "policy_id": str(evaluation.policy_id),
    }
    envelope = {
        "schema_version": 1,
        "institution_id": str(auth.institution_id),
        "action_type": "drive_publication",
        "target_id": str(publication_revision.id),
        "payload": exact_payload,
        "dependencies": dependencies,
    }
    proposal = ActionProposal(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        action_type="drive_publication",
        target_type="drive_revision",
        target_id=publication_revision.id,
        revision_number=1,
        schema_version=1,
        payload=exact_payload,
        dependencies=dependencies,
        canonical_hash=canonical_hash(envelope),
        state="pending_approval",
        requested_by_membership_id=auth.membership_id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(proposal)
    await session.flush()
    record_audit(
        session, auth, "drive:publication_proposed", "action_proposal", proposal.id, dependencies
    )
    await session.commit()
    return PublicationProposalResponse(
        id=proposal.id,
        drive_id=drive.id,
        drive_revision_id=publication_revision.id,
        evaluation_run_id=evaluation.id,
        revision_number=proposal.revision_number,
        canonical_hash=proposal.canonical_hash,
        state=proposal.state,
        payload=proposal.payload,
        dependencies=proposal.dependencies,
        created_at=proposal.created_at,
    )


@router.post(
    "/publication-proposals/{proposal_id}/decisions", response_model=PublicationProposalResponse
)
async def decide_publication_proposal(
    proposal_id: uuid.UUID,
    payload: PublicationDecisionCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> PublicationProposalResponse:
    auth.require_capability("proposal:decide")
    proposal = (
        await session.execute(
            select(ActionProposal)
            .where(
                ActionProposal.id == proposal_id,
                ActionProposal.institution_id == auth.institution_id,
                ActionProposal.action_type == "drive_publication",
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not proposal:
        raise NotFoundException("Publication proposal not found")
    drive = await load_authorized_drive(session, auth, proposal.drive_id, for_update=True)
    if proposal.state != "pending_approval":
        raise ConflictException(f"Publication proposal is already {proposal.state}")
    if (
        proposal.revision_number != payload.expected_revision
        or proposal.canonical_hash != payload.expected_hash
    ):
        raise ConflictException("Publication proposal revision or hash is stale")
    envelope = {
        "schema_version": proposal.schema_version,
        "institution_id": str(proposal.institution_id),
        "action_type": proposal.action_type,
        "target_id": str(proposal.target_id),
        "payload": proposal.payload,
        "dependencies": proposal.dependencies,
    }
    evaluation = await session.get(
        EvaluationRun, uuid.UUID(proposal.dependencies["evaluation_run_id"])
    )
    if (
        canonical_hash(envelope) != proposal.canonical_hash
        or drive.current_drive_revision_id != proposal.target_id
        or drive.concurrency_revision != proposal.dependencies["drive_concurrency_revision"]
        or evaluation is None
        or evaluation.status != "completed"
        or evaluation.is_stale
        or evaluation.run_fingerprint != proposal.dependencies["evaluation_run_fingerprint"]
    ):
        proposal.state = "stale"
        await session.commit()
        raise ConflictException("Publication dependencies changed after review was requested")

    decision = ApprovalDecision(
        institution_id=auth.institution_id,
        proposal_id=proposal.id,
        proposal_hash=proposal.canonical_hash,
        decision=payload.decision,
        comment=payload.comment,
        decided_by_membership_id=auth.membership_id,
        permission_context={
            "capability": "proposal:decide",
            "membership_id": str(auth.membership_id),
        },
    )
    session.add(decision)
    proposal.state = payload.decision
    if payload.decision == "approved":
        drive.status = "published"
        drive.published_drive_revision_id = proposal.target_id
        drive.published_evaluation_run_id = evaluation.id
        drive.publication_proposal_id = proposal.id
        drive.published_at = datetime.now(UTC)
        await validate_current_documents_for_drive(session, drive)
        await reconcile_registration_holds(
            session,
            drive=drive,
            evaluation_run=evaluation,
            actor_membership_id=auth.membership_id,
        )
    await session.flush()
    from placementos.services.workflows import enqueue_workflow_resume_for_proposal

    await enqueue_workflow_resume_for_proposal(
        session, proposal.id, decision.id, auth.membership_id
    )
    record_audit(
        session,
        auth,
        "drive:publication_decided",
        "action_proposal",
        proposal.id,
        {
            "decision": payload.decision,
            "drive_revision_id": str(proposal.target_id),
            "evaluation_run_id": str(evaluation.id),
        },
    )
    await session.commit()
    return PublicationProposalResponse(
        id=proposal.id,
        drive_id=drive.id,
        drive_revision_id=proposal.target_id,
        evaluation_run_id=evaluation.id,
        revision_number=proposal.revision_number,
        canonical_hash=proposal.canonical_hash,
        state=proposal.state,
        payload=proposal.payload,
        dependencies=proposal.dependencies,
        created_at=proposal.created_at,
    )


@router.post(
    "/student/documents/upload-sessions",
    response_model=DocumentUploadSessionResponse,
    status_code=201,
)
async def create_document_upload_session(
    payload: DocumentUploadSessionCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadSessionResponse:
    auth.require_role("student")
    profile = await load_student_profile(session, auth.institution_id, auth.user_id)
    extension = Path(payload.original_filename).suffix.lower().lstrip(".")
    if extension not in {"pdf", "docx"}:
        raise BadRequestException("Student documents must be PDF or DOCX files")
    upload_id = uuid.uuid4()
    key = storage_service.build_quarantine_key(
        auth.institution_id, "student_document", upload_id, payload.original_filename
    )
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    item = UploadSession(
        id=upload_id,
        institution_id=auth.institution_id,
        owner_user_id=auth.user_id,
        owner_membership_id=auth.membership_id,
        purpose="student_document",
        student_profile_id=profile.id,
        document_type=payload.document_type,
        quarantine_key=key,
        file_name=payload.original_filename,
        file_size_bytes=payload.byte_size,
        content_type=payload.content_type,
        status="pending",
        expires_at=expires_at,
    )
    session.add(item)
    await session.flush()
    url = storage_service.generate_presigned_upload_url(key, auth.institution_id)
    record_audit(
        session,
        auth,
        "document:upload_session_created",
        "upload_session",
        item.id,
        {
            "document_type": payload.document_type,
            "declared_size": payload.byte_size,
        },
    )
    await session.commit()
    return DocumentUploadSessionResponse(
        id=item.id,
        document_type=payload.document_type,
        original_filename=item.file_name,
        upload_url=url,
        expires_at=expires_at,
        status=item.status,
    )


@router.post(
    "/student/documents/upload-sessions/{upload_session_id}/complete",
    response_model=DocumentRevisionResponse,
    status_code=201,
)
async def complete_document_upload(
    upload_session_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DocumentRevisionResponse:
    auth.require_role("student")
    upload = (
        await session.execute(
            select(UploadSession)
            .where(
                UploadSession.id == upload_session_id,
                UploadSession.institution_id == auth.institution_id,
                UploadSession.owner_user_id == auth.user_id,
                UploadSession.purpose == "student_document",
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not upload:
        raise NotFoundException("Document upload session not found")
    if upload.status == "completed":
        existing = (
            await session.execute(
                select(DocumentRevision).where(DocumentRevision.upload_session_id == upload.id)
            )
        ).scalar_one_or_none()
        if existing:
            return _document_response(existing, upload.document_type or "resume")
    if upload.status != "pending" or upload.expires_at <= datetime.now(UTC):
        raise ConflictException("Document upload session is not available for completion")
    try:
        data, provider_type, actual_size = storage_service.inspect_quarantine_object(
            upload.quarantine_key, auth.institution_id
        )
        if actual_size > 10 * 1024 * 1024:
            raise BadRequestException("Student document exceeds the 10 MiB limit")
        if upload.file_size_bytes != actual_size:
            raise BadRequestException("Uploaded byte size does not match the declared size")
        extension = Path(upload.file_name).suffix.lower().lstrip(".")
        canonical_type = DocumentScanner.scan_bytes(data, extension)
        scan_status = MalwareScanner.scan(data)
        extraction = TextExtractor.extract(data, canonical_type)
        text_status = "manual_review" if extraction.is_empty_or_scanned else "extracted"
        accepted_key, hash_sha256, size, _ = storage_service.promote_quarantine_to_accepted(
            upload.quarantine_key,
            auth.institution_id,
            "student_document",
            extension,
            provider_type or upload.content_type,
            validated_data=data,
        )
    except (ParseError, StorageSecurityError, FileNotFoundError) as exc:
        upload.status = "rejected"
        await session.commit()
        message = exc.message if isinstance(exc, ParseError) else str(exc)
        raise BadRequestException(message) from exc

    document = (
        await session.execute(
            select(StudentDocument)
            .where(
                StudentDocument.institution_id == auth.institution_id,
                StudentDocument.student_profile_id == upload.student_profile_id,
                StudentDocument.document_type == upload.document_type,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not document:
        document = StudentDocument(
            institution_id=auth.institution_id,
            student_profile_id=upload.student_profile_id,
            document_type=upload.document_type,
        )
        session.add(document)
        await session.flush()
    last_revision = (
        await session.execute(
            select(DocumentRevision)
            .where(DocumentRevision.student_document_id == document.id)
            .order_by(DocumentRevision.revision_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    revision = DocumentRevision(
        institution_id=auth.institution_id,
        student_profile_id=upload.student_profile_id,
        student_document_id=document.id,
        upload_session_id=upload.id,
        revision_number=(last_revision.revision_number + 1) if last_revision else 1,
        object_key=accepted_key,
        original_filename=upload.file_name,
        media_type=provider_type or upload.content_type,
        file_size_bytes=size,
        hash_sha256=hash_sha256,
        scan_status=scan_status,
        structure_status="passed",
        text_status=text_status,
        supersedes_revision_id=last_revision.id if last_revision else None,
        uploaded_by_membership_id=auth.membership_id,
    )
    session.add(revision)
    await session.flush()
    document.current_revision_id = revision.id
    upload.status = "completed"
    upload.accepted_key = accepted_key
    upload.checksum_sha256 = hash_sha256

    requirements = (
        (
            await session.execute(
                select(DriveDocumentRequirement)
                .join(Drive, Drive.id == DriveDocumentRequirement.drive_id)
                .where(
                    DriveDocumentRequirement.institution_id == auth.institution_id,
                    DriveDocumentRequirement.document_type == upload.document_type,
                    Drive.published_drive_revision_id == DriveDocumentRequirement.drive_revision_id,
                )
            )
        )
        .scalars()
        .all()
    )
    for requirement in requirements:
        await validate_document_against_requirement(session, revision, requirement)
    record_audit(
        session,
        auth,
        "document:revision_accepted",
        "document_revision",
        revision.id,
        {
            "document_type": upload.document_type,
            "revision": revision.revision_number,
            "hash": hash_sha256,
            "scan_status": scan_status,
        },
    )
    await session.commit()
    return _document_response(revision, upload.document_type or "resume")


@router.get("/student/documents", response_model=list[DocumentRevisionResponse])
async def list_my_documents(
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[DocumentRevisionResponse]:
    auth.require_role("student")
    profile = await load_student_profile(session, auth.institution_id, auth.user_id)
    rows = (
        await session.execute(
            select(StudentDocument, DocumentRevision)
            .join(DocumentRevision, DocumentRevision.student_document_id == StudentDocument.id)
            .where(StudentDocument.student_profile_id == profile.id)
            .order_by(DocumentRevision.created_at.desc())
        )
    ).all()
    return [_document_response(revision, document.document_type) for document, revision in rows]


@router.get("/student/documents/{revision_id}/download-url", response_model=DownloadUrlResponse)
async def download_my_document(
    revision_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DownloadUrlResponse:
    auth.require_role("student")
    profile = await load_student_profile(session, auth.institution_id, auth.user_id)
    revision = (
        await session.execute(
            select(DocumentRevision).where(
                DocumentRevision.id == revision_id,
                DocumentRevision.institution_id == auth.institution_id,
                DocumentRevision.student_profile_id == profile.id,
            )
        )
    ).scalar_one_or_none()
    if not revision:
        raise NotFoundException("Document revision not found")
    return DownloadUrlResponse(
        download_url=storage_service.generate_presigned_download_url(
            revision.object_key, auth.institution_id, revision.original_filename
        ),
        expires_in=300,
        filename=revision.original_filename,
    )


@router.get(
    "/drives/{drive_id}/students/{student_profile_id}/documents",
    response_model=list[DocumentRevisionResponse],
)
async def list_student_documents_for_drive(
    drive_id: uuid.UUID,
    student_profile_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[DocumentRevisionResponse]:
    drive = await load_authorized_drive(session, auth, drive_id)
    if drive.published_evaluation_run_id is None:
        raise ConflictException("Drive has no published cohort")
    included = (
        await session.execute(
            select(EligibilityResult.id).where(
                EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id,
                EligibilityResult.student_profile_id == student_profile_id,
            )
        )
    ).scalar_one_or_none()
    if included is None:
        raise NotFoundException("Student is not in the published drive cohort")
    rows = (
        await session.execute(
            select(StudentDocument, DocumentRevision)
            .join(DocumentRevision, DocumentRevision.student_document_id == StudentDocument.id)
            .where(
                StudentDocument.institution_id == auth.institution_id,
                StudentDocument.student_profile_id == student_profile_id,
            )
            .order_by(DocumentRevision.created_at.desc())
        )
    ).all()
    return [_document_response(revision, document.document_type) for document, revision in rows]


@router.get(
    "/drives/{drive_id}/document-revisions/{revision_id}/download-url",
    response_model=DownloadUrlResponse,
)
async def download_student_document_for_drive(
    drive_id: uuid.UUID,
    revision_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DownloadUrlResponse:
    drive = await load_authorized_drive(session, auth, drive_id)
    revision = (
        await session.execute(
            select(DocumentRevision).where(
                DocumentRevision.id == revision_id,
                DocumentRevision.institution_id == auth.institution_id,
            )
        )
    ).scalar_one_or_none()
    if not revision or drive.published_evaluation_run_id is None:
        raise NotFoundException("Document revision not found")
    included = (
        await session.execute(
            select(EligibilityResult.id).where(
                EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id,
                EligibilityResult.student_profile_id == revision.student_profile_id,
            )
        )
    ).scalar_one_or_none()
    if included is None:
        raise NotFoundException("Document revision not found")
    record_audit(
        session,
        auth,
        "document:coordinator_downloaded",
        "document_revision",
        revision.id,
        {"drive_id": str(drive.id), "student_profile_id": str(revision.student_profile_id)},
    )
    await session.commit()
    return DownloadUrlResponse(
        download_url=storage_service.generate_presigned_download_url(
            revision.object_key, auth.institution_id, revision.original_filename
        ),
        expires_in=300,
        filename=revision.original_filename,
    )


@router.get("/student/drives", response_model=list[StudentDriveResponse])
async def list_student_drives(
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[StudentDriveResponse]:
    auth.require_role("student")
    profile = await load_student_profile(session, auth.institution_id, auth.user_id)
    drives = (
        (
            await session.execute(
                select(Drive).where(
                    Drive.institution_id == auth.institution_id,
                    Drive.status == "published",
                    Drive.published_drive_revision_id.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    responses = []
    for drive in drives:
        personal = await current_published_result(session, drive, profile.id)
        if personal is None:
            continue
        _, result = personal
        revision = await session.get(DriveRevision, drive.published_drive_revision_id)
        company = await session.get(Company, drive.company_id)
        if (
            revision is None
            or revision.registration_start_at is None
            or revision.registration_end_at is None
        ):
            continue
        readiness = await compute_readiness(
            session,
            institution_id=auth.institution_id,
            drive=drive,
            student_profile_id=profile.id,
        )
        registration = (
            await session.execute(
                select(Registration).where(
                    Registration.drive_id == drive.id,
                    Registration.student_profile_id == profile.id,
                )
            )
        ).scalar_one_or_none()
        responses.append(
            StudentDriveResponse(
                drive_id=drive.id,
                company_name=company.name if company else "Unknown company",
                role_title=revision.role_title,
                location=revision.location,
                work_mode=revision.work_mode,
                employment_type=revision.employment_type,
                compensation_details=revision.compensation_details,
                registration_start_at=revision.registration_start_at,
                registration_end_at=revision.registration_end_at,
                withdrawal_end_at=revision.withdrawal_end_at,
                eligibility_status=cast(
                    Literal["eligible", "ineligible", "needs_review"], result.outcome
                ),
                eligibility_reasons=result.reason_codes,
                document_readiness=_readiness_response(readiness),
                registration=_registration_response(registration) if registration else None,
            )
        )
    return responses


@router.post("/student/drives/{drive_id}/registrations/draft", response_model=RegistrationResponse)
async def save_registration_draft(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> RegistrationResponse:
    auth.require_role("student")
    profile = await load_student_profile(session, auth.institution_id, auth.user_id)
    drive = await session.get(Drive, drive_id)
    if not drive or drive.institution_id != auth.institution_id or drive.status != "published":
        raise NotFoundException("Published drive not found")
    existing = (
        await session.execute(
            select(Registration).where(
                Registration.drive_id == drive.id, Registration.student_profile_id == profile.id
            )
        )
    ).scalar_one_or_none()
    if existing:
        return _registration_response(existing)
    registration = Registration(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        student_profile_id=profile.id,
        state="draft",
        concurrency_revision=1,
    )
    session.add(registration)
    await session.flush()
    session.add(
        RegistrationEvent(
            institution_id=auth.institution_id,
            registration_id=registration.id,
            event_type="draft_saved",
            from_state=None,
            to_state="draft",
            actor_membership_id=auth.membership_id,
            evidence={"drive_revision_id": str(drive.published_drive_revision_id)},
        )
    )
    await session.commit()
    return _registration_response(registration)


@router.post("/student/drives/{drive_id}/registrations", response_model=RegistrationResponse)
async def submit_registration(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> RegistrationResponse:
    auth.require_capability("registration:submit")
    profile = await load_student_profile(session, auth.institution_id, auth.user_id)
    drive = (
        await session.execute(
            select(Drive)
            .where(Drive.id == drive_id, Drive.institution_id == auth.institution_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not drive or drive.status != "published" or drive.operational_hold:
        raise ConflictException("Drive is not open for registration")
    revision = await session.get(DriveRevision, drive.published_drive_revision_id)
    if not revision or not revision.registration_start_at or not revision.registration_end_at:
        raise ConflictException("Published registration window is unavailable")
    now = datetime.now(UTC)
    if not registration_window_is_open(
        now, revision.registration_start_at, revision.registration_end_at
    ):
        raise ConflictException(
            "Registration is outside the inclusive-open, exclusive-close window"
        )
    personal = await current_published_result(session, drive, profile.id)
    if personal is None:
        raise ConflictException("No current eligibility result is available")
    run, result = personal
    if run.is_stale or run.status != "completed" or result.outcome != "eligible":
        raise ConflictException("Current eligibility does not permit submission")
    readiness = await compute_readiness(
        session,
        institution_id=auth.institution_id,
        drive=drive,
        student_profile_id=profile.id,
        stage="registration",
        now=now,
    )
    if readiness["status"] != "ready":
        raise ConflictException(f"Registration documents are {readiness['status']}")
    existing = (
        await session.execute(
            select(Registration)
            .where(Registration.drive_id == drive.id, Registration.student_profile_id == profile.id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if existing and existing.state in {"submitted", "eligibility_hold"}:
        return _registration_response(existing)
    if existing and existing.state == "withdrawn":
        raise ConflictException(
            "A withdrawn registration requires coordinator-assisted restoration"
        )
    registration = existing or Registration(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        student_profile_id=profile.id,
        state="draft",
        concurrency_revision=1,
    )
    if not existing:
        session.add(registration)
        await session.flush()
    previous = registration.state
    registration.state = "submitted"
    registration.submitted_drive_revision_id = drive.published_drive_revision_id
    registration.submitted_policy_id = run.policy_id
    registration.submitted_evaluation_run_id = run.id
    registration.submitted_eligibility_result_id = result.id
    registration.submitted_at = now
    registration.withdrawn_at = None
    registration.hold_reason = None
    if existing:
        registration.concurrency_revision += 1
    session.add(
        RegistrationEvent(
            institution_id=auth.institution_id,
            registration_id=registration.id,
            event_type="submitted",
            from_state=previous,
            to_state="submitted",
            actor_membership_id=auth.membership_id,
            evidence={
                "drive_revision_id": str(drive.published_drive_revision_id),
                "policy_id": str(run.policy_id),
                "evaluation_run_id": str(run.id),
                "eligibility_result_id": str(result.id),
            },
        )
    )
    record_audit(session, auth, "registration:submitted", "registration", registration.id)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        replay = (
            await session.execute(
                select(Registration).where(
                    Registration.drive_id == drive_id,
                    Registration.student_profile_id == profile.id,
                )
            )
        ).scalar_one()
        return _registration_response(replay)
    return _registration_response(registration)


@router.post(
    "/student/registrations/{registration_id}/withdraw", response_model=RegistrationResponse
)
async def withdraw_registration(
    registration_id: uuid.UUID,
    payload: WithdrawalCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> RegistrationResponse:
    auth.require_role("student")
    profile = await load_student_profile(session, auth.institution_id, auth.user_id)
    registration = (
        await session.execute(
            select(Registration)
            .where(
                Registration.id == registration_id,
                Registration.institution_id == auth.institution_id,
                Registration.student_profile_id == profile.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not registration:
        raise NotFoundException("Registration not found")
    if registration.concurrency_revision != payload.expected_revision:
        raise ConflictException("Registration changed; reload before withdrawing")
    if registration.state not in {"submitted", "eligibility_hold"}:
        raise ConflictException(f"Registration cannot be withdrawn from {registration.state}")
    drive = await session.get(Drive, registration.drive_id)
    revision = (
        await session.get(DriveRevision, drive.published_drive_revision_id) if drive else None
    )
    cutoff = revision.withdrawal_end_at if revision else None
    if cutoff is None or datetime.now(UTC) >= cutoff:
        raise ConflictException("The self-service withdrawal cutoff has passed")
    previous = registration.state
    registration.state = "withdrawn"
    registration.withdrawn_at = datetime.now(UTC)
    registration.hold_reason = None
    registration.concurrency_revision += 1
    session.add(
        RegistrationEvent(
            institution_id=auth.institution_id,
            registration_id=registration.id,
            event_type="withdrawn",
            from_state=previous,
            to_state="withdrawn",
            reason=payload.reason,
            actor_membership_id=auth.membership_id,
            evidence={
                "drive_revision_id": str(drive.published_drive_revision_id) if drive else None
            },
        )
    )
    record_audit(
        session,
        auth,
        "registration:withdrawn",
        "registration",
        registration.id,
        {"reason": payload.reason},
    )
    await session.commit()
    return _registration_response(registration)


@router.post("/registrations/{registration_id}/coordinator-action", response_model=RegistrationResponse)
async def coordinator_registration_action(
    registration_id: uuid.UUID,
    payload: CoordinatorRegistrationAction,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> RegistrationResponse:
    registration = (
        await session.execute(
            select(Registration)
            .where(
                Registration.id == registration_id,
                Registration.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not registration:
        raise NotFoundException("Registration not found")
    drive = await load_authorized_drive(session, auth, registration.drive_id, for_update=True)
    if registration.concurrency_revision != payload.expected_revision:
        raise ConflictException("Registration changed; reload before applying an assisted action")
    previous = registration.state
    evidence: dict[str, str | None] = {
        "drive_revision_id": str(drive.published_drive_revision_id)
    }
    if payload.action == "restore":
        if registration.state != "eligibility_hold":
            raise ConflictException("Only a held registration can be restored")
        current = await current_published_result(session, drive, registration.student_profile_id)
        if current is None or current[0].is_stale or current[1].outcome != "eligible":
            raise ConflictException("Current published eligibility does not permit restoration")
        registration.state = "submitted"
        registration.hold_reason = None
        evidence.update(
            {"evaluation_run_id": str(current[0].id), "result_id": str(current[1].id)}
        )
        event_type = "restored"
    else:
        if registration.state not in {"submitted", "eligibility_hold"}:
            raise ConflictException(
                f"Registration cannot be assisted-withdrawn from {registration.state}"
            )
        registration.state = "withdrawn"
        registration.withdrawn_at = datetime.now(UTC)
        registration.hold_reason = None
        event_type = "assisted_withdrawal"
    registration.concurrency_revision += 1
    session.add(
        RegistrationEvent(
            institution_id=auth.institution_id,
            registration_id=registration.id,
            event_type=event_type,
            from_state=previous,
            to_state=registration.state,
            reason=payload.reason,
            actor_membership_id=auth.membership_id,
            evidence=evidence,
        )
    )
    record_audit(
        session,
        auth,
        f"registration:{event_type}",
        "registration",
        registration.id,
        {"reason": payload.reason, "from_state": previous, "to_state": registration.state},
    )
    await session.commit()
    return _registration_response(registration)


async def _participants(session: AsyncSession, drive: Drive) -> list[ParticipantResponse]:
    if drive.published_evaluation_run_id is None:
        return []
    rows = (
        await session.execute(
            select(EligibilityResult, StudentProfile, User)
            .join(StudentProfile, StudentProfile.id == EligibilityResult.student_profile_id)
            .join(User, User.id == StudentProfile.user_id)
            .where(EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id)
            .order_by(StudentProfile.student_identifier)
        )
    ).all()
    registrations = {
        item.student_profile_id: item
        for item in (
            await session.execute(select(Registration).where(Registration.drive_id == drive.id))
        )
        .scalars()
        .all()
    }
    items = []
    for result, profile, user in rows:
        readiness = await compute_readiness(
            session,
            institution_id=drive.institution_id,
            drive=drive,
            student_profile_id=profile.id,
        )
        registration = registrations.get(profile.id)
        items.append(
            ParticipantResponse(
                student_profile_id=profile.id,
                student_identifier=profile.student_identifier,
                student_name=user.full_name,
                eligibility_status=result.outcome,
                readiness_status=readiness["status"],
                registration_state=registration.state if registration else None,
                registration_id=registration.id if registration else None,
                registration_revision=registration.concurrency_revision if registration else None,
            )
        )
    return items


@router.get("/drives/{drive_id}/participants", response_model=ParticipantListResponse)
async def list_participants(
    drive_id: uuid.UUID,
    eligibility_status: str | None = Query(default=None),
    readiness_status: str | None = Query(default=None),
    registration_state: str | None = Query(default=None),
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> ParticipantListResponse:
    drive = await load_authorized_drive(session, auth, drive_id)
    items = await _participants(session, drive)
    counts = {
        "total": len(items),
        "eligible": sum(item.eligibility_status == "eligible" for item in items),
        "ready": sum(item.readiness_status == "ready" for item in items),
        "submitted": sum(item.registration_state == "submitted" for item in items),
        "on_hold": sum(item.registration_state == "eligibility_hold" for item in items),
    }
    filtered = [
        item
        for item in items
        if (eligibility_status is None or item.eligibility_status == eligibility_status)
        and (readiness_status is None or item.readiness_status == readiness_status)
        and (registration_state is None or item.registration_state == registration_state)
    ]
    return ParticipantListResponse(items=filtered, total=len(filtered), counts=counts)


def _safe_csv(value: str) -> str:
    return f"'{value}" if value[:1] in {"=", "+", "-", "@"} else value


@router.get("/drives/{drive_id}/participants.csv", response_class=PlainTextResponse)
async def export_participants(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    auth.require_capability("export:generate")
    drive = await load_authorized_drive(session, auth, drive_id)
    items = await _participants(session, drive)
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        ["student_identifier", "student_name", "eligibility", "readiness", "registration"]
    )
    for item in items:
        writer.writerow(
            [
                _safe_csv(item.student_identifier),
                _safe_csv(item.student_name),
                item.eligibility_status,
                item.readiness_status,
                item.registration_state or "not_started",
            ]
        )
    record_audit(
        session, auth, "participants:exported", "drive", drive.id, {"row_count": len(items)}
    )
    await session.commit()
    return PlainTextResponse(
        stream.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="drive-{drive.id}-participants.csv"'
        },
    )
