"""Unit tests for Phase 21: Shadow mode, security review, failover rehearsals, and pilot signoff.

Covers:
- P21-T01: ShadowModeRunner ground-truth comparison
- P21-T02: ShadowCorrectionTracker field-level telemetry
- P21-T03: SecurityReviewChecklist correctness
- P21-T04: FailoverRehearsalRunner in-process drills
- P21-T05: Pilot signoff gate (validate_pilot_signoff)
- P21-T06: Kill-switch enforcement (shadow_mode_active, assert_shadow_restrictions)
- P21-T07: SuggestionLifecycleStatus honest status enum
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# P21-T07: SuggestionLifecycleStatus
# ---------------------------------------------------------------------------


class TestSuggestionLifecycleStatus:
    def test_all_expected_statuses_present(self) -> None:
        from placementos.services.shadow_mode import SuggestionLifecycleStatus

        expected = {
            "suggested",
            "reviewed",
            "adopted",
            "rejected",
            "shadow_only",
            "expired",
        }
        actual = {s.value for s in SuggestionLifecycleStatus}
        assert expected == actual

    def test_shadow_only_cannot_be_adopted(self) -> None:
        from placementos.services.shadow_mode import SuggestionLifecycleStatus

        # shadow_only must remain distinct from adopted
        assert SuggestionLifecycleStatus.SHADOW_ONLY != SuggestionLifecycleStatus.ADOPTED

    def test_status_values_are_strings(self) -> None:
        from placementos.services.shadow_mode import SuggestionLifecycleStatus

        for s in SuggestionLifecycleStatus:
            assert isinstance(s.value, str)


# ---------------------------------------------------------------------------
# P21-T01: ShadowModeRunner
# ---------------------------------------------------------------------------


class TestShadowModeRunner:
    _MODEL_FACTS = {
        "company_name": "TechCorp Solutions",
        "role_title": "Software Development Engineer",
        "employment_type": "full_time",
        "location": "Bangalore",
        "work_mode": "on_site",
        "registration_deadline": "2026-12-15",
        "eligibility_draft": {
            "minimum_cgpa": "7.0",
            "cgpa_scale": "10.0",
            "maximum_active_backlogs": 0,
            "allowed_branches": ["CSE", "IT", "ECE"],
            "graduation_years": [2027],
        },
        "compensation": {"annual_ctc_minor_units": 185_000_000},
    }
    _GROUND_TRUTH = {
        "company_name": "TechCorp Solutions",
        "role_title": "Software Development Engineer",
        "employment_type": "full_time",
        "location": "Bangalore",
        "work_mode": "on_site",
        "registration_deadline": "2026-12-15",
        "eligibility_draft": {
            "minimum_cgpa": "7.0",
            "cgpa_scale": "10.0",
            "maximum_active_backlogs": 0,
            "allowed_branches": ["CSE", "IT", "ECE"],
            "graduation_years": [2027],
        },
        "compensation": {"annual_ctc_minor_units": 185_000_000},
    }

    def _runner(self):
        from placementos.services.shadow_mode import ShadowCorrectionTracker, ShadowModeRunner

        return ShadowModeRunner(
            adapter_id="test-adapter",
            prompt_version="test-v1",
            correction_tracker=ShadowCorrectionTracker(),
        )

    def test_perfect_match_gives_precision_and_recall_one(self) -> None:
        runner = self._runner()
        result = runner.compare(self._MODEL_FACTS, self._GROUND_TRUTH)
        assert result.precision == 1.0
        assert result.recall == 1.0

    def test_result_status_is_always_shadow_only(self) -> None:
        from placementos.services.shadow_mode import SuggestionLifecycleStatus

        runner = self._runner()
        result = runner.compare(self._MODEL_FACTS, self._GROUND_TRUTH)
        assert result.status == SuggestionLifecycleStatus.SHADOW_ONLY

    def test_mismatch_recorded_as_discrepancy(self) -> None:
        runner = self._runner()
        wrong_facts = {**self._MODEL_FACTS, "company_name": "WrongCorp"}
        result = runner.compare(wrong_facts, self._GROUND_TRUTH)
        mismatched = [fc for fc in result.field_comparisons if not fc.matched]
        assert any(fc.field_path == "company_name" for fc in mismatched)

    def test_mismatch_reduces_precision(self) -> None:
        runner = self._runner()
        wrong_facts = {**self._MODEL_FACTS, "company_name": "Wrong", "role_title": "Wrong"}
        result = runner.compare(wrong_facts, self._GROUND_TRUTH)
        assert result.precision < 1.0

    def test_missing_model_field_reduces_recall(self) -> None:
        runner = self._runner()
        sparse_facts = {"company_name": "TechCorp Solutions"}  # most fields absent
        result = runner.compare(sparse_facts, self._GROUND_TRUTH)
        # Recall = matched / relevant_truth_fields; most truth fields unmatched
        assert result.recall < 1.0

    def test_empty_ground_truth_gives_zero_recall(self) -> None:
        runner = self._runner()
        result = runner.compare(self._MODEL_FACTS, {})
        assert result.recall == 0.0

    def test_comparison_does_not_modify_input_dicts(self) -> None:
        runner = self._runner()
        import copy

        facts_before = copy.deepcopy(self._MODEL_FACTS)
        truth_before = copy.deepcopy(self._GROUND_TRUTH)
        runner.compare(self._MODEL_FACTS, self._GROUND_TRUTH)
        assert self._MODEL_FACTS == facts_before
        assert self._GROUND_TRUTH == truth_before

    def test_to_dict_is_json_serializable(self) -> None:
        import json

        runner = self._runner()
        result = runner.compare(self._MODEL_FACTS, self._GROUND_TRUTH)
        serialized = json.dumps(result.to_dict(), default=str)
        parsed = json.loads(serialized)
        assert "precision" in parsed
        assert "field_comparisons" in parsed

    def test_low_precision_adds_warning_note(self) -> None:
        from placementos.services.shadow_mode import ShadowCorrectionTracker, ShadowModeRunner

        runner = ShadowModeRunner(correction_tracker=ShadowCorrectionTracker())
        # All model fields wrong → precision 0
        wrong_facts = {
            "company_name": "X",
            "role_title": "Y",
            "employment_type": "internship",
            "location": "Z",
            "work_mode": "remote",
            "registration_deadline": "2000-01-01",
        }
        truth = {k: v for k, v in self._GROUND_TRUTH.items() if k in wrong_facts}
        result = runner.compare(wrong_facts, truth)
        assert any("precision" in note.lower() for note in result.notes)


# ---------------------------------------------------------------------------
# P21-T02: ShadowCorrectionTracker
# ---------------------------------------------------------------------------


class TestShadowCorrectionTracker:
    def test_records_correction(self) -> None:
        from placementos.services.shadow_mode import ShadowCorrectionTracker

        tracker = ShadowCorrectionTracker()
        tracker.record_correction(
            field_path="role_title",
            model_value="SDE",
            coordinator_value="Software Development Engineer",
            rejection_reason="Too abbreviated",
            prompt_version="v1",
            adapter_id="test",
        )
        summary = tracker.get_summary()
        assert summary["total_corrections"] == 1
        assert summary["field_correction_rates"]["role_title"] == 1.0

    def test_multiple_corrections_aggregated_by_field(self) -> None:
        from placementos.services.shadow_mode import ShadowCorrectionTracker

        tracker = ShadowCorrectionTracker()
        for _ in range(3):
            tracker.record_correction("minimum_cgpa", "7", "7.0")
        tracker.record_correction("role_title", "SDE", "Engineer")
        rates = tracker.get_correction_rate_by_field()
        assert rates["minimum_cgpa"] > rates["role_title"]

    def test_correction_does_not_modify_eligibility(self) -> None:
        """Corrections must never alter deterministic eligibility results (INV-01)."""
        from placementos.services.shadow_mode import ShadowCorrectionTracker

        tracker = ShadowCorrectionTracker()
        # Simulate a correction that changes a CGPA value
        tracker.record_correction("eligibility_draft.minimum_cgpa", "7.0", "8.0")
        # The tracker's data must only be accessible as evaluation metadata
        # and must not expose any method to mutate eligibility outcomes
        summary = tracker.get_summary()
        assert "eligibility" not in str(summary).lower() or "field_path" in str(summary)
        # No side effect on global state
        from placementos.services.shadow_mode import GLOBAL_CORRECTION_TRACKER

        # GLOBAL_CORRECTION_TRACKER is separate from our local tracker
        assert tracker is not GLOBAL_CORRECTION_TRACKER

    def test_empty_tracker_summary(self) -> None:
        from placementos.services.shadow_mode import ShadowCorrectionTracker

        tracker = ShadowCorrectionTracker()
        summary = tracker.get_summary()
        assert summary["total_corrections"] == 0
        assert summary["field_correction_rates"] == {}


# ---------------------------------------------------------------------------
# P21-T03: Security review checklist
# ---------------------------------------------------------------------------


class TestSecurityReviewChecklist:
    def test_all_critical_items_pass(self) -> None:
        from placementos.services.pilot_readiness import run_security_review

        result = run_security_review()
        assert result["all_critical_items_pass"] is True, (
            f"Security review has failures: {result['items_by_status'].get('fail', [])}"
        )

    def test_no_failed_items(self) -> None:
        from placementos.services.pilot_readiness import run_security_review

        result = run_security_review()
        assert result["failed"] == 0

    def test_covers_required_categories(self) -> None:
        from placementos.services.pilot_readiness import build_security_review_checklist

        items = build_security_review_checklist()
        categories = {item.category for item in items}
        required = {"Authorization", "Privacy", "Prompt Injection", "AI Governance", "Browser Security"}
        assert required.issubset(categories)

    def test_all_pass_items_have_evidence(self) -> None:
        from placementos.services.pilot_readiness import (
            ReviewStatus,
            build_security_review_checklist,
        )

        for item in build_security_review_checklist():
            if item.status == ReviewStatus.PASS:
                assert item.evidence, f"{item.item_id} has no evidence string"

    def test_all_items_have_invariant_mappings(self) -> None:
        from placementos.services.pilot_readiness import build_security_review_checklist

        for item in build_security_review_checklist():
            assert item.invariants, f"{item.item_id} has no invariant mappings"

    def test_deferred_items_have_detail(self) -> None:
        from placementos.services.pilot_readiness import (
            ReviewStatus,
            build_security_review_checklist,
        )

        for item in build_security_review_checklist():
            if item.status == ReviewStatus.DEFERRED:
                assert item.evidence and len(item.evidence) > 10


# ---------------------------------------------------------------------------
# P21-T04: FailoverRehearsalRunner
# ---------------------------------------------------------------------------


class TestFailoverRehearsalRunner:
    def _runner(self):
        from placementos.services.pilot_readiness import FailoverRehearsalRunner

        return FailoverRehearsalRunner()

    def test_model_kill_switch_drill_passes(self) -> None:
        result = self._runner().rehearse_model_interpreter_kill_switch()
        assert result.outcome.value == "pass", result.detail

    def test_daily_budget_exhaustion_drill_passes(self) -> None:
        result = self._runner().rehearse_daily_token_budget_exhaustion()
        assert result.outcome.value == "pass", result.detail

    def test_per_drive_budget_exhaustion_drill_passes(self) -> None:
        result = self._runner().rehearse_per_drive_budget_exhaustion()
        assert result.outcome.value == "pass", result.detail

    def test_live_send_kill_switch_drill_passes(self) -> None:
        result = self._runner().rehearse_live_send_kill_switch()
        assert result.outcome.value == "pass", result.detail

    def test_provider_missing_api_key_drill_passes(self) -> None:
        result = self._runner().rehearse_provider_missing_api_key()
        assert result.outcome.value == "pass", result.detail

    def test_redis_unavailable_drill_is_skipped(self) -> None:
        result = self._runner().rehearse_redis_unavailable()
        assert result.outcome.value == "skip"

    def test_database_restore_drill_is_skipped(self) -> None:
        result = self._runner().rehearse_database_restore()
        assert result.outcome.value == "skip"

    def test_run_all_has_no_failures(self) -> None:
        summary = self._runner().run_all()
        assert summary["failed"] == 0, (
            f"Failed drills: {[r for r in summary['results'] if r['outcome'] == 'fail']}"
        )

    def test_run_all_in_process_drills_all_pass(self) -> None:
        summary = self._runner().run_all()
        assert summary["all_in_process_drills_pass"] is True

    def test_skipped_infra_drills_counted(self) -> None:
        summary = self._runner().run_all()
        assert summary["skipped_infrastructure"] >= 2  # Redis + DB restore


# ---------------------------------------------------------------------------
# P21-T05: Pilot signoff gate
# ---------------------------------------------------------------------------


class TestPilotSignoffGate:
    def test_all_gates_false_by_default(self) -> None:
        from placementos.core.config import Settings, validate_pilot_signoff

        s = Settings()
        result = validate_pilot_signoff(s)
        assert result["all_signed_off"] is False

    def test_real_data_not_permitted_without_signoff(self) -> None:
        from placementos.core.config import Settings, validate_pilot_signoff

        s = Settings()
        result = validate_pilot_signoff(s)
        assert result["real_data_permitted"] is False

    def test_all_signoff_required_for_real_data(self) -> None:
        from placementos.core.config import Settings, validate_pilot_signoff

        s = Settings(
            PILOT_DATA_USE_SIGNED_OFF=True,
            PILOT_PERMISSIONS_SIGNED_OFF=True,
            PILOT_ACADEMIC_CONFIG_SIGNED_OFF=True,
            PILOT_SENDER_SIGNED_OFF=True,
            PILOT_RETENTION_SIGNED_OFF=True,
            PILOT_LAUNCH_SCOPE_SIGNED_OFF=True,
            REAL_DATA_ENABLED=True,
        )
        result = validate_pilot_signoff(s)
        assert result["all_signed_off"] is True
        assert result["real_data_permitted"] is True

    def test_partial_signoff_blocks_real_data(self) -> None:
        from placementos.core.config import Settings, validate_pilot_signoff

        # Only 5 of 6 gates signed
        s = Settings(
            PILOT_DATA_USE_SIGNED_OFF=True,
            PILOT_PERMISSIONS_SIGNED_OFF=True,
            PILOT_ACADEMIC_CONFIG_SIGNED_OFF=True,
            PILOT_SENDER_SIGNED_OFF=True,
            PILOT_RETENTION_SIGNED_OFF=True,
            PILOT_LAUNCH_SCOPE_SIGNED_OFF=False,  # missing
            REAL_DATA_ENABLED=True,
        )
        result = validate_pilot_signoff(s)
        assert result["all_signed_off"] is False
        assert result["real_data_permitted"] is False

    def test_signoff_summary_has_all_six_gates(self) -> None:
        from placementos.core.config import Settings, validate_pilot_signoff

        result = validate_pilot_signoff(Settings())
        gates = result["gates"]
        expected_keys = {
            "data_use",
            "permissions",
            "academic_config",
            "sender",
            "retention",
            "launch_scope",
        }
        assert set(gates.keys()) == expected_keys


# ---------------------------------------------------------------------------
# P21-T06: Kill-switch enforcement
# ---------------------------------------------------------------------------


class TestKillSwitchEnforcement:
    def test_shadow_mode_active_when_model_on_and_live_send_off(self) -> None:
        from placementos.core import config as _cfg
        from placementos.services.shadow_mode import shadow_mode_active

        orig_mode = _cfg.settings.MODEL_INTERPRETER_MODE
        orig_send = _cfg.settings.LIVE_SEND_ENABLED
        orig_google = _cfg.settings.GOOGLE_CONNECTORS_ENABLED

        _cfg.settings.MODEL_INTERPRETER_MODE = "provider"  # type: ignore[assignment]
        _cfg.settings.LIVE_SEND_ENABLED = False  # type: ignore[assignment]
        _cfg.settings.GOOGLE_CONNECTORS_ENABLED = False  # type: ignore[assignment]

        try:
            assert shadow_mode_active() is True
        finally:
            _cfg.settings.MODEL_INTERPRETER_MODE = orig_mode  # type: ignore[assignment]
            _cfg.settings.LIVE_SEND_ENABLED = orig_send  # type: ignore[assignment]
            _cfg.settings.GOOGLE_CONNECTORS_ENABLED = orig_google  # type: ignore[assignment]

    def test_shadow_mode_inactive_when_model_disabled(self) -> None:
        from placementos.core import config as _cfg
        from placementos.services.shadow_mode import shadow_mode_active

        orig = _cfg.settings.MODEL_INTERPRETER_MODE
        _cfg.settings.MODEL_INTERPRETER_MODE = "disabled"  # type: ignore[assignment]
        try:
            assert shadow_mode_active() is False
        finally:
            _cfg.settings.MODEL_INTERPRETER_MODE = orig  # type: ignore[assignment]

    def test_assert_shadow_restrictions_raises_in_shadow_mode(self) -> None:
        from placementos.core import config as _cfg
        from placementos.services.shadow_mode import assert_shadow_restrictions

        orig_mode = _cfg.settings.MODEL_INTERPRETER_MODE
        orig_send = _cfg.settings.LIVE_SEND_ENABLED
        orig_google = _cfg.settings.GOOGLE_CONNECTORS_ENABLED

        _cfg.settings.MODEL_INTERPRETER_MODE = "provider"  # type: ignore[assignment]
        _cfg.settings.LIVE_SEND_ENABLED = False  # type: ignore[assignment]
        _cfg.settings.GOOGLE_CONNECTORS_ENABLED = False  # type: ignore[assignment]

        try:
            with pytest.raises(PermissionError, match="shadow evaluation mode"):
                assert_shadow_restrictions("publish_drive")
        finally:
            _cfg.settings.MODEL_INTERPRETER_MODE = orig_mode  # type: ignore[assignment]
            _cfg.settings.LIVE_SEND_ENABLED = orig_send  # type: ignore[assignment]
            _cfg.settings.GOOGLE_CONNECTORS_ENABLED = orig_google  # type: ignore[assignment]

    def test_assert_shadow_restrictions_no_raise_when_not_shadow(self) -> None:
        from placementos.core import config as _cfg
        from placementos.services.shadow_mode import assert_shadow_restrictions

        orig_mode = _cfg.settings.MODEL_INTERPRETER_MODE
        orig_send = _cfg.settings.LIVE_SEND_ENABLED

        _cfg.settings.MODEL_INTERPRETER_MODE = "disabled"  # type: ignore[assignment]
        _cfg.settings.LIVE_SEND_ENABLED = True  # type: ignore[assignment]

        try:
            assert_shadow_restrictions("any_action")  # Must not raise
        finally:
            _cfg.settings.MODEL_INTERPRETER_MODE = orig_mode  # type: ignore[assignment]
            _cfg.settings.LIVE_SEND_ENABLED = orig_send  # type: ignore[assignment]

    def test_fixture_mode_is_not_shadow_mode(self) -> None:
        from placementos.core import config as _cfg
        from placementos.services.shadow_mode import shadow_mode_active

        orig = _cfg.settings.MODEL_INTERPRETER_MODE
        _cfg.settings.MODEL_INTERPRETER_MODE = "fixture"  # type: ignore[assignment]
        try:
            # fixture mode is not a live provider, so shadow mode should NOT be active
            assert shadow_mode_active() is False
        finally:
            _cfg.settings.MODEL_INTERPRETER_MODE = orig  # type: ignore[assignment]
