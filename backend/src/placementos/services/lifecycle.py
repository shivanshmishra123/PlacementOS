"""P09 deterministic scheduling, outcomes, reporting, and lifecycle rules."""

from __future__ import annotations

import csv
import hashlib
import io
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.errors import BadRequestException, ConflictException, NotFoundException
from placementos.models.communications import (
    AudienceRecipient,
    AudienceSnapshot,
    CommunicationDraft,
    DispatchOperation,
)
from placementos.models.eligibility import EligibilityResult, EvaluationRun
from placementos.models.identity import StudentProfile, User
from placementos.models.intelligence import ActionProposal, ApprovalDecision
from placementos.models.lifecycle import (
    AttendanceRevision,
    DriveReportRevision,
    OutcomeRevision,
    RecruitmentRound,
    RecruitmentSession,
    ReportExportGrant,
    SessionAssignment,
    SessionRevision,
)
from placementos.models.participation import Registration
from placementos.models.recruitment import Company, Drive, DriveRevision
from placementos.models.workflow import ExceptionCase
from placementos.schemas.lifecycle import OutcomeCreate, SessionCreate
from placementos.services.communications import contact_revision
from placementos.services.eligibility_engine import canonical_hash
from placementos.services.participation import compute_readiness
from placementos.services.session import AuthContext


