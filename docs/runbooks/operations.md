# PlacementOS operations runbook

Use this runbook for the synthetic release and any later institution-approved pilot. The authenticated coordinator/admin screen at `/coordinator/operations` exposes aggregate state only; it never exposes recipients, message bodies, document text, signed URLs, or secrets.

## First checks

1. Check `/health` for process liveness and `/ready` for PostgreSQL and Redis readiness. A live but not-ready API must not receive stateful traffic.
2. Sign in with an assigned operations capability and inspect `/api/v1/operations/health`.
3. Record the correlation ID, institution, alert code, affected resource IDs, and current status. Do not copy raw student data into tickets or ordinary logs.
4. Confirm the API, worker, beat, PostgreSQL, Redis, object store, scanner, and mail adapter versions before changing state.

## Stuck outbox or workflow command

- An outbox age of 300 seconds or more raises `OUTBOX_AGE_HIGH`.
- Verify Celery beat is running and the broker is ready. Restarting beat/worker is safe because relay and execution use persisted intent and uniqueness keys.
- Inspect pending/published rows by institution and operation key. Never create a replacement proposal or directly call the provider to “unstick” work.
- Restore the broker, then run the canonical relay task. Confirm that the original operation was claimed once and its attempt history advanced.
- If the dependency revision changed, leave the old operation stale/cancelled and create a new reviewed proposal.

## Unknown email outcome

- `UNKNOWN_SENDS` is critical. Do not retry automatically: the provider may have accepted the first attempt.
- Use the approved sender connection and provider request/message reference to reconcile acceptance or delivery evidence.
- Record the evidence through the reconciliation command. Only a known-safe failure can become retryable.
- If evidence remains inconclusive, keep the operation `unknown`, notify the incident owner, and block drive closure.

## Failed job or scanner/parser outage

- A terminal job raises `TERMINAL_JOBS`. Read the safe error category and immutable input reference, not document content in logs.
- A scanner outage blocks acceptance; it never silently changes a document to valid. A parser/model outage falls back to attributed manual entry where supported.
- Known-safe retryable work retains the same business operation key. Resource-limit or malicious-file findings require replacement/review, not repeated parsing.

## Workflow resume failure

- Confirm the authenticated decision/reference exists, belongs to the same institution/drive, is current, and has not expired.
- Confirm the run graph version/state schema is supported. An incompatible run remains stopped with an owned exception case.
- Reconcile domain state before checkpoint state. If the domain operation already committed, replay must reuse it rather than create another proposal/effect.

## Drive cancellation

- Use the lifecycle cancellation command with an attributable reason.
- Unclaimed work may be cancelled. Sent/accepted work is historical and cannot be recalled by changing database state.
- Preserve result, notification, approval, and audit history; create correction communication through the normal exact-proposal path when needed.
