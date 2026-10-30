"""P08 durable pause/resume, restart, event deduplication, and hold tests."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.test_communications_dispatch import _create_proposal, _publish_drive
from tests.integration.test_participation import _setup_evaluated_drive

from placementos.models.intelligence import ClarificationTask
from placementos.models.workflow import WorkflowCommand, WorkflowEvent, WorkflowRun
from placementos.services.source_jobs import SourceJobService
from placementos.services.workflows import execute_workflow_command


async def _start_completed_source_workflow(
    client: AsyncClient, admin_session: AsyncSession, monkeypatch
) -> tuple[dict[str, str], dict, WorkflowCommand]:
    context = await _setup_evaluated_drive(client, monkeypatch)
    await _publish_drive(client, context)
    proposal = await _create_proposal(client, context)
    approval = await client.post(
        f"/api/v1/communication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approval.status_code == 200
    started = await client.post(
        f"/api/v1/drives/{context['drive_id']}/workflow-runs", json={}
    )
    assert started.status_code == 201, started.text
    body = started.json()
    assert "thread_id" not in body
    command = (
        await admin_session.execute(
            select(WorkflowCommand).where(
                WorkflowCommand.workflow_run_id == uuid.UUID(body["id"]),
                WorkflowCommand.command_type == "start",
            )
        )
    ).scalar_one()
    return context, body, command


@pytest.mark.asyncio
async def test_fresh_intake_pauses_and_resumes_from_persisted_human_decisions(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    from placementos.workers.source_tasks import extract_source_text_task

    monkeypatch.setattr(extract_source_text_task, "delay", lambda *args, **kwargs: None)
    suffix = uuid.uuid4().hex[:8]
    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    institution_id = login.json()["user"]["institution_id"]
    company = await client.post("/api/v1/companies", json={"name": f"P08-{suffix}"})
    drive = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2026-2027",
            "title": "P08 Durable Workflow Engineer",
        },
    )
    source = await client.post(
        f"/api/v1/drives/{drive.json()['id']}/sources/pasted",
        json={
            "title": "P08 workflow source",
            "raw_text": (
                "Role: Engineer. CSE 2027 students need CGPA 7.50/10 and no active "
                "backlogs. Registration deadline: 2026-11-05. CTC: 12 LPA."
            ),
        },
    )
    await SourceJobService.run_extraction(
        uuid.UUID(source.json()["id"]), uuid.UUID(institution_id)
    )
    started = await client.post(
        f"/api/v1/drives/{drive.json()['id']}/workflow-runs",
        json={"source_artifact_id": source.json()["id"]},
    )
    assert started.status_code == 201
    run_id = uuid.UUID(started.json()["id"])
    start_command = (
        await admin_db_session.execute(
            select(WorkflowCommand).where(
                WorkflowCommand.workflow_run_id == run_id,
                WorkflowCommand.command_type == "start",
            )
        )
    ).scalar_one()
    assert (
        await execute_workflow_command(start_command.id, uuid.UUID(institution_id))
        == "processed"
    )
    paused = (await client.get(f"/api/v1/workflow-runs/{run_id}")).json()
    assert paused["status"] == "waiting_clarification"
    policy_pause = paused
    for _ in range(5):
        if policy_pause["status"] != "waiting_clarification":
            break
        clarification_id = policy_pause["pending_clarification_id"]
        task = await admin_db_session.get(ClarificationTask, uuid.UUID(clarification_id))
        assert task is not None
        resolution_values = {
            "eligibility_draft.allowed_branches": ["CSE"],
            "eligibility_draft.minimum_cgpa": "7.50",
            "eligibility_draft.graduation_years": [2027],
            "eligibility_draft.maximum_active_backlogs": 0,
            "registration_deadline.confirmed_instant": "2026-11-05T17:00:00+05:30",
        }
        resolved = await client.post(
            f"/api/v1/clarifications/{clarification_id}/resolve",
            json={
                "value": resolution_values[task.field_path],
                "rationale": "Coordinator confirmed the required source fact",
            },
        )
        assert resolved.status_code == 200
        clarification_command = (
            await admin_db_session.execute(
                select(WorkflowCommand).where(
                    WorkflowCommand.workflow_run_id == run_id,
                    WorkflowCommand.reference_type == "clarification",
                    WorkflowCommand.reference_id == uuid.UUID(clarification_id),
                )
            )
        ).scalar_one()
        assert (
            await execute_workflow_command(
                clarification_command.id, uuid.UUID(institution_id)
            )
            == "processed"
        )
        policy_pause = (await client.get(f"/api/v1/workflow-runs/{run_id}")).json()
    assert policy_pause["status"] == "waiting_policy_approval"
    proposal = await client.get(f"/api/v1/proposals/{policy_pause['pending_proposal_id']}")
    approved = await client.post(
        f"/api/v1/proposals/{proposal.json()['id']}/decisions",
        json={
            "expected_revision": proposal.json()["revision_number"],
            "expected_hash": proposal.json()["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200
    decision_command = (
        (
            await admin_db_session.execute(
                select(WorkflowCommand)
                .where(
                    WorkflowCommand.workflow_run_id == run_id,
                    WorkflowCommand.reference_type == "decision",
                )
                .order_by(WorkflowCommand.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .one()
    )
    assert (
        await execute_workflow_command(decision_command.id, uuid.UUID(institution_id))
        == "processed"
    )
    publication_pause = (await client.get(f"/api/v1/workflow-runs/{run_id}")).json()
    assert publication_pause["current_step"] == "publication"
    assert publication_pause["status"] == "waiting_input"
    assert publication_pause["pending_case_id"] is not None


@pytest.mark.asyncio
async def test_workflow_reaches_monitoring_and_resumes_persisted_event_once(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context, started, start_command = await _start_completed_source_workflow(
        client, admin_db_session, monkeypatch
    )
    outcome = await execute_workflow_command(
        start_command.id, uuid.UUID(context["institution_id"])
    )
    assert outcome == "processed"
    current = await client.get(f"/api/v1/workflow-runs/{started['id']}")
    assert current.status_code == 200
    assert current.json()["status"] == "monitoring"
    assert current.json()["current_step"] == "monitoring"

    event_payload = {
        "event_key": f"document:{uuid.uuid4()}:revision:2",
        "event_type": "document_changed",
        "resource_type": "student_document",
        "resource_id": str(uuid.uuid4()),
        "resource_revision": "2",
        "payload": {"document_id": str(uuid.uuid4())},
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    submitted = await client.post(
        f"/api/v1/workflow-runs/{started['id']}/events", json=event_payload
    )
    assert submitted.status_code == 202, submitted.text
    duplicate = await client.post(
        f"/api/v1/workflow-runs/{started['id']}/events", json=event_payload
    )
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == submitted.json()["id"]
    assert duplicate.json()["created"] is False
    later = await client.post(
        f"/api/v1/workflow-runs/{started['id']}/events",
        json={
            **event_payload,
            "event_key": f"registration:{uuid.uuid4()}",
            "event_type": "registration_changed",
            "resource_type": "registration",
            "resource_id": str(uuid.uuid4()),
        },
    )
    assert later.status_code == 202

    event_command = await admin_db_session.get(
        WorkflowCommand, uuid.UUID(submitted.json()["command_id"])
    )
    assert event_command is not None
    event_command_id = event_command.id
    first = await execute_workflow_command(
        event_command_id, uuid.UUID(context["institution_id"])
    )
    # Simulate a worker crash after the checkpoint/domain event commit but before
    # command finalization. Reclaiming the stale command must not repeat the handler.
    admin_db_session.expire_all()
    recovery_command = await admin_db_session.get(WorkflowCommand, event_command_id)
    assert recovery_command is not None
    recovery_command.status = "claimed"
    recovery_command.processed_at = None
    recovery_command.updated_at = datetime.now(UTC) - timedelta(minutes=2)
    recovery_command.result = {}
    await admin_db_session.commit()
    second = await execute_workflow_command(
        event_command_id, uuid.UUID(context["institution_id"])
    )
    assert first == second == "processed"
    assert (
        await execute_workflow_command(
            uuid.UUID(later.json()["command_id"]), uuid.UUID(context["institution_id"])
        )
        == "processed"
    )
    admin_db_session.expire_all()
    event = await admin_db_session.get(WorkflowEvent, uuid.UUID(submitted.json()["id"]))
    assert event is not None
    assert event.status == "processed"
    assert event.processing_result["scope"] == "document_readiness_projection"
    assert event.processing_result["replayed_intake"] is False


@pytest.mark.asyncio
async def test_operational_hold_preserves_event_until_release_and_cross_tenant_is_hidden(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context, started, start_command = await _start_completed_source_workflow(
        client, admin_db_session, monkeypatch
    )
    await execute_workflow_command(start_command.id, uuid.UUID(context["institution_id"]))
    current = (await client.get(f"/api/v1/workflow-runs/{started['id']}")).json()
    held = await client.post(
        f"/api/v1/workflow-runs/{started['id']}/hold",
        json={
            "reason": "Coordinator is verifying a source correction",
            "expected_run_revision": current["concurrency_revision"],
        },
    )
    assert held.status_code == 200
    event = await client.post(
        f"/api/v1/workflow-runs/{started['id']}/events",
        json={
            "event_key": f"registration:{uuid.uuid4()}",
            "event_type": "registration_changed",
            "resource_type": "registration",
            "resource_id": str(uuid.uuid4()),
            "payload": {},
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    assert event.status_code == 202
    command_id = uuid.UUID(event.json()["command_id"])
    assert (
        await execute_workflow_command(command_id, uuid.UUID(context["institution_id"]))
        == "held"
    )
    release = await client.post(
        f"/api/v1/workflow-runs/{started['id']}/release-hold",
        json={
            "reason": "Source correction verified",
            "expected_run_revision": held.json()["concurrency_revision"],
        },
    )
    assert release.status_code == 200
    assert (
        await execute_workflow_command(command_id, uuid.UUID(context["institution_id"]))
        == "processed"
    )

    beacon = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_beacon"})
    assert beacon.status_code == 200
    hidden = await client.get(f"/api/v1/workflow-runs/{started['id']}")
    assert hidden.status_code == 404


@pytest.mark.asyncio
async def test_incompatible_graph_version_opens_case_instead_of_blind_resume(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context, started, start_command = await _start_completed_source_workflow(
        client, admin_db_session, monkeypatch
    )
    run = await admin_db_session.get(WorkflowRun, uuid.UUID(started["id"]))
    assert run is not None
    run_id = run.id
    run.graph_version = "drive-lifecycle-v0"
    await admin_db_session.commit()
    result = await execute_workflow_command(
        start_command.id, uuid.UUID(context["institution_id"])
    )
    assert result == "incompatible"
    admin_db_session.expire_all()
    incompatible = await admin_db_session.get(WorkflowRun, run_id)
    assert incompatible is not None
    assert incompatible.status == "incompatible"
    assert incompatible.error_category == "incompatible_workflow_version"
    assert incompatible.pending_case_id is not None
