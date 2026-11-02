"""Pure P12 recovery-plan schema and planner boundary tests."""

import uuid

import pytest
from pydantic import ValidationError

from placementos.models.recovery import ExceptionImpactAnalysis
from placementos.schemas.recovery import RecoveryPlanCreate, RecoveryStepCreate
from placementos.services.recovery import DeterministicExceptionPlanner, _validated_step


def _analysis(category: str) -> ExceptionImpactAnalysis:
    return ExceptionImpactAnalysis(
        institution_id=uuid.uuid4(),
        drive_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        revision_number=1,
        category=category,
        status="current",
        input_references={},
        dependency_snapshot={},
        dependency_fingerprint="0" * 64,
        impact_summary={"submitted_registration_count": 0},
        affected_students=[],
        affected_resources=[],
        manual_fallback="Coordinator performs the scoped manual review.",
        created_by_membership_id=uuid.uuid4(),
    )


def test_fixture_planner_is_proposal_only_and_bounded() -> None:
    steps = DeterministicExceptionPlanner().propose(_analysis("notification_failure"))
    assert len(steps) == 1
    assert steps[0].operation_type == "record_manual_followup"
    assert all(step.operation_type not in {"send_email", "write_calendar"} for step in steps)


def test_manual_plan_requires_typed_steps_and_rejects_unknown_operation() -> None:
    with pytest.raises(ValidationError):
        RecoveryPlanCreate(planner_mode="manual", rationale="Manual fallback")
    with pytest.raises(ValidationError):
        RecoveryStepCreate(
            operation_type="send_email",
            exact_payload={},
            expected_effects=["Would send"],
            approval_type="recovery_plan",
        )


def test_step_dependencies_must_reference_earlier_steps() -> None:
    step = RecoveryStepCreate(
        operation_type="record_manual_followup",
        exact_payload={"note": "Review this case manually"},
        dependencies=[2],
        expected_effects=["Record follow-up"],
        approval_type="manual_evidence",
    )
    with pytest.raises(Exception, match="earlier steps"):
        _validated_step(step, 1)
