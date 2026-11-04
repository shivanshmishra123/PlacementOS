# P13 measured expansion verification

Release 0.13.0 completes the demand-driven local Phase 13 slice. It optimizes the one bottleneck demonstrated by P10, adds revisioned institution operating limits, and verifies mixed-tenant load and restore scope. It does not authorize real student data, a live provider account, production deployment, or broader policy semantics.

## Prioritized evidence

The P10 evidence showed that deterministic eligibility was already well inside its target, while the full drive-list endpoint degraded under synchronized load because it hydrated complete revision, source, and extraction histories for an index screen. No observed evidence justified a new eligibility operator, scheduling rule, microservice split, HA topology, or model feature.

P13 therefore made an additive API change: `/api/v1/drive-summaries` returns only the indexed coordinator projection. The legacy `/api/v1/drives` contract remains available for compatibility, while the web drive index uses the summary projection. Four measured access-path indexes support institutional scope, creator/assignee access, and assignment lookup.

## Before and after

The local benchmark created 100 authenticated sessions split evenly between Apex and Beacon, exercised ordinary concurrency two and a synchronized 100-request burst, and checked every response item against the caller's institution.

| Measurement | Legacy full projection | Summary projection | Result |
| --- | ---: | ---: | --- |
| Ordinary p95 | 891.41 ms | 56.34 ms | Within the 500 ms target |
| Burst p95 | 4,141.82 ms | 2,531.55 ms | 38.88% lower |
| Median response payload | 8,853 bytes | 4,152 bytes | 53.1% smaller |
| Successful responses | 200/200 | 200/200 | Passed |
| Tenant-isolation violations | 0 | 0 | Passed |

This is synthetic local evidence, not a production capacity claim. The synchronized burst remains a stress observation; the ordinary-load target is the release gate. Raw results and index inventory are in `docs/evidence/p13-scaling.json`.

## Multi-institution operations

- A revisioned `institution_operating_policies` record owns onboarding state plus open-drive, import-row, and export-row limits. Revision conflicts fail closed and every change records an attributed reason and audit event.
- Only `config:manage` may revise the operating policy. Coordinators with `ops:view` can inspect it; institution administrators do not inherit drive authority.
- Quotas are enforced in domain/API services for drive creation, CSV/Sheets import preview, participant CSV export, and approved Sheets report export.
- PostgreSQL RLS, service predicates, and acceptance tests keep the policy and summary projection institution-scoped.
- The mixed-tenant benchmark used 50 sessions from each synthetic institution and observed no cross-tenant response item.

## Policy and scheduling extension review

No authorized institution rule or measured pilot request specified a new eligibility predicate, normalization, conflict rule, or scheduling operator. P13 deliberately makes no policy or scheduling semantic change. Existing immutable policy versions and half-open scheduling behavior therefore remain unchanged. A future requested extension must carry an explicit institution rule, a new versioned contract, and old-version regression coverage.

## Availability and recovery review

The demonstrated objectives remain a 24-hour RPO and 8-hour RTO. No evidence required an HA or managed-service topology change, so P13 does not claim one. Existing durable outbox, idempotency, unknown-outcome, retry, and restart tests remain the recovery boundary.

The P13 isolated restore recovered the database, workflow checkpoints, and 575 objects; matched selected whole-table and per-institution counts; matched every object hash; and reapplied the synthetic tombstone before exposure. It completed in 89.709 seconds (0.024919 hours), within the 8-hour objective. Pending work reconciliation remains mandatory before promotion. Raw evidence is in `docs/evidence/p13-backup-restore.json`.

## Verification commands

```text
uv run --project backend pytest backend/tests/unit/test_scaling.py backend/tests/integration/test_measured_scaling.py
uv run --project backend python scripts/benchmark_p13_scaling.py
uv run --project backend python scripts/backup_restore_drill.py --output docs/evidence/p13-backup-restore.json
```

The final release gate passed 116 backend tests, Ruff, mypy, frontend lint/typecheck/build, OpenAPI export and zero-drift validation, an empty-database upgrade/downgrade/re-upgrade rehearsal, release smoke, and the rendered keyboard/mobile accessibility audit. The release scan found no high-risk file pattern in 237 release files and no secret/content category in 3,166 workflow checkpoint rows. Evidence is retained under `docs/evidence/p13-*.json`. P11 live-account acceptance and every real-data readiness gate remain open.
