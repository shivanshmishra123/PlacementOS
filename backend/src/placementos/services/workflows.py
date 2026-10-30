"""P08 durable workflow commands, trusted resume validation, and reconciliation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.types import Command
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import async_session_maker
from placementos.core.errors import ConflictException, NotFoundException
from placementos.models.identity import Institution, Membership, User
from placementos.models.intelligence import ActionProposal, ApprovalDecision, ClarificationTask
from placementos.models.recruitment import Drive
from placementos.models.workflow import (
    ExceptionCase,
    WorkflowCommand,
    WorkflowEvent,
    WorkflowRun,
)
from placementos.services.authorization import load_authorized_drive
from placementos.services.session import AuthContext
from placementos.services.workflow_checkpoints import workflow_checkpointer
from placementos.services.workflow_domain import ensure_case
from placementos.workflows.drive_lifecycle import (
    COMPATIBLE_GRAPH_VERSIONS,
    GRAPH_VERSION,
    STATE_SCHEMA_VERSION,
    build_drive_workflow,
    initial_state,
)

TERMINAL_RUN_STATUSES = {"failed", "completed", "cancelled", "incompatible"}
WAITING_RUN_STATUSES = {
    "waiting_clarification",
    "waiting_policy_approval",
    "waiting_publication_approval",
    "waiting_communication_approval",
    "waiting_input",
    "monitoring",
    "held",
}
SUPPORTED_EVENTS = {
    "registration_changed",
    "document_changed",
    "policy_changed",
    "deadline_reached",
    "dispatch_changed",
}


async def create_workflow_run(
    session: AsyncSession,
    auth: AuthContext,
    drive: Drive,
    *,
    source_artifact_id: uuid.UUID | None,
) -> tuple[WorkflowRun, WorkflowCommand]:
    """Persist a new run and its start intent in one tenant-scoped transaction."""
    active = (
        await session.execute(
            select(WorkflowRun).where(
                WorkflowRun.institution_id == auth.institution_id,
                WorkflowRun.drive_id == drive.id,
                WorkflowRun.status.not_in(TERMINAL_RUN_STATUSES),
            )
        )
    ).scalar_one_or_none()
    if active:
        raise ConflictException(
            "This drive already has an active workflow run",
            details={"workflow_run_id": str(active.id), "status": active.status},
        )
    run = WorkflowRun(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        thread_id=uuid.uuid4(),
        graph_version=GRAPH_VERSION,
        state_schema_version=STATE_SCHEMA_VERSION,
        status="queued",
        current_step="intake",
        state_references=(
            {"source_artifact_id": str(source_artifact_id)} if source_artifact_id else {}
        ),
        concurrency_revision=1,
        created_by_membership_id=auth.membership_id,
    )
    session.add(run)
    await session.flush()
    command = _new_command(
        run,
        requested_by_membership_id=auth.membership_id,
        command_type="start",
        command_key=f"workflow:{run.id}:start",
    )
    session.add(command)
    await session.flush()
    return run, command


def _new_command(
    run: WorkflowRun,
    *,
    requested_by_membership_id: uuid.UUID,
    command_type: str,
    command_key: str,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> WorkflowCommand:
    return WorkflowCommand(
        institution_id=run.institution_id,
        workflow_run_id=run.id,
        command_key=command_key,
        command_type=command_type,
        reference_type=reference_type,
        reference_id=reference_id,
        expected_run_revision=run.concurrency_revision,
        status="pending",
        publish_attempts=0,
        next_attempt_at=datetime.now(UTC),
        result={},
        requested_by_membership_id=requested_by_membership_id,
    )


async def enqueue_resume_command(
    session: AsyncSession,
    run: WorkflowRun,
    *,
    requested_by_membership_id: uuid.UUID,
    reference_type: str,
    reference_id: uuid.UUID,
    command_key: str | None = None,
) -> WorkflowCommand:
    """Create or return a durable, deduplicated trusted resume intent."""
    key = command_key or f"workflow:{run.id}:resume:{reference_type}:{reference_id}"
    existing = (
        await session.execute(
            select(WorkflowCommand).where(
                WorkflowCommand.institution_id == run.institution_id,
                WorkflowCommand.command_key == key,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    command = _new_command(
        run,
        requested_by_membership_id=requested_by_membership_id,
        command_type="resume",
        command_key=key,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    session.add(command)
    await session.flush()
    return command


async def enqueue_workflow_resume_for_proposal(
    session: AsyncSession,
    proposal_id: uuid.UUID,
    decision_id: uuid.UUID,
    requested_by_membership_id: uuid.UUID,
) -> list[WorkflowCommand]:
    runs = (
        (
            await session.execute(
                select(WorkflowRun).where(
                    WorkflowRun.pending_proposal_id == proposal_id,
                    WorkflowRun.status.in_(
                        {
                            "waiting_policy_approval",
                            "waiting_publication_approval",
                            "waiting_communication_approval",
                        }
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    return [
        await enqueue_resume_command(
            session,
            run,
            requested_by_membership_id=requested_by_membership_id,
            reference_type="decision",
            reference_id=decision_id,
        )
        for run in runs
    ]


async def enqueue_workflow_resume_for_clarification(
    session: AsyncSession,
    clarification_id: uuid.UUID,
    requested_by_membership_id: uuid.UUID,
) -> list[WorkflowCommand]:
    runs = (
        (
            await session.execute(
                select(WorkflowRun).where(
                    WorkflowRun.pending_clarification_id == clarification_id,
                    WorkflowRun.status == "waiting_clarification",
                )
            )
        )
        .scalars()
        .all()
    )
    return [
        await enqueue_resume_command(
            session,
            run,
            requested_by_membership_id=requested_by_membership_id,
            reference_type="clarification",
            reference_id=clarification_id,
        )
        for run in runs
    ]


async def create_workflow_event(
    session: AsyncSession,
    run: WorkflowRun,
    *,
    actor_membership_id: uuid.UUID,
    event_key: str,
    event_type: str,
    resource_type: str,
    resource_id: uuid.UUID,
    resource_revision: str | None,
    event_payload: dict[str, Any],
    occurred_at: datetime,
) -> tuple[WorkflowEvent, WorkflowCommand, bool]:
    if event_type not in SUPPORTED_EVENTS:
        raise ConflictException("Unsupported workflow event type")
    existing = (
        await session.execute(
            select(WorkflowEvent).where(
                WorkflowEvent.institution_id == run.institution_id,
                WorkflowEvent.event_key == event_key,
            )
        )
    ).scalar_one_or_none()
    if existing:
        if existing.workflow_run_id != run.id:
            raise ConflictException("Event key is already used by another workflow run")
        command = (
            await session.execute(
                select(WorkflowCommand).where(
                    WorkflowCommand.institution_id == run.institution_id,
                    WorkflowCommand.command_key == f"workflow:{run.id}:event:{existing.id}",
                )
            )
        ).scalar_one()
        return existing, command, False
    event = WorkflowEvent(
        institution_id=run.institution_id,
        workflow_run_id=run.id,
        event_key=event_key,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_revision=resource_revision,
        event_payload=event_payload,
        occurred_at=occurred_at,
        status="pending",
        processing_result={},
    )
    session.add(event)
    await session.flush()
    command = await enqueue_resume_command(
        session,
        run,
        requested_by_membership_id=actor_membership_id,
        reference_type="event",
        reference_id=event.id,
        command_key=f"workflow:{run.id}:event:{event.id}",
    )
    return event, command, True


async def relay_pending_workflow_commands(limit: int = 100) -> int:
    """Relay persisted intents per tenant; a broker failure leaves them retryable."""
    from placementos.workers.workflow_tasks import execute_workflow_command_task

    now = datetime.now(UTC)
    async with async_session_maker() as discovery:
        institution_ids = (
            (await discovery.execute(select(Institution.id).where(Institution.is_active.is_(True))))
            .scalars()
            .all()
        )
    published = 0
    for institution_id in institution_ids:
        if published >= limit:
            break
        async with async_session_maker() as session:
            session.info["institution_id"] = str(institution_id)
            commands = (
                (
                    await session.execute(
                        select(WorkflowCommand)
                        .where(
                            WorkflowCommand.next_attempt_at <= now,
                            or_(
                                WorkflowCommand.status.in_({"pending", "published"}),
                                and_(
                                    WorkflowCommand.status == "claimed",
                                    WorkflowCommand.updated_at < now - timedelta(seconds=90),
                                ),
                            ),
                        )
                        .order_by(WorkflowCommand.created_at)
                        .limit(limit - published)
                        .with_for_update(skip_locked=True)
                    )
                )
                .scalars()
                .all()
            )
            for command in commands:
                command.publish_attempts += 1
                try:
                    execute_workflow_command_task.delay(
                        str(command.id), str(command.institution_id)
                    )
                    command.status = "published"
                    command.published_at = now
                    command.next_attempt_at = now + timedelta(seconds=30)
                    command.last_error = None
                    published += 1
                except Exception as exc:  # broker boundary
                    command.status = "pending"
                    command.last_error = str(exc)[:1000]
                    command.next_attempt_at = now + timedelta(
                        seconds=min(300, 2**command.publish_attempts)
                    )
            await session.commit()
    return published


async def _auth_for_membership(
    session: AsyncSession, institution_id: uuid.UUID, membership_id: uuid.UUID
) -> AuthContext:
    row = (
        await session.execute(
            select(Membership, User, Institution)
            .join(User, User.id == Membership.user_id)
            .join(Institution, Institution.id == Membership.institution_id)
            .where(
                Membership.id == membership_id,
                Membership.institution_id == institution_id,
                Membership.is_active.is_(True),
                User.is_active.is_(True),
                Institution.is_active.is_(True),
            )
        )
    ).one_or_none()
    if not row:
        raise ConflictException("Workflow command actor is no longer authorized")
    membership, user, institution = row
    return AuthContext(
        session_id=f"workflow-command:{membership_id}",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        institution_id=institution_id,
        institution_slug=institution.slug,
        membership_id=membership.id,
        role=membership.role,
        capabilities=list(membership.capabilities),
    )


async def _validate_reference(
    session: AsyncSession,
    run: WorkflowRun,
    drive: Drive,
    command: WorkflowCommand,
) -> dict[str, str]:
    if command.command_type == "start":
        if command.reference_type or command.reference_id:
            raise ConflictException("Start command must not include a resume reference")
        return {}
    if not command.reference_type or not command.reference_id:
        raise ConflictException("Resume command requires a persisted reference")
    reference_type = command.reference_type
    reference_id = command.reference_id
    if reference_type == "decision":
        decision = await session.get(ApprovalDecision, reference_id)
        if (
            not decision
            or decision.institution_id != run.institution_id
            or decision.proposal_id != run.pending_proposal_id
        ):
            raise ConflictException("Decision does not match the run's pending proposal")
        proposal = await session.get(ActionProposal, decision.proposal_id)
        reviewer = await session.get(Membership, decision.decided_by_membership_id)
        required_capability = str(decision.permission_context.get("capability", ""))
        if (
            not proposal
            or proposal.institution_id != run.institution_id
            or proposal.canonical_hash != decision.proposal_hash
            or proposal.state != decision.decision
            or not reviewer
            or not reviewer.is_active
            or (
                required_capability
                and required_capability not in reviewer.capabilities
                and reviewer.role != "super_admin"
            )
        ):
            raise ConflictException("Decision authority or exact proposal evidence is stale")
    elif reference_type == "clarification":
        clarification = await session.get(ClarificationTask, reference_id)
        if (
            not clarification
            or clarification.institution_id != run.institution_id
            or clarification.id != run.pending_clarification_id
            or clarification.status != "resolved"
        ):
            raise ConflictException("Clarification is not the resolved pending task")
    elif reference_type == "case":
        case = await session.get(ExceptionCase, reference_id)
        if (
            not case
            or case.workflow_run_id != run.id
            or case.id != run.pending_case_id
            or case.status not in {"resolved", "dismissed"}
        ):
            raise ConflictException("Case is not the resolved pending workflow case")
    elif reference_type == "event":
        event = await session.get(WorkflowEvent, reference_id)
        if (
            not event
            or event.workflow_run_id != run.id
            or event.institution_id != run.institution_id
        ):
            raise ConflictException("Event does not belong to this workflow run")
    elif reference_type == "hold_release":
        if drive.operational_hold:
            raise ConflictException("Operational hold is still active")
    else:
        raise ConflictException("Unsupported workflow resume reference")
    return {"reference_type": reference_type, "reference_id": str(reference_id)}


async def _mark_command_failure(
    command_id: uuid.UUID,
    institution_id: uuid.UUID,
    *,
    category: str,
    detail: str,
    incompatible: bool = False,
) -> str:
    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        command = await session.get(WorkflowCommand, command_id)
        if not command:
            return "not_found"
        run = await session.get(WorkflowRun, command.workflow_run_id)
        if not run:
            return "not_found"
        command.status = "failed"
        command.last_error = detail[:1000]
        command.processed_at = datetime.now(UTC)
        command.result = {"category": category}
        run.status = "incompatible" if incompatible else "failed"
        run.error_category = category
        run.error_detail = detail[:1000]
        run.concurrency_revision += 1
        case = await ensure_case(
            session,
            run,
            key_suffix=f"command:{command.id}:{category}",
            category=category,
            severity="critical" if incompatible else "high",
            resources=[{"type": "workflow_command", "id": str(command.id)}],
            evidence={
                "command_type": command.command_type,
                "reference_type": command.reference_type,
            },
            next_action=(
                "Run the documented compatible-state migration or start a reviewed replacement run."
                if incompatible
                else "Review the persisted error, correct the blocking input, and retry deliberately."
            ),
        )
        run.pending_case_id = case.id
        await session.commit()
    return "incompatible" if incompatible else "failed"


async def execute_workflow_command(command_id: uuid.UUID, institution_id: uuid.UUID) -> str:
    """Authorize, claim, validate, and invoke one trusted workflow command."""
    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        command = (
            await session.execute(
                select(WorkflowCommand)
                .where(
                    WorkflowCommand.id == command_id,
                    WorkflowCommand.institution_id == institution_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not command:
            return "not_found"
        if command.status in {"processed", "failed", "cancelled"}:
            return command.status
        if command.status == "claimed" and command.updated_at >= datetime.now(UTC) - timedelta(
            seconds=90
        ):
            return "already_claimed"
        run = await session.get(WorkflowRun, command.workflow_run_id)
        if not run:
            return "not_found"
        try:
            actor = await _auth_for_membership(
                session, institution_id, command.requested_by_membership_id
            )
            drive = await load_authorized_drive(session, actor, run.drive_id)
        except (ConflictException, NotFoundException) as exc:
            detail = str(exc)
            await session.rollback()
            return await _mark_command_failure(
                command_id,
                institution_id,
                category="workflow_authorization_failed",
                detail=detail,
            )
        if drive.operational_hold and command.reference_type != "hold_release":
            command.status = "pending"
            command.next_attempt_at = datetime.now(UTC) + timedelta(minutes=5)
            command.last_error = "Operational hold blocks workflow execution"
            run.status = "held"
            await session.commit()
            return "held"
        if run.status in TERMINAL_RUN_STATUSES:
            command.status = "cancelled"
            command.processed_at = datetime.now(UTC)
            command.result = {"run_status": run.status}
            await session.commit()
            return "cancelled"
        if command.expected_run_revision != run.concurrency_revision:
            if command.reference_type == "event" and run.status == "monitoring":
                # Multiple domain events may be persisted against the same monitoring
                # revision. Serialize them here and rebase only this bounded event command.
                command.expected_run_revision = run.concurrency_revision
            else:
                command.status = "cancelled"
                command.processed_at = datetime.now(UTC)
                command.result = {
                    "reason": "stale_run_revision",
                    "expected": command.expected_run_revision,
                    "actual": run.concurrency_revision,
                }
                await session.commit()
                return "stale"
        if (
            run.graph_version not in COMPATIBLE_GRAPH_VERSIONS
            or run.state_schema_version != STATE_SCHEMA_VERSION
        ):
            run_graph_version = run.graph_version
            run_state_schema_version = run.state_schema_version
            await session.rollback()
            return await _mark_command_failure(
                command_id,
                institution_id,
                category="incompatible_workflow_version",
                detail=(
                    f"Run uses graph={run_graph_version} state={run_state_schema_version}; "
                    f"worker supports graph={GRAPH_VERSION} state={STATE_SCHEMA_VERSION}"
                ),
                incompatible=True,
            )
        try:
            resume_payload = await _validate_reference(session, run, drive, command)
            source_artifact_id = (
                uuid.UUID(run.state_references["source_artifact_id"])
                if run.state_references.get("source_artifact_id")
                else None
            )
        except (ConflictException, NotFoundException, ValueError) as exc:
            detail = str(exc)
            await session.rollback()
            return await _mark_command_failure(
                command_id,
                institution_id,
                category="stale_resume_reference",
                detail=detail,
            )
        thread_id = run.thread_id
        command.status = "claimed"
        run.status = "running"
        await session.commit()

    config = {"configurable": {"thread_id": str(thread_id)}}
    try:
        async with workflow_checkpointer() as checkpointer:
            graph = build_drive_workflow(checkpointer)
            if command.command_type == "start":
                graph_input: Any = {
                    **initial_state(run, source_artifact_id),
                    "active_command_id": str(command_id),
                }
            else:
                graph_input = Command(
                    resume=resume_payload,
                    update={"active_command_id": str(command_id)},
                )
            await graph.ainvoke(graph_input, config=config, durability="sync")
            snapshot = await graph.aget_state(config)
            checkpoint_values = dict(snapshot.values)
    except Exception as exc:
        return await _mark_command_failure(
            command_id,
            institution_id,
            category="workflow_execution_failed",
            detail=f"{type(exc).__name__}: {exc}",
        )

    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        command = (
            await session.execute(
                select(WorkflowCommand).where(WorkflowCommand.id == command_id).with_for_update()
            )
        ).scalar_one_or_none()
        if not command:
            return "not_found"
        run = await session.get(WorkflowRun, command.workflow_run_id)
        if not run:
            return "not_found"
        command.status = "processed"
        command.processed_at = datetime.now(UTC)
        command.last_error = None
        command.result = {
            "current_step": checkpoint_values.get("current_step", run.current_step),
            "interrupted": bool(snapshot.interrupts),
        }
        run.last_processed_command_id = command.id
        if run.status == "running" and snapshot.interrupts:
            run.status = "waiting_input"
        await session.commit()
    return "processed"


async def load_scoped_run(
    session: AsyncSession,
    auth: AuthContext,
    workflow_run_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> WorkflowRun:
    statement = select(WorkflowRun).where(
        WorkflowRun.id == workflow_run_id,
        WorkflowRun.institution_id == auth.institution_id,
    )
    if for_update:
        statement = statement.with_for_update()
    run = (await session.execute(statement)).scalar_one_or_none()
    if not run:
        raise NotFoundException(f"Workflow run '{workflow_run_id}' not found")
    await load_authorized_drive(session, auth, run.drive_id, for_update=for_update)
    return run
