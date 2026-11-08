"""P21: Shadow mode comparison engine for PlacementOS.

Runs the AI model on permitted JDs in read-only shadow mode (P21-T01).
Model suggestions are compared with coordinator ground truth without
silently adopting them into live drives. All results are stored for
prompt quality improvement only — they never modify deterministic
eligibility decisions or approved policies.

Implements:
- P21-T01: Ground-truth comparison (ShadowModeRunner)
- P21-T02: Field-level correction telemetry (ShadowCorrectionTracker)
- P21-T06: Kill-switch enforcement (shadow_mode_active())
- P21-T07: Honest operational status enum (SuggestionLifecycleStatus)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# P21-T07: Honest operational status lifecycle
# ---------------------------------------------------------------------------


class SuggestionLifecycleStatus(StrEnum):
    """Transparent lifecycle for every AI suggestion (P21-T07).

    Status published to coordinators shows exactly where in the pipeline
    a suggestion lives — it is never aggregated into a vague 'processing'.
    """

    SUGGESTED = "suggested"
    """Model produced a candidate; not yet reviewed by a human."""

    REVIEWED = "reviewed"
    """A coordinator has read and evaluated the suggestion."""

    ADOPTED = "adopted"
    """Coordinator accepted the suggestion into an immutable policy draft."""

    REJECTED = "rejected"
    """Coordinator explicitly rejected the suggestion with a reason."""

    SHADOW_ONLY = "shadow_only"
    """Suggestion produced in shadow mode; cannot be adopted into a live drive."""

    EXPIRED = "expired"
    """Source revision changed; suggestion is stale and cannot be used."""


# ---------------------------------------------------------------------------
# P21-T02: Field-level correction tracking
# ---------------------------------------------------------------------------


@dataclass
class FieldCorrectionRecord:
    """Immutable record of one coordinator correction to a model suggestion."""

    field_path: str
    model_value: Any
    coordinator_value: Any
    rejection_reason: str | None
    corrected_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    prompt_version: str = ""
    adapter_id: str = ""


@dataclass
class ShadowCorrectionTracker:
    """Accumulates field-level corrections to improve prompts/evals (P21-T02).

    Corrections are stored for prompt-quality analysis only.
    They must NEVER be used to modify deterministic eligibility results
    or approved historical policies (INV-01, INV-09).
    """

    _records: list[FieldCorrectionRecord] = field(default_factory=list)

    def record_correction(
        self,
        field_path: str,
        model_value: Any,
        coordinator_value: Any,
        rejection_reason: str | None = None,
        prompt_version: str = "",
        adapter_id: str = "",
    ) -> None:
        """Record a coordinator correction to a model-suggested field value."""
        record = FieldCorrectionRecord(
            field_path=field_path,
            model_value=model_value,
            coordinator_value=coordinator_value,
            rejection_reason=rejection_reason,
            prompt_version=prompt_version,
            adapter_id=adapter_id,
        )
        self._records.append(record)
        logger.info(
            "Shadow correction recorded: field=%s prompt_version=%s",
            field_path,
            prompt_version,
        )

    def get_correction_rate_by_field(self) -> dict[str, float]:
        """Return per-field correction frequency across all recorded comparisons."""
        from collections import Counter

        counts: Counter[str] = Counter(r.field_path for r in self._records)
        total = len(self._records) or 1
        return {fp: round(count / total, 4) for fp, count in counts.most_common()}

    def get_summary(self) -> dict[str, Any]:
        """Return aggregate correction statistics for prompt evaluation."""
        return {
            "total_corrections": len(self._records),
            "field_correction_rates": self.get_correction_rate_by_field(),
            "records": [
                {
                    "field_path": r.field_path,
                    "rejection_reason": r.rejection_reason,
                    "corrected_at": r.corrected_at,
                    "prompt_version": r.prompt_version,
                    "adapter_id": r.adapter_id,
                }
                for r in self._records
            ],
        }


GLOBAL_CORRECTION_TRACKER = ShadowCorrectionTracker()


# ---------------------------------------------------------------------------
# P21-T01: Shadow mode comparison runner
# ---------------------------------------------------------------------------


COMPARABLE_FIELDS = [
    "company_name",
    "role_title",
    "employment_type",
    "location",
    "work_mode",
    "registration_deadline",
    "eligibility_draft.minimum_cgpa",
    "eligibility_draft.cgpa_scale",
    "eligibility_draft.maximum_active_backlogs",
    "eligibility_draft.allowed_branches",
    "eligibility_draft.graduation_years",
    "compensation.annual_ctc_minor_units",
]


def _resolve_nested(data: dict[str, Any], path: str) -> Any:
    """Navigate a dot-separated path into a nested dict, return None if absent."""
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


@dataclass
class ShadowFieldComparison:
    """Comparison outcome for a single extracted field."""

    field_path: str
    model_value: Any
    ground_truth_value: Any
    matched: bool
    discrepancy_detail: str | None = None


@dataclass
class ShadowComparisonResult:
    """Full comparison result for one JD shadow evaluation run."""

    source_hash: str
    adapter_id: str
    prompt_version: str
    model_extraction_hash: str
    ground_truth_hash: str
    status: SuggestionLifecycleStatus
    field_comparisons: list[ShadowFieldComparison]
    precision: float
    recall: float
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_hash": self.source_hash,
            "adapter_id": self.adapter_id,
            "prompt_version": self.prompt_version,
            "model_extraction_hash": self.model_extraction_hash,
            "ground_truth_hash": self.ground_truth_hash,
            "status": self.status.value,
            "precision": self.precision,
            "recall": self.recall,
            "evaluated_at": self.evaluated_at,
            "notes": self.notes,
            "field_comparisons": [
                {
                    "field_path": fc.field_path,
                    "model_value": fc.model_value,
                    "ground_truth_value": fc.ground_truth_value,
                    "matched": fc.matched,
                    "discrepancy_detail": fc.discrepancy_detail,
                }
                for fc in self.field_comparisons
            ],
        }


class ShadowModeRunner:
    """Compare AI model suggestions with coordinator ground truth (P21-T01).

    The runner operates in read-only shadow mode:
    - Model output is compared but NEVER written to a live drive.
    - Results feed prompt quality evaluation only.
    - Adoption into an immutable policy requires explicit coordinator review
      and an authorized approval (INV-04, INV-05).
    """

    def __init__(
        self,
        adapter_id: str = "fixture",
        prompt_version: str = "unknown",
        correction_tracker: ShadowCorrectionTracker | None = None,
    ) -> None:
        self.adapter_id = adapter_id
        self.prompt_version = prompt_version
        self.correction_tracker = correction_tracker or GLOBAL_CORRECTION_TRACKER

    @staticmethod
    def _stable_hash(data: Any) -> str:
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @staticmethod
    def _values_match(model_val: Any, truth_val: Any) -> bool:
        """Fuzzy but deterministic field comparison."""
        if model_val is None and truth_val is None:
            return True
        if model_val is None or truth_val is None:
            return False
        # Normalize strings
        if isinstance(model_val, str) and isinstance(truth_val, str):
            return model_val.strip().lower() == truth_val.strip().lower()
        # Normalize lists (order-independent)
        if isinstance(model_val, list) and isinstance(truth_val, list):
            return sorted(str(x).lower() for x in model_val) == sorted(
                str(x).lower() for x in truth_val
            )
        return str(model_val) == str(truth_val)

    def compare(
        self,
        model_facts: dict[str, Any],
        ground_truth: dict[str, Any],
        source_text: str = "",
    ) -> ShadowComparisonResult:
        """Compare model extraction against coordinator-reviewed ground truth.

        Args:
            model_facts: Extracted facts dict from the AI model (read-only).
            ground_truth: Coordinator-reviewed and corrected field values.
            source_text: Original source text used to compute a stable hash.

        Returns:
            ShadowComparisonResult with field-level comparisons and metrics.
            Status is always SHADOW_ONLY — results cannot be auto-adopted.
        """
        source_hash = self._stable_hash(source_text or model_facts)
        model_hash = self._stable_hash(model_facts)
        truth_hash = self._stable_hash(ground_truth)

        field_comparisons: list[ShadowFieldComparison] = []
        matched_count = 0
        relevant_truth_fields = 0

        for field_path in COMPARABLE_FIELDS:
            model_val = _resolve_nested(model_facts, field_path)
            truth_val = _resolve_nested(ground_truth, field_path)

            # Only compare fields where ground truth was supplied
            if truth_val is None:
                continue

            relevant_truth_fields += 1
            matched = self._values_match(model_val, truth_val)
            if matched:
                matched_count += 1

            discrepancy: str | None = None
            if not matched:
                discrepancy = (
                    f"Model extracted {model_val!r} but coordinator confirmed {truth_val!r}"
                )
                # Record correction for prompt evaluation (P21-T02)
                self.correction_tracker.record_correction(
                    field_path=field_path,
                    model_value=model_val,
                    coordinator_value=truth_val,
                    prompt_version=self.prompt_version,
                    adapter_id=self.adapter_id,
                )

            field_comparisons.append(
                ShadowFieldComparison(
                    field_path=field_path,
                    model_value=model_val,
                    ground_truth_value=truth_val,
                    matched=matched,
                    discrepancy_detail=discrepancy,
                )
            )

        total_model_non_null = sum(
            1
            for fp in COMPARABLE_FIELDS
            if _resolve_nested(model_facts, fp) is not None
        )

        # Precision = matched / what model extracted (avoid div-by-zero)
        precision = matched_count / total_model_non_null if total_model_non_null else 0.0
        # Recall = matched / what ground truth contains
        recall = matched_count / relevant_truth_fields if relevant_truth_fields else 0.0

        notes: list[str] = []
        if precision < 0.70:
            notes.append(
                "WARNING: Model precision below 70%% threshold — prompt review recommended."
            )
        if recall < 0.70:
            notes.append(
                "WARNING: Model recall below 70%% threshold — missing field patterns need investigation."
            )

        logger.info(
            "Shadow comparison complete: precision=%.2f recall=%.2f adapter=%s",
            precision,
            recall,
            self.adapter_id,
        )

        return ShadowComparisonResult(
            source_hash=source_hash,
            adapter_id=self.adapter_id,
            prompt_version=self.prompt_version,
            model_extraction_hash=model_hash,
            ground_truth_hash=truth_hash,
            status=SuggestionLifecycleStatus.SHADOW_ONLY,
            field_comparisons=field_comparisons,
            precision=round(precision, 4),
            recall=round(recall, 4),
            notes=notes,
        )


# ---------------------------------------------------------------------------
# P21-T06: Kill-switch enforcement
# ---------------------------------------------------------------------------


def shadow_mode_active() -> bool:
    """Return True when the platform is in shadow evaluation mode.

    Shadow mode is distinct from live pilot mode.  In shadow mode, the model
    runs alongside the coordinator's manual path but its output is never
    permitted to publish or execute any drive action (P21-T06).
    """
    from placementos.core.config import settings

    # Shadow mode is active when the model is enabled but live sends are
    # disabled and Google connectors are not yet authorized — the platform
    # operates in comparison-only mode.
    return (
        settings.MODEL_INTERPRETER_MODE in {"provider", "cached"}
        and not settings.LIVE_SEND_ENABLED
        and not settings.GOOGLE_CONNECTORS_ENABLED
    )


def assert_shadow_restrictions(action: str) -> None:
    """Raise if a consequential action is attempted while in shadow mode.

    Live writes (email, calendar, policy publish) must be blocked when the
    platform has not completed P21 institutional acceptance (INV-04, P21-T06).
    """
    if shadow_mode_active():
        raise PermissionError(
            f"Action '{action}' is blocked in shadow evaluation mode. "
            "Complete institutional acceptance (P21) before enabling live features."
        )
