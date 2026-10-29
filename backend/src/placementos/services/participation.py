"""P06 deterministic document readiness and registration hold services."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.models.eligibility import EligibilityResult, EvaluationRun
from placementos.models.identity import StudentProfile
from placementos.models.participation import (
    DocumentRevision,
    DocumentValidationRun,
    DriveDocumentRequirement,
    Registration,
    RegistrationEvent,
    StudentDocument,
)
from placementos.models.recruitment import Drive

VALIDATOR_VERSION = "document-validator-v1.0.0"
READINESS_PRIORITY = {"ready": 0, "pending": 1, "needs_review": 2, "blocked": 3}


def registration_window_is_open(now: datetime, opens_at: datetime, deadline_at: datetime) -> bool:
    """Opening is inclusive and the deadline is exclusive (INV-11)."""
    return opens_at <= now < deadline_at


def aggregate_readiness(statuses: list[str]) -> str:
    """Return blocked > needs_review > pending > ready, independent of eligibility."""
    if not statuses:
        return "ready"
    return max(statuses, key=lambda item: READINESS_PRIORITY[item])


async def load_student_profile(
    session: AsyncSession, institution_id: uuid.UUID, user_id: uuid.UUID
) -> StudentProfile:
    profile = (
        await session.execute(
            select(StudentProfile).where(
                StudentProfile.institution_id == institution_id,
                StudentProfile.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        from placementos.core.errors import NotFoundException

        raise NotFoundException("Student profile not found in the active institution")
    return profile


def _finding(code: str, severity: str, message: str, required_action: str | None = None) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "required_action": required_action,
    }


async def validate_document_against_requirement(
    session: AsyncSession,
    revision: DocumentRevision,
    requirement: DriveDocumentRequirement,
) -> DocumentValidationRun:
    existing = (
        await session.execute(
            select(DocumentValidationRun).where(
                DocumentValidationRun.document_revision_id == revision.id,
                DocumentValidationRun.requirement_id == requirement.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    findings: list[dict] = []
    extension = Path(revision.original_filename).suffix.lower().lstrip(".")
    if extension not in requirement.allowed_extensions:
        findings.append(
            _finding(
                "EXTENSION_NOT_ALLOWED",
                "error",
                f".{extension or 'unknown'} is not allowed for {requirement.display_label}",
                f"Upload one of: {', '.join(requirement.allowed_extensions)}",
            )
        )
    if revision.file_size_bytes > requirement.max_size_bytes:
        findings.append(
            _finding(
                "FILE_TOO_LARGE",
                "error",
                "The accepted file exceeds this requirement's size limit",
                "Upload a smaller original document",
            )
        )
    if requirement.filename_pattern:
        try:
            matches = (
                re.fullmatch(requirement.filename_pattern, revision.original_filename) is not None
            )
        except re.error:
            matches = False
        if not matches:
            findings.append(
                _finding(
                    "FILENAME_PATTERN_MISMATCH",
                    "error",
                    "The original filename does not match the configured pattern",
                    "Rename the local file and upload a new revision",
                )
            )
    if revision.scan_status not in {"clean", "development_fixture"}:
        findings.append(_finding("SCAN_NOT_CLEAN", "error", "Security scanning did not pass"))
    if revision.structure_status != "passed":
        findings.append(
            _finding("STRUCTURE_INVALID", "error", "Document structure validation failed")
        )

    duplicate_count = (
        await session.execute(
            select(func.count())
            .select_from(DocumentRevision)
            .where(
                DocumentRevision.institution_id == revision.institution_id,
                DocumentRevision.student_profile_id == revision.student_profile_id,
                DocumentRevision.hash_sha256 == revision.hash_sha256,
                DocumentRevision.id != revision.id,
            )
        )
    ).scalar_one()
    if duplicate_count:
        findings.append(
            _finding(
                "SAME_STUDENT_DUPLICATE",
                "warning",
                "These bytes match an earlier document revision for your profile",
                "Confirm that the intended document type and revision were selected",
            )
        )
    if revision.text_status == "manual_review":
        findings.append(
            _finding(
                "TEXT_REVIEW_REQUIRED",
                "warning",
                "The container is valid but text extraction needs manual inspection",
                "Wait for coordinator review before scheduling",
            )
        )

    if any(item["severity"] == "error" for item in findings):
        status = "failed"
    elif any(item["severity"] == "warning" for item in findings):
        status = "needs_review"
    else:
        status = "passed"
        findings.append(
            _finding("VALIDATION_PASSED", "info", "All required operational checks passed")
        )

    validation = DocumentValidationRun(
        institution_id=revision.institution_id,
        student_profile_id=revision.student_profile_id,
        drive_id=requirement.drive_id,
        document_revision_id=revision.id,
        requirement_id=requirement.id,
        validator_version=VALIDATOR_VERSION,
        status=status,
        findings=findings,
    )
    session.add(validation)
    await session.flush()
    return validation


async def compute_readiness(
    session: AsyncSession,
    *,
    institution_id: uuid.UUID,
    drive: Drive,
    student_profile_id: uuid.UUID,
    stage: str | None = None,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(UTC)
    if drive.published_drive_revision_id is None:
        return {"status": "pending", "requirements": []}
    requirement_query = select(DriveDocumentRequirement).where(
        DriveDocumentRequirement.institution_id == institution_id,
        DriveDocumentRequirement.drive_id == drive.id,
        DriveDocumentRequirement.drive_revision_id == drive.published_drive_revision_id,
    )
    if stage:
        requirement_query = requirement_query.where(
            DriveDocumentRequirement.required_stage == stage
        )
    requirements = (
        (await session.execute(requirement_query.order_by(DriveDocumentRequirement.document_type)))
        .scalars()
        .all()
    )
    rows: list[dict] = []
    statuses: list[str] = []
    for requirement in requirements:
        document = (
            await session.execute(
                select(StudentDocument).where(
                    StudentDocument.institution_id == institution_id,
                    StudentDocument.student_profile_id == student_profile_id,
                    StudentDocument.document_type == requirement.document_type,
                )
            )
        ).scalar_one_or_none()
        revision = None
        validation = None
        if document and document.current_revision_id:
            revision = await session.get(DocumentRevision, document.current_revision_id)
            if revision:
                validation = (
                    await session.execute(
                        select(DocumentValidationRun).where(
                            DocumentValidationRun.document_revision_id == revision.id,
                            DocumentValidationRun.requirement_id == requirement.id,
                        )
                    )
                ).scalar_one_or_none()

        if revision is None:
            overdue = requirement.due_at is not None and now >= requirement.due_at
            status = "blocked" if overdue else "pending"
            findings = [
                _finding(
                    "REQUIRED_DOCUMENT_MISSING" if overdue else "DOCUMENT_NOT_UPLOADED",
                    "error" if overdue else "info",
                    f"{requirement.display_label} is {'overdue' if overdue else 'not uploaded'}",
                    "Upload the required document",
                )
            ]
        elif validation is None:
            status = "pending"
            findings = [_finding("VALIDATION_PENDING", "info", "Validation has not completed")]
        elif validation.status == "failed":
            status = "blocked"
            findings = validation.findings
        elif validation.status == "needs_review":
            status = "needs_review"
            findings = validation.findings
        else:
            status = "ready"
            findings = validation.findings
        statuses.append(status)
        rows.append(
            {
                "requirement_id": requirement.id,
                "document_type": requirement.document_type,
                "display_label": requirement.display_label,
                "required_stage": requirement.required_stage,
                "due_at": requirement.due_at,
                "status": status,
                "findings": findings,
                "current_document": revision,
            }
        )
    return {"status": aggregate_readiness(statuses), "requirements": rows}


async def validate_current_documents_for_drive(session: AsyncSession, drive: Drive) -> None:
    if drive.published_drive_revision_id is None:
        return
    requirements = (
        (
            await session.execute(
                select(DriveDocumentRequirement).where(
                    DriveDocumentRequirement.drive_revision_id == drive.published_drive_revision_id
                )
            )
        )
        .scalars()
        .all()
    )
    for requirement in requirements:
        documents = (
            (
                await session.execute(
                    select(StudentDocument).where(
                        StudentDocument.institution_id == drive.institution_id,
                        StudentDocument.document_type == requirement.document_type,
                        StudentDocument.current_revision_id.is_not(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for document in documents:
            revision = await session.get(DocumentRevision, document.current_revision_id)
            if revision:
                await validate_document_against_requirement(session, revision, requirement)


async def reconcile_registration_holds(
    session: AsyncSession,
    *,
    drive: Drive,
    evaluation_run: EvaluationRun,
    actor_membership_id: uuid.UUID,
) -> None:
    """Hold submitted registrations lacking a current eligible result; never delete them."""
    registrations = (
        (
            await session.execute(
                select(Registration)
                .where(
                    Registration.drive_id == drive.id,
                    Registration.state.in_(["submitted", "eligibility_hold"]),
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    results = {
        item.student_profile_id: item
        for item in (
            await session.execute(
                select(EligibilityResult).where(
                    EligibilityResult.evaluation_run_id == evaluation_run.id
                )
            )
        )
        .scalars()
        .all()
    }
    for registration in registrations:
        result = results.get(registration.student_profile_id)
        eligible = (
            result is not None and result.outcome == "eligible" and not evaluation_run.is_stale
        )
        if registration.state == "submitted" and not eligible:
            registration.state = "eligibility_hold"
            registration.hold_reason = (
                "Current eligibility requires review"
                if result and result.outcome == "needs_review"
                else "Current eligibility is not eligible"
            )
            registration.concurrency_revision += 1
            session.add(
                RegistrationEvent(
                    institution_id=registration.institution_id,
                    registration_id=registration.id,
                    event_type="held",
                    from_state="submitted",
                    to_state="eligibility_hold",
                    reason=registration.hold_reason,
                    actor_membership_id=actor_membership_id,
                    evidence={
                        "evaluation_run_id": str(evaluation_run.id),
                        "result_id": str(result.id) if result else None,
                    },
                )
            )
        # An eligible reevaluation does not silently restore a hold. An assigned
        # coordinator must execute the explicit, audited restoration command.


async def current_published_result(
    session: AsyncSession, drive: Drive, student_profile_id: uuid.UUID
) -> tuple[EvaluationRun, EligibilityResult] | None:
    if drive.published_evaluation_run_id is None:
        return None
    row = (
        await session.execute(
            select(EvaluationRun, EligibilityResult)
            .join(EligibilityResult, EligibilityResult.evaluation_run_id == EvaluationRun.id)
            .where(
                EvaluationRun.id == drive.published_evaluation_run_id,
                EvaluationRun.institution_id == drive.institution_id,
                EligibilityResult.student_profile_id == student_profile_id,
            )
        )
    ).one_or_none()
    return row
