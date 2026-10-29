"""Pure P06 readiness precedence and deadline semantics."""

from datetime import UTC, datetime, timedelta

from placementos.services.participation import aggregate_readiness, registration_window_is_open


def test_readiness_precedence_is_independent_and_conservative() -> None:
    assert aggregate_readiness([]) == "ready"
    assert aggregate_readiness(["ready", "pending"]) == "pending"
    assert aggregate_readiness(["ready", "pending", "needs_review"]) == "needs_review"
    assert aggregate_readiness(["needs_review", "blocked", "pending"]) == "blocked"


def test_registration_window_is_inclusive_open_and_exclusive_close() -> None:
    opens_at = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)
    deadline_at = opens_at + timedelta(hours=1)
    assert registration_window_is_open(opens_at, opens_at, deadline_at)
    assert registration_window_is_open(
        deadline_at - timedelta(microseconds=1), opens_at, deadline_at
    )
    assert not registration_window_is_open(deadline_at, opens_at, deadline_at)
    assert not registration_window_is_open(
        opens_at - timedelta(microseconds=1), opens_at, deadline_at
    )
