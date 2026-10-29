# P06 participation verification

Verified 30 October 2026 against the local synthetic environment.

## Delivered boundaries

- Document requirements are immutable and bound to a drive revision. Validation records bind both the exact accepted document revision and the exact requirement.
- Student files remain private, keep original metadata and immutable revision history, and use short-lived owner/coordinator-scoped download URLs. Coordinator downloads are audited.
- Operational validation covers declared/actual size, extension, sniffed structure, parser integrity, development scanner result, configurable filename pattern, same-student duplicate triage, and text/manual-review state. It makes no authenticity claim.
- Readiness follows `blocked > needs_review > pending > ready` without changing academic eligibility.
- Drive publication reuses immutable action proposals and freezes student-visible facts, the current completed evaluation, registration window, withdrawal window, and document requirements. Publication does not dispatch communication.
- Registration uses the server clock with an inclusive opening and exclusive cutoff, current non-stale eligibility, registration-stage readiness, uniqueness, immutable evidence references, and append-only events.
- Changed eligibility retains submitted evidence on `eligibility_hold`. Restoration is never automatic; an assigned coordinator must provide a reason against a current eligible published evaluation.
- Coordinator views reconcile unique evaluated students across eligibility, readiness, and registration; export guards spreadsheet formula cells.

## Verification evidence

```text
uv run --project backend pytest backend/tests -q
69 passed

uv run --project backend ruff check backend/src backend/tests
All checks passed

uv run --project backend mypy backend/src
Success: no issues found in 49 source files

pnpm lint
No ESLint warnings or errors

pnpm typecheck
Passed for api-client and web

pnpm build
Next.js production build passed

uv run --project backend python scripts/check_contracts_drift.py
Zero schema drift

alembic downgrade p05_eligibility; alembic upgrade head
P06 downgrade/upgrade cycle passed
```

The integration scenario uses synthetic records, the local object store, and the explicit development scanner fixture. It does not authorize real student data or provider connections.
