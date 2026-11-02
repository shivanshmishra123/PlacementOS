# P12 structured exception recovery verification

Release 0.12.0 implements structured exception impact analysis and bounded recovery for synthetic local operation. It does not authorize or perform a live provider action, send a correction message, alter academic eligibility through AI output, or resolve an exception automatically.

## Implemented boundary

- Four discriminated impact inputs are supported: criteria change, current verified academic correction, deadline or schedule revision, and failed or unknown notification.
- Deterministic services calculate the affected set from immutable evaluations, revisions, registrations, published assignments, dispatch state, pending proposals, and provider mappings. Planner output cannot add or remove an affected student.
- Every impact revision freezes input references, a dependency snapshot and fingerprint, minimal student context, affected resources, summary counts, and a manual fallback.
- Recovery plans accept only five typed internal commands: place a drive hold, stale exact pending proposals, prepare an unsent correction draft, mark exact external mappings for reconciliation, or record a manual follow-up.
- A plan proposal freezes ordered steps, exact payloads, dependencies, preconditions, expected effects, approval type, and irreversible-effect notes. Unsupported actions such as direct email or calendar writes fail schema validation.
- The development planner is an explicit deterministic fixture with no mutation or provider tools. Production configuration rejects `PLACEMENTOS_EXCEPTION_PLANNER_MODE=fixture`; `disabled` preserves manual typed planning.
- Exact approval, active reviewer capability, proposal and plan hashes, expiry, case and drive state, and source freshness are rechecked before execution and every step.
- A new impact or plan revision marks the prior pending proposal and unexecuted steps stale; its approval hash cannot be reused.
- Each step commits atomically with its attempt record. Completed steps are not replayed. A later failure produces a visible `partial` execution and stops remaining work; coordinator cancellation marks only pending/running steps cancelled and preserves completed evidence.
- A prepared correction communication remains a draft with `send_status=not_proposed_or_sent`; ordinary communication proposal and approval controls still apply.
- A successful plan appends execution evidence but leaves the exception acknowledged for explicit coordinator resolution.

## Demonstrated scenarios

| Scenario | Expected local evidence |
| --- | --- |
| Minimum CGPA changes from 7.50 to 8.00 | Deterministic eligible-to-ineligible transitions are enumerated; an existing submitted registration is preserved; the approved plan places a hold and stales the exact pending proposal. |
| Verified academic correction | Only the referenced student is analyzed against the current verified revision and the two evaluation runs; the result changes from ineligible to eligible without a direct override. |
| Deadline changes after an accepted announcement | The announced student is included, old and new immutable drive revisions remain available, and registration state is never deleted or rewritten. |
| Notification outcome is unknown | Blind retry is prohibited; manual provider reconciliation is required; an approved plan stops as partial when a later exact precondition fails, while the unknown dispatch is unchanged. |
| Coordinator cancels queued recovery | Pending steps become cancelled, a later worker call remains cancelled, and the drive is not placed on hold. |
| Cross-institution request | The exception case and its recovery evidence are hidden with a not-found response. |

## Verification commands

Run from the repository root with the local PostgreSQL/Redis services available:

```text
uv run --project backend pytest backend/tests/unit/test_recovery.py backend/tests/integration/test_exception_recovery.py
uv run --project backend pytest backend/tests
uv run --project backend ruff check backend/src backend/tests backend/migrations/versions/20261103_0900_p12_exception_recovery.py
uv run --project backend mypy backend/src
uv run --project backend alembic -c backend/alembic.ini upgrade head
uv run --project backend python scripts/export_openapi.py
uv run --project backend python scripts/check_contracts_drift.py
pnpm lint
pnpm typecheck
pnpm build
```

Migration verification must cover an empty database and a populated P11 database upgraded to P12, plus P12 downgrade to `p11_google_connectors` and re-upgrade. The committed OpenAPI document is the current contract source.

Recorded local result on 3 November 2026: all nine focused recovery tests and all 111 backend tests passed; Ruff and mypy passed; OpenAPI drift was zero; frontend lint, typecheck, and the optimized Next.js build passed; the release scan found no repository or checkpoint secrets. The populated development database completed P12 downgrade/re-upgrade, and a disposable empty database completed the full migration chain, P12 downgrade, and re-upgrade before being removed.

## Remaining limits

The only automated local planner is a deterministic development fixture, not a live model-provider claim. Manual typed recovery remains the supported production fallback. P11 isolated live-account connector acceptance is still open, so P12 provider-mapping and notification recovery is evidenced with synthetic adapters only. Real student data, deployment, provider connections, and live messages remain blocked by the P10/P11 gates in `PLAN.md`.
