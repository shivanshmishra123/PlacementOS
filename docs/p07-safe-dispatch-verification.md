# P07 exact proposals, approvals, and safe dispatch

Status: completed local implementation and verification on 30 October 2026.

## Delivered behavior

- A coordinator can create a deterministic communication draft for a published drive using current eligible students, submitted registrants, students with document findings, or an explicitly reviewed student list.
- The backend computes the audience; it freezes normalized recipients, inclusion reasons, exclusion/duplicate/unresolved counts, merge values, exact personalized subject/body text, and hashes. No model selects recipient IDs.
- Review submission creates an immutable `send_communication` action proposal bound to the drive revision, evaluation ID and fingerprint, policy, content, audience, sender configuration, execution bounds, and expiry.
- The approval center exposes every exact render and supports approve, reject, and revision-request decisions with optimistic hash/revision checks.
- Approval atomically commits the decision, audit event, batch, unique per-recipient operations, and durable outbox events. Approval does not call SMTP.
- The relay publishes tenant-scoped outbox intents. The worker revalidates approval authority, current evaluation, drive state/hold, sender revision, expiry, audience/content hashes, contact revision, and the development allowlist before claiming an operation.
- Each provider call has a persisted attempt and lease. Duplicate tasks return the existing terminal state. A claim that expires after entering the provider boundary becomes `unknown`, not an automatic resend.
- Mailpit SMTP acceptance is recorded as `provider_accepted`, never as delivery. Unknown outcomes require evidence-backed reconciliation before a retry can be queued.
- Cancellation stops only pending/unclaimed operations. Claimed, accepted, failed, and unknown history is retained and the UI states that transmitted mail cannot be recalled.

The current deterministic templates are backed by facts available through P06: drive announcements, deadline reminders, missing-document reminders, and clarifications. Interview schedules, schedule corrections, and result notices remain registered extension kinds but are not exposed until P09 supplies approved published schedule/result facts. This prevents a free-text message from masquerading as an authorized schedule or result.

## Local demonstration

1. Start PostgreSQL, Redis, object storage, and Mailpit with `docker compose up -d postgres redis object-store mailpit`.
2. Start the API and a Celery worker. Start Celery beat as a separate process, or invoke the relay task manually in development.
3. Publish a drive with a current completed evaluation.
4. Open `/coordinator/drives/{drive_id}/communications`, choose a message kind and audience, and freeze the draft.
5. Inspect its counts and exact personalized sample, then submit it for review.
6. Open `/coordinator/approvals`, inspect all exact recipients/renders, and approve.
7. The outbox relay queues the individual logical operations. The worker sends each exact frozen message to Mailpit.
8. Inspect Mailpit at `http://127.0.0.1:8025`. The batch UI reports SMTP acceptance separately from delivery.

There is deliberately no direct send HTTP endpoint. Calling a worker with an invented or rejected operation ID cannot construct send authority because the worker requires the persisted approved proposal, decision, batch, recipient snapshot, and current dependencies.

## Verification evidence

- Backend suite: `74 passed`.
- P07 integration suite: exact hash conflict, atomic decision/outbox records, tenant-scoped relay, duplicate task deduplication, one Mailpit message for one logical operation, unknown timeout classification/reconciliation, and rejected-proposal non-execution all passed.
- Python: Ruff and mypy passed.
- Database: P07 migration upgraded, downgraded to P06, and upgraded to head successfully.
- Contracts: OpenAPI regenerated and the contract drift check passed.
- Frontend: API client typecheck, Next lint, and production build passed. The build includes the drive communication workspace and approval/dispatch center.

## Production transport readiness

Mailpit is a development sink only. Configuration validation refuses `EMAIL_ADAPTER_MODE=mailpit` in production. A real-data pilot remains blocked until an authorized institution and operator select and verify a production mail adapter with all of the following:

- verified sender identity and reply/support address ownership;
- recipient domains/allowlist policy and test-recipient isolation;
- provider quotas, rate limits, batch limits, and backoff expectations;
- exact meaning of provider acceptance, delivery, bounce, complaint, and suppression receipts;
- provider idempotency behavior and the stability of the PlacementOS operation key;
- lookup/reconciliation support for an ambiguous timeout;
- credential encryption, rotation, revocation, scope, and connection-revision behavior;
- webhook authenticity and missed-event reconciliation if delivery events are enabled;
- institutional privacy, retention, support ownership, and incident procedures.

The generic SMTP adapter is an implementation boundary, not a production-readiness claim: SMTP commonly cannot prove inbox delivery or reliably look up an ambiguous transaction. Production sending must remain disabled until the selected provider contract and operating configuration are recorded and tested in P10/P11 scope.