def _norm(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _revision_payload(revision: SessionRevision) -> dict[str, Any]:
    return {
        "id": str(revision.id),
        "revision_number": revision.revision_number,
        "start_at": revision.start_at.isoformat(),
        "end_at": revision.end_at.isoformat(),
        "timezone": revision.timezone,
        "buffer_minutes": revision.buffer_minutes,
        "capacity": revision.capacity,
        "venue": revision.venue,
        "meeting_url": revision.meeting_url,
        "panel_members": revision.panel_members,
        "change_reason": revision.change_reason,
    }


async def create_session_revision(
    session: AsyncSession,
    auth: AuthContext,
    drive: Drive,
    round_item: RecruitmentRound,
    payload: SessionCreate,
    logical_session: RecruitmentSession | None = None,
) -> tuple[RecruitmentSession, SessionRevision, list[SessionAssignment]]:
    auth.require_capability("drive:edit")
    if drive.status in {"completed", "cancelled"}:
        raise ConflictException(
            "Completed or cancelled drives must be reopened before scheduling changes"
        )
    try:
        ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError as exc:
        raise BadRequestException("Unknown IANA timezone") from exc
    if len(payload.student_profile_ids) > payload.capacity:
        raise BadRequestException("Assigned participant count exceeds session capacity")
    if payload.document_override_reason and not auth.has_capability("schedule:override_documents"):
        raise ConflictException("Document readiness overrides require schedule:override_documents")

    item = logical_session or RecruitmentSession(
        institution_id=drive.institution_id,
        drive_id=drive.id,
        round_id=round_item.id,
        status="draft",
        concurrency_revision=1,
        created_by_membership_id=auth.membership_id,
    )
    if logical_session is None:
        session.add(item)
        await session.flush()
    if item.round_id != round_item.id or item.drive_id != drive.id:
        raise NotFoundException("Session not found in this round")
    previous = (
        await session.get(SessionRevision, item.current_revision_id)
        if item.current_revision_id
        else None
    )
    revision = SessionRevision(
        institution_id=drive.institution_id,
        drive_id=drive.id,
        session_id=item.id,
        round_id=round_item.id,
        revision_number=(previous.revision_number + 1 if previous else 1),
        start_at=payload.start_at,
        end_at=payload.end_at,
        timezone=payload.timezone,
        buffer_minutes=payload.buffer_minutes,
        capacity=payload.capacity,
        venue=payload.venue.strip() if payload.venue else None,
        meeting_url=payload.meeting_url.strip() if payload.meeting_url else None,
        panel_members=sorted({_norm(v) for v in payload.panel_members if v.strip()}),
        change_reason=payload.change_reason,
        supersedes_revision_id=previous.id if previous else None,
        created_by_membership_id=auth.membership_id,
    )
    session.add(revision)
    await session.flush()
    assignments: list[SessionAssignment] = []
    for student_id in payload.student_profile_ids:
        profile = await session.get(StudentProfile, student_id)
        if not profile or profile.institution_id != drive.institution_id:
            raise BadRequestException("One or more students are unavailable in this institution")
        registration = (
            await session.execute(
                select(Registration).where(
                    Registration.drive_id == drive.id,
                    Registration.student_profile_id == student_id,
                    Registration.state == "submitted",
                )
            )
        ).scalar_one_or_none()
        if not registration:
            raise ConflictException(
                "Every scheduled student must have a submitted registration",
                details={"student_profile_id": str(student_id)},
            )
        eligible = (
            await session.execute(
                select(EligibilityResult).where(
                    EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id,
                    EligibilityResult.student_profile_id == student_id,
                    EligibilityResult.outcome == "eligible",
                )
            )
        ).scalar_one_or_none()
        if not eligible:
            raise ConflictException(
                "Every scheduled student must be currently eligible",
                details={"student_profile_id": str(student_id)},
            )
        readiness = await compute_readiness(
            session,
            institution_id=drive.institution_id,
            drive=drive,
            student_profile_id=student_id,
            stage="scheduling",
        )
        override = payload.document_override_reason if readiness["status"] != "ready" else None
        if readiness["status"] != "ready" and not override:
            raise ConflictException(
                "Scheduling-stage documents are not ready",
                details={"student_profile_id": str(student_id), "readiness": readiness["status"]},
            )
        if round_item.sequence_number > 1 and round_item.requires_previous_round_outcome:
            prior_round = (
                await session.execute(
                    select(RecruitmentRound).where(
                        RecruitmentRound.drive_id == drive.id,
                        RecruitmentRound.sequence_number == round_item.sequence_number - 1,
                    )
                )
            ).scalar_one_or_none()
            prior = None
            if prior_round:
                prior = (
                    (
                        await session.execute(
                            select(OutcomeRevision)
                            .where(
                                OutcomeRevision.round_id == prior_round.id,
                                OutcomeRevision.student_profile_id == student_id,
                                OutcomeRevision.published_at.is_not(None),
                                OutcomeRevision.outcome.in_(["advanced", "selected"]),
                            )
                            .order_by(OutcomeRevision.revision_number.desc())
                        )
                    )
                    .scalars()
                    .first()
                )
            if not prior:
                raise ConflictException(
                    "A published advancing outcome from the previous round is required",
                    details={"student_profile_id": str(student_id)},
                )
        assignment = SessionAssignment(
            institution_id=drive.institution_id,
            drive_id=drive.id,
            session_id=item.id,
            session_revision_id=revision.id,
            student_profile_id=student_id,
            registration_id=registration.id,
            status="draft",
            document_override_reason=override,
            assigned_by_membership_id=auth.membership_id,
        )
        session.add(assignment)
        assignments.append(assignment)
    item.current_revision_id = revision.id
    item.concurrency_revision += 1
    await session.flush()
    return item, revision, assignments


async def _conflicts(session: AsyncSession, revision: SessionRevision) -> list[dict[str, str]]:
    new_assignments = (
        (
            await session.execute(
                select(SessionAssignment).where(
                    SessionAssignment.session_revision_id == revision.id
                )
            )
        )
        .scalars()
        .all()
    )
    new_students = {a.student_profile_id for a in new_assignments}
    others = (
        await session.execute(
            select(RecruitmentSession, SessionRevision)
            .join(SessionRevision, SessionRevision.id == RecruitmentSession.published_revision_id)
            .where(
                RecruitmentSession.institution_id == revision.institution_id,
                RecruitmentSession.id != revision.session_id,
                RecruitmentSession.status.in_(["published", "completed"]),
            )
        )
    ).all()
    found: list[dict[str, str]] = []
    for other_session, other in others:
        new_start = revision.start_at - timedelta(minutes=revision.buffer_minutes)
        new_end = revision.end_at + timedelta(minutes=revision.buffer_minutes)
        old_start = other.start_at - timedelta(minutes=other.buffer_minutes)
        old_end = other.end_at + timedelta(minutes=other.buffer_minutes)
        if not (new_start < old_end and old_start < new_end):
            continue
        if revision.venue and other.venue and _norm(revision.venue) == _norm(other.venue):
            found.append({"resource": "venue", "conflicting_session_id": str(other_session.id)})
        if set(revision.panel_members) & set(other.panel_members):
            found.append({"resource": "panel", "conflicting_session_id": str(other_session.id)})
        old_students = set(
            (
                await session.execute(
                    select(SessionAssignment.student_profile_id).where(
                        SessionAssignment.session_revision_id == other.id,
                        SessionAssignment.status == "published",
                    )
                )
            )
            .scalars()
            .all()
        )
        if new_students & old_students:
            found.append({"resource": "student", "conflicting_session_id": str(other_session.id)})
    return found


async def _validate_current_participation(
    session: AsyncSession,
    drive: Drive,
    logical: RecruitmentSession,
    revision: SessionRevision,
) -> None:
    """Recheck mutable participant evidence at the serialized publication boundary."""
    round_item = await session.get(RecruitmentRound, logical.round_id)
    assignments = (
        (
            await session.execute(
                select(SessionAssignment).where(
                    SessionAssignment.session_revision_id == revision.id
                )
            )
        )
        .scalars()
        .all()
    )
    if len(assignments) > revision.capacity:
        raise ConflictException("Participant count now exceeds session capacity")
    for assignment in assignments:
        registration = await session.get(Registration, assignment.registration_id)
        if not registration or registration.state != "submitted":
            raise ConflictException(
                "A participant registration changed before publication",
                details={"student_profile_id": str(assignment.student_profile_id)},
            )
        eligible = (
            await session.execute(
                select(EligibilityResult).where(
                    EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id,
                    EligibilityResult.student_profile_id == assignment.student_profile_id,
                    EligibilityResult.outcome == "eligible",
                )
            )
        ).scalar_one_or_none()
        if not eligible:
            raise ConflictException(
                "A participant is no longer eligible in the published evaluation",
                details={"student_profile_id": str(assignment.student_profile_id)},
            )
        readiness = await compute_readiness(
            session,
            institution_id=drive.institution_id,
            drive=drive,
            student_profile_id=assignment.student_profile_id,
            stage="scheduling",
        )
        if readiness["status"] != "ready" and not assignment.document_override_reason:
            raise ConflictException(
                "Scheduling document readiness changed before publication",
                details={"student_profile_id": str(assignment.student_profile_id)},
            )
        if (
            round_item
            and round_item.sequence_number > 1
            and round_item.requires_previous_round_outcome
        ):
            previous_round = (
                await session.execute(
                    select(RecruitmentRound).where(
                        RecruitmentRound.drive_id == drive.id,
                        RecruitmentRound.sequence_number == round_item.sequence_number - 1,
                    )
                )
            ).scalar_one_or_none()
            advancing = None
            if previous_round:
                advancing = (
                    (
                        await session.execute(
                            select(OutcomeRevision)
                            .where(
                                OutcomeRevision.round_id == previous_round.id,
                                OutcomeRevision.student_profile_id == assignment.student_profile_id,
                                OutcomeRevision.published_at.is_not(None),
                                OutcomeRevision.outcome.in_(["advanced", "selected"]),
                            )
                            .order_by(OutcomeRevision.revision_number.desc())
                        )
                    )
                    .scalars()
                    .first()
                )
            if not advancing:
                raise ConflictException(
                    "The required prior-round outcome changed before publication",
                    details={"student_profile_id": str(assignment.student_profile_id)},
                )


async def create_schedule_proposal(
    session: AsyncSession, auth: AuthContext, drive: Drive, revision: SessionRevision
) -> ActionProposal:
    auth.require_capability("schedule:publish")
    logical = await session.get(RecruitmentSession, revision.session_id)
    if not logical or logical.current_revision_id != revision.id:
        raise ConflictException("Only the current immutable session revision can be proposed")
    assignments = (
        (
            await session.execute(
                select(SessionAssignment).where(
                    SessionAssignment.session_revision_id == revision.id
                )
            )
        )
        .scalars()
        .all()
    )
    notices: list[dict[str, str]] = []
    for assignment in assignments:
        profile = await session.get(StudentProfile, assignment.student_profile_id)
        user = await session.get(User, profile.user_id) if profile else None
        if user and profile:
            location = revision.venue or revision.meeting_url or "location to be confirmed"
            subject = (
                "Placement session schedule updated"
                if revision.revision_number > 1
                else "Placement session scheduled"
            )
            notices.append(
                {
                    "student_profile_id": str(profile.id),
                    "email": user.email,
                    "subject": subject,
                    "body": (
                        f"Hello {user.full_name},\n\nYour placement session is scheduled for "
                        f"{revision.start_at.isoformat()} to {revision.end_at.isoformat()} "
                        f"({revision.timezone}) at {location}.\n"
                    ),
                }
            )
    proposal_payload = {
        "session_revision": _revision_payload(revision),
        "student_profile_ids": sorted(str(a.student_profile_id) for a in assignments),
        "exact_notifications": notices,
    }
    dependencies = {
        "drive_revision_id": str(drive.published_drive_revision_id),
        "evaluation_run_id": str(drive.published_evaluation_run_id),
        "session_concurrency_revision": logical.concurrency_revision,
    }
    proposal_hash = canonical_hash(
        {
            "action_type": "publish_schedule",
            "payload": proposal_payload,
            "dependencies": dependencies,
        }
    )
    previous = (
        (
            await session.execute(
                select(ActionProposal).where(
                    ActionProposal.institution_id == drive.institution_id,
                    ActionProposal.action_type == "publish_schedule",
                    ActionProposal.target_type == "session",
                    ActionProposal.target_id == logical.id,
                    ActionProposal.state == "pending_approval",
                )
            )
        )
        .scalars()
        .all()
    )
    for old in previous:
        old.state = "stale"
    proposal = ActionProposal(
        institution_id=drive.institution_id,
        drive_id=drive.id,
        action_type="publish_schedule",
        target_type="session",
        target_id=logical.id,
        revision_number=revision.revision_number,
        schema_version=1,
        payload=proposal_payload,
        dependencies=dependencies,
        canonical_hash=proposal_hash,
        state="pending_approval",
        requested_by_membership_id=auth.membership_id,
        execution_bounds={"revision_id": str(revision.id)},
    )
    session.add(proposal)
    await session.flush()
    return proposal


async def _prepare_schedule_notice_draft(
    session: AsyncSession,
    auth: AuthContext,
    drive: Drive,
    logical: RecruitmentSession,
    revision: SessionRevision,
    proposal: ActionProposal,
) -> CommunicationDraft:
    """Create a P07-dispatchable exact notice and stale unsent notices for this session."""
    prior_drafts = (
        (
            await session.execute(
                select(CommunicationDraft).where(
                    CommunicationDraft.drive_id == drive.id,
                    CommunicationDraft.communication_kind.in_(
                        ["interview_schedule", "schedule_correction"]
                    ),
                    CommunicationDraft.state.in_(["draft", "in_review"]),
                )
            )
        )
        .scalars()
        .all()
    )
    for old_draft in prior_drafts:
        old_snapshot = (
            await session.execute(
                select(AudienceSnapshot).where(
                    AudienceSnapshot.communication_draft_id == old_draft.id
                )
            )
        ).scalar_one_or_none()
        if old_snapshot and old_snapshot.query_spec.get("session_id") == str(logical.id):
            old_draft.state = "stale"
            old_proposals = (
                (
                    await session.execute(
                        select(ActionProposal).where(
                            ActionProposal.target_type == "communication_draft",
                            ActionProposal.target_id == old_draft.id,
                            ActionProposal.state == "pending_approval",
                        )
                    )
                )
                .scalars()
                .all()
            )
            for old_proposal in old_proposals:
                old_proposal.state = "stale"

    notices = list(proposal.payload.get("exact_notifications", []))
    if not notices:
        raise ConflictException("The approved schedule contains no deliverable notice evidence")
    communication_kind = (
        "schedule_correction" if revision.revision_number > 1 else "interview_schedule"
    )
    next_revision = (
        int(
            await session.scalar(
                select(func.coalesce(func.max(CommunicationDraft.revision_number), 0)).where(
                    CommunicationDraft.drive_id == drive.id,
                    CommunicationDraft.communication_kind == communication_kind,
                )
            )
            or 0
        )
        + 1
    )
    subject = "Placement session schedule"
    body = (
        "Recipient-specific content is frozen in this audience revision for "
        f"session revision {revision.revision_number}."
    )
    content_hash = canonical_hash(
        {
            "template_version": "session-schedule-v1",
            "subject": subject,
            "body": body,
            "sender": settings.SMTP_SENDER.lower(),
            "reply_to": auth.email.lower(),
            "session_revision_id": str(revision.id),
        }
    )
    draft = CommunicationDraft(
        institution_id=drive.institution_id,
        drive_id=drive.id,
        revision_number=next_revision,
        communication_kind=communication_kind,
        audience_type="session_participants",
        template_version="session-schedule-v1",
        subject_template=subject,
        body_template=body,
        sender_email=settings.SMTP_SENDER.lower(),
        reply_to=auth.email.lower(),
        state="draft",
        content_hash=content_hash,
        created_by_membership_id=auth.membership_id,
    )
    session.add(draft)
    await session.flush()
    descriptors: list[dict[str, str]] = []
    recipient_evidence: list[tuple[StudentProfile, User, dict[str, str]]] = []
    for notice in notices:
        profile = await session.get(StudentProfile, uuid.UUID(notice["student_profile_id"]))
        user = await session.get(User, profile.user_id) if profile else None
        if not profile or not user or user.email.strip().lower() != notice["email"].strip().lower():
            raise ConflictException(
                "A schedule recipient contact changed before notice preparation"
            )
        descriptor = {
            "student_profile_id": str(profile.id),
            "email": user.email.strip().lower(),
            "contact_revision": contact_revision(user),
        }
        descriptors.append(descriptor)
        recipient_evidence.append((profile, user, notice))
    audience_hash = canonical_hash(sorted(descriptors, key=lambda value: value["email"]))
    snapshot = AudienceSnapshot(
        institution_id=drive.institution_id,
        drive_id=drive.id,
        communication_draft_id=draft.id,
        audience_type="session_participants",
        query_spec={
            "type": "session_participants",
            "session_id": str(logical.id),
            "session_revision_id": str(revision.id),
            "schedule_proposal_id": str(proposal.id),
        },
        included_count=len(recipient_evidence),
        excluded_count=0,
        duplicate_count=0,
        unresolved_count=0,
        exclusion_summary={},
        canonical_hash=audience_hash,
    )
    session.add(snapshot)
    await session.flush()
    for profile, user, notice in recipient_evidence:
        session.add(
            AudienceRecipient(
                institution_id=drive.institution_id,
                audience_snapshot_id=snapshot.id,
                student_profile_id=profile.id,
                user_id=user.id,
                email=user.email,
                normalized_email=user.email.strip().lower(),
                display_name=user.full_name,
                inclusion_reason="Published participant in the approved session revision",
                contact_revision=contact_revision(user),
                merge_data={
                    "session_id": str(logical.id),
                    "session_revision_id": str(revision.id),
                },
                rendered_subject=notice["subject"],
                rendered_body=notice["body"],
                rendered_hash=canonical_hash(
                    {"subject": notice["subject"], "body": notice["body"]}
                ),
            )
        )
    await session.flush()
    return draft


async def decide_schedule_proposal(
    session: AsyncSession,
    auth: AuthContext,
    drive: Drive,
    proposal: ActionProposal,
    decision: str,
    expected_revision: int,
    expected_hash: str,
    comment: str | None,
) -> None:
    auth.require_capability("proposal:decide")
    auth.require_capability("schedule:publish")
    if (
        proposal.state != "pending_approval"
        or proposal.revision_number != expected_revision
        or proposal.canonical_hash != expected_hash
    ):
        raise ConflictException(
            "Schedule proposal is stale or no longer pending", code="PROPOSAL_STALE"
        )
    logical = await session.get(RecruitmentSession, proposal.target_id)
    revision_id = uuid.UUID(str(proposal.execution_bounds["revision_id"]))
    revision = await session.get(SessionRevision, revision_id)
    if (
        not logical
        or not revision
        or logical.current_revision_id != revision.id
        or logical.concurrency_revision != proposal.dependencies["session_concurrency_revision"]
    ):
        proposal.state = "stale"
        raise ConflictException("Schedule dependencies changed", code="PROPOSAL_STALE")
    if (
        str(drive.published_drive_revision_id) != proposal.dependencies["drive_revision_id"]
        or str(drive.published_evaluation_run_id) != proposal.dependencies["evaluation_run_id"]
    ):
        proposal.state = "stale"
        raise ConflictException("Drive dependencies changed", code="PROPOSAL_STALE")
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"schedule:{drive.institution_id}"},
    )
    if decision == "approved":
        await _validate_current_participation(session, drive, logical, revision)
        conflicts = await _conflicts(session, revision)
        if conflicts:
            raise ConflictException(
                "Session conflicts with published institutional resources",
                details={"conflicts": conflicts},
            )
    session.add(
        ApprovalDecision(
            institution_id=drive.institution_id,
            proposal_id=proposal.id,
            proposal_hash=proposal.canonical_hash,
            decision=decision,
            comment=comment,
            decided_by_membership_id=auth.membership_id,
            permission_context={
                "capabilities": sorted(auth.capabilities),
                "institution_id": str(auth.institution_id),
            },
        )
    )
    proposal.state = {
        "approved": "approved",
        "rejected": "rejected",
        "revision_requested": "revision_requested",
    }[decision]
    if decision == "approved":
        if logical.published_revision_id and logical.published_revision_id != revision.id:
            old_rows = (
                (
                    await session.execute(
                        select(SessionAssignment).where(
                            SessionAssignment.session_revision_id == logical.published_revision_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            for row in old_rows:
                row.status = "cancelled"
        rows = (
            (
                await session.execute(
                    select(SessionAssignment).where(
                        SessionAssignment.session_revision_id == revision.id
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in rows:
            row.status = "published"
        logical.published_revision_id = revision.id
        logical.status = "published"
        revision.published_proposal_id = proposal.id
        await _prepare_schedule_notice_draft(session, auth, drive, logical, revision, proposal)


async def record_outcome(
    session: AsyncSession,
    auth: AuthContext,
    drive: Drive,
    round_item: RecruitmentRound,
    payload: OutcomeCreate,
) -> OutcomeRevision:
    auth.require_capability("drive:edit")
    if drive.status in {"completed", "cancelled"}:
        raise ConflictException(
            "Completed or cancelled drives must be reopened before recording outcomes"
        )
    assigned = (
        (
            await session.execute(
                select(SessionAssignment)
                .join(RecruitmentSession, RecruitmentSession.id == SessionAssignment.session_id)
                .where(
                    RecruitmentSession.round_id == round_item.id,
                    SessionAssignment.student_profile_id == payload.student_profile_id,
                    SessionAssignment.status == "published",
                )
            )
        )
        .scalars()
        .first()
    )
    if not assigned:
        raise ConflictException("An outcome can only be recorded for a published round participant")
    previous = (
        (
            await session.execute(
                select(OutcomeRevision)
                .where(
                    OutcomeRevision.round_id == round_item.id,
                    OutcomeRevision.student_profile_id == payload.student_profile_id,
                )
                .order_by(OutcomeRevision.revision_number.desc())
            )
        )
        .scalars()
        .first()
    )
    item = OutcomeRevision(
        institution_id=drive.institution_id,
        drive_id=drive.id,
        round_id=round_item.id,
        student_profile_id=payload.student_profile_id,
        revision_number=(previous.revision_number + 1 if previous else 1),
        outcome=payload.outcome,
        source_type=payload.source_type,
        source_reference=payload.source_reference,
        source_evidence=payload.source_evidence,
        note=payload.note,
        offer_status=payload.offer_status,
        acceptance_status=payload.acceptance_status,
        joining_status=payload.joining_status,
        supersedes_revision_id=previous.id if previous else None,
        recorded_by_membership_id=auth.membership_id,
    )
    session.add(item)
    await session.flush()
    return item


async def create_result_proposal(
    session: AsyncSession, auth: AuthContext, drive: Drive, outcome: OutcomeRevision
) -> ActionProposal:
    auth.require_capability("result:publish")
    latest = (
        (
            await session.execute(
                select(OutcomeRevision)
                .where(
                    OutcomeRevision.round_id == outcome.round_id,
                    OutcomeRevision.student_profile_id == outcome.student_profile_id,
                )
                .order_by(OutcomeRevision.revision_number.desc())
            )
        )
        .scalars()
        .first()
    )
    if not latest or latest.id != outcome.id:
        raise ConflictException("Only the latest result revision can be proposed")
    payload = {
        "outcome_revision_id": str(outcome.id),
        "round_id": str(outcome.round_id),
        "student_profile_id": str(outcome.student_profile_id),
        "outcome": outcome.outcome,
        "offer_status": outcome.offer_status,
        "acceptance_status": outcome.acceptance_status,
        "joining_status": outcome.joining_status,
    }
    dependencies = {
        "drive_revision_id": str(drive.published_drive_revision_id),
        "outcome_revision_id": str(outcome.id),
    }
    proposal_hash = canonical_hash(
        {"action_type": "publish_result", "payload": payload, "dependencies": dependencies}
    )
    olds = (
        (
            await session.execute(
                select(ActionProposal).where(
                    ActionProposal.action_type == "publish_result",
                    ActionProposal.drive_id == drive.id,
                    ActionProposal.state == "pending_approval",
                )
            )
        )
        .scalars()
        .all()
    )
    for old in olds:
        if old.payload.get("round_id") == str(outcome.round_id) and old.payload.get(
            "student_profile_id"
        ) == str(outcome.student_profile_id):
            old.state = "stale"
    proposal = ActionProposal(
        institution_id=drive.institution_id,
        drive_id=drive.id,
        action_type="publish_result",
        target_type="outcome",
        target_id=outcome.id,
        revision_number=outcome.revision_number,
        schema_version=1,
        payload=payload,
        dependencies=dependencies,
        canonical_hash=proposal_hash,
        state="pending_approval",
        requested_by_membership_id=auth.membership_id,
        execution_bounds={"outcome_revision_id": str(outcome.id)},
    )
    session.add(proposal)
    await session.flush()
    return proposal


async def decide_result_proposal(
    session: AsyncSession,
    auth: AuthContext,
    drive: Drive,
    proposal: ActionProposal,
    decision: str,
    expected_revision: int,
    expected_hash: str,
    comment: str | None,
) -> None:
    auth.require_capability("proposal:decide")
    auth.require_capability("result:publish")
    if (
        proposal.state != "pending_approval"
        or proposal.revision_number != expected_revision
        or proposal.canonical_hash != expected_hash
    ):
        raise ConflictException(
            "Result proposal is stale or no longer pending", code="PROPOSAL_STALE"
        )
    outcome = await session.get(
        OutcomeRevision, uuid.UUID(proposal.execution_bounds["outcome_revision_id"])
    )
    latest = (
        (
            await session.execute(
                select(OutcomeRevision)
                .where(
                    OutcomeRevision.round_id == outcome.round_id,
                    OutcomeRevision.student_profile_id == outcome.student_profile_id,
                )
                .order_by(OutcomeRevision.revision_number.desc())
            )
        )
        .scalars()
        .first()
        if outcome
        else None
    )
    if (
        not outcome
        or not latest
        or latest.id != outcome.id
        or str(drive.published_drive_revision_id) != proposal.dependencies["drive_revision_id"]
    ):
        proposal.state = "stale"
        raise ConflictException("Result dependencies changed", code="PROPOSAL_STALE")
    session.add(
        ApprovalDecision(
            institution_id=drive.institution_id,
            proposal_id=proposal.id,
            proposal_hash=proposal.canonical_hash,
            decision=decision,
            comment=comment,
            decided_by_membership_id=auth.membership_id,
            permission_context={
                "capabilities": sorted(auth.capabilities),
                "institution_id": str(auth.institution_id),
            },
        )
    )
    proposal.state = {
        "approved": "approved",
        "rejected": "rejected",
        "revision_requested": "revision_requested",
    }[decision]
    if decision == "approved":
        outcome.published_proposal_id = proposal.id
        outcome.published_at = datetime.now(UTC)


async def build_report_snapshot(session: AsyncSession, drive: Drive) -> dict[str, Any]:
    evaluation = (
        await session.get(EvaluationRun, drive.published_evaluation_run_id)
        if drive.published_evaluation_run_id
        else None
    )
    company = await session.get(Company, drive.company_id)
    revision = (
        await session.get(DriveRevision, drive.published_drive_revision_id)
        if drive.published_drive_revision_id
        else None
    )
    registrations = (
        (await session.execute(select(Registration).where(Registration.drive_id == drive.id)))
        .scalars()
        .all()
    )
    sessions = (
        (
            await session.execute(
                select(RecruitmentSession).where(RecruitmentSession.drive_id == drive.id)
            )
        )
        .scalars()
        .all()
    )
    rounds = (
        (
            await session.execute(
                select(RecruitmentRound)
                .where(RecruitmentRound.drive_id == drive.id)
                .order_by(RecruitmentRound.sequence_number)
            )
        )
        .scalars()
        .all()
    )
    candidates: list[dict[str, Any]] = []
    for registration in sorted(registrations, key=lambda r: str(r.student_profile_id)):
        profile = await session.get(StudentProfile, registration.student_profile_id)
        user = await session.get(User, profile.user_id) if profile else None
        result = (
            (
                await session.execute(
                    select(EligibilityResult).where(
                        EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id,
                        EligibilityResult.student_profile_id == registration.student_profile_id,
                    )
                )
            ).scalar_one_or_none()
            if drive.published_evaluation_run_id
            else None
        )
        outcomes = (
            (
                await session.execute(
                    select(OutcomeRevision)
                    .where(
                        OutcomeRevision.drive_id == drive.id,
                        OutcomeRevision.student_profile_id == registration.student_profile_id,
                        OutcomeRevision.published_at.is_not(None),
                    )
                    .order_by(OutcomeRevision.round_id, OutcomeRevision.revision_number.desc())
                )
            )
            .scalars()
            .all()
        )
        latest_by_round: dict[str, OutcomeRevision] = {}
        for outcome in outcomes:
            latest_by_round.setdefault(str(outcome.round_id), outcome)
        readiness = await compute_readiness(
            session,
            institution_id=drive.institution_id,
            drive=drive,
            student_profile_id=registration.student_profile_id,
        )
        candidates.append(
            {
                "student_profile_id": str(registration.student_profile_id),
                "student_identifier": profile.student_identifier if profile else "",
                "student_name": user.full_name if user else "",
                "email": user.email if user else "",
                "registration_status": registration.state,
                "eligibility_status": result.outcome if result else "not_evaluated",
                "document_readiness": readiness["status"],
                "published_outcomes": [
                    {"round_id": rid, "revision_id": str(value.id), "outcome": value.outcome}
                    for rid, value in sorted(latest_by_round.items())
                ],
            }
        )
    attendance_counts: dict[str, int] = {"present": 0, "absent": 0, "excused": 0, "not_recorded": 0}
    outcome_counts: dict[str, int] = {}
    for item in sessions:
        if not item.published_revision_id:
            continue
        assigns = (
            (
                await session.execute(
                    select(SessionAssignment).where(
                        SessionAssignment.session_revision_id == item.published_revision_id,
                        SessionAssignment.status == "published",
                    )
                )
            )
            .scalars()
            .all()
        )
        for assignment in assigns:
            attendance = (
                (
                    await session.execute(
                        select(AttendanceRevision)
                        .where(
                            AttendanceRevision.session_id == item.id,
                            AttendanceRevision.student_profile_id == assignment.student_profile_id,
                        )
                        .order_by(AttendanceRevision.revision_number.desc())
                    )
                )
                .scalars()
                .first()
            )
            attendance_counts[attendance.status if attendance else "not_recorded"] += 1
    published_latest: dict[tuple[uuid.UUID, uuid.UUID], OutcomeRevision] = {}
    for outcome in (
        (
            await session.execute(
                select(OutcomeRevision)
                .where(
                    OutcomeRevision.drive_id == drive.id, OutcomeRevision.published_at.is_not(None)
                )
                .order_by(OutcomeRevision.revision_number.desc())
            )
        )
        .scalars()
        .all()
    ):
        published_latest.setdefault((outcome.round_id, outcome.student_profile_id), outcome)
    for outcome in published_latest.values():
        outcome_counts[outcome.outcome] = outcome_counts.get(outcome.outcome, 0) + 1
    dispatch_counts = dict(
        (
            await session.execute(
                select(DispatchOperation.status, func.count())
                .where(DispatchOperation.drive_id == drive.id)
                .group_by(DispatchOperation.status)
            )
        ).all()
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "drive_id": str(drive.id),
        "company": company.name if company else None,
        "role_title": revision.role_title if revision else drive.title,
        "revision_references": {
            "drive_revision_id": str(drive.published_drive_revision_id),
            "evaluation_run_id": str(drive.published_evaluation_run_id),
            "policy_id": str(evaluation.policy_id) if evaluation else None,
        },
        "denominators": {
            "evaluated": evaluation.total_count if evaluation else 0,
            "registered_records": len(registrations),
            "published_assignments": sum(attendance_counts.values()),
        },
        "eligibility": {
            "eligible": evaluation.eligible_count if evaluation else 0,
            "ineligible": evaluation.ineligible_count if evaluation else 0,
            "needs_review": evaluation.needs_review_count if evaluation else 0,
        },
        "registrations": dict(
            (
                await session.execute(
                    select(Registration.state, func.count())
                    .where(Registration.drive_id == drive.id)
                    .group_by(Registration.state)
                )
            ).all()
        ),
        "rounds": [
            {
                "id": str(r.id),
                "sequence_number": r.sequence_number,
                "name": r.name,
                "status": r.status,
            }
            for r in rounds
        ],
        "sessions": [
            {
                "id": str(s.id),
                "status": s.status,
                "published_revision_id": str(s.published_revision_id)
                if s.published_revision_id
                else None,
            }
            for s in sessions
        ],
        "attendance": attendance_counts,
        "published_outcomes": outcome_counts,
        "dispatch": dispatch_counts,
        "candidate_rows": candidates,
    }


async def create_report(
    session: AsyncSession, auth: AuthContext, drive: Drive, kind: str, reason: str
) -> DriveReportRevision:
    snapshot = await build_report_snapshot(session, drive)
    previous = (
        (
            await session.execute(
                select(DriveReportRevision)
                .where(DriveReportRevision.drive_id == drive.id)
                .order_by(DriveReportRevision.revision_number.desc())
            )
        )
        .scalars()
        .first()
    )
    report = DriveReportRevision(
        institution_id=drive.institution_id,
        drive_id=drive.id,
        revision_number=(previous.revision_number + 1 if previous else 1),
        report_kind=kind,
        status="frozen",
        snapshot_payload=snapshot,
        snapshot_hash=canonical_hash(snapshot),
        reason=reason,
        supersedes_report_id=previous.id if previous else None,
        created_by_membership_id=auth.membership_id,
    )
    session.add(report)
    await session.flush()
    drive.latest_report_revision_id = report.id
    return report


async def closure_blockers(session: AsyncSession, drive: Drive) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if not drive.registration_closed_at:
        blockers.append({"code": "REGISTRATION_OPEN"})
    sessions = (
        (
            await session.execute(
                select(RecruitmentSession).where(RecruitmentSession.drive_id == drive.id)
            )
        )
        .scalars()
        .all()
    )
    if not sessions:
        blockers.append({"code": "NO_SESSIONS"})
    active = [str(s.id) for s in sessions if s.status not in {"completed", "cancelled"}]
    if active:
        blockers.append({"code": "SESSIONS_INCOMPLETE", "session_ids": active})
    pending = int(
        await session.scalar(
            select(func.count())
            .select_from(ActionProposal)
            .where(ActionProposal.drive_id == drive.id, ActionProposal.state == "pending_approval")
        )
        or 0
    )
    if pending:
        blockers.append({"code": "PENDING_PROPOSALS", "count": pending})
    delivery = dict(
        (
            await session.execute(
                select(DispatchOperation.status, func.count())
                .where(
                    DispatchOperation.drive_id == drive.id,
                    DispatchOperation.status.in_(["pending", "claimed", "unknown"]),
                )
                .group_by(DispatchOperation.status)
            )
        ).all()
    )
    if delivery:
        blockers.append({"code": "ACTIVE_OR_UNKNOWN_DELIVERY", "counts": delivery})
    cases = (
        (
            await session.execute(
                select(ExceptionCase).where(
                    ExceptionCase.drive_id == drive.id,
                    ExceptionCase.status.in_(["open", "acknowledged"]),
                )
            )
        )
        .scalars()
        .all()
    )
    blocking_cases = [
        str(c.id) for c in cases if c.severity in {"high", "critical"} or c.status == "open"
    ]
    if blocking_cases:
        blockers.append({"code": "UNRESOLVED_CASES", "case_ids": blocking_cases})
    return blockers


def report_csv(report: DriveReportRevision) -> str:
    output = io.StringIO(newline="")
    fields = [
        "student_identifier",
        "student_name",
        "email",
        "registration_status",
        "eligibility_status",
        "document_readiness",
        "published_outcomes",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in report.snapshot_payload.get("candidate_rows", []):
        values = {key: row.get(key, "") for key in fields}
        values["published_outcomes"] = "; ".join(
            f"{x['round_id']}:{x['outcome']}" for x in row.get("published_outcomes", [])
        )
        for key, value in values.items():
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
                values[key] = "'" + value
        writer.writerow(values)
    return output.getvalue()


async def create_export_grant(
    session: AsyncSession, auth: AuthContext, report: DriveReportRevision
) -> tuple[ReportExportGrant, str]:
    auth.require_capability("export:generate")
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    grant = ReportExportGrant(
        institution_id=report.institution_id,
        drive_id=report.drive_id,
        report_revision_id=report.id,
        token_hash=digest,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        created_by_membership_id=auth.membership_id,
    )
    session.add(grant)
    await session.flush()
    return grant, raw


async def student_profile_for_auth(session: AsyncSession, auth: AuthContext) -> StudentProfile:
    profile = (
        await session.execute(
            select(StudentProfile).where(
                StudentProfile.institution_id == auth.institution_id,
                StudentProfile.user_id == auth.user_id,
            )
        )
    ).scalar_one_or_none()
    if not profile:
        raise NotFoundException("Student profile not found")
    return profile
