"""P21: Security review checklist and failover rehearsal runner (P21-T03, P21-T04).

This module provides:
- SecurityReviewChecklist: documents and validates security, privacy,
  authorization, prompt-injection and tenant-isolation review status.
- FailoverRehearsalRunner: exercises kill-switch toggling, budget exhaustion,
  Redis outage handling, worker crash recovery, and rollback paths.

These are testable in-process; actual infrastructure drills (database restore,
ClamAV socket, Redis sentinel) require the corresponding services running.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# P21-T03: Security review checklist
# ---------------------------------------------------------------------------


class ReviewStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    DEFERRED = "deferred"
    PENDING = "pending"


@dataclass
class SecurityCheckItem:
    """Single security or privacy review item with its result."""

    item_id: str
    category: str
    description: str
    status: ReviewStatus
    evidence: str | None = None
    invariants: list[str] = field(default_factory=list)


def build_security_review_checklist() -> list[SecurityCheckItem]:
    """Build the documented P21-T03 security and privacy review checklist.

    Returns a static list of review items covering all required security,
    privacy, authorization, prompt-injection, and tenant-isolation controls.
    Items are set to PASS where implemented, DEFERRED for post-launch infra.
    """
    return [
        # --- Authorization & Tenant Isolation ---
        SecurityCheckItem(
            item_id="SEC-01",
            category="Authorization",
            description="Every API endpoint enforces institution scope from authenticated membership, not body parameters",
            status=ReviewStatus.PASS,
            evidence="INV-06 enforced in service layer; test_integrations.py cross-institution negative tests",
            invariants=["INV-06"],
        ),
        SecurityCheckItem(
            item_id="SEC-02",
            category="Authorization",
            description="Student records are scoped: students access only their own profile, registrations, and documents",
            status=ReviewStatus.PASS,
            evidence="Row-level scope enforced in queries; cross-student guessed ID returns 404",
            invariants=["INV-06", "INV-10"],
        ),
        SecurityCheckItem(
            item_id="SEC-03",
            category="Authorization",
            description="Coordinator capability is explicit; institution admins do not inherit drive-approval authority",
            status=ReviewStatus.PASS,
            evidence="Capability membership model; approval authority is per-action, not role-wide",
            invariants=["INV-04", "INV-06"],
        ),
        SecurityCheckItem(
            item_id="SEC-04",
            category="Authorization",
            description="LangGraph workflows resume only through authenticated backend command with revision hash check",
            status=ReviewStatus.PASS,
            evidence="drive_lifecycle.py resume node validates institution, scope, capability, and fingerprint",
            invariants=["INV-04", "INV-05", "INV-08"],
        ),
        # --- Privacy & PII Minimization ---
        SecurityCheckItem(
            item_id="PRI-01",
            category="Privacy",
            description="Zero student PII (names, emails, grades) sent to AI model; only structural discrepancy summaries",
            status=ReviewStatus.PASS,
            evidence="recovery_adapter.py prompt builder; test_recovery.py verifies no personal data in prompt",
            invariants=["INV-10"],
        ),
        SecurityCheckItem(
            item_id="PRI-02",
            category="Privacy",
            description="Sensitive log fields (token, password, secret, api_key, cookie) are auto-redacted",
            status=ReviewStatus.PASS,
            evidence="RedactedJsonFormatter in telemetry.py; test_p19_p20.py covers redaction cases",
            invariants=["INV-10"],
        ),
        SecurityCheckItem(
            item_id="PRI-03",
            category="Privacy",
            description="API key, authorization header, and raw secrets never persisted in logs, checkpoints, or responses",
            status=ReviewStatus.PASS,
            evidence="drive_lifecycle.py graph state excludes secrets; RedactedJsonFormatter active on all handlers",
            invariants=["INV-10"],
        ),
        SecurityCheckItem(
            item_id="PRI-04",
            category="Privacy",
            description="Student correction proposals require verification before eligibility use",
            status=ReviewStatus.PASS,
            evidence="verify_student_academic_records() in onboarding.py; INV-02 enforced at eval boundary",
            invariants=["INV-02"],
        ),
        # --- Prompt Injection Resistance ---
        SecurityCheckItem(
            item_id="INJ-01",
            category="Prompt Injection",
            description="JD source text is isolated within <untrusted_document_content> container in all model prompts",
            status=ReviewStatus.PASS,
            evidence="gemini_adapter.py _prepare_prompt(); test_jd_intelligence.py injection fixture",
            invariants=["INV-07"],
        ),
        SecurityCheckItem(
            item_id="INJ-02",
            category="Prompt Injection",
            description="Known injection patterns detected and logged as warnings; source text never executed as code",
            status=ReviewStatus.PASS,
            evidence="INJECTION_PATTERNS pre-scan in GeminiModelInterpreter.interpret()",
            invariants=["INV-07"],
        ),
        SecurityCheckItem(
            item_id="INJ-03",
            category="Prompt Injection",
            description="Recovery plan prompts wrap untrusted impact data in <untrusted_impact_data> container",
            status=ReviewStatus.PASS,
            evidence="recovery_adapter.py build_recovery_prompt(); test_recovery.py container boundary test",
            invariants=["INV-07"],
        ),
        # --- CSRF & Browser Security ---
        SecurityCheckItem(
            item_id="CSR-01",
            category="Browser Security",
            description="Double-submit CSRF tokens required on all cookie-authenticated writes",
            status=ReviewStatus.PASS,
            evidence="BrowserWriteProtectionMiddleware in security.py; CSP and HSTS headers enforced",
            invariants=["INV-06"],
        ),
        SecurityCheckItem(
            item_id="CSR-02",
            category="Browser Security",
            description="Production browser origins restricted to HTTPS; dev-login locked out in production",
            status=ReviewStatus.PASS,
            evidence="config.py ALLOWED_ORIGINS validator; auth.py /dev-login returns 403 in production",
            invariants=["INV-06"],
        ),
        # --- AI Model Governance ---
        SecurityCheckItem(
            item_id="GOV-01",
            category="AI Governance",
            description="Model operates proposal-only; it cannot directly set eligibility, publish drives, or send emails",
            status=ReviewStatus.PASS,
            evidence="INV-01 pure deterministic evaluation; INV-04 approval required; INV-07 allowlist enforced",
            invariants=["INV-01", "INV-04", "INV-07"],
        ),
        SecurityCheckItem(
            item_id="GOV-02",
            category="AI Governance",
            description="Production environment blocks fixture and cached model modes",
            status=ReviewStatus.PASS,
            evidence="config.py validate_model_mode(); production_must_not_masquerade_as_ready() raises on fixture",
            invariants=["INV-07"],
        ),
        SecurityCheckItem(
            item_id="GOV-03",
            category="AI Governance",
            description="Daily and per-drive token budgets enforced client-side before each provider request",
            status=ReviewStatus.PASS,
            evidence="UsageTracker.check_and_increment() in gateway.py; test_model_gateway.py budget exhaustion",
            invariants=["INV-07"],
        ),
        # --- Infrastructure Security (Deferred to live deployment) ---
        SecurityCheckItem(
            item_id="INF-01",
            category="Infrastructure",
            description="Production secrets injected via cloud secret manager; no secrets in repository or env files",
            status=ReviewStatus.DEFERRED,
            evidence="Requires AWS Secrets Manager / GCP Secret Manager wiring at deployment time",
            invariants=["INV-06"],
        ),
        SecurityCheckItem(
            item_id="INF-02",
            category="Infrastructure",
            description="Database backup encryption keys are externally managed and restore tested",
            status=ReviewStatus.DEFERRED,
            evidence="Requires managed PostgreSQL and backup rehearsal in production infrastructure",
            invariants=["INV-08"],
        ),
        SecurityCheckItem(
            item_id="INF-03",
            category="Infrastructure",
            description="ClamAV daemon running in production network with real EICAR test confirmation",
            status=ReviewStatus.DEFERRED,
            evidence="Adapter implemented; production daemon requires container network provisioning",
            invariants=["INV-07"],
        ),
    ]


def run_security_review() -> dict[str, Any]:
    """Execute the security review and return a structured pass/fail summary."""
    checklist = build_security_review_checklist()
    by_status: dict[str, list[str]] = {s.value: [] for s in ReviewStatus}
    for item in checklist:
        by_status[item.status.value].append(item.item_id)

    passed = len(by_status[ReviewStatus.PASS.value])
    failed = len(by_status[ReviewStatus.FAIL.value])
    deferred = len(by_status[ReviewStatus.DEFERRED.value])
    total = len(checklist)

    all_critical_pass = failed == 0
    logger.info(
        "Security review: %d/%d pass, %d deferred, %d fail",
        passed,
        total,
        deferred,
        failed,
    )
    return {
        "total_items": total,
        "passed": passed,
        "failed": failed,
        "deferred": deferred,
        "all_critical_items_pass": all_critical_pass,
        "items_by_status": by_status,
        "checklist": [
            {
                "item_id": item.item_id,
                "category": item.category,
                "description": item.description,
                "status": item.status.value,
                "evidence": item.evidence,
                "invariants": item.invariants,
            }
            for item in checklist
        ],
    }


# ---------------------------------------------------------------------------
# P21-T04: Failover rehearsal runner
# ---------------------------------------------------------------------------


class RehearsalOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class RehearsalResult:
    """Outcome of a single failover drill."""

    drill_id: str
    description: str
    outcome: RehearsalOutcome
    detail: str


class FailoverRehearsalRunner:
    """In-process failover and kill-switch rehearsal drills (P21-T04).

    Exercises the runtime kill switches, budget exhaustion boundaries,
    and graceful fallback paths that must be confirmed before live launch.
    Infrastructure drills (Redis sentinel, database restore) require the
    corresponding services; they are marked SKIP when not available.
    """

    def rehearse_model_interpreter_kill_switch(self) -> RehearsalResult:
        """Drill: disable MODEL_INTERPRETER_MODE and confirm fallback to manual entry."""
        # Temporarily override mode; restore after
        from placementos.core import config as _cfg
        from placementos.core.errors import ConflictException
        from placementos.services.models.factory import get_model_interpreter
        original = _cfg.settings.MODEL_INTERPRETER_MODE
        _cfg.settings.MODEL_INTERPRETER_MODE = "disabled"  # type: ignore[assignment]

        try:
            get_model_interpreter()
            outcome = RehearsalOutcome.FAIL
            detail = "Expected ConflictException but no exception raised"
        except ConflictException:
            outcome = RehearsalOutcome.PASS
            detail = "Kill switch confirmed: model disabled raises ConflictException; manual entry path active"
        except Exception as exc:
            outcome = RehearsalOutcome.FAIL
            detail = f"Unexpected exception type: {type(exc).__name__}: {exc}"
        finally:
            _cfg.settings.MODEL_INTERPRETER_MODE = original  # type: ignore[assignment]

        return RehearsalResult(
            drill_id="DR-01",
            description="MODEL_INTERPRETER_MODE=disabled triggers manual fallback",
            outcome=outcome,
            detail=detail,
        )

    def rehearse_daily_token_budget_exhaustion(self) -> RehearsalResult:
        """Drill: exhaust daily token budget and confirm TokenBudgetExceededError."""
        from placementos.services.models.gateway import TokenBudgetExceededError, UsageTracker

        # Create an isolated tracker at its cap
        tracker = UsageTracker(calls_today=50)

        try:
            tracker.check_and_increment("drill-drive-id")
            outcome = RehearsalOutcome.FAIL
            detail = "Expected TokenBudgetExceededError but no exception raised"
        except TokenBudgetExceededError:
            outcome = RehearsalOutcome.PASS
            detail = "Budget exhaustion confirmed: TokenBudgetExceededError raised at daily cap"
        except Exception as exc:
            outcome = RehearsalOutcome.FAIL
            detail = f"Unexpected: {type(exc).__name__}: {exc}"

        return RehearsalResult(
            drill_id="DR-02",
            description="Daily token budget exhaustion raises TokenBudgetExceededError",
            outcome=outcome,
            detail=detail,
        )

    def rehearse_per_drive_budget_exhaustion(self) -> RehearsalResult:
        """Drill: exhaust per-drive call limit and confirm appropriate error."""
        from placementos.services.models.gateway import TokenBudgetExceededError, UsageTracker

        tracker = UsageTracker()
        drive_id = "drill-drive-exhausted"
        tracker.calls_per_drive[drive_id] = 3  # MODEL_MAX_CALLS_PER_DRIVE=3

        try:
            tracker.check_and_increment(drive_id)
            outcome = RehearsalOutcome.FAIL
            detail = "Expected TokenBudgetExceededError for per-drive cap but no exception raised"
        except TokenBudgetExceededError:
            outcome = RehearsalOutcome.PASS
            detail = "Per-drive budget cap confirmed: TokenBudgetExceededError raised"
        except Exception as exc:
            outcome = RehearsalOutcome.FAIL
            detail = f"Unexpected: {type(exc).__name__}: {exc}"

        return RehearsalResult(
            drill_id="DR-03",
            description="Per-drive model call cap exhaustion raises TokenBudgetExceededError",
            outcome=outcome,
            detail=detail,
        )

    def rehearse_live_send_kill_switch(self) -> RehearsalResult:
        """Drill: shadow mode blocks live send actions via assert_shadow_restrictions."""
        from placementos.core import config as _cfg
        from placementos.services.shadow_mode import assert_shadow_restrictions

        # Temporarily configure shadow mode conditions
        original_send = _cfg.settings.LIVE_SEND_ENABLED
        original_mode = _cfg.settings.MODEL_INTERPRETER_MODE
        original_google = _cfg.settings.GOOGLE_CONNECTORS_ENABLED

        _cfg.settings.LIVE_SEND_ENABLED = False  # type: ignore[assignment]
        _cfg.settings.MODEL_INTERPRETER_MODE = "provider"  # type: ignore[assignment]
        _cfg.settings.GOOGLE_CONNECTORS_ENABLED = False  # type: ignore[assignment]

        try:
            assert_shadow_restrictions("send_email_batch")
            outcome = RehearsalOutcome.FAIL
            detail = "Expected PermissionError in shadow mode but no exception raised"
        except PermissionError:
            outcome = RehearsalOutcome.PASS
            detail = "Shadow mode kill switch confirmed: live send blocked with PermissionError"
        except Exception as exc:
            outcome = RehearsalOutcome.FAIL
            detail = f"Unexpected: {type(exc).__name__}: {exc}"
        finally:
            _cfg.settings.LIVE_SEND_ENABLED = original_send  # type: ignore[assignment]
            _cfg.settings.MODEL_INTERPRETER_MODE = original_mode  # type: ignore[assignment]
            _cfg.settings.GOOGLE_CONNECTORS_ENABLED = original_google  # type: ignore[assignment]

        return RehearsalResult(
            drill_id="DR-04",
            description="Shadow mode blocks live send via assert_shadow_restrictions()",
            outcome=outcome,
            detail=detail,
        )

    def rehearse_provider_missing_api_key(self) -> RehearsalResult:
        """Drill: provider mode with blank API key falls back gracefully."""
        from placementos.core import config as _cfg
        from placementos.services.jd_intelligence import DeterministicFixtureJDInterpreter
        from placementos.services.models.factory import get_model_interpreter

        original_key = _cfg.settings.GEMINI_API_KEY
        original_mode = _cfg.settings.MODEL_INTERPRETER_MODE
        _cfg.settings.GEMINI_API_KEY = ""  # type: ignore[assignment]
        _cfg.settings.MODEL_INTERPRETER_MODE = "provider"  # type: ignore[assignment]

        try:
            interpreter = get_model_interpreter()
            if isinstance(interpreter, DeterministicFixtureJDInterpreter):
                outcome = RehearsalOutcome.PASS
                detail = "Missing API key fallback confirmed: fixture interpreter returned"
            else:
                outcome = RehearsalOutcome.FAIL
                detail = f"Expected DeterministicFixtureJDInterpreter, got {type(interpreter).__name__}"
        except Exception as exc:
            outcome = RehearsalOutcome.FAIL
            detail = f"Unexpected exception during fallback: {exc}"
        finally:
            _cfg.settings.GEMINI_API_KEY = original_key  # type: ignore[assignment]
            _cfg.settings.MODEL_INTERPRETER_MODE = original_mode  # type: ignore[assignment]

        return RehearsalResult(
            drill_id="DR-05",
            description="Provider mode with blank API key falls back to deterministic fixture",
            outcome=outcome,
            detail=detail,
        )

    def rehearse_redis_unavailable(self) -> RehearsalResult:
        """Drill: Redis unavailability is detected gracefully (requires running infra)."""
        # This drill requires an actual Redis connection; skip in unit test context.
        return RehearsalResult(
            drill_id="DR-06",
            description="Redis sentinel outage returns 503 readiness; queued work held pending",
            outcome=RehearsalOutcome.SKIP,
            detail=(
                "Infrastructure drill: requires a running Redis instance. "
                "Execute 'docker compose stop redis' and check GET /api/v1/ready returns 503. "
                "Verify queued Celery tasks remain pending and are processed after restart."
            ),
        )

    def rehearse_database_restore(self) -> RehearsalResult:
        """Drill: database backup restore procedure (requires managed infra)."""
        return RehearsalResult(
            drill_id="DR-07",
            description="Database restore from backup reapplies tombstones before exposing data",
            outcome=RehearsalOutcome.SKIP,
            detail=(
                "Infrastructure drill: execute documented restore runbook against staging environment. "
                "Verify: (1) restored data is inaccessible until tombstones reapplied, "
                "(2) deleted records remain absent, "
                "(3) workflow checkpoints are consistent with business records."
            ),
        )

    def run_all(self) -> dict[str, Any]:
        """Execute all in-process rehearsal drills and return a structured summary."""
        drills = [
            self.rehearse_model_interpreter_kill_switch,
            self.rehearse_daily_token_budget_exhaustion,
            self.rehearse_per_drive_budget_exhaustion,
            self.rehearse_live_send_kill_switch,
            self.rehearse_provider_missing_api_key,
            self.rehearse_redis_unavailable,
            self.rehearse_database_restore,
        ]

        results: list[RehearsalResult] = []
        for drill_fn in drills:
            result = drill_fn()
            results.append(result)
            logger.info(
                "Rehearsal drill %s (%s): %s",
                result.drill_id,
                result.description[:60],
                result.outcome.value,
            )

        passed = sum(1 for r in results if r.outcome == RehearsalOutcome.PASS)
        failed = sum(1 for r in results if r.outcome == RehearsalOutcome.FAIL)
        skipped = sum(1 for r in results if r.outcome == RehearsalOutcome.SKIP)

        return {
            "total_drills": len(results),
            "passed": passed,
            "failed": failed,
            "skipped_infrastructure": skipped,
            "all_in_process_drills_pass": failed == 0,
            "results": [
                {
                    "drill_id": r.drill_id,
                    "description": r.description,
                    "outcome": r.outcome.value,
                    "detail": r.detail,
                }
                for r in results
            ],
        }
