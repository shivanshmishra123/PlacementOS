# P10 hardened MVP and pilot-readiness verification

Verified 1 November 2026 against synthetic Apex/Beacon data and the local PostgreSQL, Redis, SeaweedFS, Mailpit, FastAPI, Next.js, and Microsoft Edge environment.

## Release decision

PlacementOS 0.10.0 is releaseable as a **synthetic-data local MVP demonstration**. It is **not ready for a real-data pilot or live sending**. The product and CLI preflight state this explicitly; production startup rejects development identity/scanner/model/mail choices, local database/object credentials, HTTP browser origins, placeholder values, missing retention/backup configuration, and unnamed owners.

Current real-data blockers include the unimplemented production OIDC and ClamAV adapters, OIDC/membership ownership, institution-approved permission and academic configuration, reviewed model policy/provider choice, verified production sender, private production object storage, retention/deletion policy, encrypted backup schedule and accepted restore drill, approved region, and named operations/security/backup/incident owners. Configuration cannot mark an unimplemented adapter ready. The institution/provider decisions were not invented during development.

## Delivered hardening

- Restricted pilot-readiness and operational-health APIs plus coordinator/admin UI. Projections contain aggregate counts and safe resource state only.
- Structured privacy-safe access events, validated correlation IDs, no-store private responses, frame/sniff/referrer/permissions headers, real Redis readiness, and production missing-origin CSRF rejection.
- Configurable upload, PDF-page, extracted-text, model-call, and token limits. Development adapters are visible and fail closed in production.
- Skip navigation, strong focus indicators, reduced-motion handling, menu semantics, named controls, responsive operations UI, and honest synthetic-only status.
- API/web container images, non-root processes, one-shot migration/checkpoint jobs, injected secrets, private service network, limited provider egress, and gateway-only staging exposure.
- Operator, incident, backup/retention, release, and rollback runbooks.

## Security and resilience evidence

The cumulative P02-P09 integration suite plus `test_pilot_hardening.py` covers cross-institution/student ID denial, runtime RLS scope, revoked membership/session, CSRF/origin enforcement, private export grants, safe CSV, worker/resume authorization, stale approvals, duplicate relay/task delivery, provider timeout `unknown`, cancellation races, immutable uploads, corrupt/encrypted/mismatched files, prompt injection, bounded model failure/manual fallback, restart-safe workflow pauses, checkpoint/domain crash gaps, and closure blocking on uncertain work.

The release scan inspected 196 release files and 1,296 durable checkpoint/write rows. It found no high-risk file secrets and no session/CSRF tokens, passwords, provider secrets, signed URLs, document text, recipient email, or message bodies in checkpoints. See `docs/evidence/p10-secret-scan.json`.

## Performance and cost evidence

`scripts/benchmark_pilot_envelope.py` evaluated 5,000 deterministic academic snapshots across 20 policies (100,000 decisions). Per-drive maximum was 218.42 ms, far below the 60-second target. The exact outcome distribution across all drives was 57,700 eligible, 37,000 ineligible, and 5,300 needs-review.

With 100 active authenticated sessions and ordinary peak concurrency of two requests, the coordinator drive-list p95 was 151.19 ms (100/100 HTTP 200) against a database containing 382 drives. A deliberately synchronized 100-request burst also completed 100/100 but had p95 6.65 seconds. That burst is a documented capacity limit and a P13 optimization candidate; it is not represented as meeting the ordinary-load 500 ms target.

Eligibility makes zero model calls. Parser/model caps and the explicit model mode are recorded in `docs/evidence/p10-performance.json`; production cost remains unapproved until the institution selects a provider/policy.

## Accessibility/usability evidence

The rendered Edge audit used keyboard events and a 390×844 viewport. It verified the skip link and main target, persona trigger/menu and coordinator/student switching, operations status/refresh, approval heading and accessible form names, separate student eligibility/document/registration messaging, server deadline semantics, named file controls, no page-level mobile overflow, and named interactive accessibility-tree nodes. All 18 checks passed. This is engineering evidence, not a WCAG certification; see `docs/evidence/p10-accessibility.json`.

## Backup and recovery evidence

The isolated drill restored PostgreSQL records plus workflow checkpoints and 389 objects, matched selected table counts and every object hash, and reapplied a deletion record in the restored bucket before exposure. Observed restore time was 49.187 seconds versus the configured RTO objective of 8 hours; the RPO objective is 24 hours. Pending work reconciliation is still mandatory before promotion. See `docs/evidence/p10-backup-restore.json` and the backup runbook.

## Verification commands

```text
uv run --project backend pytest backend/tests -q
uv run --project backend ruff check backend/src backend/tests
uv run --project backend mypy backend/src
uv run --project backend python scripts/export_openapi.py
uv run --project backend python scripts/check_contracts_drift.py
pnpm lint
pnpm typecheck
pnpm build
node scripts/accessibility_audit.mjs
uv run --project backend python scripts/benchmark_pilot_envelope.py
uv run --project backend python scripts/backup_restore_drill.py
uv run --project backend python scripts/scan_release_secrets.py
uv run --project backend python scripts/release_smoke.py
uv run --project backend python scripts/pilot_preflight.py
docker compose -f compose.pilot.yaml config --quiet
docker build -f infra/docker/api.Dockerfile -t placementos-api:0.10.0 .
docker build -f infra/docker/web.Dockerfile -t placementos-web:0.10.0 .
```

Final regression result: 89 backend tests passed; Ruff, Mypy, OpenAPI drift, frontend lint/type checks, and the production Next.js build passed. Release smoke passed all eight checks. Both non-root images built and passed isolated HTTP/readiness checks; the migration image reported `p09_complete_lifecycle (head)`. An empty temporary database upgraded through every revision, downgraded P09 to P08, and upgraded to head again. See `docs/evidence/p10-deployment.json`.

## Deferred scope

Gmail, Google Sheets, and Google Calendar connectors remain P11 and require explicit account authorization. Advanced deterministic exception impact/recovery remains P12. The 100-request synchronized-burst drive-list bottleneck is recorded for measured P13 optimization. No deployment, external account connection, real student data, live email, or production provider action occurred in P10.
