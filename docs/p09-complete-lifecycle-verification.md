# P09 complete lifecycle verification

Verified 31 October 2026 against synthetic Apex/Beacon data and the local PostgreSQL, Redis, private object-store, and Mailpit development stack.

## Delivered behavior

- Ordered recruitment rounds and immutable session revisions preserve draft/current/published pointers, timezone-aware intervals, buffers, capacity, venue/meeting details, panel identifiers, and frozen participants.
- Schedule publication uses an exact `ActionProposal` and attributable `ApprovalDecision`. The institution-level PostgreSQL advisory lock serializes the final current-registration, eligibility, scheduling-readiness, prerequisite, capacity, student, panel, and venue checks. Intervals use half-open semantics; configured buffers expand the conflict interval.
- Schedule proposals freeze recipient-specific notification content. A new timing or participant revision stales an older pending schedule action while preserving already decided history; the revised action must be reviewed again before students see it.
- Attendance revisions and source-backed employer outcome revisions are separate. Result publication points to one exact revision, so an internal correction remains private until separately approved. Offer, acceptance, and joining states remain separate fields.
- Coordinator lifecycle UI covers rounds, private session drafts, exact schedule publication, attendance, source-referenced results, report snapshots, registration close, drive close, and reopen. The student UI shows only the authenticated student's approved assignments and published result revisions.
- Operational and closure reports freeze their full dataset, revision references, denominators, counts, candidate rows, and canonical hash. Short-lived authenticated export grants produce private CSV output with spreadsheet-formula escaping.
- Closure requires closed registration, completed/cancelled sessions, no pending proposals, no pending/claimed/unknown deliveries, and no unacknowledged or high/critical cases. Completing a session requires attendance plus an outcome or explicitly acknowledged result gap for every published participant. Reopen and cancellation create new attributable report revisions rather than erasing history.
- Every P09 mutation records an institutional audit event. All nine new domain tables have forced institution row-level security and runtime-role grants.

## Requirement and invariant coverage

P09 implements FR-SCHED-01 through FR-SCHED-08, FR-RESULT-01 through FR-RESULT-05, FR-REPORT-01 through FR-REPORT-05, and FR-CLOSE-01 through FR-CLOSE-05. It specifically reinforces INV-02, INV-04, INV-05, INV-06, INV-08, INV-09, INV-10, INV-11, and INV-12.

## Verification evidence

The focused `test_complete_lifecycle.py` suite proves the synthetic intake-to-closure continuation: published drive and deterministic eligibility; submitted registration; private session drafting; exact schedule approval; student-only visibility; attendance without inferred rejection; source-backed result publication; corrected result privacy and revision history; session completion; deterministic report hash reproduction; controlled CSV download; closure mutation restriction; and attributable reopening. It also proves half-open adjacency and overlapping venue/panel/student rejection at the serialized publication boundary.

The migration was verified both as an existing database downgrade/upgrade (`P09 -> P08 -> P09`) and on an empty temporary database upgraded from the first revision through P09. The empty upgrade created all nine P09 tables.

Final results: 80 backend tests passed; Ruff and Mypy passed; OpenAPI contract drift was zero; API-client type checking passed; and Next.js lint plus the production build passed with both new lifecycle routes included.

Commands used for the final gate:

```text
uv run --project backend pytest backend/tests -q
uv run --project backend ruff check backend/src/placementos backend/tests backend/migrations/versions/20261031_0900_p09_complete_lifecycle.py
uv run --project backend mypy backend/src/placementos
uv run --project backend python scripts/check_contracts_drift.py
pnpm --filter @placementos/api-client typecheck
pnpm --filter @placementos/web lint
pnpm --filter @placementos/web build
```

## Local-development boundaries

JD interpretation and malware scanning still use explicit development fixtures; outbound email remains the Mailpit adapter and is not proof of delivery. Schedule notifications are frozen as exact P07-compatible drafts, while results use exact publication approval and authenticated portal visibility; any additional outbound result email still goes through the P07 communication approval/dispatch workflow. Google Calendar, Gmail, and Sheets remain deferred adapters and are not required for the local end-to-end lifecycle.
