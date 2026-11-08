"""Unit tests for Phase 17 LangGraph production workflow state, routing, and guards."""

import uuid
from datetime import UTC, datetime

import pytest

from placementos.models.workflow import WorkflowRun
from placementos.schemas.workflow import WorkflowEventCreate
from placementos.services.workflows import (
    COMPATIBLE_GRAPH_VERSIONS,
    GRAPH_VERSION,
    STATE_SCHEMA_VERSION,
    _new_command,
)
from placementos.workflows.drive_lifecycle import initial_state, route_step


def test_initial_workflow_state_is_minimized_and_omits_secrets():
    """P17-T01 & P17-T07: Asserts graph state contains only IDs and minimal references."""
    institution_id = uuid.uuid4()
    drive_id = uuid.uuid4()
    artifact_id = uuid.uuid4()

    run = WorkflowRun(
        id=uuid.uuid4(),
        institution_id=institution_id,
        drive_id=drive_id,
        thread_id=uuid.uuid4(),
        graph_version=GRAPH_VERSION,
        state_schema_version=STATE_SCHEMA_VERSION,
        status="queued",
        current_step="intake",
        concurrency_revision=1,
    )

    state = initial_state(run, source_artifact_id=artifact_id)

    # Asserts exact state structure
    assert state["institution_id"] == str(institution_id)
    assert state["drive_id"] == str(drive_id)
    assert state["workflow_run_id"] == str(run.id)
    assert state["source_artifact_id"] == str(artifact_id)
    assert state["graph_version"] == GRAPH_VERSION
    assert state["state_schema_version"] == STATE_SCHEMA_VERSION
    assert state["current_step"] == "intake"

    # Strict privacy check: No prompts, tokens, or PII keys in state
    forbidden_keys = {"prompt", "secret", "api_key", "student", "password", "token"}
    for key in state:
        assert not any(forbidden in key.lower() for forbidden in forbidden_keys)


def test_route_step_determines_correct_next_node():
    """P17-T02: Asserts conditional edge routing transitions."""
    assert route_step({"current_step": "intake"}) == "intake"
    assert route_step({"current_step": "policy"}) == "policy"
    assert route_step({"current_step": "evaluation"}) == "evaluation"
    assert route_step({"current_step": "publication"}) == "publication"
    assert route_step({"current_step": "communication"}) == "communication"
    assert route_step({"current_step": "monitoring"}) == "monitoring"
    assert route_step({}) == "intake"


def test_graph_versions_and_compatibility():
    """P17-T06: Asserts active graph version is allowlisted in compatible versions."""
    assert GRAPH_VERSION in COMPATIBLE_GRAPH_VERSIONS
    assert STATE_SCHEMA_VERSION >= 1


def test_new_command_preserves_expected_revision_and_status():
    """P17-T04: Asserts commands bind to exact expected run revision."""
    run = WorkflowRun(
        id=uuid.uuid4(),
        institution_id=uuid.uuid4(),
        drive_id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        graph_version=GRAPH_VERSION,
        state_schema_version=STATE_SCHEMA_VERSION,
        status="running",
        current_step="policy",
        concurrency_revision=5,
    )
    actor_id = uuid.uuid4()
    cmd = _new_command(
        run,
        requested_by_membership_id=actor_id,
        command_type="resume",
        command_key=f"workflow:{run.id}:resume:decision:123",
        reference_type="decision",
        reference_id=uuid.uuid4(),
    )

    assert cmd.expected_run_revision == 5
    assert cmd.status == "pending"
    assert cmd.publish_attempts == 0
    assert cmd.requested_by_membership_id == actor_id
    assert cmd.reference_type == "decision"


def test_workflow_event_payload_rejects_sensitive_keys():
    """P17-T07: Validates that event payloads reject sensitive tokens or secrets."""
    # Rejection of secret key
    with pytest.raises(ValueError) as exc:
        WorkflowEventCreate(
            event_key="evt:test:1",
            event_type="document_changed",
            resource_type="student_document",
            resource_id=uuid.uuid4(),
            payload={"secret_token": "abc123xyz"},
            occurred_at=datetime.now(UTC),
        )
    assert "prohibited sensitive field" in str(exc.value)

    # Rejection of missing timezone
    with pytest.raises(ValueError) as exc_tz:
        WorkflowEventCreate(
            event_key="evt:test:2",
            event_type="document_changed",
            resource_type="student_document",
            resource_id=uuid.uuid4(),
            payload={"doc_id": "123"},
            occurred_at=datetime.now(),  # Naive datetime
        )
    assert "timezone" in str(exc_tz.value)


@pytest.mark.asyncio
async def test_intake_node_handles_model_failure_with_exception_case(monkeypatch):
    """P17-T05: Asserts provider exception is captured in exception case rather than crashing."""
    from unittest.mock import AsyncMock, MagicMock

    from placementos.workflows.drive_lifecycle import intake_node

    run_mock = MagicMock(id=uuid.uuid4(), institution_id=uuid.uuid4(), drive_id=uuid.uuid4(), state_references={})
    drive_mock = MagicMock(id=run_mock.drive_id, operational_hold=False)
    artifact_mock = MagicMock(id=uuid.uuid4())
    extraction_mock = MagicMock(id=uuid.uuid4())
    case_mock = MagicMock(id=uuid.uuid4(), category="ai_model_failure", proposed_next_action="Retry")

    monkeypatch.setattr("placementos.workflows.drive_lifecycle._load", AsyncMock(return_value=(run_mock, drive_mock)))
    monkeypatch.setattr("placementos.workflows.drive_lifecycle._pause_for_hold", AsyncMock())
    monkeypatch.setattr("placementos.workflows.drive_lifecycle.ensure_source_and_extraction", AsyncMock(return_value=(artifact_mock, extraction_mock, None)))
    monkeypatch.setattr("placementos.workflows.drive_lifecycle.ensure_interpretation", AsyncMock(side_effect=RuntimeError("AI Model 503 Overloaded")))
    monkeypatch.setattr("placementos.workflows.drive_lifecycle.ensure_case", AsyncMock(return_value=case_mock))
    monkeypatch.setattr("placementos.workflows.drive_lifecycle._set_run", AsyncMock())

    interrupted_payload = None
    def mock_interrupt(payload):
        nonlocal interrupted_payload
        interrupted_payload = payload

    monkeypatch.setattr("placementos.workflows.drive_lifecycle.interrupt", mock_interrupt)

    state = {
        "institution_id": str(run_mock.institution_id),
        "drive_id": str(run_mock.drive_id),
        "workflow_run_id": str(run_mock.id),
        "graph_version": GRAPH_VERSION,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "source_artifact_id": str(artifact_mock.id),
        "current_step": "intake",
    }

    await intake_node(state)
    assert interrupted_payload is not None
    assert interrupted_payload["kind"] == "exception_case"
    assert interrupted_payload["category"] == "ai_model_failure"
    assert str(case_mock.id) == interrupted_payload["case_id"]

