"""P08 versioned LangGraph coordinating existing PlacementOS domain services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TypedDict

from langgraph.graph import START, StateGraph
from langgraph.types import interrupt
from sqlalchemy import func, select

from placementos.core.database import async_session_maker
from placementos.models.communications import DispatchOperation
from placementos.models.intelligence import (
    ActionProposal,
    ClarificationTask,
    EligibilityPolicyVersion,
    JDInterpretationRevision,
)
from placementos.models.recruitment import Drive
from placementos.models.workflow import WorkflowEvent, WorkflowRun
from placementos.services.workflow_domain import (
    ensure_announcement_proposal,
    ensure_case,
    ensure_evaluation,
    ensure_interpretation,
    ensure_policy_and_proposal,
    ensure_source_and_extraction,
)

GRAPH_VERSION = "drive-lifecycle-v1"
STATE_SCHEMA_VERSION = 1
COMPATIBLE_GRAPH_VERSIONS = {GRAPH_VERSION}


class WorkflowState(TypedDict, total=False):
    institution_id: str
    drive_id: str
    workflow_run_id: str
    graph_version: str
    state_schema_version: int
    source_artifact_id: str | None
    extraction_id: str | None
    interpretation_id: str | None
    policy_id: str | None
    evaluation_run_id: str | None
    publication_proposal_id: str | None
    communication_proposal_id: str | None
    current_step: str
    pending_proposal_id: str | None
    pending_clarification_id: str | None
    pending_case_id: str | None
    processed_event_id: str | None
    active_command_id: str | None
    processed_command_id: str | None
    error_category: str | None
    error_detail: str | None


def initial_state(run: WorkflowRun, source_artifact_id: uuid.UUID | None) -> WorkflowState:
    return {
        "institution_id": str(run.institution_id),
        "drive_id": str(run.drive_id),
        "workflow_run_id": str(run.id),
        "graph_version": GRAPH_VERSION,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "source_artifact_id": str(source_artifact_id) if source_artifact_id else None,
        "current_step": "intake",
        "error_category": None,
        "error_detail": None,
    }


async def _load(session, state: WorkflowState) -> tuple[WorkflowRun, Drive]:
    institution_id = uuid.UUID(state["institution_id"])
    session.info["institution_id"] = str(institution_id)
    run = (
        await session.execute(
            select(WorkflowRun).where(
                WorkflowRun.id == uuid.UUID(state["workflow_run_id"]),
                WorkflowRun.institution_id == institution_id,
            )
        )
    ).scalar_one()
    drive = (
        await session.execute(
            select(Drive).where(
                Drive.id == run.drive_id,
                Drive.institution_id == institution_id,
            )
        )
    ).scalar_one()
    return run, drive


async def _set_run(
    session,
    run: WorkflowRun,
    *,
    status: str,
    step: str,
    references: dict | None = None,
    proposal_id: uuid.UUID | None = None,
    clarification_id: uuid.UUID | None = None,
    case_id: uuid.UUID | None = None,
) -> None:
    run.status = status
    run.current_step = step
    if references:
        run.state_references = {**run.state_references, **references}
    run.pending_proposal_id = proposal_id
    run.pending_clarification_id = clarification_id
    run.pending_case_id = case_id
    run.error_category = None
    run.error_detail = None
    run.concurrency_revision += 1
    await session.commit()


async def _pause_for_hold(state: WorkflowState, run: WorkflowRun, drive: Drive, session) -> None:
    if not drive.operational_hold:
        return
    await _set_run(session, run, status="held", step=run.current_step)
    interrupt(
        {
            "kind": "operational_hold",
            "workflow_run_id": str(run.id),
            "drive_id": str(drive.id),
            "reason": drive.hold_reason,
        }
    )


def _mark_command(result: WorkflowState, state: WorkflowState) -> WorkflowState:
    result["processed_command_id"] = state.get("active_command_id")
    return result


async def intake_node(state: WorkflowState) -> WorkflowState:
    pause_payload = None
    result: WorkflowState = {}
    async with async_session_maker() as session:
        run, drive = await _load(session, state)
        await _pause_for_hold(state, run, drive, session)
        artifact, extraction, case = await ensure_source_and_extraction(
            session,
            run,
            uuid.UUID(state["source_artifact_id"]) if state.get("source_artifact_id") else None,
        )
        if case:
            await _set_run(session, run, status="waiting_input", step="intake", case_id=case.id)
            pause_payload = {
                "kind": "exception_case",
                "case_id": str(case.id),
                "category": case.category,
                "next_action": case.proposed_next_action,
            }
        else:
            assert artifact is not None and extraction is not None
            interpretation = await ensure_interpretation(session, run, artifact, extraction)
            clarification = (
                await session.execute(
                    select(ClarificationTask)
                    .where(
                        ClarificationTask.interpretation_id == interpretation.id,
                        ClarificationTask.blocking.is_(True),
                        ClarificationTask.status == "open",
                    )
                    .order_by(ClarificationTask.created_at)
                    .limit(1)
                )
            ).scalar_one_or_none()
            references = {
                "source_artifact_id": str(artifact.id),
                "extraction_id": str(extraction.id),
                "interpretation_id": str(interpretation.id),
            }
            if clarification:
                await _set_run(
                    session,
                    run,
                    status="waiting_clarification",
                    step="intake",
                    references=references,
                    clarification_id=clarification.id,
                )
                pause_payload = {
                    "kind": "clarification",
                    "clarification_id": str(clarification.id),
                    "question": clarification.question,
                }
            else:
                await _set_run(session, run, status="running", step="policy", references=references)
                result = _mark_command(
                    {
                        "source_artifact_id": references["source_artifact_id"],
                        "extraction_id": references["extraction_id"],
                        "interpretation_id": references["interpretation_id"],
                        "current_step": "policy",
                        "pending_case_id": None,
                        "pending_clarification_id": None,
                    },
                    state,
                )
    if pause_payload:
        interrupt(pause_payload)
    return result


async def policy_node(state: WorkflowState) -> WorkflowState:
    pause_payload = None
    result: WorkflowState = {}
    async with async_session_maker() as session:
        run, drive = await _load(session, state)
        await _pause_for_hold(state, run, drive, session)
        interpretation = await session.get(
            JDInterpretationRevision, uuid.UUID(state["interpretation_id"])
        )
        if interpretation is None:
            raise RuntimeError("Workflow interpretation reference is missing")
        previous = (
            await session.get(ActionProposal, run.pending_proposal_id)
            if run.pending_proposal_id
            else None
        )
        if (
            previous
            and previous.action_type == "approve_eligibility_policy"
            and previous.state
            in {
                "rejected",
                "revision_requested",
                "stale",
                "expired",
            }
        ):
            case = await ensure_case(
                session,
                run,
                key_suffix=f"policy-proposal:{previous.id}:{previous.state}",
                category="stale_approval"
                if previous.state in {"stale", "expired"}
                else "unresolved_input",
                severity="high",
                resources=[{"type": "action_proposal", "id": str(previous.id)}],
                evidence={"proposal_state": previous.state},
                next_action="Revise the reviewed facts or policy, then submit a new exact proposal.",
            )
            await _set_run(session, run, status="waiting_input", step="policy", case_id=case.id)
            pause_payload = {
                "kind": "exception_case",
                "case_id": str(case.id),
                "category": case.category,
                "next_action": case.proposed_next_action,
            }
        else:
            policy, proposal = await ensure_policy_and_proposal(session, run, interpretation)
            if policy and policy.status == "approved":
                await _set_run(
                    session,
                    run,
                    status="running",
                    step="evaluation",
                    references={"policy_id": str(policy.id)},
                )
                result = _mark_command(
                    {
                        "policy_id": str(policy.id),
                        "current_step": "evaluation",
                        "pending_proposal_id": None,
                    },
                    state,
                )
            else:
                assert proposal is not None
                await _set_run(
                    session,
                    run,
                    status="waiting_policy_approval",
                    step="policy",
                    references={"policy_id": str(policy.id)} if policy else None,
                    proposal_id=proposal.id,
                )
                pause_payload = {
                    "kind": "proposal_decision",
                    "proposal_id": str(proposal.id),
                    "action_type": proposal.action_type,
                    "canonical_hash": proposal.canonical_hash,
                }
    if pause_payload:
        interrupt(pause_payload)
    return result


async def evaluation_node(state: WorkflowState) -> WorkflowState:
    async with async_session_maker() as session:
        run, drive = await _load(session, state)
        await _pause_for_hold(state, run, drive, session)
        policy = await session.get(EligibilityPolicyVersion, uuid.UUID(state["policy_id"]))
        if not policy or policy.status != "approved":
            raise RuntimeError("Approved policy reference is unavailable")
        evaluation = await ensure_evaluation(session, run, policy)
    async with async_session_maker() as session:
        run, _drive = await _load(session, state)
        await _set_run(
            session,
            run,
            status="running",
            step="publication",
            references={"evaluation_run_id": str(evaluation.id)},
        )
    return _mark_command(
        {
            "evaluation_run_id": str(evaluation.id),
            "current_step": "publication",
        },
        state,
    )


async def publication_node(state: WorkflowState) -> WorkflowState:
    pause_payload = None
    result: WorkflowState = {}
    async with async_session_maker() as session:
        run, drive = await _load(session, state)
        await _pause_for_hold(state, run, drive, session)
        if drive.status == "published" and str(drive.published_evaluation_run_id) == state.get(
            "evaluation_run_id"
        ):
            await _set_run(session, run, status="running", step="communication")
            result = _mark_command({"current_step": "communication"}, state)
        else:
            proposal = (
                await session.execute(
                    select(ActionProposal)
                    .where(
                        ActionProposal.institution_id == run.institution_id,
                        ActionProposal.drive_id == run.drive_id,
                        ActionProposal.action_type == "drive_publication",
                        ActionProposal.state == "pending_approval",
                    )
                    .order_by(ActionProposal.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if proposal:
                await _set_run(
                    session,
                    run,
                    status="waiting_publication_approval",
                    step="publication",
                    proposal_id=proposal.id,
                )
                pause_payload = {
                    "kind": "proposal_decision",
                    "proposal_id": str(proposal.id),
                    "action_type": proposal.action_type,
                    "canonical_hash": proposal.canonical_hash,
                }
            else:
                previous = (
                    await session.get(ActionProposal, run.pending_proposal_id)
                    if run.pending_proposal_id
                    else None
                )
                suffix = (
                    f"publication-proposal:{previous.id}:{previous.state}"
                    if previous and previous.action_type == "drive_publication"
                    else f"publication-input:{state.get('evaluation_run_id')}"
                )
                proposal_state = previous.state if previous else None
                case = await ensure_case(
                    session,
                    run,
                    key_suffix=suffix,
                    category=(
                        "stale_approval"
                        if proposal_state in {"stale", "expired"}
                        else "unresolved_input"
                    ),
                    severity="high",
                    resources=[
                        {
                            "type": "action_proposal" if previous else "evaluation_run",
                            "id": str(previous.id) if previous else state.get("evaluation_run_id"),
                        }
                    ],
                    evidence={
                        "code": "PUBLICATION_PROPOSAL_REQUIRED",
                        "proposal_state": proposal_state,
                    },
                    next_action="Configure document requirements and submit an exact publication proposal.",
                )
                await _set_run(
                    session,
                    run,
                    status="waiting_input",
                    step="publication",
                    case_id=case.id,
                )
                pause_payload = {
                    "kind": "exception_case",
                    "case_id": str(case.id),
                    "category": case.category,
                    "next_action": case.proposed_next_action,
                }
    if pause_payload:
        interrupt(pause_payload)
    return result


async def communication_node(state: WorkflowState) -> WorkflowState:
    pause_payload = None
    result: WorkflowState = {}
    async with async_session_maker() as session:
        run, drive = await _load(session, state)
        await _pause_for_hold(state, run, drive, session)
        previous = (
            await session.get(ActionProposal, run.pending_proposal_id)
            if run.pending_proposal_id
            else None
        )
        if (
            previous
            and previous.action_type == "send_communication"
            and previous.state
            in {
                "rejected",
                "revision_requested",
                "stale",
                "expired",
            }
        ):
            case = await ensure_case(
                session,
                run,
                key_suffix=f"communication-proposal:{previous.id}:{previous.state}",
                category="stale_approval"
                if previous.state in {"stale", "expired"}
                else "unresolved_input",
                severity="high",
                resources=[{"type": "action_proposal", "id": str(previous.id)}],
                evidence={"proposal_state": previous.state},
                next_action="Revise the frozen draft or audience and submit a new exact proposal.",
            )
            await _set_run(
                session, run, status="waiting_input", step="communication", case_id=case.id
            )
            pause_payload = {
                "kind": "exception_case",
                "case_id": str(case.id),
                "category": case.category,
                "next_action": case.proposed_next_action,
            }
            proposal = None
            batch = None
        else:
            proposal, batch = await ensure_announcement_proposal(session, run, drive)
        if pause_payload:
            pass
        elif proposal and proposal.state == "approved" and batch:
            await _set_run(
                session,
                run,
                status="monitoring",
                step="monitoring",
                references={"communication_proposal_id": str(proposal.id)},
            )
            result = _mark_command(
                {
                    "communication_proposal_id": str(proposal.id),
                    "current_step": "monitoring",
                    "pending_proposal_id": None,
                },
                state,
            )
        else:
            assert proposal is not None
            await _set_run(
                session,
                run,
                status="waiting_communication_approval",
                step="communication",
                references={"communication_proposal_id": str(proposal.id)},
                proposal_id=proposal.id,
            )
            pause_payload = {
                "kind": "proposal_decision",
                "proposal_id": str(proposal.id),
                "action_type": proposal.action_type,
                "canonical_hash": proposal.canonical_hash,
            }
    if pause_payload:
        interrupt(pause_payload)
    return result


async def monitoring_node(state: WorkflowState) -> WorkflowState:
    async with async_session_maker() as session:
        run, drive = await _load(session, state)
        await _pause_for_hold(state, run, drive, session)
        await _set_run(session, run, status="monitoring", step="monitoring")
    resume = interrupt(
        {
            "kind": "monitoring",
            "workflow_run_id": state["workflow_run_id"],
            "accepted_events": [
                "registration_changed",
                "document_changed",
                "policy_changed",
                "deadline_reached",
                "dispatch_changed",
            ],
        }
    )
    if not isinstance(resume, dict) or resume.get("reference_type") != "event":
        raise RuntimeError("Monitoring resume requires a persisted workflow event")
    event_id = uuid.UUID(str(resume["reference_id"]))
    async with async_session_maker() as session:
        run, _drive = await _load(session, state)
        event = (
            await session.execute(
                select(WorkflowEvent).where(
                    WorkflowEvent.id == event_id,
                    WorkflowEvent.workflow_run_id == run.id,
                    WorkflowEvent.institution_id == run.institution_id,
                )
            )
        ).scalar_one()
        if event.status == "pending":
            result = {"handler": "bounded_monitoring_handler", "replayed_intake": False}
            if event.event_type == "dispatch_changed":
                unknown_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(DispatchOperation)
                        .where(
                            DispatchOperation.drive_id == run.drive_id,
                            DispatchOperation.status == "unknown",
                        )
                    )
                    or 0
                )
                if unknown_count:
                    case = await ensure_case(
                        session,
                        run,
                        key_suffix=f"dispatch-unknown:{event.id}",
                        category="delivery_uncertainty",
                        severity="high",
                        resources=[{"type": "drive", "id": str(run.drive_id)}],
                        evidence={"unknown_operation_count": unknown_count},
                        next_action="Reconcile each unknown provider outcome before any resend.",
                    )
                    result["exception_case_id"] = str(case.id)
            result["event_type"] = event.event_type
            result["scope"] = {
                "registration_changed": "registration_projection",
                "document_changed": "document_readiness_projection",
                "policy_changed": "policy_freshness_check",
                "deadline_reached": "deadline_action_review",
                "dispatch_changed": "dispatch_reconciliation",
            }[event.event_type]
            event.status = "processed"
            event.processed_at = datetime.now(UTC)
            event.processing_result = result
        run.last_event_id = event.id
        run.concurrency_revision += 1
        await session.commit()
    return _mark_command(
        {
            "current_step": "monitoring",
            "processed_event_id": str(event_id),
        },
        state,
    )


def route_step(state: WorkflowState) -> str:
    return state.get("current_step", "intake")


def build_drive_workflow(checkpointer):
    builder = StateGraph(WorkflowState)
    builder.add_node("intake", intake_node)
    builder.add_node("policy", policy_node)
    builder.add_node("evaluation", evaluation_node)
    builder.add_node("publication", publication_node)
    builder.add_node("communication", communication_node)
    builder.add_node("monitoring", monitoring_node)
    builder.add_edge(START, "intake")
    builder.add_conditional_edges("intake", route_step, {"policy": "policy", "intake": "intake"})
    builder.add_conditional_edges(
        "policy", route_step, {"evaluation": "evaluation", "policy": "policy"}
    )
    builder.add_conditional_edges("evaluation", route_step, {"publication": "publication"})
    builder.add_conditional_edges(
        "publication",
        route_step,
        {"communication": "communication", "publication": "publication"},
    )
    builder.add_conditional_edges(
        "communication",
        route_step,
        {"monitoring": "monitoring", "communication": "communication"},
    )
    builder.add_edge("monitoring", "monitoring")
    return builder.compile(checkpointer=checkpointer)
