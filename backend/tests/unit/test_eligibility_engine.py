"""P05 deterministic engine acceptance tests from specification Section 10.2."""

import time
from decimal import Decimal

import pytest

from placementos.services.eligibility_engine import (
    AcademicFacts,
    InvalidEligibilityPolicy,
    evaluate,
    input_fingerprint,
)

POLICY = {
    "schema_version": 1,
    "engine_contract": "eligibility-v1",
    "aggregation": "required_unknown_first_then_failure",
    "evidence_revision": "fixture-policy-v1",
    "branch": {"mode": "required", "operator": "in", "values": ["CSE", "IT"]},
    "cgpa": {"mode": "required", "operator": "gte", "minimum": "7.50", "scale": "10.00"},
    "graduation_year": {"mode": "required", "operator": "in", "values": [2027]},
    "active_backlogs": {"mode": "required", "operator": "lte", "maximum": 0},
}


def facts(
    branch: str,
    cgpa: str,
    backlogs: int | None,
    *,
    verified: bool = True,
    scale: str = "10.00",
) -> AcademicFacts:
    return AcademicFacts(
        branch=branch,
        cgpa=Decimal(cgpa),
        cgpa_scale=Decimal(scale),
        graduation_year=2027,
        active_backlogs=backlogs,
        is_verified=verified,
        academic_revision_id="fixture-revision",
    )


@pytest.mark.parametrize(
    ("student", "record", "expected", "reason"),
    [
        ("A", facts("CSE", "8.20", 0), "eligible", None),
        ("B", facts("ECE", "8.80", 0), "ineligible", "BRANCH_NOT_ALLOWED"),
        ("C", facts("IT", "7.20", 0), "ineligible", "CGPA_BELOW_MINIMUM"),
        ("D", facts("CSE", "8.00", 1), "ineligible", "ACTIVE_BACKLOGS_EXCEED_LIMIT"),
        ("E", facts("IT", "7.90", None), "needs_review", "REQUIRED_VALUE_MISSING"),
        ("F", facts("CSE", "7.50", 0), "eligible", None),
        ("G", facts("IT", "7.49", 0), "ineligible", "CGPA_BELOW_MINIMUM"),
        ("H", facts("ECE", "8.80", None), "needs_review", "REQUIRED_VALUE_MISSING"),
        ("I", facts("CSE", "8.20", 0, verified=False), "needs_review", "RECORD_UNVERIFIED"),
        ("J", facts("CSE", "3.80", 0, scale="4.00"), "needs_review", "SCALE_UNSUPPORTED"),
    ],
)
def test_section_10_2_truth_table(student, record, expected, reason):
    decision = evaluate(POLICY, record)
    assert decision.outcome == expected, student
    if reason:
        assert reason in decision.reason_codes, student
    if student == "H":
        assert "BRANCH_NOT_ALLOWED" in decision.reason_codes


def test_exact_decimal_threshold_and_stable_fingerprint():
    equality = facts("CSE", "7.50", 0)
    below = facts("CSE", "7.499", 0)
    assert evaluate(POLICY, equality).outcome == "eligible"
    assert evaluate(POLICY, below).outcome == "ineligible"
    assert input_fingerprint("a" * 64, equality, "normalization-v1") == input_fingerprint(
        "a" * 64, equality, "normalization-v1"
    )


def test_empty_policy_fails_the_run_instead_of_classifying_students():
    invalid = {
        **POLICY,
        "branch": {"mode": "not_required"},
        "cgpa": {"mode": "not_required"},
        "graduation_year": {"mode": "not_required"},
        "active_backlogs": {"mode": "not_required"},
    }
    with pytest.raises(InvalidEligibilityPolicy):
        evaluate(invalid, facts("CSE", "8.20", 0))


def test_fixture_benchmark_is_measured_without_relaxing_correctness():
    cohort = [facts("CSE", "8.20", 0) for _ in range(1000)]
    started = time.perf_counter()
    decisions = [evaluate(POLICY, record) for record in cohort]
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert all(item.outcome == "eligible" for item in decisions)
    assert elapsed_ms < 1000, f"1000 deterministic evaluations took {elapsed_ms:.2f} ms"
