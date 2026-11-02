"""P12 deterministic exception impact and bounded recovery acceptance tests."""

import copy
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.test_communications_dispatch import (
    CountingAcceptedAdapter,
    UnknownAdapter,
    _create_proposal,
    _publish_drive,
)
from tests.integration.test_participation import _setup_evaluated_drive

from placementos.models.academic import AcademicRecordRevision
from placementos.models.communications import DispatchBatch, DispatchOperation
from placementos.models.identity import Membership, StudentProfile, User
from placementos.models.intelligence import ActionProposal, EligibilityPolicyVersion
from placementos.models.participation import Registration
from placementos.models.recovery import RecoveryPlan, RecoveryPlanStep
from placementos.models.recruitment import Drive, DriveRevision
from placementos.models.workflow import ExceptionCase
from placementos.services.dispatch import execute_dispatch_operation
from placementos.services.eligibility_engine import canonical_hash
from placementos.services.eligibility_runs import EligibilityRunService
from placementos.services.recovery import execute_recovery_plan
from placementos.services.source_jobs import SourceJobService


async def _coordinator_membership(session: AsyncSession, institution_id: uuid.UUID) -> Membership:
    return (
        await session.execute(
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.institution_id == institution_id,
                User.email == "priya.sharma@apex.edu",
            )
        )
    ).scalar_one()


async def _open_case(
    session: AsyncSession,
    *,
    institution_id: uuid.UUID,
    drive_id: uuid.UUID,
    owner_id: uuid.UUID,
    category: str,
) -> ExceptionCase:
    item = ExceptionCase(
        institution_id=institution_id,
        drive_id=drive_id,
        case_key=f"p12:{category}:{uuid.uuid4()}",
        category=category,
        severity="high",
        status="open",
        affected_resources=[],
        evidence={"fixture": "synthetic-p12"},
        proposed_next_action="Run deterministic impact analysis",
        owner_membership_id=owner_id,
        resolution_history=[],
    )
    session.add(item)
    await session.commit()
    return item


