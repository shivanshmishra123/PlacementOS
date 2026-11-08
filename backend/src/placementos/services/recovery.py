"""P12 deterministic impact analysis and controlled recovery execution."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.database import async_session_maker
from placementos.core.errors import BadRequestException, ConflictException, NotFoundException
from placementos.models.academic import AcademicRecordRevision
from placementos.models.communications import (
    AudienceRecipient,
    DispatchBatch,
    DispatchOperation,
    OutboxEvent,
)
from placementos.models.eligibility import EligibilityResult, EvaluationRun
from placementos.models.identity import Institution, Membership, StudentProfile, User
from placementos.models.integrations import ProviderResourceMapping
from placementos.models.intelligence import ActionProposal, ApprovalDecision
from placementos.models.lifecycle import SessionAssignment, SessionRevision
from placementos.models.participation import Registration
from placementos.models.recovery import (
    ExceptionImpactAnalysis,
    RecoveryExecution,
    RecoveryPlan,
    RecoveryPlanStep,
    RecoveryStepAttempt,
)
from placementos.models.recruitment import Drive, DriveRevision
from placementos.models.workflow import ExceptionCase
from placementos.schemas.communications import CommunicationDraftCreate
from placementos.schemas.recovery import (
    AcademicCorrectionImpactCreate,
    CriteriaChangeImpactCreate,
    DeadlineScheduleImpactCreate,
    ExceptionImpactCreate,
    NotificationFailureImpactCreate,
    RecoveryPlanCreate,
    RecoveryStepCreate,
)
from placementos.services.audit import record_audit
from placementos.services.authorization import load_authorized_drive
from placementos.services.communications import DEFAULT_TEMPLATES, create_frozen_draft
from placementos.services.eligibility_engine import canonical_hash
from placementos.services.session import AuthContext

MAX_PLAN_STEPS = 10
NOTIFIED_DISPATCH_STATUSES = {"provider_accepted", "delivered", "unknown"}
ALLOWLISTED_OPERATIONS = {
    "place_drive_hold",
    "stale_pending_proposals",
    "prepare_correction_draft",
    "mark_external_reconciliation",
    "record_manual_followup",
}


@dataclass
class ImpactDraft:
    drive_id: uuid.UUID
    input_references: dict[str, Any]
    dependency_snapshot: dict[str, Any]
    impact_summary: dict[str, Any]
    affected_students: list[dict[str, Any]]
    affected_resources: list[dict[str, Any]]
    manual_fallback: str


async def load_scoped_case(
    session: AsyncSession, auth: AuthContext, case_id: uuid.UUID, *, for_update: bool = False
) -> ExceptionCase:
    statement = select(ExceptionCase).where(
        ExceptionCase.id == case_id,
        ExceptionCase.institution_id == auth.institution_id,
    )
    if for_update:
        statement = statement.with_for_update()
    item = (await session.execute(statement)).scalar_one_or_none()
    if not item:
        raise NotFoundException("Exception case not found")
    await load_authorized_drive(session, auth, item.drive_id)
    return item


async def _load_evaluation(
    session: AsyncSession, institution_id: uuid.UUID, drive_id: uuid.UUID, run_id: uuid.UUID
) -> EvaluationRun:
    run = (
        await session.execute(
            select(EvaluationRun).where(
                EvaluationRun.id == run_id,
                EvaluationRun.institution_id == institution_id,
                EvaluationRun.drive_id == drive_id,
            )
        )
    ).scalar_one_or_none()
    if not run:
        raise NotFoundException("Evaluation run not found for this drive")
    if run.status != "completed":
        raise ConflictException("Impact analysis requires completed evaluation runs")
    return run


def _drive_dependency(drive: Drive) -> dict[str, Any]:
    return {
        "drive_id": str(drive.id),
        "status": drive.status,
        "current_drive_revision_id": str(drive.current_drive_revision_id)
        if drive.current_drive_revision_id
        else None,
        "published_drive_revision_id": str(drive.published_drive_revision_id)
        if drive.published_drive_revision_id
        else None,
        "published_evaluation_run_id": str(drive.published_evaluation_run_id)
        if drive.published_evaluation_run_id
        else None,
    }


def _evaluation_dependency(run: EvaluationRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "policy_id": str(run.policy_id),
        "policy_hash": run.policy_hash,
        "cohort_fingerprint": run.cohort_fingerprint,
        "run_fingerprint": run.run_fingerprint,
        "status": run.status,
        "is_stale": run.is_stale,
    }


async def _affected_student_context(
    session: AsyncSession,
    *,
    institution_id: uuid.UUID,
    drive_id: uuid.UUID,
    outcomes: Mapping[uuid.UUID, tuple[str | None, str | None]],
) -> list[dict[str, Any]]:
    student_ids = sorted(outcomes, key=str)
    if not student_ids:
        return []
    registrations = {
        row.student_profile_id: row
        for row in (
            await session.execute(
                select(Registration).where(
                    Registration.institution_id == institution_id,
                    Registration.drive_id == drive_id,
                    Registration.student_profile_id.in_(student_ids),
                )
            )
        )
        .scalars()
        .all()
    }
    assignment_rows = (
        await session.execute(
            select(SessionAssignment.student_profile_id, func.count(SessionAssignment.id))
            .where(
                SessionAssignment.institution_id == institution_id,
                SessionAssignment.drive_id == drive_id,
                SessionAssignment.student_profile_id.in_(student_ids),
                SessionAssignment.status == "published",
            )
            .group_by(SessionAssignment.student_profile_id)
        )
    ).all()
    assignment_counts = {student_id: int(count) for student_id, count in assignment_rows}
    dispatch_rows = (
        await session.execute(
            select(AudienceRecipient.student_profile_id, DispatchOperation.status)
            .join(
                DispatchOperation,
                DispatchOperation.audience_recipient_id == AudienceRecipient.id,
            )
            .where(
                DispatchOperation.institution_id == institution_id,
                DispatchOperation.drive_id == drive_id,
                AudienceRecipient.student_profile_id.in_(student_ids),
            )
        )
    ).all()
    dispatch: dict[uuid.UUID, set[str]] = {}
    for student_id, status in dispatch_rows:
        dispatch.setdefault(student_id, set()).add(status)
    return [
        {
            "student_profile_id": str(student_id),
            "old_outcome": outcomes[student_id][0],
            "new_outcome": outcomes[student_id][1],
            "registration_state": registrations[student_id].state
            if student_id in registrations
            else None,
            "registration_id": str(registrations[student_id].id)
            if student_id in registrations
            else None,
            "published_assignment_count": assignment_counts.get(student_id, 0),
            "notification_statuses": sorted(dispatch.get(student_id, set())),
            "was_notified": bool(dispatch.get(student_id, set()) & NOTIFIED_DISPATCH_STATUSES),
        }
        for student_id in student_ids
    ]


async def _drive_resources(
    session: AsyncSession,
    institution_id: uuid.UUID,
    drive_id: uuid.UUID,
    student_ids: Sequence[uuid.UUID],
) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    proposals = (
        await session.execute(
            select(ActionProposal).where(
                ActionProposal.institution_id == institution_id,
                ActionProposal.drive_id == drive_id,
                ActionProposal.state == "pending_approval",
            )
        )
    ).scalars()
    resources.extend(
        {"type": "action_proposal", "id": str(item.id), "state": item.state} for item in proposals
    )
    if student_ids:
        registrations = (
            await session.execute(
                select(Registration).where(
                    Registration.institution_id == institution_id,
                    Registration.drive_id == drive_id,
                    Registration.student_profile_id.in_(student_ids),
                )
            )
        ).scalars()
        resources.extend(
            {
                "type": "registration",
                "id": str(item.id),
                "student_profile_id": str(item.student_profile_id),
                "state": item.state,
                "revision": item.concurrency_revision,
            }
            for item in registrations
        )
        assignments = (
            await session.execute(
                select(SessionAssignment).where(
                    SessionAssignment.institution_id == institution_id,
                    SessionAssignment.drive_id == drive_id,
                    SessionAssignment.student_profile_id.in_(student_ids),
                    SessionAssignment.status == "published",
                )
            )
        ).scalars()
        resources.extend(
            {
                "type": "session_assignment",
                "id": str(item.id),
                "student_profile_id": str(item.student_profile_id),
                "session_revision_id": str(item.session_revision_id),
                "state": item.status,
            }
            for item in assignments
        )
    return resources


async def _criteria_impact(
    session: AsyncSession,
    institution_id: uuid.UUID,
    drive: Drive,
    payload: CriteriaChangeImpactCreate,
) -> ImpactDraft:
    old_run = await _load_evaluation(
        session, institution_id, drive.id, payload.old_evaluation_run_id
    )
    new_run = await _load_evaluation(
        session, institution_id, drive.id, payload.new_evaluation_run_id
    )
    if old_run.id == new_run.id or old_run.policy_hash == new_run.policy_hash:
        raise BadRequestException("Criteria impact requires distinct policy evaluations")
    old_results = {
        row.student_profile_id: row.outcome
        for row in (
            await session.execute(
                select(EligibilityResult).where(EligibilityResult.evaluation_run_id == old_run.id)
            )
        )
        .scalars()
        .all()
    }
    new_results = {
        row.student_profile_id: row.outcome
        for row in (
            await session.execute(
                select(EligibilityResult).where(EligibilityResult.evaluation_run_id == new_run.id)
            )
        )
        .scalars()
        .all()
    }
    student_ids = sorted(set(old_results) | set(new_results), key=str)
    changed = {
        student_id: (old_results.get(student_id), new_results.get(student_id))
        for student_id in student_ids
        if old_results.get(student_id) != new_results.get(student_id)
    }
    affected_students = await _affected_student_context(
        session,
        institution_id=institution_id,
        drive_id=drive.id,
        outcomes=changed,
    )
    resources = await _drive_resources(session, institution_id, drive.id, list(changed))
    transitions: dict[str, int] = {}
    for old_outcome, new_outcome in changed.values():
        key = f"{old_outcome or 'absent'}_to_{new_outcome or 'absent'}"
        transitions[key] = transitions.get(key, 0) + 1
    dependency = {
        "drive": _drive_dependency(drive),
        "old_evaluation": _evaluation_dependency(old_run),
        "new_evaluation": _evaluation_dependency(new_run),
    }
    return ImpactDraft(
        drive_id=drive.id,
        input_references={
            "old_evaluation_run_id": str(old_run.id),
            "new_evaluation_run_id": str(new_run.id),
        },
        dependency_snapshot=dependency,
        impact_summary={
            "changed_student_count": len(changed),
            "transition_counts": transitions,
            "submitted_registration_count": sum(
                item["registration_state"] == "submitted" for item in affected_students
            ),
            "notified_student_count": sum(item["was_notified"] for item in affected_students),
            "scheduled_student_count": sum(
                item["published_assignment_count"] > 0 for item in affected_students
            ),
        },
        affected_students=affected_students,
        affected_resources=resources,
        manual_fallback=(
            "Review each changed deterministic outcome, preserve registrations, place holds where "
            "needed, and create separately approved correction communications."
        ),
    )


async def _academic_impact(
    session: AsyncSession,
    institution_id: uuid.UUID,
    drive: Drive,
    payload: AcademicCorrectionImpactCreate,
) -> ImpactDraft:
    profile = await session.get(StudentProfile, payload.student_profile_id)
    old_revision = await session.get(AcademicRecordRevision, payload.old_academic_revision_id)
    new_revision = await session.get(AcademicRecordRevision, payload.new_academic_revision_id)
    if (
        not profile
        or profile.institution_id != institution_id
        or not old_revision
        or not new_revision
        or old_revision.student_profile_id != profile.id
        or new_revision.student_profile_id != profile.id
        or old_revision.institution_id != institution_id
        or new_revision.institution_id != institution_id
    ):
        raise NotFoundException("Academic correction references were not found in this institution")
    if profile.current_academic_revision_id != new_revision.id or not new_revision.is_verified:
        raise ConflictException("The new academic revision must be the current verified revision")
    old_run = await _load_evaluation(
        session, institution_id, drive.id, payload.old_evaluation_run_id
    )
    new_run = await _load_evaluation(
        session, institution_id, drive.id, payload.new_evaluation_run_id
    )
    old_result = (
        await session.execute(
            select(EligibilityResult).where(
                EligibilityResult.evaluation_run_id == old_run.id,
                EligibilityResult.student_profile_id == profile.id,
            )
        )
    ).scalar_one_or_none()
    new_result = (
        await session.execute(
            select(EligibilityResult).where(
                EligibilityResult.evaluation_run_id == new_run.id,
                EligibilityResult.student_profile_id == profile.id,
            )
        )
    ).scalar_one_or_none()
    if not old_result or not new_result:
        raise ConflictException("Both evaluations must contain the corrected student")
    outcomes: dict[uuid.UUID, tuple[str | None, str | None]] = {
        profile.id: (old_result.outcome, new_result.outcome)
    }
    affected_students = await _affected_student_context(
        session,
        institution_id=institution_id,
        drive_id=drive.id,
        outcomes=outcomes,
    )
    resources = await _drive_resources(session, institution_id, drive.id, [profile.id])
    dependency = {
        "drive": _drive_dependency(drive),
        "student_profile_id": str(profile.id),
        "current_academic_revision_id": str(profile.current_academic_revision_id),
        "old_academic_revision_id": str(old_revision.id),
        "new_academic_revision_id": str(new_revision.id),
        "old_evaluation": _evaluation_dependency(old_run),
        "new_evaluation": _evaluation_dependency(new_run),
    }
    return ImpactDraft(
        drive_id=drive.id,
        input_references={
            "student_profile_id": str(profile.id),
            "old_academic_revision_id": str(old_revision.id),
            "new_academic_revision_id": str(new_revision.id),
            "old_evaluation_run_id": str(old_run.id),
            "new_evaluation_run_id": str(new_run.id),
        },
        dependency_snapshot=dependency,
        impact_summary={
            "changed_student_count": int(old_result.outcome != new_result.outcome),
            "old_outcome": old_result.outcome,
            "new_outcome": new_result.outcome,
            "registration_preserved": True,
            "was_notified": affected_students[0]["was_notified"],
        },
        affected_students=affected_students,
        affected_resources=resources,
        manual_fallback=(
            "Review the verified academic revision and deterministic result. Preserve the existing "
            "registration and use a hold or new approved communication instead of an override."
        ),
    )


async def _deadline_schedule_impact(
    session: AsyncSession,
    institution_id: uuid.UUID,
    drive: Drive,
    payload: DeadlineScheduleImpactCreate,
) -> ImpactDraft:
    affected_ids: set[uuid.UUID] = set()
    resources: list[dict[str, Any]] = []
    if payload.change_kind == "deadline":
        drive_old_revision = await session.get(DriveRevision, payload.old_revision_id)
        drive_new_revision = await session.get(DriveRevision, payload.new_revision_id)
        if (
            not drive_old_revision
            or not drive_new_revision
            or drive_old_revision.institution_id != institution_id
            or drive_new_revision.institution_id != institution_id
            or drive_old_revision.drive_id != drive.id
            or drive_new_revision.drive_id != drive.id
            or drive_old_revision.registration_end_at == drive_new_revision.registration_end_at
        ):
            raise BadRequestException("Distinct deadline revisions for this drive are required")
        registration_rows = (
            await session.execute(
                select(Registration).where(
                    Registration.institution_id == institution_id,
                    Registration.drive_id == drive.id,
                    Registration.state.in_(["draft", "submitted", "eligibility_hold"]),
                )
            )
        ).scalars()
        affected_ids.update(row.student_profile_id for row in registration_rows)
        notified_ids = (
            await session.execute(
                select(AudienceRecipient.student_profile_id)
                .join(
                    DispatchOperation,
                    DispatchOperation.audience_recipient_id == AudienceRecipient.id,
                )
                .where(
                    DispatchOperation.institution_id == institution_id,
                    DispatchOperation.drive_id == drive.id,
                    DispatchOperation.status.in_(NOTIFIED_DISPATCH_STATUSES),
                )
            )
        ).scalars()
        affected_ids.update(notified_ids)
        dependency = {
            "drive": _drive_dependency(drive),
            "change_kind": "deadline",
            "old_revision": {
                "id": str(drive_old_revision.id),
                "revision": drive_old_revision.revision_number,
                "registration_end_at": drive_old_revision.registration_end_at.isoformat()
                if drive_old_revision.registration_end_at
                else None,
            },
            "new_revision": {
                "id": str(drive_new_revision.id),
                "revision": drive_new_revision.revision_number,
                "registration_end_at": drive_new_revision.registration_end_at.isoformat()
                if drive_new_revision.registration_end_at
                else None,
            },
        }
        summary_extra = {
            "old_deadline": drive_old_revision.registration_end_at.isoformat()
            if drive_old_revision.registration_end_at
            else None,
            "new_deadline": drive_new_revision.registration_end_at.isoformat()
            if drive_new_revision.registration_end_at
            else None,
        }
    else:
        session_old_revision = await session.get(SessionRevision, payload.old_revision_id)
        session_new_revision = await session.get(SessionRevision, payload.new_revision_id)
        if (
            not session_old_revision
            or not session_new_revision
            or session_old_revision.institution_id != institution_id
            or session_new_revision.institution_id != institution_id
            or session_old_revision.drive_id != drive.id
            or session_new_revision.drive_id != drive.id
            or session_old_revision.session_id != session_new_revision.session_id
            or (session_old_revision.start_at, session_old_revision.end_at)
            == (session_new_revision.start_at, session_new_revision.end_at)
        ):
            raise BadRequestException(
                "Distinct schedule revisions for one drive session are required"
            )
        assignment_rows = (
            await session.execute(
                select(SessionAssignment).where(
                    SessionAssignment.institution_id == institution_id,
                    SessionAssignment.session_revision_id.in_(
                        [session_old_revision.id, session_new_revision.id]
                    ),
                )
            )
        ).scalars()
        affected_ids.update(row.student_profile_id for row in assignment_rows)
        mappings = (
            await session.execute(
                select(ProviderResourceMapping).where(
                    ProviderResourceMapping.institution_id == institution_id,
                    ProviderResourceMapping.local_resource_type == "session_revision",
                    ProviderResourceMapping.local_resource_id.in_(
                        [session_old_revision.id, session_new_revision.id]
                    ),
                )
            )
        ).scalars()
        resources.extend(
            {"type": "provider_mapping", "id": str(item.id), "state": item.status}
            for item in mappings
        )
        dependency = {
            "drive": _drive_dependency(drive),
            "change_kind": "schedule",
            "old_revision": {
                "id": str(session_old_revision.id),
                "revision": session_old_revision.revision_number,
                "start_at": session_old_revision.start_at.isoformat(),
                "end_at": session_old_revision.end_at.isoformat(),
            },
            "new_revision": {
                "id": str(session_new_revision.id),
                "revision": session_new_revision.revision_number,
                "start_at": session_new_revision.start_at.isoformat(),
                "end_at": session_new_revision.end_at.isoformat(),
            },
        }
        summary_extra = {
            "old_start_at": session_old_revision.start_at.isoformat(),
            "new_start_at": session_new_revision.start_at.isoformat(),
        }
    outcomes: dict[uuid.UUID, tuple[str | None, str | None]] = dict.fromkeys(
        affected_ids, (None, None)
    )
    affected_students = await _affected_student_context(
        session,
        institution_id=institution_id,
        drive_id=drive.id,
        outcomes=outcomes,
    )
    resources.extend(await _drive_resources(session, institution_id, drive.id, list(affected_ids)))
    return ImpactDraft(
        drive_id=drive.id,
        input_references={
            "change_kind": payload.change_kind,
            "old_revision_id": str(payload.old_revision_id),
            "new_revision_id": str(payload.new_revision_id),
        },
        dependency_snapshot=dependency,
        impact_summary={
            "affected_student_count": len(affected_ids),
            "notified_student_count": sum(item["was_notified"] for item in affected_students),
            "registration_preserved": True,
            **summary_extra,
        },
        affected_students=affected_students,
        affected_resources=resources,
        manual_fallback=(
            "Review affected registrations or assignments, preserve prior published history, and "
            "prepare a new separately approved correction notice and external update if needed."
        ),
    )


async def _notification_impact(
    session: AsyncSession,
    institution_id: uuid.UUID,
    drive: Drive,
    payload: NotificationFailureImpactCreate,
) -> ImpactDraft:
    operation = await session.get(DispatchOperation, payload.dispatch_operation_id)
    if (
        not operation
        or operation.institution_id != institution_id
        or operation.drive_id != drive.id
    ):
        raise NotFoundException("Dispatch operation not found for this drive")
    if operation.status not in {"failed", "unknown"}:
        raise ConflictException("Notification recovery requires a failed or unknown operation")
    recipient = await session.get(AudienceRecipient, operation.audience_recipient_id)
    batch = await session.get(DispatchBatch, operation.dispatch_batch_id)
    if not recipient or not batch:
        raise ConflictException("Notification operation dependencies are incomplete")
    affected_students = await _affected_student_context(
        session,
        institution_id=institution_id,
        drive_id=drive.id,
        outcomes={recipient.student_profile_id: (None, None)},
    )
    dependency = {
        "drive": _drive_dependency(drive),
        "dispatch_operation": {
            "id": str(operation.id),
            "status": operation.status,
            "attempt_count": operation.attempt_count,
            "provider_message_id": operation.provider_message_id,
            "last_error_code": operation.last_error_code,
        },
        "dispatch_batch_id": str(batch.id),
    }
    return ImpactDraft(
        drive_id=drive.id,
        input_references={"dispatch_operation_id": str(operation.id)},
        dependency_snapshot=dependency,
        impact_summary={
            "affected_student_count": 1,
            "operation_status": operation.status,
            "blind_retry_allowed": False,
            "manual_reconciliation_required": operation.status == "unknown",
        },
        affected_students=affected_students,
        affected_resources=[
            {
                "type": "dispatch_operation",
                "id": str(operation.id),
                "state": operation.status,
                "irreversible_if_accepted": True,
            },
            {"type": "dispatch_batch", "id": str(batch.id), "state": batch.status},
        ],
        manual_fallback=(
            "Reconcile the provider outcome with evidence. Do not retry an unknown send until it is "
            "confirmed not accepted; any correction message requires a new exact approval."
        ),
    )


async def create_impact_analysis(
    session: AsyncSession,
    auth: AuthContext,
    case: ExceptionCase,
    payload: ExceptionImpactCreate,
) -> ExceptionImpactAnalysis:
    if case.status not in {"open", "acknowledged"}:
        raise ConflictException("Only open or acknowledged cases can be analyzed")
    drive = await load_authorized_drive(session, auth, case.drive_id)
    if isinstance(payload, CriteriaChangeImpactCreate):
        draft = await _criteria_impact(session, auth.institution_id, drive, payload)
    elif isinstance(payload, AcademicCorrectionImpactCreate):
        draft = await _academic_impact(session, auth.institution_id, drive, payload)
    elif isinstance(payload, DeadlineScheduleImpactCreate):
        draft = await _deadline_schedule_impact(session, auth.institution_id, drive, payload)
    elif isinstance(payload, NotificationFailureImpactCreate):
        draft = await _notification_impact(session, auth.institution_id, drive, payload)
    else:  # pragma: no cover - discriminated schema prevents this
        raise BadRequestException("Unsupported exception impact category")
    previous = (
        await session.execute(
            select(ExceptionImpactAnalysis).where(
                ExceptionImpactAnalysis.case_id == case.id,
                ExceptionImpactAnalysis.status == "current",
            )
        )
    ).scalars()
    for item in previous:
        item.status = "superseded"
        pending_plans = (
            await session.execute(
                select(RecoveryPlan).where(
                    RecoveryPlan.analysis_id == item.id,
                    RecoveryPlan.status.in_(["draft", "pending_approval"]),
                )
            )
        ).scalars()
        for old_plan in pending_plans:
            old_plan.status = "stale"
            if old_plan.proposal_id:
                old_proposal = await session.get(ActionProposal, old_plan.proposal_id)
                if old_proposal and old_proposal.state == "pending_approval":
                    old_proposal.state = "stale"
            old_steps = (
                await session.execute(
                    select(RecoveryPlanStep).where(
                        RecoveryPlanStep.plan_id == old_plan.id,
                        RecoveryPlanStep.status.in_(["pending", "running"]),
                    )
                )
            ).scalars()
            for old_step in old_steps:
                old_step.status = "stale"
                old_step.error_code = "IMPACT_ANALYSIS_SUPERSEDED"
    next_revision = (
        int(
            await session.scalar(
                select(func.coalesce(func.max(ExceptionImpactAnalysis.revision_number), 0)).where(
                    ExceptionImpactAnalysis.case_id == case.id
                )
            )
            or 0
        )
        + 1
    )
    item = ExceptionImpactAnalysis(
        institution_id=auth.institution_id,
        drive_id=draft.drive_id,
        case_id=case.id,
        revision_number=next_revision,
        category=payload.category,
        input_references=draft.input_references,
        dependency_snapshot=draft.dependency_snapshot,
        dependency_fingerprint=canonical_hash(draft.dependency_snapshot),
        impact_summary=draft.impact_summary,
        affected_students=draft.affected_students,
        affected_resources=draft.affected_resources,
        manual_fallback=draft.manual_fallback,
        created_by_membership_id=auth.membership_id,
    )
    session.add(item)
    case.owner_membership_id = auth.membership_id
    if case.status == "open":
        case.status = "acknowledged"
    await session.flush()
    record_audit(
        session,
        auth,
        "exception:impact_analyzed",
        "exception_impact_analysis",
        item.id,
        {
            "case_id": str(case.id),
            "category": item.category,
            "revision": item.revision_number,
            "affected_student_count": len(item.affected_students),
        },
    )
    await session.commit()
    return item


async def _current_dependency_snapshot(
    session: AsyncSession, analysis: ExceptionImpactAnalysis
) -> dict[str, Any]:
    drive = await session.get(Drive, analysis.drive_id)
    if not drive:
        raise ConflictException("Recovery drive no longer exists")
    refs = analysis.input_references
    if analysis.category == "criteria_change":
        old_run = await session.get(EvaluationRun, uuid.UUID(refs["old_evaluation_run_id"]))
        new_run = await session.get(EvaluationRun, uuid.UUID(refs["new_evaluation_run_id"]))
        if not old_run or not new_run:
            raise ConflictException("Evaluation dependency no longer exists")
        return {
            "drive": _drive_dependency(drive),
            "old_evaluation": _evaluation_dependency(old_run),
            "new_evaluation": _evaluation_dependency(new_run),
        }
    if analysis.category == "academic_correction":
        profile = await session.get(StudentProfile, uuid.UUID(refs["student_profile_id"]))
        old_run = await session.get(EvaluationRun, uuid.UUID(refs["old_evaluation_run_id"]))
        new_run = await session.get(EvaluationRun, uuid.UUID(refs["new_evaluation_run_id"]))
        if not profile or not old_run or not new_run:
            raise ConflictException("Academic correction dependency no longer exists")
        return {
            "drive": _drive_dependency(drive),
            "student_profile_id": str(profile.id),
            "current_academic_revision_id": str(profile.current_academic_revision_id)
            if profile.current_academic_revision_id
            else None,
            "old_academic_revision_id": refs["old_academic_revision_id"],
            "new_academic_revision_id": refs["new_academic_revision_id"],
            "old_evaluation": _evaluation_dependency(old_run),
            "new_evaluation": _evaluation_dependency(new_run),
        }
    if analysis.category == "deadline_schedule_change":
        if refs["change_kind"] == "deadline":
            current_drive_old = await session.get(DriveRevision, uuid.UUID(refs["old_revision_id"]))
            current_drive_new = await session.get(DriveRevision, uuid.UUID(refs["new_revision_id"]))
            if not current_drive_old or not current_drive_new:
                raise ConflictException("Deadline dependency no longer exists")
            return {
                "drive": _drive_dependency(drive),
                "change_kind": "deadline",
                "old_revision": {
                    "id": str(current_drive_old.id),
                    "revision": current_drive_old.revision_number,
                    "registration_end_at": current_drive_old.registration_end_at.isoformat()
                    if current_drive_old.registration_end_at
                    else None,
                },
                "new_revision": {
                    "id": str(current_drive_new.id),
                    "revision": current_drive_new.revision_number,
                    "registration_end_at": current_drive_new.registration_end_at.isoformat()
                    if current_drive_new.registration_end_at
                    else None,
                },
            }
        current_session_old = await session.get(SessionRevision, uuid.UUID(refs["old_revision_id"]))
        current_session_new = await session.get(SessionRevision, uuid.UUID(refs["new_revision_id"]))
        if not current_session_old or not current_session_new:
            raise ConflictException("Schedule dependency no longer exists")
        return {
            "drive": _drive_dependency(drive),
            "change_kind": "schedule",
            "old_revision": {
                "id": str(current_session_old.id),
                "revision": current_session_old.revision_number,
                "start_at": current_session_old.start_at.isoformat(),
                "end_at": current_session_old.end_at.isoformat(),
            },
            "new_revision": {
                "id": str(current_session_new.id),
                "revision": current_session_new.revision_number,
                "start_at": current_session_new.start_at.isoformat(),
                "end_at": current_session_new.end_at.isoformat(),
            },
        }
    operation = await session.get(DispatchOperation, uuid.UUID(refs["dispatch_operation_id"]))
    if not operation:
        raise ConflictException("Notification dependency no longer exists")
    return {
        "drive": _drive_dependency(drive),
        "dispatch_operation": {
            "id": str(operation.id),
            "status": operation.status,
            "attempt_count": operation.attempt_count,
            "provider_message_id": operation.provider_message_id,
            "last_error_code": operation.last_error_code,
        },
        "dispatch_batch_id": str(operation.dispatch_batch_id),
    }


async def analysis_is_fresh(session: AsyncSession, analysis: ExceptionImpactAnalysis) -> bool:
    current = await _current_dependency_snapshot(session, analysis)
    return canonical_hash(current) == analysis.dependency_fingerprint


def _proposal_ids(analysis: ExceptionImpactAnalysis) -> list[str]:
    return sorted(
        item["id"]
        for item in analysis.affected_resources
        if item.get("type") == "action_proposal" and item.get("state") == "pending_approval"
    )


def _mapping_ids(analysis: ExceptionImpactAnalysis) -> list[str]:
    return sorted(
        item["id"] for item in analysis.affected_resources if item.get("type") == "provider_mapping"
    )


def _notified_student_ids(analysis: ExceptionImpactAnalysis) -> list[str]:
    return sorted(
        item["student_profile_id"]
        for item in analysis.affected_students
        if item.get("was_notified")
    )


class DeterministicExceptionPlanner:
    """Visible development fixture: proposes typed steps and has no execution tools."""

    planner_id = "exception-planner-fixture"
    version = "recovery-plan-v1"

    def propose(self, analysis: ExceptionImpactAnalysis) -> list[RecoveryStepCreate]:
        proposals = _proposal_ids(analysis)
        mappings = _mapping_ids(analysis)
        notified = _notified_student_ids(analysis)
        steps: list[RecoveryStepCreate] = []
        if analysis.category == "criteria_change" and analysis.impact_summary.get(
            "submitted_registration_count", 0
        ):
            steps.append(
                RecoveryStepCreate(
                    operation_type="place_drive_hold",
                    exact_payload={
                        "reason": "Approved recovery plan: eligibility criteria changed after publication"
                    },
                    expected_effects=[
                        "Pause new consequential drive work without deleting registrations"
                    ],
                    approval_type="recovery_plan",
                    irreversible_effects=[],
                )
            )
        if proposals:
            steps.append(
                RecoveryStepCreate(
                    operation_type="stale_pending_proposals",
                    exact_payload={"proposal_ids": proposals},
                    dependencies=list(range(1, len(steps) + 1)),
                    expected_effects=["Invalidate only listed pending proposals"],
                    approval_type="recovery_plan",
                    irreversible_effects=[],
                )
            )
        if mappings:
            steps.append(
                RecoveryStepCreate(
                    operation_type="mark_external_reconciliation",
                    exact_payload={"mapping_ids": mappings},
                    dependencies=list(range(1, len(steps) + 1)),
                    expected_effects=[
                        "Flag listed external mappings for a separately approved update"
                    ],
                    approval_type="recovery_plan",
                    irreversible_effects=[],
                )
            )
        if notified:
            subject, body = DEFAULT_TEMPLATES["clarification"]
            steps.append(
                RecoveryStepCreate(
                    operation_type="prepare_correction_draft",
                    exact_payload={
                        "student_profile_ids": notified,
                        "communication_kind": "clarification",
                        "subject_template": subject,
                        "body_template": body,
                        "sender_email": settings.SMTP_SENDER,
                        "reply_to": settings.SMTP_SENDER,
                    },
                    dependencies=list(range(1, len(steps) + 1)),
                    expected_effects=[
                        "Create an exact correction draft; sending still requires separate approval"
                    ],
                    approval_type="separate_action_approval",
                    irreversible_effects=["A later approved send cannot be recalled"],
                )
            )
        steps.append(
            RecoveryStepCreate(
                operation_type="record_manual_followup",
                exact_payload={"note": analysis.manual_fallback},
                dependencies=list(range(1, len(steps) + 1)),
                expected_effects=["Record the remaining coordinator review requirement"],
                approval_type="manual_evidence",
                irreversible_effects=[],
            )
        )
        return steps[:MAX_PLAN_STEPS]


def _validated_step(step: RecoveryStepCreate, step_number: int) -> dict[str, Any]:
    if step.operation_type not in ALLOWLISTED_OPERATIONS:
        raise BadRequestException("Unsupported recovery operation")
    if any(dep < 1 or dep >= step_number for dep in step.dependencies):
        raise BadRequestException("Recovery step dependencies must reference earlier steps")
    payload = step.exact_payload
    if step.operation_type == "place_drive_hold":
        if not isinstance(payload.get("reason"), str) or len(payload["reason"].strip()) < 3:
            raise BadRequestException("Drive hold step requires a reason")
        if step.approval_type != "recovery_plan":
            raise BadRequestException("Drive holds must be bound to recovery-plan approval")
    elif step.operation_type == "stale_pending_proposals":
        ids = payload.get("proposal_ids")
        if not isinstance(ids, list) or not ids or len(ids) > 100:
            raise BadRequestException("Proposal invalidation requires bounded proposal IDs")
        try:
            [uuid.UUID(str(item)) for item in ids]
        except ValueError as exc:
            raise BadRequestException("Proposal invalidation contains an invalid ID") from exc
    elif step.operation_type == "prepare_correction_draft":
        ids = payload.get("student_profile_ids")
        if not isinstance(ids, list) or not ids or len(ids) > 500:
            raise BadRequestException("Correction draft requires explicit student profile IDs")
        try:
            [uuid.UUID(str(item)) for item in ids]
        except ValueError as exc:
            raise BadRequestException("Correction draft contains an invalid student ID") from exc
        required = {"subject_template", "body_template", "reply_to", "sender_email"}
        if not required.issubset(payload) or step.approval_type != "separate_action_approval":
            raise BadRequestException(
                "Correction draft must freeze content and require separate action approval"
            )
    elif step.operation_type == "mark_external_reconciliation":
        ids = payload.get("mapping_ids")
        if not isinstance(ids, list) or not ids or len(ids) > 100:
            raise BadRequestException("External reconciliation requires bounded mapping IDs")
    elif step.operation_type == "record_manual_followup":
        if not isinstance(payload.get("note"), str) or len(payload["note"].strip()) < 3:
            raise BadRequestException("Manual follow-up requires a note")
        if step.approval_type != "manual_evidence":
            raise BadRequestException("Manual follow-up must remain a manual evidence step")
    return step.model_dump(mode="json")


async def create_recovery_plan(
    session: AsyncSession,
    auth: AuthContext,
    analysis: ExceptionImpactAnalysis,
    payload: RecoveryPlanCreate,
) -> RecoveryPlan:
    if analysis.status != "current" or not await analysis_is_fresh(session, analysis):
        analysis.status = "stale"
        await session.commit()
        raise ConflictException("Impact analysis is stale; run it again before planning")
    rationale = payload.rationale
    if payload.planner_mode == "fixture":
        if settings.ENVIRONMENT == "production" or settings.EXCEPTION_PLANNER_MODE != "fixture":
            raise ConflictException("Fixture exception planner is unavailable; use manual planning")
        planner = DeterministicExceptionPlanner()
        raw_steps = planner.propose(analysis)
        planner_id = planner.planner_id
        planner_version = planner.version
        usage = {"provider": "deterministic_fixture", "calls": 1, "repair_attempts": 0}
    elif payload.planner_mode == "model":
        if settings.EXCEPTION_PLANNER_MODE == "disabled":
            raise ConflictException("AI recovery planning is disabled; use manual planning")
        from placementos.services.models.recovery_adapter import get_recovery_planner

        ai_planner = get_recovery_planner("model")
        raw_steps, ai_rationale, planner_id, planner_version, usage = ai_planner.propose(analysis)
        if ai_rationale and (not rationale or rationale == "Propose recovery plan"):
            rationale = ai_rationale
    elif payload.planner_mode == "cached":
        from placementos.services.models.recovery_adapter import CachedRecoveryPlanner

        cached_planner = CachedRecoveryPlanner()
        raw_steps, cached_rationale, planner_id, planner_version, usage = cached_planner.propose(analysis)
        if cached_rationale and (not rationale or rationale == "Propose recovery plan"):
            rationale = cached_rationale
    else:
        raw_steps = payload.manual_steps
        planner_id = "manual-coordinator"
        planner_version = "recovery-plan-v1"
        usage = {"provider": "manual", "calls": 0, "repair_attempts": 0}
    if not raw_steps or len(raw_steps) > MAX_PLAN_STEPS:
        raise BadRequestException("Recovery plans require between one and ten steps")
    step_specs = [_validated_step(step, index) for index, step in enumerate(raw_steps, 1)]
    previous = (
        await session.execute(
            select(RecoveryPlan).where(
                RecoveryPlan.analysis_id == analysis.id,
                RecoveryPlan.status.in_(["draft", "pending_approval"]),
            )
        )
    ).scalars()
    for item in previous:
        item.status = "stale"
        if item.proposal_id:
            proposal = await session.get(ActionProposal, item.proposal_id)
            if proposal and proposal.state == "pending_approval":
                proposal.state = "stale"
        old_steps = (
            await session.execute(
                select(RecoveryPlanStep).where(
                    RecoveryPlanStep.plan_id == item.id,
                    RecoveryPlanStep.status.in_(["pending", "running"]),
                )
            )
        ).scalars()
        for old_step in old_steps:
            old_step.status = "stale"
            old_step.error_code = "RECOVERY_PLAN_SUPERSEDED"
    revision_number = (
        int(
            await session.scalar(
                select(func.coalesce(func.max(RecoveryPlan.revision_number), 0)).where(
                    RecoveryPlan.analysis_id == analysis.id
                )
            )
            or 0
        )
        + 1
    )
    plan_hash = canonical_hash(
        {
            "analysis_id": str(analysis.id),
            "analysis_fingerprint": analysis.dependency_fingerprint,
            "revision_number": revision_number,
            "rationale": rationale,
            "steps": step_specs,
        }
    )
    plan = RecoveryPlan(
        institution_id=auth.institution_id,
        drive_id=analysis.drive_id,
        case_id=analysis.case_id,
        analysis_id=analysis.id,
        revision_number=revision_number,
        planner_mode=payload.planner_mode,
        planner_id=planner_id,
        planner_version=planner_version,
        status="draft",
        rationale=rationale,
        canonical_hash=plan_hash,
        dependency_fingerprint=analysis.dependency_fingerprint,
        usage_metadata=usage,
        created_by_membership_id=auth.membership_id,
    )
    session.add(plan)
    await session.flush()
    for index, spec in enumerate(step_specs, 1):
        session.add(
            RecoveryPlanStep(
                institution_id=auth.institution_id,
                plan_id=plan.id,
                step_number=index,
                operation_key=f"recovery:{plan.id}:step:{index}",
                operation_type=spec["operation_type"],
                exact_payload=spec["exact_payload"],
                preconditions={
                    "analysis_id": str(analysis.id),
                    "dependency_fingerprint": analysis.dependency_fingerprint,
                },
                dependencies=spec["dependencies"],
                expected_effects=spec["expected_effects"],
                approval_type=spec["approval_type"],
                irreversible_effects=spec["irreversible_effects"],
            )
        )
    await session.flush()
    proposal = ActionProposal(
        institution_id=auth.institution_id,
        drive_id=analysis.drive_id,
        action_type="execute_recovery_plan",
        target_type="recovery_plan",
        target_id=plan.id,
        revision_number=1,
        schema_version=1,
        payload={
            "plan_id": str(plan.id),
            "plan_hash": plan_hash,
            "rationale": plan.rationale,
            "impact_summary": analysis.impact_summary,
            "affected_students": analysis.affected_students,
            "steps": step_specs,
        },
        dependencies={
            "analysis_id": str(analysis.id),
            "analysis_fingerprint": analysis.dependency_fingerprint,
            "case_id": str(analysis.case_id),
        },
        canonical_hash=canonical_hash(
            {
                "institution_id": str(auth.institution_id),
                "action_type": "execute_recovery_plan",
                "target_id": str(plan.id),
                "plan_hash": plan_hash,
                "dependency_fingerprint": analysis.dependency_fingerprint,
            }
        ),
        state="pending_approval",
        requested_by_membership_id=auth.membership_id,
        execution_expires_at=datetime.now(UTC) + timedelta(hours=24),
        execution_bounds={"max_steps": len(step_specs)},
    )
    session.add(proposal)
    await session.flush()
    plan.proposal_id = proposal.id
    plan.status = "pending_approval"
    record_audit(
        session,
        auth,
        "exception:recovery_plan_proposed",
        "recovery_plan",
        plan.id,
        {
            "case_id": str(plan.case_id),
            "planner_mode": plan.planner_mode,
            "step_count": len(step_specs),
            "proposal_id": str(proposal.id),
        },
    )
    await session.commit()
    return plan


async def plan_steps(session: AsyncSession, plan_id: uuid.UUID) -> list[RecoveryPlanStep]:
    return list(
        (
            await session.execute(
                select(RecoveryPlanStep)
                .where(RecoveryPlanStep.plan_id == plan_id)
                .order_by(RecoveryPlanStep.step_number)
            )
        )
        .scalars()
        .all()
    )


async def decide_recovery_plan(
    session: AsyncSession,
    auth: AuthContext,
    plan: RecoveryPlan,
    *,
    expected_revision: int,
    expected_hash: str,
    decision: str,
    comment: str | None,
) -> RecoveryExecution | None:
    plan = (
        await session.execute(
            select(RecoveryPlan)
            .where(
                RecoveryPlan.id == plan.id,
                RecoveryPlan.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one()
    if not plan.proposal_id:
        raise ConflictException("Recovery plan has no approval proposal")
    proposal = await session.get(ActionProposal, plan.proposal_id, with_for_update=True)
    analysis = await session.get(ExceptionImpactAnalysis, plan.analysis_id)
    if not proposal or not analysis:
        raise ConflictException("Recovery plan dependencies are incomplete")
    existing = (
        await session.execute(select(RecoveryExecution).where(RecoveryExecution.plan_id == plan.id))
    ).scalar_one_or_none()
    if (
        analysis.status != "current"
        or plan.status != "pending_approval"
        or proposal.state != "pending_approval"
    ):
        if decision == "approved" and existing:
            return existing
        raise ConflictException("Recovery plan is no longer pending approval")
    if plan.revision_number != expected_revision or proposal.canonical_hash != expected_hash:
        raise ConflictException("Recovery plan revision or approval hash changed")
    if not await analysis_is_fresh(session, analysis):
        plan.status = proposal.state = analysis.status = "stale"
        await session.commit()
        raise ConflictException("Recovery plan inputs changed after analysis")
    now = datetime.now(UTC)
    if proposal.execution_expires_at and proposal.execution_expires_at <= now:
        plan.status = proposal.state = "stale"
        await session.commit()
        raise ConflictException("Recovery plan approval window expired")
    session.add(
        ApprovalDecision(
            institution_id=auth.institution_id,
            proposal_id=proposal.id,
            proposal_hash=proposal.canonical_hash,
            decision=decision,
            comment=comment,
            decided_by_membership_id=auth.membership_id,
            permission_context={
                "capability": "proposal:decide",
                "recovery_plan": True,
            },
        )
    )
    proposal.state = decision if decision != "revision_requested" else "revision_requested"
    plan.status = proposal.state
    execution = None
    if decision == "approved":
        steps = await plan_steps(session, plan.id)
        execution = RecoveryExecution(
            institution_id=auth.institution_id,
            drive_id=plan.drive_id,
            case_id=plan.case_id,
            plan_id=plan.id,
            proposal_id=proposal.id,
            status="queued",
            pending_step_count=len(steps),
            irreversible_step_count=sum(bool(step.irreversible_effects) for step in steps),
        )
        session.add(execution)
        await session.flush()
        session.add(
            OutboxEvent(
                institution_id=auth.institution_id,
                event_key=f"recovery.execute:{execution.id}",
                event_type="recovery.execute",
                aggregate_type="recovery_execution",
                aggregate_id=execution.id,
                payload={
                    "execution_id": str(execution.id),
                    "institution_id": str(auth.institution_id),
                },
                status="pending",
                next_attempt_at=now,
            )
        )
        plan.status = "queued"
    record_audit(
        session,
        auth,
        "exception:recovery_plan_decided",
        "recovery_plan",
        plan.id,
        {"decision": decision, "execution_id": str(execution.id) if execution else None},
    )
    await session.commit()
    return execution


async def cancel_recovery_execution(
    session: AsyncSession,
    auth: AuthContext,
    execution_id: uuid.UUID,
    *,
    reason: str,
) -> RecoveryExecution:
    execution = (
        await session.execute(
            select(RecoveryExecution)
            .where(
                RecoveryExecution.id == execution_id,
                RecoveryExecution.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not execution:
        raise NotFoundException("Recovery execution not found")
    await load_authorized_drive(session, auth, execution.drive_id)
    if execution.status == "cancelled":
        return execution
    if execution.status not in {"queued", "executing"}:
        raise ConflictException("Only queued or executing recovery can be cancelled")
    plan = await session.get(RecoveryPlan, execution.plan_id, with_for_update=True)
    if not plan:
        raise ConflictException("Recovery plan is unavailable")
    remaining = list(
        (
            await session.execute(
                select(RecoveryPlanStep)
                .where(
                    RecoveryPlanStep.plan_id == plan.id,
                    RecoveryPlanStep.status.in_(["pending", "running"]),
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    for step in remaining:
        step.status = "cancelled"
        step.error_code = "CANCELLED_BY_COORDINATOR"
        step.error_detail = reason
    if remaining:
        running_attempts = (
            await session.execute(
                select(RecoveryStepAttempt)
                .where(
                    RecoveryStepAttempt.step_id.in_([step.id for step in remaining]),
                    RecoveryStepAttempt.status == "running",
                )
                .with_for_update()
            )
        ).scalars()
        for attempt in running_attempts:
            attempt.status = "cancelled"
            attempt.error_code = "CANCELLED_BY_COORDINATOR"
            attempt.error_detail = reason
            attempt.completed_at = datetime.now(UTC)
    execution.status = "cancelled"
    execution.pending_step_count = 0
    execution.current_step_number = None
    execution.completed_at = datetime.now(UTC)
    execution.last_error_code = "CANCELLED_BY_COORDINATOR"
    plan.status = "cancelled"
    record_audit(
        session,
        auth,
        "exception:recovery_execution_cancelled",
        "recovery_execution",
        execution.id,
        {"plan_id": str(plan.id), "reason": reason},
    )
    await session.commit()
    return execution


async def relay_pending_recovery_executions(limit: int = 50) -> int:
    from placementos.workers.recovery_tasks import execute_recovery_plan_task

    async with async_session_maker() as discovery:
        institution_ids = (
            (await discovery.execute(select(Institution.id).where(Institution.is_active.is_(True))))
            .scalars()
            .all()
        )
    published = 0
    now = datetime.now(UTC)
    for institution_id in institution_ids:
        if published >= limit:
            break
        async with async_session_maker() as session:
            session.info["institution_id"] = str(institution_id)
            rows = (
                (
                    await session.execute(
                        select(OutboxEvent)
                        .where(
                            OutboxEvent.institution_id == institution_id,
                            OutboxEvent.aggregate_type == "recovery_execution",
                            OutboxEvent.next_attempt_at <= now,
                            or_(OutboxEvent.status == "pending", OutboxEvent.status == "published"),
                        )
                        .order_by(OutboxEvent.created_at)
                        .limit(limit - published)
                        .with_for_update(skip_locked=True)
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                execution = await session.get(RecoveryExecution, row.aggregate_id)
                if not execution or execution.status not in {"queued", "executing"}:
                    row.status = "processed"
                    continue
                try:
                    execute_recovery_plan_task.delay(str(execution.id), str(institution_id))
                    row.status = "published"
                    row.published_at = now
                    row.publish_attempts += 1
                    row.next_attempt_at = now + timedelta(seconds=30)
                    row.last_error = None
                    published += 1
                except Exception as exc:
                    row.publish_attempts += 1
                    row.last_error = str(exc)[:1000]
                    row.next_attempt_at = now + timedelta(seconds=min(300, 2**row.publish_attempts))
            await session.commit()
    return published


async def _execution_authority(
    session: AsyncSession, execution: RecoveryExecution
) -> tuple[RecoveryPlan, ExceptionImpactAnalysis, ExceptionCase, Drive, Membership]:
    plan = await session.get(RecoveryPlan, execution.plan_id)
    proposal = await session.get(ActionProposal, execution.proposal_id)
    decision = (
        await session.execute(
            select(ApprovalDecision).where(ApprovalDecision.proposal_id == execution.proposal_id)
        )
    ).scalar_one_or_none()
    analysis = await session.get(ExceptionImpactAnalysis, plan.analysis_id) if plan else None
    case = await session.get(ExceptionCase, execution.case_id)
    drive = await session.get(Drive, execution.drive_id)
    reviewer = (
        await session.get(Membership, decision.decided_by_membership_id) if decision else None
    )
    if (
        not plan
        or not proposal
        or not decision
        or not analysis
        or not case
        or not drive
        or not reviewer
        or not reviewer.is_active
        or "proposal:decide" not in reviewer.capabilities
        or proposal.state != "approved"
        or decision.decision != "approved"
        or proposal.canonical_hash != decision.proposal_hash
        or plan.canonical_hash != proposal.payload.get("plan_hash")
        or plan.dependency_fingerprint != analysis.dependency_fingerprint
        or analysis.status != "current"
        or case.status not in {"open", "acknowledged"}
        or drive.status in {"cancelled", "archived"}
        or (proposal.execution_expires_at and proposal.execution_expires_at <= datetime.now(UTC))
    ):
        raise ConflictException("Recovery execution authority or dependency is stale")
    if not await analysis_is_fresh(session, analysis):
        raise ConflictException("Recovery impact inputs changed before execution")
    return plan, analysis, case, drive, reviewer


async def _reviewer_auth(
    session: AsyncSession, reviewer: Membership, institution_id: uuid.UUID
) -> AuthContext:
    user = await session.get(User, reviewer.user_id)
    institution = await session.get(Institution, institution_id)
    if not user or not institution:
        raise ConflictException("Recovery reviewer identity is unavailable")
    return AuthContext(
        session_id="recovery-worker",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        institution_id=institution.id,
        institution_slug=institution.slug,
        membership_id=reviewer.id,
        role=reviewer.role,
        capabilities=list(reviewer.capabilities),
    )


async def _execute_step_domain(
    session: AsyncSession,
    auth: AuthContext,
    execution: RecoveryExecution,
    step: RecoveryPlanStep,
) -> dict[str, Any]:
    payload = step.exact_payload
    if step.operation_type == "place_drive_hold":
        drive = (
            await session.execute(
                select(Drive)
                .where(
                    Drive.id == execution.drive_id,
                    Drive.institution_id == execution.institution_id,
                )
                .with_for_update()
            )
        ).scalar_one()
        reason = str(payload["reason"])
        if drive.operational_hold and drive.hold_reason != reason:
            raise ConflictException("Drive already has a different operational hold")
        if not drive.operational_hold:
            drive.operational_hold = True
            drive.hold_reason = reason
            drive.concurrency_revision += 1
        return {"drive_id": str(drive.id), "operational_hold": True}
    if step.operation_type == "stale_pending_proposals":
        proposal_ids = [uuid.UUID(str(item)) for item in payload["proposal_ids"]]
        proposals = (
            (
                await session.execute(
                    select(ActionProposal)
                    .where(
                        ActionProposal.id.in_(proposal_ids),
                        ActionProposal.institution_id == execution.institution_id,
                        ActionProposal.drive_id == execution.drive_id,
                    )
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if {item.id for item in proposals} != set(proposal_ids):
            raise ConflictException("A listed proposal is unavailable in this drive")
        stale_count = 0
        for proposal in proposals:
            if proposal.state == "pending_approval":
                proposal.state = "stale"
                stale_count += 1
            elif proposal.state != "stale":
                raise ConflictException("A listed proposal has already been decided")
        return {"stale_proposal_count": stale_count}
    if step.operation_type == "mark_external_reconciliation":
        mapping_ids = [uuid.UUID(str(item)) for item in payload["mapping_ids"]]
        mappings = (
            (
                await session.execute(
                    select(ProviderResourceMapping)
                    .where(
                        ProviderResourceMapping.id.in_(mapping_ids),
                        ProviderResourceMapping.institution_id == execution.institution_id,
                    )
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if {item.id for item in mappings} != set(mapping_ids):
            raise ConflictException("A listed provider mapping is unavailable")
        for mapping in mappings:
            mapping.status = "internal_change_pending_reconciliation"
        return {"mapping_count": len(mappings)}
    if step.operation_type == "prepare_correction_draft":
        draft_drive = await session.get(Drive, execution.drive_id)
        if not draft_drive:
            raise ConflictException("Recovery drive no longer exists")
        request = CommunicationDraftCreate(
            communication_kind="clarification",
            audience_type="explicit_recipients",
            explicit_student_ids=[uuid.UUID(str(item)) for item in payload["student_profile_ids"]],
            subject_template=str(payload["subject_template"]),
            body_template=str(payload["body_template"]),
            sender_email=str(payload["sender_email"]),
            reply_to=str(payload["reply_to"]),
        )
        draft, snapshot, recipients = await create_frozen_draft(session, auth, draft_drive, request)
        return {
            "communication_draft_id": str(draft.id),
            "audience_snapshot_id": str(snapshot.id),
            "recipient_count": len(recipients),
            "send_status": "not_proposed_or_sent",
        }
    if step.operation_type == "record_manual_followup":
        item = await session.get(ExceptionCase, execution.case_id, with_for_update=True)
        if not item:
            raise ConflictException("Recovery case no longer exists")
        item.resolution_history = [
            *item.resolution_history,
            {
                "action": "recovery_manual_followup_required",
                "note": str(payload["note"]),
                "plan_id": str(execution.plan_id),
                "at": datetime.now(UTC).isoformat(),
            },
        ]
        return {"case_id": str(item.id), "case_status": item.status}
    raise BadRequestException("Unsupported recovery operation")


async def _mark_execution_stale(
    session: AsyncSession, execution: RecoveryExecution, plan: RecoveryPlan, code: str
) -> None:
    execution.status = "stale"
    execution.last_error_code = code
    execution.completed_at = datetime.now(UTC)
    plan.status = "stale"
    remaining = (
        await session.execute(
            select(RecoveryPlanStep).where(
                RecoveryPlanStep.plan_id == plan.id,
                RecoveryPlanStep.status.in_(["pending", "running"]),
            )
        )
    ).scalars()
    for step in remaining:
        step.status = "stale"
        step.error_code = code
    await session.commit()


async def execute_recovery_plan(execution_id: uuid.UUID, institution_id: uuid.UUID) -> str:
    """Execute an approved plan stepwise; each step is one atomic domain transaction."""
    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        execution = (
            await session.execute(
                select(RecoveryExecution)
                .where(
                    RecoveryExecution.id == execution_id,
                    RecoveryExecution.institution_id == institution_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not execution:
            return "not_found"
        if execution.status in {"succeeded", "partial", "failed", "stale", "cancelled"}:
            return execution.status
        try:
            plan, _analysis, _case, _drive, _reviewer = await _execution_authority(
                session, execution
            )
        except ConflictException:
            stale_plan = await session.get(RecoveryPlan, execution.plan_id)
            if stale_plan:
                await _mark_execution_stale(
                    session, execution, stale_plan, "AUTHORIZATION_OR_DEPENDENCY_STALE"
                )
            return "stale"
        execution.status = "executing"
        execution.started_at = execution.started_at or datetime.now(UTC)
        plan.status = "executing"
        await session.commit()

    while True:
        async with async_session_maker() as session:
            session.info["institution_id"] = str(institution_id)
            execution = await session.get(RecoveryExecution, execution_id, with_for_update=True)
            if not execution:
                return "not_found"
            if execution.status in {"succeeded", "partial", "failed", "stale", "cancelled"}:
                return execution.status
            try:
                plan, _analysis, case, _drive, reviewer = await _execution_authority(
                    session, execution
                )
            except ConflictException:
                stale_plan = await session.get(RecoveryPlan, execution.plan_id)
                if stale_plan:
                    await _mark_execution_stale(
                        session, execution, stale_plan, "AUTHORIZATION_OR_DEPENDENCY_STALE"
                    )
                return "stale"
            steps = await plan_steps(session, plan.id)
            next_step = next(
                (step for step in steps if step.status in {"pending", "running"}), None
            )
            if not next_step:
                execution.status = "succeeded"
                execution.completed_at = datetime.now(UTC)
                execution.current_step_number = None
                execution.pending_step_count = 0
                plan.status = "succeeded"
                case.resolution_history = [
                    *case.resolution_history,
                    {
                        "action": "recovery_plan_executed",
                        "plan_id": str(plan.id),
                        "execution_id": str(execution.id),
                        "note": "Execution completed; coordinator resolution is still required.",
                        "at": datetime.now(UTC).isoformat(),
                    },
                ]
                outbox = (
                    await session.execute(
                        select(OutboxEvent).where(
                            OutboxEvent.aggregate_type == "recovery_execution",
                            OutboxEvent.aggregate_id == execution.id,
                        )
                    )
                ).scalar_one_or_none()
                if outbox:
                    outbox.status = "processed"
                await session.commit()
                return "succeeded"
            completed_numbers = {step.step_number for step in steps if step.status == "completed"}
            if not set(next_step.dependencies).issubset(completed_numbers):
                next_step.status = "failed"
                next_step.error_code = "STEP_DEPENDENCY_INCOMPLETE"
                execution.status = "partial" if completed_numbers else "failed"
                execution.failed_step_count += 1
                execution.last_error_code = next_step.error_code
                plan.status = execution.status
                await session.commit()
                return execution.status
            if next_step.status == "running":
                abandoned = (
                    await session.execute(
                        select(RecoveryStepAttempt).where(
                            RecoveryStepAttempt.step_id == next_step.id,
                            RecoveryStepAttempt.status == "running",
                        )
                    )
                ).scalars()
                for prior_attempt in abandoned:
                    prior_attempt.status = "failed_recoverable"
                    prior_attempt.error_code = "WORKER_INTERRUPTED_BEFORE_ATOMIC_STEP"
                    prior_attempt.completed_at = datetime.now(UTC)
            next_step.status = "running"
            next_step.attempt_count += 1
            execution.current_step_number = next_step.step_number
            attempt = RecoveryStepAttempt(
                institution_id=institution_id,
                execution_id=execution.id,
                step_id=next_step.id,
                attempt_number=next_step.attempt_count,
                status="running",
                started_at=datetime.now(UTC),
            )
            session.add(attempt)
            await session.commit()
            step_id = next_step.id
            attempt_number = next_step.attempt_count
            reviewer_id = reviewer.id

        try:
            async with async_session_maker() as step_session:
                step_session.info["institution_id"] = str(institution_id)
                execution = await step_session.get(
                    RecoveryExecution, execution_id, with_for_update=True
                )
                step = await step_session.get(RecoveryPlanStep, step_id, with_for_update=True)
                step_reviewer = await step_session.get(Membership, reviewer_id)
                if not execution or not step or not step_reviewer:
                    raise ConflictException("Recovery step dependencies disappeared")
                attempt = (
                    await step_session.execute(
                        select(RecoveryStepAttempt).where(
                            RecoveryStepAttempt.step_id == step.id,
                            RecoveryStepAttempt.attempt_number == attempt_number,
                        )
                    )
                ).scalar_one()
                if execution.status == "cancelled" or step.status == "cancelled":
                    if attempt.status == "running":
                        attempt.status = "cancelled"
                        attempt.error_code = "CANCELLED_BY_COORDINATOR"
                        attempt.completed_at = datetime.now(UTC)
                        await step_session.commit()
                    return "cancelled"
                auth = await _reviewer_auth(step_session, step_reviewer, institution_id)
                result = await _execute_step_domain(step_session, auth, execution, step)
                step.status = "completed"
                step.result = result
                step.error_code = None
                step.error_detail = None
                step.completed_at = datetime.now(UTC)
                attempt.status = "completed"
                attempt.result = result
                attempt.completed_at = datetime.now(UTC)
                execution.completed_step_count += 1
                execution.pending_step_count = max(0, execution.pending_step_count - 1)
                record_audit(
                    step_session,
                    auth,
                    "exception:recovery_step_completed",
                    "recovery_plan_step",
                    step.id,
                    {
                        "execution_id": str(execution.id),
                        "step_number": step.step_number,
                        "operation_type": step.operation_type,
                    },
                )
                await step_session.commit()
        except Exception as exc:
            async with async_session_maker() as failure_session:
                failure_session.info["institution_id"] = str(institution_id)
                execution = await failure_session.get(
                    RecoveryExecution, execution_id, with_for_update=True
                )
                step = await failure_session.get(RecoveryPlanStep, step_id, with_for_update=True)
                failed_plan = (
                    await failure_session.get(RecoveryPlan, execution.plan_id)
                    if execution
                    else None
                )
                if not execution or not step or not failed_plan:
                    return "failed"
                attempt = (
                    await failure_session.execute(
                        select(RecoveryStepAttempt).where(
                            RecoveryStepAttempt.step_id == step.id,
                            RecoveryStepAttempt.attempt_number == attempt_number,
                        )
                    )
                ).scalar_one()
                code = (
                    "STEP_PRECONDITION_FAILED"
                    if isinstance(exc, (BadRequestException, ConflictException, NotFoundException))
                    else "STEP_EXECUTION_FAILED"
                )
                detail = str(exc)[:1000]
                step.status = "failed"
                step.error_code = code
                step.error_detail = detail
                attempt.status = "failed"
                attempt.error_code = code
                attempt.error_detail = detail
                attempt.completed_at = datetime.now(UTC)
                execution.failed_step_count += 1
                execution.status = "partial" if execution.completed_step_count else "failed"
                execution.last_error_code = code
                execution.completed_at = datetime.now(UTC)
                failed_plan.status = execution.status
                await failure_session.commit()
                return execution.status
