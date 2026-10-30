"""P09 scheduling, results, reports, and drive completion API."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import ConflictException, NotFoundException
from placementos.models.intelligence import ActionProposal
from placementos.models.lifecycle import (
    AttendanceRevision,
    DriveReportRevision,
    OutcomeGapAcknowledgement,
    OutcomeRevision,
    RecruitmentRound,
    RecruitmentSession,
    ReportExportGrant,
    SessionAssignment,
    SessionRevision,
)
from placementos.models.workflow import WorkflowRun
from placementos.schemas.lifecycle import (
    AttendanceCreate,
    ExportGrantResponse,
    GapAcknowledgementCreate,
    OutcomeCreate,
    OutcomeResponse,
    ProposalDecisionCreate,
    ProposalResponse,
    ReasonCreate,
    ReportCreate,
    ReportResponse,
    RoundCreate,
    RoundResponse,
    SessionCreate,
    SessionResponse,
)
from placementos.services.audit import record_audit
from placementos.services.authorization import load_authorized_drive
from placementos.services.lifecycle import (
    closure_blockers,
    create_export_grant,
    create_report,
    create_result_proposal,
    create_schedule_proposal,
    create_session_revision,
    decide_result_proposal,
    decide_schedule_proposal,
    record_outcome,
    report_csv,
    student_profile_for_auth,
)
from placementos.services.session import AuthContext

router = APIRouter(tags=["Scheduling, results, reports & closure"])


def round_response(item: RecruitmentRound) -> RoundResponse:
    return RoundResponse(
        id=item.id,
        drive_id=item.drive_id,
        sequence_number=item.sequence_number,
        name=item.name,
        round_type=item.round_type,
        requires_previous_round_outcome=item.requires_previous_round_outcome,
        status=item.status,
    )


def proposal_response(item: ActionProposal) -> ProposalResponse:
    return ProposalResponse(
        id=item.id,
        action_type=item.action_type,
        target_type=item.target_type,
        target_id=item.target_id,
        revision_number=item.revision_number,
        canonical_hash=item.canonical_hash,
        state=item.state,
        payload=item.payload,
        dependencies=item.dependencies,
    )


def outcome_response(item: OutcomeRevision) -> OutcomeResponse:
    return OutcomeResponse(
        id=item.id,
        round_id=item.round_id,
        student_profile_id=item.student_profile_id,
        revision_number=item.revision_number,
        outcome=item.outcome,
        source_type=item.source_type,
        source_reference=item.source_reference,
        source_evidence=item.source_evidence,
        note=item.note,
        offer_status=item.offer_status,
        acceptance_status=item.acceptance_status,
        joining_status=item.joining_status,
        published_at=item.published_at,
    )


def report_response(item: DriveReportRevision) -> ReportResponse:
    return ReportResponse(
        id=item.id,
        drive_id=item.drive_id,
        revision_number=item.revision_number,
        report_kind=item.report_kind,
        status=item.status,
        snapshot_payload=item.snapshot_payload,
        snapshot_hash=item.snapshot_hash,
        reason=item.reason,
        created_at=item.created_at,
    )


async def session_response(db: AsyncSession, item: RecruitmentSession) -> SessionResponse:
    revision = (
        await db.get(SessionRevision, item.current_revision_id)
        if item.current_revision_id
        else None
    )
    assignments = (
        (
            await db.execute(
                select(SessionAssignment).where(
                    SessionAssignment.session_revision_id == item.current_revision_id
                )
            )
        )
        .scalars()
        .all()
        if item.current_revision_id
        else []
    )
    revision_payload = (
        None
        if not revision
        else {
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
    )
    return SessionResponse(
        id=item.id,
        drive_id=item.drive_id,
        round_id=item.round_id,
        status=item.status,
        current_revision_id=item.current_revision_id,
        published_revision_id=item.published_revision_id,
        revision=revision_payload,
        assignments=[
            {
                "student_profile_id": str(a.student_profile_id),
                "status": a.status,
                "document_override_reason": a.document_override_reason,
            }
            for a in assignments
        ],
    )


@router.post("/drives/{drive_id}/rounds", response_model=RoundResponse)
async def create_round(
    drive_id: uuid.UUID,
    payload: RoundCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> RoundResponse:
    auth.require_capability("drive:edit")
    drive = await load_authorized_drive(db, auth, drive_id, for_update=True)
    if drive.status in {"completed", "cancelled"}:
        raise ConflictException("Reopen this drive before adding rounds")
    item = RecruitmentRound(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        sequence_number=payload.sequence_number,
        name=payload.name.strip(),
        round_type=payload.round_type.strip(),
        requires_previous_round_outcome=payload.requires_previous_round_outcome,
        status="active",
        created_by_membership_id=auth.membership_id,
    )
    db.add(item)
    await db.flush()
    record_audit(
        db,
        auth,
        "round.created",
        "recruitment_round",
        item.id,
        {"drive_id": str(drive.id), "sequence_number": item.sequence_number},
    )
    await db.commit()
    return round_response(item)


@router.get("/drives/{drive_id}/rounds", response_model=list[RoundResponse])
async def list_rounds(
    drive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> list[RoundResponse]:
    await load_authorized_drive(db, auth, drive_id)
    rows = (
        (
            await db.execute(
                select(RecruitmentRound)
                .where(RecruitmentRound.drive_id == drive_id)
                .order_by(RecruitmentRound.sequence_number)
            )
        )
        .scalars()
        .all()
    )
    return [round_response(x) for x in rows]


@router.post("/rounds/{round_id}/sessions", response_model=SessionResponse)
async def create_session(
    round_id: uuid.UUID,
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> SessionResponse:
    round_item = await db.get(RecruitmentRound, round_id)
    if not round_item or round_item.institution_id != auth.institution_id:
        raise NotFoundException("Round not found")
    drive = await load_authorized_drive(db, auth, round_item.drive_id, for_update=True)
    item, revision, _ = await create_session_revision(db, auth, drive, round_item, payload)
    record_audit(
        db,
        auth,
        "session.revision_created",
        "session_revision",
        revision.id,
        {"session_id": str(item.id)},
    )
    await db.commit()
    return await session_response(db, item)


@router.post("/sessions/{session_id}/revisions", response_model=SessionResponse)
async def revise_session(
    session_id: uuid.UUID,
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> SessionResponse:
    item = await db.get(RecruitmentSession, session_id)
    if not item or item.institution_id != auth.institution_id:
        raise NotFoundException("Session not found")
    drive = await load_authorized_drive(db, auth, item.drive_id, for_update=True)
    round_item = await db.get(RecruitmentRound, item.round_id)
    if not round_item:
        raise NotFoundException("Round not found")
    item, revision, _ = await create_session_revision(db, auth, drive, round_item, payload, item)
    record_audit(
        db,
        auth,
        "session.rescheduled",
        "session_revision",
        revision.id,
        {"change_reason": revision.change_reason},
    )
    await db.commit()
    return await session_response(db, item)


@router.get("/drives/{drive_id}/sessions", response_model=list[SessionResponse])
async def list_sessions(
    drive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> list[SessionResponse]:
    await load_authorized_drive(db, auth, drive_id)
    items = (
        (
            await db.execute(
                select(RecruitmentSession)
                .where(RecruitmentSession.drive_id == drive_id)
                .order_by(RecruitmentSession.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [await session_response(db, item) for item in items]


@router.post(
    "/session-revisions/{revision_id}/publication-proposals", response_model=ProposalResponse
)
async def propose_session(
    revision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ProposalResponse:
    revision = await db.get(SessionRevision, revision_id)
    if not revision or revision.institution_id != auth.institution_id:
        raise NotFoundException("Session revision not found")
    drive = await load_authorized_drive(db, auth, revision.drive_id)
    proposal = await create_schedule_proposal(db, auth, drive, revision)
    record_audit(db, auth, "schedule.proposed", "action_proposal", proposal.id)
    await db.commit()
    return proposal_response(proposal)


@router.post("/schedule-proposals/{proposal_id}/decisions", response_model=ProposalResponse)
async def decide_schedule(
    proposal_id: uuid.UUID,
    payload: ProposalDecisionCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ProposalResponse:
    proposal = await db.get(ActionProposal, proposal_id)
    if (
        not proposal
        or proposal.institution_id != auth.institution_id
        or proposal.action_type != "publish_schedule"
    ):
        raise NotFoundException("Schedule proposal not found")
    drive = await load_authorized_drive(db, auth, proposal.drive_id, for_update=True)
    await decide_schedule_proposal(
        db,
        auth,
        drive,
        proposal,
        payload.decision,
        payload.expected_revision,
        payload.expected_hash,
        payload.comment,
    )
    record_audit(db, auth, f"schedule.{payload.decision}", "action_proposal", proposal.id)
    await db.commit()
    return proposal_response(proposal)


@router.post("/sessions/{session_id}/attendance", response_model=list[dict])
async def record_attendance(
    session_id: uuid.UUID,
    payload: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> list[dict]:
    auth.require_capability("drive:edit")
    item = await db.get(RecruitmentSession, session_id)
    if not item or item.institution_id != auth.institution_id:
        raise NotFoundException("Session not found")
    drive = await load_authorized_drive(db, auth, item.drive_id)
    if drive.status in {"completed", "cancelled"}:
        raise ConflictException("Reopen this drive before changing attendance")
    assigned = set(
        (
            await db.execute(
                select(SessionAssignment.student_profile_id).where(
                    SessionAssignment.session_revision_id == item.published_revision_id,
                    SessionAssignment.status == "published",
                )
            )
        )
        .scalars()
        .all()
    )
    result: list[dict] = []
    for value in payload.items:
        if value.student_profile_id not in assigned:
            raise ConflictException("Attendance can only be recorded for a published participant")
        previous = (
            (
                await db.execute(
                    select(AttendanceRevision)
                    .where(
                        AttendanceRevision.session_id == item.id,
                        AttendanceRevision.student_profile_id == value.student_profile_id,
                    )
                    .order_by(AttendanceRevision.revision_number.desc())
                )
            )
            .scalars()
            .first()
        )
        row = AttendanceRevision(
            institution_id=auth.institution_id,
            drive_id=item.drive_id,
            session_id=item.id,
            student_profile_id=value.student_profile_id,
            revision_number=(previous.revision_number + 1 if previous else 1),
            status=value.status,
            note=value.note,
            recorded_at=datetime.now(UTC),
            recorded_by_membership_id=auth.membership_id,
        )
        db.add(row)
        await db.flush()
        result.append(
            {
                "id": str(row.id),
                "student_profile_id": str(row.student_profile_id),
                "revision_number": row.revision_number,
                "status": row.status,
            }
        )
    record_audit(
        db, auth, "attendance.recorded", "recruitment_session", item.id, {"count": len(result)}
    )
    await db.commit()
    return result


@router.post("/sessions/{session_id}/outcome-gaps", response_model=dict)
async def acknowledge_gap(
    session_id: uuid.UUID,
    payload: GapAcknowledgementCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> dict:
    auth.require_capability("drive:edit")
    item = await db.get(RecruitmentSession, session_id)
    if not item or item.institution_id != auth.institution_id:
        raise NotFoundException("Session not found")
    await load_authorized_drive(db, auth, item.drive_id)
    row = OutcomeGapAcknowledgement(
        institution_id=auth.institution_id,
        drive_id=item.drive_id,
        session_id=item.id,
        student_profile_id=payload.student_profile_id,
        reason=payload.reason,
        acknowledged_by_membership_id=auth.membership_id,
    )
    db.add(row)
    await db.flush()
    record_audit(db, auth, "outcome_gap.acknowledged", "outcome_gap", row.id)
    await db.commit()
    return {"id": str(row.id), "reason": row.reason}


@router.post("/rounds/{round_id}/outcomes", response_model=OutcomeResponse)
async def add_outcome(
    round_id: uuid.UUID,
    payload: OutcomeCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> OutcomeResponse:
    round_item = await db.get(RecruitmentRound, round_id)
    if not round_item or round_item.institution_id != auth.institution_id:
        raise NotFoundException("Round not found")
    drive = await load_authorized_drive(db, auth, round_item.drive_id)
    item = await record_outcome(db, auth, drive, round_item, payload)
    record_audit(db, auth, "outcome.revision_recorded", "outcome_revision", item.id)
    await db.commit()
    return outcome_response(item)


@router.post("/outcomes/{outcome_id}/publication-proposals", response_model=ProposalResponse)
async def propose_outcome(
    outcome_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ProposalResponse:
    item = await db.get(OutcomeRevision, outcome_id)
    if not item or item.institution_id != auth.institution_id:
        raise NotFoundException("Outcome not found")
    drive = await load_authorized_drive(db, auth, item.drive_id)
    proposal = await create_result_proposal(db, auth, drive, item)
    record_audit(db, auth, "result.proposed", "action_proposal", proposal.id)
    await db.commit()
    return proposal_response(proposal)


@router.get("/drives/{drive_id}/outcomes", response_model=list[OutcomeResponse])
async def list_outcomes(
    drive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> list[OutcomeResponse]:
    await load_authorized_drive(db, auth, drive_id)
    rows = (
        (
            await db.execute(
                select(OutcomeRevision)
                .where(OutcomeRevision.drive_id == drive_id)
                .order_by(
                    OutcomeRevision.round_id,
                    OutcomeRevision.student_profile_id,
                    OutcomeRevision.revision_number.desc(),
                )
            )
        )
        .scalars()
        .all()
    )
    return [outcome_response(row) for row in rows]


@router.post("/result-proposals/{proposal_id}/decisions", response_model=ProposalResponse)
async def decide_result(
    proposal_id: uuid.UUID,
    payload: ProposalDecisionCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ProposalResponse:
    proposal = await db.get(ActionProposal, proposal_id)
    if (
        not proposal
        or proposal.institution_id != auth.institution_id
        or proposal.action_type != "publish_result"
    ):
        raise NotFoundException("Result proposal not found")
    drive = await load_authorized_drive(db, auth, proposal.drive_id, for_update=True)
    await decide_result_proposal(
        db,
        auth,
        drive,
        proposal,
        payload.decision,
        payload.expected_revision,
        payload.expected_hash,
        payload.comment,
    )
    record_audit(db, auth, f"result.{payload.decision}", "action_proposal", proposal.id)
    await db.commit()
    return proposal_response(proposal)


@router.post("/sessions/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> SessionResponse:
    auth.require_capability("drive:edit")
    item = await db.get(RecruitmentSession, session_id)
    if not item or item.institution_id != auth.institution_id:
        raise NotFoundException("Session not found")
    await load_authorized_drive(db, auth, item.drive_id, for_update=True)
    assignments = (
        (
            await db.execute(
                select(SessionAssignment).where(
                    SessionAssignment.session_revision_id == item.published_revision_id,
                    SessionAssignment.status == "published",
                )
            )
        )
        .scalars()
        .all()
    )
    for assignment in assignments:
        attendance = (
            (
                await db.execute(
                    select(AttendanceRevision).where(
                        AttendanceRevision.session_id == item.id,
                        AttendanceRevision.student_profile_id == assignment.student_profile_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        outcome = (
            (
                await db.execute(
                    select(OutcomeRevision).where(
                        OutcomeRevision.round_id == item.round_id,
                        OutcomeRevision.student_profile_id == assignment.student_profile_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        gap = (
            await db.execute(
                select(OutcomeGapAcknowledgement).where(
                    OutcomeGapAcknowledgement.session_id == item.id,
                    OutcomeGapAcknowledgement.student_profile_id == assignment.student_profile_id,
                )
            )
        ).scalar_one_or_none()
        if not attendance or (not outcome and not gap):
            raise ConflictException(
                "Every participant needs attendance and an employer outcome or acknowledged gap"
            )
    item.status = "completed"
    record_audit(db, auth, "session.completed", "recruitment_session", item.id)
    await db.commit()
    return await session_response(db, item)


@router.post("/sessions/{session_id}/cancel", response_model=SessionResponse)
async def cancel_session(
    session_id: uuid.UUID,
    payload: ReasonCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> SessionResponse:
    auth.require_capability("drive:edit")
    item = await db.get(RecruitmentSession, session_id)
    if not item or item.institution_id != auth.institution_id:
        raise NotFoundException("Session not found")
    await load_authorized_drive(db, auth, item.drive_id, for_update=True)
    item.status = "cancelled"
    record_audit(
        db, auth, "session.cancelled", "recruitment_session", item.id, {"reason": payload.reason}
    )
    await db.commit()
    return await session_response(db, item)


@router.get("/student/schedule-results", response_model=list[dict])
async def student_schedule_results(
    db: AsyncSession = Depends(get_db), auth: AuthContext = Depends(get_current_auth)
) -> list[dict]:
    auth.require_role("student")
    profile = await student_profile_for_auth(db, auth)
    assignments = (
        await db.execute(
            select(SessionAssignment, RecruitmentSession, SessionRevision, RecruitmentRound)
            .join(RecruitmentSession, RecruitmentSession.id == SessionAssignment.session_id)
            .join(SessionRevision, SessionRevision.id == RecruitmentSession.published_revision_id)
            .join(RecruitmentRound, RecruitmentRound.id == RecruitmentSession.round_id)
            .where(
                SessionAssignment.student_profile_id == profile.id,
                SessionAssignment.status == "published",
                RecruitmentSession.status.in_(["published", "completed"]),
            )
        )
    ).all()
    result: list[dict] = []
    for _assignment, logical, revision, round_item in assignments:
        outcome = (
            (
                await db.execute(
                    select(OutcomeRevision)
                    .where(
                        OutcomeRevision.round_id == round_item.id,
                        OutcomeRevision.student_profile_id == profile.id,
                        OutcomeRevision.published_at.is_not(None),
                    )
                    .order_by(OutcomeRevision.revision_number.desc())
                )
            )
            .scalars()
            .first()
        )
        result.append(
            {
                "drive_id": str(logical.drive_id),
                "session_id": str(logical.id),
                "round": round_item.name,
                "start_at": revision.start_at.isoformat(),
                "end_at": revision.end_at.isoformat(),
                "timezone": revision.timezone,
                "venue": revision.venue,
                "meeting_url": revision.meeting_url,
                "outcome": outcome_response(outcome).model_dump(mode="json") if outcome else None,
            }
        )
    return result


@router.post("/drives/{drive_id}/registration-close", response_model=dict)
async def close_registration(
    drive_id: uuid.UUID,
    payload: ReasonCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> dict:
    auth.require_capability("drive:edit")
    drive = await load_authorized_drive(db, auth, drive_id, for_update=True)
    drive.registration_closed_at = datetime.now(UTC)
    record_audit(db, auth, "registration.closed", "drive", drive.id, {"reason": payload.reason})
    await db.commit()
    return {
        "drive_id": str(drive.id),
        "registration_closed_at": drive.registration_closed_at.isoformat(),
    }


@router.post("/drives/{drive_id}/reports", response_model=ReportResponse)
async def freeze_report(
    drive_id: uuid.UUID,
    payload: ReportCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ReportResponse:
    auth.require_capability("export:generate")
    drive = await load_authorized_drive(db, auth, drive_id)
    report = await create_report(db, auth, drive, "operational", payload.reason)
    record_audit(
        db,
        auth,
        "report.frozen",
        "drive_report_revision",
        report.id,
        {"hash": report.snapshot_hash},
    )
    await db.commit()
    return report_response(report)


@router.get("/drives/{drive_id}/reports", response_model=list[ReportResponse])
async def list_reports(
    drive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> list[ReportResponse]:
    await load_authorized_drive(db, auth, drive_id)
    rows = (
        (
            await db.execute(
                select(DriveReportRevision)
                .where(DriveReportRevision.drive_id == drive_id)
                .order_by(DriveReportRevision.revision_number.desc())
            )
        )
        .scalars()
        .all()
    )
    return [report_response(x) for x in rows]


@router.post("/reports/{report_id}/export-grants", response_model=ExportGrantResponse)
async def export_grant(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ExportGrantResponse:
    report = await db.get(DriveReportRevision, report_id)
    if not report or report.institution_id != auth.institution_id:
        raise NotFoundException("Report not found")
    await load_authorized_drive(db, auth, report.drive_id)
    grant, token = await create_export_grant(db, auth, report)
    record_audit(
        db,
        auth,
        "report.export_granted",
        "drive_report_revision",
        report.id,
        {"expires_at": grant.expires_at.isoformat()},
    )
    await db.commit()
    return ExportGrantResponse(
        download_url=f"/api/v1/report-exports/{token}.csv", expires_at=grant.expires_at
    )


@router.get("/report-exports/{token}.csv")
async def download_report(
    token: str, db: AsyncSession = Depends(get_db), auth: AuthContext = Depends(get_current_auth)
) -> Response:
    digest = hashlib.sha256(token.encode()).hexdigest()
    grant = (
        await db.execute(
            select(ReportExportGrant).where(
                ReportExportGrant.token_hash == digest,
                ReportExportGrant.institution_id == auth.institution_id,
            )
        )
    ).scalar_one_or_none()
    if not grant or grant.expires_at <= datetime.now(UTC):
        raise NotFoundException("Export grant is invalid or expired")
    await load_authorized_drive(db, auth, grant.drive_id)
    report = await db.get(DriveReportRevision, grant.report_revision_id)
    if not report:
        raise NotFoundException("Report not found")
    grant.downloaded_at = datetime.now(UTC)
    record_audit(db, auth, "report.export_downloaded", "drive_report_revision", report.id)
    await db.commit()
    return Response(
        report_csv(report),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="placementos-report-{report.id}.csv"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/drives/{drive_id}/close", response_model=ReportResponse)
async def close_drive(
    drive_id: uuid.UUID,
    payload: ReasonCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ReportResponse:
    auth.require_capability("drive:close")
    drive = await load_authorized_drive(db, auth, drive_id, for_update=True)
    blockers = await closure_blockers(db, drive)
    if blockers:
        raise ConflictException(
            "Drive closure preconditions are not satisfied", details={"blockers": blockers}
        )
    report = await create_report(db, auth, drive, "closure", payload.reason)
    drive.status = "completed"
    drive.completed_at = datetime.now(UTC)
    drive.closed_by_membership_id = auth.membership_id
    drive.concurrency_revision += 1
    runs = (
        (
            await db.execute(
                select(WorkflowRun).where(
                    WorkflowRun.drive_id == drive.id,
                    WorkflowRun.status.not_in(["completed", "cancelled"]),
                )
            )
        )
        .scalars()
        .all()
    )
    for run in runs:
        run.status = "completed"
        run.current_step = "completed"
    record_audit(
        db,
        auth,
        "drive.closed",
        "drive",
        drive.id,
        {"report_id": str(report.id), "snapshot_hash": report.snapshot_hash},
    )
    await db.commit()
    return report_response(report)


@router.post("/drives/{drive_id}/reopen", response_model=ReportResponse)
async def reopen_drive(
    drive_id: uuid.UUID,
    payload: ReasonCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ReportResponse:
    auth.require_capability("drive:reopen")
    drive = await load_authorized_drive(db, auth, drive_id, for_update=True)
    if drive.status != "completed":
        raise ConflictException("Only a completed drive can be reopened")
    report = await create_report(db, auth, drive, "reopen", payload.reason)
    drive.status = "published"
    drive.completed_at = None
    drive.closed_by_membership_id = None
    drive.concurrency_revision += 1
    record_audit(
        db,
        auth,
        "drive.reopened",
        "drive",
        drive.id,
        {"report_id": str(report.id), "reason": payload.reason},
    )
    await db.commit()
    return report_response(report)


@router.post("/drives/{drive_id}/cancel", response_model=ReportResponse)
async def cancel_drive(
    drive_id: uuid.UUID,
    payload: ReasonCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_auth),
) -> ReportResponse:
    auth.require_capability("drive:cancel")
    drive = await load_authorized_drive(db, auth, drive_id, for_update=True)
    report = await create_report(db, auth, drive, "cancellation", payload.reason)
    drive.status = "cancelled"
    drive.completed_at = datetime.now(UTC)
    drive.closed_by_membership_id = auth.membership_id
    drive.concurrency_revision += 1
    record_audit(
        db,
        auth,
        "drive.cancelled",
        "drive",
        drive.id,
        {"report_id": str(report.id), "reason": payload.reason},
    )
    await db.commit()
    return report_response(report)