async def _setup_threshold_change(
    client: AsyncClient, session: AsyncSession, monkeypatch
) -> dict[str, object]:
    from placementos.workers.eligibility_tasks import evaluate_eligibility_task
    from placementos.workers.source_tasks import extract_source_text_task

    monkeypatch.setattr(extract_source_text_task, "delay", lambda *args, **kwargs: None)
    monkeypatch.setattr(evaluate_eligibility_task, "delay", lambda *args, **kwargs: None)
    suffix = uuid.uuid4().hex[:8]
    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    institution_id = uuid.UUID(login.json()["user"]["institution_id"])
    membership = await _coordinator_membership(session, institution_id)
    company = await client.post("/api/v1/companies", json={"name": f"P12-{suffix}"})
    drive_response = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2026-2027",
            "title": "P12 Criteria Recovery",
        },
    )
    drive_id = uuid.UUID(drive_response.json()["id"])
    source = await client.post(
        f"/api/v1/drives/{drive_id}/sources/pasted",
        json={
            "title": "P12 threshold source",
            "raw_text": (
                "Role: Engineer. CSE 2027 students need CGPA 7.50/10 and no active "
                "backlogs. Registration deadline: 2026-11-20. CTC: 12 LPA."
            ),
        },
    )
    await SourceJobService.run_extraction(uuid.UUID(source.json()["id"]), institution_id)
    interpretation = (
        await client.post(
            f"/api/v1/drives/{drive_id}/interpretations",
            json={"source_artifact_id": source.json()["id"], "mode": "fixture"},
        )
    ).json()
    resolutions = {
        "eligibility_draft.allowed_branches": ["CSE"],
        "eligibility_draft.minimum_cgpa": "7.50",
        "eligibility_draft.graduation_years": [2027],
        "eligibility_draft.maximum_active_backlogs": 0,
        "registration_deadline.confirmed_instant": "2026-11-20T17:00:00+05:30",
    }
    for clarification in interpretation["clarifications"]:
        await client.post(
            f"/api/v1/clarifications/{clarification['id']}/resolve",
            json={
                "value": resolutions[clarification["field_path"]],
                "rationale": "Synthetic P12 fixture confirmation",
            },
        )
    old_policy_response = await client.post(
        f"/api/v1/drives/{drive_id}/policies",
        json={"interpretation_id": interpretation["id"], "explicitly_not_required": []},
    )
    old_policy_body = old_policy_response.json()
    review = await client.post(f"/api/v1/policies/{old_policy_body['id']}/submit-review")
    approved = await client.post(
        f"/api/v1/proposals/{review.json()['id']}/decisions",
        json={
            "expected_revision": review.json()["revision_number"],
            "expected_hash": review.json()["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200
    csv_text = f"""student_identifier,full_name,email,branch,cgpa,scale,graduation_year,active_backlogs
P12-{suffix},P12 Student,p12-{suffix}@apex.edu,CSE,7.75,10.00,2027,0
"""
    preview = await client.post("/api/v1/students/import-preview", json={"csv_content": csv_text})
    assert (
        await client.post(
            "/api/v1/students/import-commit",
            json={"preview_token": preview.json()["preview_token"]},
        )
    ).status_code == 200
    old_run_response = await client.post(
        f"/api/v1/drives/{drive_id}/evaluations",
        json={"policy_id": old_policy_body["id"]},
    )
    old_run_id = uuid.UUID(old_run_response.json()["id"])
    assert (
        await EligibilityRunService.execute_run(old_run_id, institution_id)
    ).status == "completed"

    old_policy = await session.get(EligibilityPolicyVersion, uuid.UUID(old_policy_body["id"]))
    assert old_policy is not None
    new_payload = copy.deepcopy(old_policy.policy_payload)
    new_payload["cgpa"]["minimum"] = "8.00"
    new_policy = EligibilityPolicyVersion(
        institution_id=institution_id,
        drive_id=drive_id,
        interpretation_id=old_policy.interpretation_id,
        version_number=old_policy.version_number + 1,
        schema_version=1,
        engine_contract="eligibility-v1",
        status="approved",
        policy_payload=new_payload,
        human_summary="Minimum CGPA 8.00; remaining criteria unchanged",
        canonical_hash=canonical_hash(new_payload),
        created_by_membership_id=membership.id,
    )
    session.add(new_policy)
    await session.commit()
    new_run_response = await client.post(
        f"/api/v1/drives/{drive_id}/evaluations", json={"policy_id": str(new_policy.id)}
    )
    new_run_id = uuid.UUID(new_run_response.json()["id"])
    assert (
        await EligibilityRunService.execute_run(new_run_id, institution_id)
    ).status == "completed"
    profile = (
        await session.execute(
            select(StudentProfile).where(StudentProfile.student_identifier == f"P12-{suffix}")
        )
    ).scalar_one()
    registration = Registration(
        institution_id=institution_id,
        drive_id=drive_id,
        student_profile_id=profile.id,
        state="submitted",
        submitted_policy_id=old_policy.id,
        submitted_evaluation_run_id=old_run_id,
        submitted_at=datetime.now(UTC),
    )
    session.add(registration)
    pending = ActionProposal(
        institution_id=institution_id,
        drive_id=drive_id,
        action_type="fixture_pending_action",
        target_type="drive",
        target_id=drive_id,
        revision_number=1,
        payload={"fixture": True},
        dependencies={},
        canonical_hash=canonical_hash({"fixture": str(drive_id)}),
        state="pending_approval",
        requested_by_membership_id=membership.id,
    )
    session.add(pending)
    await session.commit()
    return {
        "institution_id": institution_id,
        "membership_id": membership.id,
        "drive_id": drive_id,
        "profile_id": profile.id,
        "old_run_id": old_run_id,
        "new_run_id": new_run_id,
        "pending_proposal_id": pending.id,
    }


@pytest.mark.asyncio
async def test_cgpa_750_to_800_impact_and_approved_plan_execute_once(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_threshold_change(client, admin_db_session, monkeypatch)
    case = await _open_case(
        admin_db_session,
        institution_id=context["institution_id"],
        drive_id=context["drive_id"],
        owner_id=context["membership_id"],
        category="criteria_change",
    )
    case_id = case.id
    impact = await client.post(
        f"/api/v1/exception-cases/{case_id}/impact-analyses",
        json={
            "category": "criteria_change",
            "old_evaluation_run_id": str(context["old_run_id"]),
            "new_evaluation_run_id": str(context["new_run_id"]),
        },
    )
    assert impact.status_code == 201, impact.text
    assert impact.json()["impact_summary"]["transition_counts"]["eligible_to_ineligible"] >= 1
    target = next(
        student
        for student in impact.json()["affected_students"]
        if student["student_profile_id"] == str(context["profile_id"])
    )
    assert (target["old_outcome"], target["new_outcome"]) == (
        "eligible",
        "ineligible",
    )
    assert impact.json()["impact_summary"]["submitted_registration_count"] == 1
    plan_response = await client.post(
        f"/api/v1/impact-analyses/{impact.json()['id']}/recovery-plans",
        json={
            "planner_mode": "fixture",
            "rationale": "Review the deterministic threshold-change impact",
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan = plan_response.json()
    assert [step["operation_type"] for step in plan["steps"]] == [
        "place_drive_hold",
        "stale_pending_proposals",
        "record_manual_followup",
    ]
    approved = await client.post(
        f"/api/v1/recovery-plans/{plan['id']}/decisions",
        json={
            "expected_revision": plan["revision_number"],
            "expected_hash": plan["approval_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200, approved.text
    execution_id = uuid.UUID(approved.json()["id"])
    first = await execute_recovery_plan(execution_id, context["institution_id"])
    second = await execute_recovery_plan(execution_id, context["institution_id"])
    assert first == second == "succeeded"
    admin_db_session.expire_all()
    drive = await admin_db_session.get(Drive, context["drive_id"])
    pending = await admin_db_session.get(ActionProposal, context["pending_proposal_id"])
    registration = (
        await admin_db_session.execute(
            select(Registration).where(Registration.drive_id == context["drive_id"])
        )
    ).scalar_one()
    current_case = await admin_db_session.get(ExceptionCase, case_id)
    assert drive and drive.operational_hold is True
    assert pending and pending.state == "stale"
    assert registration.state == "submitted"
    assert current_case and current_case.status == "acknowledged"


@pytest.mark.asyncio
async def test_queued_recovery_cancellation_preserves_unexecuted_state(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_threshold_change(client, admin_db_session, monkeypatch)
    case = await _open_case(
        admin_db_session,
        institution_id=context["institution_id"],
        drive_id=context["drive_id"],
        owner_id=context["membership_id"],
        category="criteria_change",
    )
    impact = await client.post(
        f"/api/v1/exception-cases/{case.id}/impact-analyses",
        json={
            "category": "criteria_change",
            "old_evaluation_run_id": str(context["old_run_id"]),
            "new_evaluation_run_id": str(context["new_run_id"]),
        },
    )
    plan_response = await client.post(
        f"/api/v1/impact-analyses/{impact.json()['id']}/recovery-plans",
        json={"planner_mode": "fixture", "rationale": "Cancellation safety fixture"},
    )
    superseded_plan = plan_response.json()
    reanalysis = await client.post(
        f"/api/v1/exception-cases/{case.id}/impact-analyses",
        json={
            "category": "criteria_change",
            "old_evaluation_run_id": str(context["old_run_id"]),
            "new_evaluation_run_id": str(context["new_run_id"]),
        },
    )
    stale_decision = await client.post(
        f"/api/v1/recovery-plans/{superseded_plan['id']}/decisions",
        json={
            "expected_revision": superseded_plan["revision_number"],
            "expected_hash": superseded_plan["approval_hash"],
            "decision": "approved",
        },
    )
    assert stale_decision.status_code == 409
    stale_plan = await client.get(f"/api/v1/recovery-plans/{superseded_plan['id']}")
    assert stale_plan.json()["status"] == "stale"
    assert {step["status"] for step in stale_plan.json()["steps"]} == {"stale"}
    plan_response = await client.post(
        f"/api/v1/impact-analyses/{reanalysis.json()['id']}/recovery-plans",
        json={"planner_mode": "fixture", "rationale": "Cancellation safety fixture"},
    )
    plan = plan_response.json()
    decision = await client.post(
        f"/api/v1/recovery-plans/{plan['id']}/decisions",
        json={
            "expected_revision": plan["revision_number"],
            "expected_hash": plan["approval_hash"],
            "decision": "approved",
        },
    )
    assert decision.status_code == 200
    execution_id = uuid.UUID(decision.json()["id"])
    cancelled = await client.post(
        f"/api/v1/recovery-executions/{execution_id}/cancel",
        json={"reason": "Coordinator stopped remaining steps before execution"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert await execute_recovery_plan(execution_id, context["institution_id"]) == "cancelled"
    admin_db_session.expire_all()
    drive = await admin_db_session.get(Drive, context["drive_id"])
    steps = (
        (
            await admin_db_session.execute(
                select(RecoveryPlanStep)
                .where(RecoveryPlanStep.plan_id == uuid.UUID(plan["id"]))
                .order_by(RecoveryPlanStep.step_number)
            )
        )
        .scalars()
        .all()
    )
    assert drive and drive.operational_hold is False
    assert {step.status for step in steps} == {"cancelled"}


@pytest.mark.asyncio
async def test_verified_academic_correction_changes_only_scoped_student(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_threshold_change(client, admin_db_session, monkeypatch)
    profile = await admin_db_session.get(StudentProfile, context["profile_id"])
    assert profile is not None
    old_revision_id = profile.current_academic_revision_id
    assert old_revision_id is not None
    new_revision = AcademicRecordRevision(
        institution_id=context["institution_id"],
        student_profile_id=profile.id,
        revision_number=2,
        source="correction_request",
        source_reference="synthetic-p12-correction",
        is_verified=True,
        verified_at=datetime.now(UTC),
        verified_by_membership_id=context["membership_id"],
        branch="CSE",
        cgpa=Decimal("8.10"),
        cgpa_scale=Decimal("10.00"),
        graduation_year=2027,
        active_backlogs=0,
    )
    admin_db_session.add(new_revision)
    await admin_db_session.flush()
    new_revision_id = new_revision.id
    profile.current_academic_revision_id = new_revision.id
    await admin_db_session.commit()
    policy = (
        await admin_db_session.execute(
            select(EligibilityPolicyVersion).where(
                EligibilityPolicyVersion.drive_id == context["drive_id"],
                EligibilityPolicyVersion.version_number == 2,
            )
        )
    ).scalar_one()
    run, _created = await EligibilityRunService.create_run(
        admin_db_session,
        institution_id=context["institution_id"],
        drive_id=context["drive_id"],
        policy=policy,
        created_by_membership_id=context["membership_id"],
    )
    await admin_db_session.commit()
    run_id = run.id
    assert (
        await EligibilityRunService.execute_run(run_id, context["institution_id"])
    ).status == "completed"
    case = await _open_case(
        admin_db_session,
        institution_id=context["institution_id"],
        drive_id=context["drive_id"],
        owner_id=context["membership_id"],
        category="academic_correction",
    )
    case_id = case.id
    response = await client.post(
        f"/api/v1/exception-cases/{case_id}/impact-analyses",
        json={
            "category": "academic_correction",
            "student_profile_id": str(profile.id),
            "old_academic_revision_id": str(old_revision_id),
            "new_academic_revision_id": str(new_revision_id),
            "old_evaluation_run_id": str(context["new_run_id"]),
            "new_evaluation_run_id": str(run_id),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["impact_summary"]["old_outcome"] == "ineligible"
    assert response.json()["impact_summary"]["new_outcome"] == "eligible"
    assert response.json()["impact_summary"]["registration_preserved"] is True
    assert len(response.json()["affected_students"]) == 1


@pytest.mark.asyncio
async def test_deadline_change_after_prior_revision_preserves_history(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_evaluated_drive(client, monkeypatch)
    await _publish_drive(client, context)
    communication = await _create_proposal(client, context)
    approved = await client.post(
        f"/api/v1/communication-proposals/{communication['id']}/decisions",
        json={
            "expected_revision": communication["revision_number"],
            "expected_hash": communication["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200
    operation = (
        await admin_db_session.execute(
            select(DispatchOperation)
            .join(DispatchBatch, DispatchBatch.id == DispatchOperation.dispatch_batch_id)
            .where(DispatchBatch.proposal_id == uuid.UUID(communication["id"]))
        )
    ).scalar_one()
    assert (
        await execute_dispatch_operation(
            operation.id,
            uuid.UUID(context["institution_id"]),
            adapter=CountingAcceptedAdapter(),
        )
        == "provider_accepted"
    )
    drive_id = uuid.UUID(context["drive_id"])
    institution_id = uuid.UUID(context["institution_id"])
    drive = await admin_db_session.get(Drive, drive_id)
    assert drive and drive.current_drive_revision_id
    base_revision = await admin_db_session.get(DriveRevision, drive.current_drive_revision_id)
    assert base_revision is not None
    assert base_revision.registration_end_at is not None
    membership = await _coordinator_membership(admin_db_session, institution_id)
    membership_id = membership.id
    old_revision_id = base_revision.id
    new_revision = DriveRevision(
        institution_id=institution_id,
        drive_id=drive.id,
        revision_number=base_revision.revision_number + 1,
        role_title=base_revision.role_title,
        employment_type=base_revision.employment_type,
        work_mode=base_revision.work_mode,
        registration_start_at=base_revision.registration_start_at,
        registration_end_at=datetime.now(UTC) + timedelta(days=4),
        created_by_membership_id=membership_id,
    )
    admin_db_session.add(new_revision)
    await admin_db_session.flush()
    new_revision_id = new_revision.id
    drive.current_drive_revision_id = new_revision.id
    await admin_db_session.commit()
    case = await _open_case(
        admin_db_session,
        institution_id=institution_id,
        drive_id=drive_id,
        owner_id=membership_id,
        category="deadline_schedule_change",
    )
    case_id = case.id
    response = await client.post(
        f"/api/v1/exception-cases/{case_id}/impact-analyses",
        json={
            "category": "deadline_schedule_change",
            "change_kind": "deadline",
            "old_revision_id": str(old_revision_id),
            "new_revision_id": str(new_revision_id),
        },
    )
    assert response.status_code == 201, response.text
    assert (
        response.json()["impact_summary"]["old_deadline"]
        != response.json()["impact_summary"]["new_deadline"]
    )
    assert response.json()["impact_summary"]["registration_preserved"] is True
    assert response.json()["impact_summary"]["notified_student_count"] == 1
    assert await admin_db_session.get(DriveRevision, old_revision_id) is not None
    plan_response = await client.post(
        f"/api/v1/impact-analyses/{response.json()['id']}/recovery-plans",
        json={
            "planner_mode": "fixture",
            "rationale": "Prepare a separately controlled deadline correction",
        },
    )
    plan = plan_response.json()
    assert [step["operation_type"] for step in plan["steps"]] == [
        "prepare_correction_draft",
        "record_manual_followup",
    ]
    decision = await client.post(
        f"/api/v1/recovery-plans/{plan['id']}/decisions",
        json={
            "expected_revision": plan["revision_number"],
            "expected_hash": plan["approval_hash"],
            "decision": "approved",
        },
    )
    assert decision.status_code == 200
    assert (
        await execute_recovery_plan(
            uuid.UUID(decision.json()["id"]),
            institution_id,
        )
        == "succeeded"
    )
    dispatches = (
        (
            await admin_db_session.execute(
                select(DispatchOperation).where(DispatchOperation.drive_id == drive_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(dispatches) == 1


@pytest.mark.asyncio
async def test_unknown_notification_manual_plan_stops_after_partial_failure(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_evaluated_drive(client, monkeypatch)
    await _publish_drive(client, context)
    communication = await _create_proposal(client, context)
    approved = await client.post(
        f"/api/v1/communication-proposals/{communication['id']}/decisions",
        json={
            "expected_revision": communication["revision_number"],
            "expected_hash": communication["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200
    batch = (
        await admin_db_session.execute(
            select(DispatchBatch).where(DispatchBatch.proposal_id == uuid.UUID(communication["id"]))
        )
    ).scalar_one()
    operation = (
        await admin_db_session.execute(
            select(DispatchOperation).where(DispatchOperation.dispatch_batch_id == batch.id)
        )
    ).scalar_one()
    operation_id = operation.id
    assert (
        await execute_dispatch_operation(
            operation_id, uuid.UUID(context["institution_id"]), adapter=UnknownAdapter()
        )
        == "unknown"
    )
    membership = await _coordinator_membership(
        admin_db_session, uuid.UUID(context["institution_id"])
    )
    case = await _open_case(
        admin_db_session,
        institution_id=uuid.UUID(context["institution_id"]),
        drive_id=uuid.UUID(context["drive_id"]),
        owner_id=membership.id,
        category="notification_failure",
    )
    case_id = case.id
    impact = await client.post(
        f"/api/v1/exception-cases/{case_id}/impact-analyses",
        json={
            "category": "notification_failure",
            "dispatch_operation_id": str(operation_id),
        },
    )
    assert impact.status_code == 201, impact.text
    assert impact.json()["impact_summary"]["blind_retry_allowed"] is False
    nonexistent_proposal_id = uuid.uuid4()
    plan_response = await client.post(
        f"/api/v1/impact-analyses/{impact.json()['id']}/recovery-plans",
        json={
            "planner_mode": "manual",
            "rationale": "Record evidence before any provider reconciliation",
            "manual_steps": [
                {
                    "operation_type": "record_manual_followup",
                    "exact_payload": {"note": "Confirm provider acceptance before retry"},
                    "expected_effects": ["Record manual reconciliation requirement"],
                    "approval_type": "manual_evidence",
                    "irreversible_effects": [],
                },
                {
                    "operation_type": "stale_pending_proposals",
                    "exact_payload": {"proposal_ids": [str(nonexistent_proposal_id)]},
                    "dependencies": [1],
                    "expected_effects": ["Invalidate an exact pending proposal"],
                    "approval_type": "recovery_plan",
                    "irreversible_effects": [],
                },
            ],
        },
    )
    assert plan_response.status_code == 201, plan_response.text
    plan = plan_response.json()
    decision = await client.post(
        f"/api/v1/recovery-plans/{plan['id']}/decisions",
        json={
            "expected_revision": plan["revision_number"],
            "expected_hash": plan["approval_hash"],
            "decision": "approved",
        },
    )
    assert decision.status_code == 200, decision.text
    execution_id = uuid.UUID(decision.json()["id"])
    assert (
        await execute_recovery_plan(execution_id, uuid.UUID(context["institution_id"])) == "partial"
    )
    assert (
        await execute_recovery_plan(execution_id, uuid.UUID(context["institution_id"])) == "partial"
    )
    admin_db_session.expire_all()
    current_operation = await admin_db_session.get(DispatchOperation, operation_id)
    persisted_plan = await admin_db_session.get(RecoveryPlan, uuid.UUID(plan["id"]))
    steps = (
        (
            await admin_db_session.execute(
                select(RecoveryPlanStep)
                .where(RecoveryPlanStep.plan_id == uuid.UUID(plan["id"]))
                .order_by(RecoveryPlanStep.step_number)
            )
        )
        .scalars()
        .all()
    )
    assert current_operation and current_operation.status == "unknown"
    assert persisted_plan and persisted_plan.status == "partial"
    assert [step.status for step in steps] == ["completed", "failed"]
    current_case = await admin_db_session.get(ExceptionCase, case_id)
    assert (
        current_case
        and sum(
            row["action"] == "recovery_manual_followup_required"
            for row in current_case.resolution_history
        )
        == 1
    )


@pytest.mark.asyncio
async def test_cross_tenant_recovery_case_is_hidden(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_threshold_change(client, admin_db_session, monkeypatch)
    case = await _open_case(
        admin_db_session,
        institution_id=context["institution_id"],
        drive_id=context["drive_id"],
        owner_id=context["membership_id"],
        category="criteria_change",
    )
    client.cookies.clear()
    assert (
        await client.post("/api/v1/auth/dev-login", json={"persona": "coord_beacon"})
    ).status_code == 200
    response = await client.post(
        f"/api/v1/exception-cases/{case.id}/impact-analyses",
        json={
            "category": "criteria_change",
            "old_evaluation_run_id": str(context["old_run_id"]),
            "new_evaluation_run_id": str(context["new_run_id"]),
        },
    )
    assert response.status_code == 404
