"""Pure, deterministic eligibility-v1 engine (INV-01 / INV-02)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

ENGINE_VERSION = "eligibility-v1.0.0"
SUPPORTED_PREDICATES = ("branch", "cgpa", "graduation_year", "active_backlogs")

PredicateOutcome = Literal["true", "false", "unknown"]
EligibilityOutcome = Literal["eligible", "ineligible", "needs_review"]


class InvalidEligibilityPolicy(ValueError):
    """Raised before cohort evaluation when a policy contract is invalid."""


@dataclass(frozen=True)
class AcademicFacts:
    branch: str | None
    cgpa: Decimal | None
    cgpa_scale: Decimal | None
    graduation_year: int | None
    active_backlogs: int | None
    is_verified: bool
    academic_revision_id: str | None = None
    evidence_conflict: bool = False

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "branch": self.branch,
            "cgpa": str(self.cgpa) if self.cgpa is not None else None,
            "cgpa_scale": str(self.cgpa_scale) if self.cgpa_scale is not None else None,
            "graduation_year": self.graduation_year,
            "active_backlogs": self.active_backlogs,
            "is_verified": self.is_verified,
            "academic_revision_id": self.academic_revision_id,
            "evidence_conflict": self.evidence_conflict,
        }


@dataclass(frozen=True)
class PredicateFinding:
    predicate: str
    outcome: PredicateOutcome
    reason_code: str
    expected: Any
    actual: Any
    evidence_status: str
    explanation: str


@dataclass(frozen=True)
class EligibilityDecision:
    outcome: EligibilityOutcome
    findings: tuple[PredicateFinding, ...]
    reason_codes: tuple[str, ...]
    student_explanation: str

    def findings_payload(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in self.findings]


def canonical_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != 1 or policy.get("engine_contract") != "eligibility-v1":
        raise InvalidEligibilityPolicy("Unsupported eligibility policy schema or engine contract")
    if policy.get("aggregation") != "required_unknown_first_then_failure":
        raise InvalidEligibilityPolicy("Unsupported eligibility aggregation contract")

    required_count = 0
    for name in SUPPORTED_PREDICATES:
        rule = policy.get(name)
        if not isinstance(rule, dict) or rule.get("mode") not in {"required", "not_required"}:
            raise InvalidEligibilityPolicy(f"Predicate '{name}' must declare a supported mode")
        if rule["mode"] == "not_required":
            continue
        required_count += 1
        if name == "branch":
            values = rule.get("values")
            if rule.get("operator") != "in" or not isinstance(values, list) or not values:
                raise InvalidEligibilityPolicy("Required branch scope must be a non-empty list")
        elif name == "cgpa":
            try:
                minimum = Decimal(str(rule.get("minimum")))
                scale = Decimal(str(rule.get("scale")))
            except (InvalidOperation, TypeError):
                raise InvalidEligibilityPolicy("CGPA rule requires exact decimal values") from None
            if rule.get("operator") != "gte" or scale <= 0 or minimum < 0 or minimum > scale:
                raise InvalidEligibilityPolicy("CGPA rule is outside its declared scale")
        elif name == "graduation_year":
            values = rule.get("values")
            if rule.get("operator") != "in" or not isinstance(values, list) or not values:
                raise InvalidEligibilityPolicy("Graduation-year scope must be non-empty")
            if not all(isinstance(item, int) and 2000 <= item <= 2100 for item in values):
                raise InvalidEligibilityPolicy("Graduation-year scope contains an invalid year")
        elif name == "active_backlogs":
            maximum = rule.get("maximum")
            if rule.get("operator") != "lte" or not isinstance(maximum, int) or maximum < 0:
                raise InvalidEligibilityPolicy("Active-backlog maximum must be a non-negative integer")
    if required_count == 0:
        raise InvalidEligibilityPolicy("At least one academic predicate must be required")


def _unknown(name: str, expected: Any, actual: Any, code: str, explanation: str) -> PredicateFinding:
    return PredicateFinding(name, "unknown", code, expected, actual, "unresolved", explanation)


def evaluate(policy: dict[str, Any], facts: AcademicFacts) -> EligibilityDecision:
    """Evaluate verified facts without hidden I/O, randomness, or model involvement."""
    validate_policy(policy)
    findings: list[PredicateFinding] = []

    for name in SUPPORTED_PREDICATES:
        rule = policy[name]
        if rule["mode"] != "required":
            continue
        if facts.evidence_conflict:
            findings.append(_unknown(name, rule, None, "EVIDENCE_CONFLICT", "Academic evidence conflicts and requires review."))
            continue
        if not facts.is_verified:
            findings.append(_unknown(name, rule, None, "RECORD_UNVERIFIED", "The academic record is not institutionally verified."))
            continue

        if name == "branch":
            expected = sorted({str(value).strip().upper() for value in rule["values"]})
            branch_actual = facts.branch.strip().upper() if facts.branch else None
            if branch_actual is None:
                findings.append(_unknown(name, expected, None, "REQUIRED_VALUE_MISSING", "Branch evidence is missing."))
            elif branch_actual in expected:
                findings.append(PredicateFinding(name, "true", "PREDICATE_SATISFIED", expected, branch_actual, "verified", "Branch is allowed."))
            else:
                findings.append(PredicateFinding(name, "false", "BRANCH_NOT_ALLOWED", expected, branch_actual, "verified", "Branch is not in the approved scope."))
        elif name == "cgpa":
            minimum = Decimal(str(rule["minimum"]))
            scale = Decimal(str(rule["scale"]))
            actual_payload = {
                "value": str(facts.cgpa) if facts.cgpa is not None else None,
                "scale": str(facts.cgpa_scale) if facts.cgpa_scale is not None else None,
            }
            if facts.cgpa is None or facts.cgpa_scale is None:
                findings.append(_unknown(name, {"minimum": str(minimum), "scale": str(scale)}, actual_payload, "REQUIRED_VALUE_MISSING", "CGPA evidence is missing."))
            elif facts.cgpa_scale != scale:
                findings.append(_unknown(name, {"minimum": str(minimum), "scale": str(scale)}, actual_payload, "SCALE_UNSUPPORTED", "CGPA scale does not match the approved policy."))
            elif facts.cgpa >= minimum:
                findings.append(PredicateFinding(name, "true", "PREDICATE_SATISFIED", {"minimum": str(minimum), "scale": str(scale)}, actual_payload, "verified", "CGPA meets the approved minimum."))
            else:
                findings.append(PredicateFinding(name, "false", "CGPA_BELOW_MINIMUM", {"minimum": str(minimum), "scale": str(scale)}, actual_payload, "verified", "CGPA is below the approved minimum."))
        elif name == "graduation_year":
            expected = sorted(set(rule["values"]))
            graduation_actual = facts.graduation_year
            if graduation_actual is None:
                findings.append(_unknown(name, expected, None, "REQUIRED_VALUE_MISSING", "Graduation-year evidence is missing."))
            elif graduation_actual in expected:
                findings.append(PredicateFinding(name, "true", "PREDICATE_SATISFIED", expected, graduation_actual, "verified", "Graduation year is allowed."))
            else:
                findings.append(PredicateFinding(name, "false", "GRADUATION_YEAR_NOT_ALLOWED", expected, graduation_actual, "verified", "Graduation year is outside the approved cohort."))
        else:
            maximum = rule["maximum"]
            backlog_actual = facts.active_backlogs
            if backlog_actual is None:
                findings.append(_unknown(name, maximum, None, "REQUIRED_VALUE_MISSING", "Active-backlog evidence is missing."))
            elif backlog_actual <= maximum:
                findings.append(PredicateFinding(name, "true", "PREDICATE_SATISFIED", maximum, backlog_actual, "verified", "Active backlogs are within the approved limit."))
            else:
                findings.append(PredicateFinding(name, "false", "ACTIVE_BACKLOGS_EXCEED_LIMIT", maximum, backlog_actual, "verified", "Active backlogs exceed the approved limit."))

    if any(item.outcome == "unknown" for item in findings):
        outcome: EligibilityOutcome = "needs_review"
    elif any(item.outcome == "false" for item in findings):
        outcome = "ineligible"
    else:
        outcome = "eligible"

    reason_codes = tuple(dict.fromkeys(item.reason_code for item in findings if item.outcome != "true"))
    if outcome == "eligible":
        explanation = "All required academic criteria are satisfied."
    elif outcome == "needs_review":
        explanation = "Required academic evidence needs review: " + ", ".join(reason_codes) + "."
    else:
        explanation = "One or more approved academic criteria are not satisfied: " + ", ".join(reason_codes) + "."
    return EligibilityDecision(outcome, tuple(findings), reason_codes, explanation)


def input_fingerprint(
    policy_hash: str,
    facts: AcademicFacts,
    normalization_version: str,
    engine_version: str = ENGINE_VERSION,
) -> str:
    return canonical_hash(
        {
            "policy_hash": policy_hash,
            "facts": facts.canonical_payload(),
            "normalization_version": normalization_version,
            "engine_version": engine_version,
        }
    )
