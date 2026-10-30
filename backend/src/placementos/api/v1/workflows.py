"""P08 coordinator API for durable workflow runs, events, holds, and cases."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import ConflictException, NotFoundException
from placementos.models.identity import DriveAssignment
from placementos.models.intelligence import ApprovalDecision, ClarificationTask
from placementos.models.storage import SourceArtifact
from placementos.models.workflow import ExceptionCase, WorkflowCommand, WorkflowEvent, WorkflowRun
from placementos.schemas.workflow import (
    ExceptionCaseAction,
    ExceptionCaseResponse,
    OperationalHoldCreate,
    OperationalHoldRelease,
    WorkflowCommandResponse,
    WorkflowEventCreate,
    WorkflowEventResponse,
    WorkflowResumeCreate,
    WorkflowRunCreate,
    WorkflowRunResponse,
)
from placementos.services.audit import record_audit
from placementos.services.authorization import load_authorized_drive
from placementos.services.session import AuthContext
from placementos.services.workflows import (
    create_workflow_event,
    create_workflow_run,
    enqueue_resume_command,
    load_scoped_run,
)

router = APIRouter(tags=["Durable Workflows"])


def _run_response(run: WorkflowRun) -> WorkflowRunResponse:
    return WorkflowRunResponse.model_validate(run)


@router.post(
    "/drives/{drive_id}/workflow-runs",
    response_model=WorkflowRunResponse,
    status_code=201,
)
async def start_workflow_run(
    drive_id: uuid.UUID,
    payload: WorkflowRunCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunResponse:
    auth.require_coordinator()
    drive = await load_authorized_drive(session, auth, drive_id, for_update=True)
    if payload.source_artifact_id:
        artifact = (
            await session.execute(
                select(SourceArtifact).where(
                    SourceArtifact.id == payload.source_artifact_id,
                    SourceArtifact.institution_id == auth.institution_id,
                    SourceArtifact.drive_id == drive.id,
                    SourceArtifact.acceptance_status == "accepted",
                )
            )
        ).scalar_one_or_none()
        if not artifact:
            raise NotFoundException("Accepted source artifact not found for this drive")
    run, command = await create_workflow_run(
        session, auth, drive, source_artifact_id=payload.source_artifact_id
    )
    record_audit(
        session,
        auth,
        "workflow:started",
        "workflow_run",
        run.id,
        {"command_id": str(command.id), "graph_version": run.graph_version},
    )
    await session.commit()
    return _run_response(run)


@router.get("/drives/{drive_id}/workflow-runs", response_model=list[WorkflowRunResponse])
async def list_workflow_runs(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[WorkflowRunResponse]:
    await load_authorized_drive(session, auth, drive_id)
    runs = (
        (
            await session.execute(
                select(WorkflowRun)
                .where(
                    WorkflowRun.institution_id == auth.institution_id,
                    WorkflowRun.drive_id == drive_id,
                )
                .order_by(WorkflowRun.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [_run_response(item) for item in runs]


@router.get("/workflow-runs/{workflow_run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    workflow_run_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunResponse:
    run = await load_scoped_run(session, auth, workflow_run_id)
    return _run_response(run)


@router.post(
    "/workflow-runs/{workflow_run_id}/resume",
    response_model=WorkflowCommandResponse,
    status_code=202,
)
async def resume_workflow_run(
    workflow_run_id: uuid.UUID,
    payload: WorkflowResumeCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> WorkflowCommandResponse:
    auth.require_coordinator()
    run = await load_scoped_run(session, auth, workflow_run_id, for_update=True)
    if run.concurrency_revision != payload.expected_run_revision:
        raise ConflictException(
            "Workflow run revision is stale",
            details={"current_revision": run.concurrency_revision},
        )
    if payload.reference_type == "decision":
        decision = await session.get(ApprovalDecision, payload.reference_id)
        if not decision or decision.proposal_id != run.pending_proposal_id:
            raise ConflictException("Decision does not match the pending proposal")
    elif payload.reference_type == "clarification":
        clarification = await session.get(ClarificationTask, payload.reference_id)
        if (
            not clarification
            or clarification.id != run.pending_clarification_id
            or clarification.status != "resolved"
        ):
            raise ConflictException("Clarification is not the resolved pending task")
    else:
        event = await session.get(WorkflowEvent, payload.reference_id)
        if not event or event.workflow_run_id != run.id:
            raise ConflictException("Event does not belong to this workflow run")
    command = await enqueue_resume_command(
        session,
        run,
        requested_by_membership_id=auth.membership_id,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
    )
    record_audit(
        session,
        auth,
        "workflow:resume_requested",
        "workflow_command",
        command.id,
        {"reference_type": payload.reference_type, "reference_id": str(payload.reference_id)},
    )
    await session.commit()
    return WorkflowCommandResponse.model_validate(command)


@router.post(
    "/workflow-runs/{workflow_run_id}/events",
    response_model=WorkflowEventResponse,
    status_code=202,
)
async def submit_workflow_event(
    workflow_run_id: uuid.UUID,
    payload: WorkflowEventCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> WorkflowEventResponse:
    auth.require_coordinator()
    run = await load_scoped_run(session, auth, workflow_run_id, for_update=True)
    if run.status not in {"monitoring", "held"}:
        raise ConflictException("Workflow events are accepted only during monitoring or a hold")
    event, command, created = await create_workflow_event(
        session,
        run,
        actor_membership_id=auth.membership_id,
        event_key=payload.event_key,
        event_type=payload.event_type,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        resource_revision=payload.resource_revision,
        event_payload=payload.payload,
        occurred_at=payload.occurred_at,
    )
    if created:
        record_audit(
            session,
            auth,
            "workflow:event_recorded",
            "workflow_event",
            event.id,
            {"event_type": event.event_type, "resource_type": event.resource_type},
        )
    await session.commit()
    return WorkflowEventResponse(
        id=event.id,
        workflow_run_id=event.workflow_run_id,
        event_key=event.event_key,
        event_type=event.event_type,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        resource_revision=event.resource_revision,
        payload=event.event_payload,
        occurred_at=event.occurred_at,
        status=event.status,
        processing_result=event.processing_result,
        command_id=command.id,
        created=created,
    )


@router.post("/workflow-runs/{workflow_run_id}/hold", response_model=WorkflowRunResponse)
async def place_operational_hold(
    workflow_run_id: uuid.UUID,
    payload: OperationalHoldCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunResponse:
    auth.require_coordinator()
    run = await load_scoped_run(session, auth, workflow_run_id, for_update=True)
    drive = await load_authorized_drive(session, auth, run.drive_id, for_update=True)
    if run.concurrency_revision != payload.expected_run_revision:
        raise ConflictException("Workflow run revision is stale")
    if drive.operational_hold:
        raise ConflictException("Drive already has an operational hold")
    run.state_references = {**run.state_references, "pre_hold_status": run.status}
    run.status = "held"
    run.concurrency_revision += 1
    drive.operational_hold = True
    drive.hold_reason = payload.reason
    record_audit(
        session,
        auth,
        "workflow:hold_placed",
        "workflow_run",
        run.id,
        {"reason": payload.reason},
    )
    await session.commit()
    return _run_response(run)


@router.post("/workflow-runs/{workflow_run_id}/release-hold", response_model=WorkflowRunResponse)
async def release_operational_hold(
    workflow_run_id: uuid.UUID,
    payload: OperationalHoldRelease,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunResponse:
    auth.require_coordinator()
    run = await load_scoped_run(session, auth, workflow_run_id, for_update=True)
    drive = await load_authorized_drive(session, auth, run.drive_id, for_update=True)
    if run.concurrency_revision != payload.expected_run_revision:
        raise ConflictException("Workflow run revision is stale")
    if not drive.operational_hold:
        raise ConflictException("Drive does not have an operational hold")
    drive.operational_hold = False
    drive.hold_reason = None
    run.status = str(run.state_references.get("pre_hold_status", "waiting_input"))
    run.state_references = {
        key: value for key, value in run.state_references.items() if key != "pre_hold_status"
    }
    run.concurrency_revision += 1
    pending_commands = (
        (
            await session.execute(
                select(WorkflowCommand).where(
                    WorkflowCommand.workflow_run_id == run.id,
                    WorkflowCommand.status.in_({"pending", "published"}),
                )
            )
        )
        .scalars()
        .all()
    )
    for command in pending_commands:
        command.status = "pending"
        command.expected_run_revision = run.concurrency_revision
        command.next_attempt_at = datetime.now(UTC)
        command.last_error = None
    record_audit(
        session,
        auth,
        "workflow:hold_released",
        "workflow_run",
        run.id,
        {"reason": payload.reason, "resumed_commands": len(pending_commands)},
    )
    await session.commit()
    return _run_response(run)


@router.get("/exception-cases", response_model=list[ExceptionCaseResponse])
async def list_exception_cases(
    status: str | None = Query(default=None, pattern="^(open|acknowledged|resolved|dismissed)$"),
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[ExceptionCaseResponse]:
    auth.require_coordinator()
    assigned_drive_ids = select(DriveAssignment.drive_id).where(
        DriveAssignment.institution_id == auth.institution_id,
        DriveAssignment.membership_id == auth.membership_id,
    )
    query = select(ExceptionCase).where(
        ExceptionCase.institution_id == auth.institution_id,
        ExceptionCase.drive_id.in_(assigned_drive_ids),
    )
    if status:
        query = query.where(ExceptionCase.status == status)
    cases = (await session.execute(query.order_by(ExceptionCase.created_at.desc()))).scalars().all()
    return [ExceptionCaseResponse.model_validate(item) for item in cases]


@router.post("/exception-cases/{case_id}/actions", response_model=ExceptionCaseResponse)
async def act_on_exception_case(
    case_id: uuid.UUID,
    payload: ExceptionCaseAction,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> ExceptionCaseResponse:
    auth.require_coordinator()
    item = (
        await session.execute(
            select(ExceptionCase)
            .where(
                ExceptionCase.id == case_id,
                ExceptionCase.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not item:
        raise NotFoundException("Exception case not found")
    await load_authorized_drive(session, auth, item.drive_id)
    run = await session.get(WorkflowRun, item.workflow_run_id) if item.workflow_run_id else None
    if run and payload.expected_run_revision is not None:
        if run.concurrency_revision != payload.expected_run_revision:
            raise ConflictException("Workflow run revision is stale")
    item.status = payload.action
    item.owner_membership_id = auth.membership_id
    item.resolution_history = [
        *item.resolution_history,
        {
            "action": payload.action,
            "note": payload.note,
            "membership_id": str(auth.membership_id),
            "at": datetime.now(UTC).isoformat(),
        },
    ]
    if run and payload.action in {"resolved", "dismissed"} and run.pending_case_id == item.id:
        await enqueue_resume_command(
            session,
            run,
            requested_by_membership_id=auth.membership_id,
            reference_type="case",
            reference_id=item.id,
        )
    record_audit(
        session,
        auth,
        "exception_case:updated",
        "exception_case",
        item.id,
        {"action": payload.action, "note": payload.note},
    )
    await session.commit()
    return ExceptionCaseResponse.model_validate(item)
