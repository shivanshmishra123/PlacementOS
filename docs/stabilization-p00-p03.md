# P00-P03 Stabilization Record

Date: 29 October 2026  
Scope: prerequisite hardening completed before P04; no P05 work included.

## Outcome

The P00-P03 slices were re-audited against `Agents.md`, the product specification, and architecture invariants. The follow-up preserved their user journeys while closing authorization, tenant-isolation, upload-validation, and asynchronous-work gaps. The three original source inputs were also restored unchanged.

## Changes

- Added a restricted PostgreSQL runtime role, row-level security policies, composite tenant constraints, canonical state checks, and transaction-local institution scope. Alembic retains a separate migration-owner connection.
- Reloaded the current user, membership, role, and capabilities for every authenticated request. Inactive memberships and users are rejected; institutional administrators no longer inherit coordinator approval authority.
- Enforced assigned-coordinator object scope in domain services and workers. Added CSRF double-submit and trusted-origin checks for cookie-authenticated writes.
- Recorded attributable audit events with drive/company mutations and drive assignment creation.
- Bound upload sessions to their creator, drive, purpose, and expiry. The service validates actual bytes, size, content type, signature/container safety, checksum, and the configured scanner before promoting an object out of quarantine.
- Prevented failed or unaccepted sources from receiving download URLs and removed private object keys from public API responses.
- Moved extraction behind persisted jobs and Celery dispatch. Worker execution re-establishes institution scope and retries idempotently.
- Added explicit development scanner/model fixtures and production configuration guards. A mock can no longer silently present itself as a live provider.
- Updated the coordinator intake UI to poll persisted processing state and hand completed sources to the P04 review workspace.

## Evidence

- Migration `20261029_1000_stabilize_p01_p03_boundaries` applies runtime grants, data normalization, constraints, composite foreign keys, and RLS policies.
- Fresh database migration was exercised from base to head, downgraded to base, then upgraded to head again.
- Integration coverage includes CSRF/origin rejection, cross-institution denial, assigned-drive scope, pre-acceptance corrupt/spoofed upload rejection, asynchronous job state, and source provenance.
- The complete verification results are recorded in the P04 completion record in `PLAN.md`; generated OpenAPI and TypeScript contracts are checked for drift.

## Remaining release boundaries

The local scanner and deterministic JD interpreter are development fixtures. A real scanner, live model provider, production secrets, retention policy, and institutional real-data authorization remain P10 decisions. Gmail, Google Sheets, and Google Calendar integrations remain P11. These limits do not block the synthetic local P04 demonstration.
