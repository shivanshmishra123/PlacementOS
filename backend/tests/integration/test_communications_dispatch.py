"""P07 exact approval, transactional outbox, deduplication, and uncertainty tests."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.test_participation import _setup_evaluated_drive

from placementos.models.communications import DispatchBatch, DispatchOperation, OutboxEvent
from placementos.models.eligibility import EvaluationRun
from placementos.services.dispatch import execute_dispatch_operation, relay_pending_outbox
from placementos.services.mail import EmailAdapter, ProviderOutcome


class CountingAcceptedAdapter(EmailAdapter):
    adapter_id = "counting-accepted-v1"

    def __init__(self) -> None:
        self.calls = 0

    def send(self, message):
        self.calls += 1
        return ProviderOutcome(
            status="provider_accepted",
            provider_message_id=f"test:{message.operation_key}",
            evidence={"fixture": "accepted"},
        )


class UnknownAdapter(EmailAdapter):
    adapter_id = "unknown-outcome-v1"

    def send(self, message):
        return ProviderOutcome(
            status="unknown",
            error_code="PROVIDER_OUTCOME_UNKNOWN",
            error_detail="Fixture timeout after possible acceptance",
        )


async def _publish_drive(client: AsyncClient, context: dict[str, str]) -> None:
    requirements = await client.put(
        f"/api/v1/drives/{context['drive_id']}/document-requirements",
        json={
            "expected_drive_revision": 1,
            "requirements": [
                {
                    "document_type": "resume",
                    "display_label": "Resume",
                    "allowed_extensions": ["pdf", "docx"],
                    "required_stage": "registration",
                }
            ],
        },
    )
    assert requirements.status_code == 200
    now = datetime.now(UTC)
    proposal = await client.post(
        f"/api/v1/drives/{context['drive_id']}/publication-proposals",
        json={
            "expected_drive_revision": 1,
            "evaluation_run_id": context["run_id"],
            "registration_start_at": (now - timedelta(minutes=1)).isoformat(),
            "registration_end_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    assert proposal.status_code == 201
    approved = await client.post(
        f"/api/v1/publication-proposals/{proposal.json()['id']}/decisions",
        json={
            "expected_revision": proposal.json()["revision_number"],
            "expected_hash": proposal.json()["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200


async def _create_proposal(
    client: AsyncClient,
    context: dict[str, str],
    *,
    kind: str = "drive_announcement",
) -> dict:
    participants = await client.get(f"/api/v1/drives/{context['drive_id']}/participants")
    assert participants.status_code == 200
    student_id = next(
        item["student_profile_id"]
        for item in participants.json()["items"]
        if item["student_identifier"] == context["student_identifier"]
    )
    draft = await client.post(
        f"/api/v1/drives/{context['drive_id']}/communication-drafts",
        json={
            "communication_kind": kind,
            "audience_type": "explicit_recipients",
            "explicit_student_ids": [student_id],
            "reply_to": "placements@apex.edu",
        },
    )
    assert draft.status_code == 201, draft.text
    body = draft.json()
    assert body["included_count"] == 1
    assert body["duplicate_count"] == 0
    assert body["recipients"][0]["email"] == context["student_email"]
    submitted = await client.post(
        f"/api/v1/communication-drafts/{body['id']}/submit-review",
        json={"execution_expires_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat()},
    )
    assert submitted.status_code == 201, submitted.text
    return submitted.json()


@pytest.mark.asyncio
async def test_exact_approval_creates_outbox_and_duplicate_execution_sends_once(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_evaluated_drive(client, monkeypatch)
    await _publish_drive(client, context)
    proposal = await _create_proposal(client, context)

    stale = await client.post(
        f"/api/v1/communication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": "0" * 64,
            "decision": "approved",
        },
    )
    assert stale.status_code == 409
    approved = await client.post(
        f"/api/v1/communication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["state"] == "approved"
    duplicate_decision = await client.post(
        f"/api/v1/communication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "approved",
        },
    )
    assert duplicate_decision.status_code == 409

    batch = (
        await admin_db_session.execute(
            select(DispatchBatch).where(DispatchBatch.proposal_id == uuid.UUID(proposal["id"]))
        )
    ).scalar_one()
    operation = (
        await admin_db_session.execute(
            select(DispatchOperation).where(DispatchOperation.dispatch_batch_id == batch.id)
        )
    ).scalar_one()
    outbox = (
        await admin_db_session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == operation.id)
        )
    ).scalar_one()
    assert outbox.status == "pending"

    from placementos.workers.dispatch_tasks import dispatch_operation_task

    def broker_down(*args, **kwargs):
        raise RuntimeError("fixture broker unavailable")

    monkeypatch.setattr(dispatch_operation_task, "delay", broker_down)
    await relay_pending_outbox()
    await admin_db_session.refresh(outbox)
    assert outbox.status == "pending"
    assert "broker unavailable" in (outbox.last_error or "")
    outbox.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    await admin_db_session.commit()

    monkeypatch.setattr(dispatch_operation_task, "delay", lambda *args, **kwargs: None)
    await relay_pending_outbox()
    await admin_db_session.refresh(outbox)
    assert outbox.status == "published"

    adapter = CountingAcceptedAdapter()
    first = await execute_dispatch_operation(
        operation.id, uuid.UUID(context["institution_id"]), adapter=adapter
    )
    second = await execute_dispatch_operation(
        operation.id, uuid.UUID(context["institution_id"]), adapter=adapter
    )
    assert first == second == "provider_accepted"
    assert adapter.calls == 1


@pytest.mark.asyncio
async def test_mailpit_receives_one_exact_message_and_timeout_requires_reconciliation(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_evaluated_drive(client, monkeypatch)
    await _publish_drive(client, context)
    proposal = await _create_proposal(client, context)
    approved = await client.post(
        f"/api/v1/communication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200
    batch = (
        await admin_db_session.execute(
            select(DispatchBatch).where(DispatchBatch.proposal_id == uuid.UUID(proposal["id"]))
        )
    ).scalar_one()
    operation = (
        await admin_db_session.execute(
            select(DispatchOperation).where(DispatchOperation.dispatch_batch_id == batch.id)
        )
    ).scalar_one()
    result = await execute_dispatch_operation(operation.id, uuid.UUID(context["institution_id"]))
    repeated = await execute_dispatch_operation(operation.id, uuid.UUID(context["institution_id"]))
    assert result == repeated == "provider_accepted"
    await admin_db_session.refresh(operation)
    async with httpx.AsyncClient() as external:
        messages = (await external.get("http://127.0.0.1:8025/api/v1/messages")).json()["messages"]
    matching = [
        item
        for item in messages
        if item.get("MessageID") == (operation.provider_message_id or "").strip("<>")
    ]
    assert len(matching) == 1

    uncertain_proposal = await _create_proposal(client, context, kind="clarification")
    uncertain_approval = await client.post(
        f"/api/v1/communication-proposals/{uncertain_proposal['id']}/decisions",
        json={
            "expected_revision": uncertain_proposal["revision_number"],
            "expected_hash": uncertain_proposal["canonical_hash"],
            "decision": "approved",
        },
    )
    assert uncertain_approval.status_code == 200
    uncertain_batch = (
        await admin_db_session.execute(
            select(DispatchBatch).where(
                DispatchBatch.proposal_id == uuid.UUID(uncertain_proposal["id"])
            )
        )
    ).scalar_one()
    uncertain_operation = (
        await admin_db_session.execute(
            select(DispatchOperation).where(
                DispatchOperation.dispatch_batch_id == uncertain_batch.id
            )
        )
    ).scalar_one()
    uncertain = await execute_dispatch_operation(
        uncertain_operation.id,
        uuid.UUID(context["institution_id"]),
        adapter=UnknownAdapter(),
    )
    assert uncertain == "unknown"
    reconciliation = await client.post(
        f"/api/v1/dispatch-operations/{uncertain_operation.id}/reconcile",
        json={
            "resolution": "confirmed_not_accepted",
            "evidence": "Provider support confirmed that the SMTP transaction was not accepted",
        },
    )
    assert reconciliation.status_code == 200, reconciliation.text
    assert reconciliation.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_rejected_proposal_has_no_dispatch_intent(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_evaluated_drive(client, monkeypatch)
    await _publish_drive(client, context)
    proposal = await _create_proposal(client, context)
    rejected = await client.post(
        f"/api/v1/communication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "rejected",
        },
    )
    assert rejected.status_code == 200
    batch = (
        await admin_db_session.execute(
            select(DispatchBatch).where(DispatchBatch.proposal_id == uuid.UUID(proposal["id"]))
        )
    ).scalar_one_or_none()
    assert batch is None


@pytest.mark.asyncio
async def test_stale_evaluation_stops_an_unclaimed_approved_operation(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_evaluated_drive(client, monkeypatch)
    await _publish_drive(client, context)
    proposal = await _create_proposal(client, context)
    approved = await client.post(
        f"/api/v1/communication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200
    batch = (
        await admin_db_session.execute(
            select(DispatchBatch).where(DispatchBatch.proposal_id == uuid.UUID(proposal["id"]))
        )
    ).scalar_one()
    operation = (
        await admin_db_session.execute(
            select(DispatchOperation).where(DispatchOperation.dispatch_batch_id == batch.id)
        )
    ).scalar_one()
    evaluation = await admin_db_session.get(EvaluationRun, uuid.UUID(context["run_id"]))
    assert evaluation is not None
    evaluation.is_stale = True
    evaluation.stale_reason = "Fixture academic evidence revision"
    await admin_db_session.commit()

    adapter = CountingAcceptedAdapter()
    result = await execute_dispatch_operation(
        operation.id, uuid.UUID(context["institution_id"]), adapter=adapter
    )
    assert result == "cancelled"
    assert adapter.calls == 0
