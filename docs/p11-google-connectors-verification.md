# P11 Google Workspace connector verification

## Status and safety boundary

Release 0.11.0 implements the disabled-by-default Google Workspace connector boundary. Local verification uses deterministic fake provider adapters and synthetic records. No Google account was connected, no live mailbox or spreadsheet was read, no Calendar event or watch was created externally, and no real recipient was contacted.

P11-T01 through P11-T07 are implemented. P11-T08 and P11-T09 remain open because the required isolated live-account acceptance needs explicit owner authorization plus an OAuth client, isolated Google account, 32-byte base64url token-encryption key, and publicly reachable HTTPS webhook endpoint.

## Provider contracts and scopes

The OAuth web-server flow uses one-time state, PKCE, offline access, incremental authorization, server-side code exchange, encrypted refresh tokens, and a local post-callback redirect. Official contract: <https://developers.google.com/identity/protocols/oauth2/web-server>.

Enabled features request only these feature scopes in addition to `openid email`:

| Feature | Scope | Boundary |
| --- | --- | --- |
| Gmail JD intake | `https://www.googleapis.com/auth/gmail.readonly` | Exact message and optional attachment ID; no mailbox enumeration endpoint. |
| Sheets roster import | `https://www.googleapis.com/auth/spreadsheets.readonly` | Exact spreadsheet and range, preview before commit. |
| Sheets report export | `https://www.googleapis.com/auth/spreadsheets` | Exact approved spreadsheet/range and RAW frozen values. |
| Calendar events | `https://www.googleapis.com/auth/calendar.events.owned` | Owned calendars only; exact approved event and explicit `sendUpdates`. |

References: [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes), [Gmail messages](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages), [Gmail attachments](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments/get), [Sheets values](https://developers.google.com/workspace/sheets/api/guides/values), [Sheets batch update](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdate), [Calendar scopes](https://developers.google.com/workspace/calendar/api/auth), [Calendar insert](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert), [Calendar update](https://developers.google.com/workspace/calendar/api/v3/reference/events/update), and [Calendar watch](https://developers.google.com/workspace/calendar/api/v3/reference/events/watch).

The implementation does not request Gmail send, unrestricted Gmail, or Google Drive scopes. Gmail readonly is classified as restricted by Google and therefore requires the institution to complete applicable consent-screen, verification, privacy, and data-use review before any real deployment.

## Implemented controls

- OAuth tokens and PKCE verifiers use AES-GCM with a fresh nonce. Production requires an externally supplied 32-byte base64url encryption key.
- Tokens never enter browser storage, API responses, job payloads, checkpoints, logs, or fixtures.
- Disconnect clears usable grants/token state, increments the connection revision, stops active webhook channels, and invalidates queued/claimed work.
- Gmail captures immutable bytes, provider identifiers, source hash, sender, subject, receipt time, thread/history identifiers, and the selecting membership.
- Sheets import re-reads and fingerprints the range at commit and checks expected academic revisions before using the existing import service.
- Sheets/Calendar writes freeze exact payload and dependencies in an approval proposal. Execution rechecks the reviewer capability, proposal hash, connection revision, drive state, and expiry.
- Operations have a unique business key, durable attempts, bounded retry for known-safe failures, and an `unknown` terminal state for ambiguous write outcomes.
- Calendar watches use server-generated signed channel IDs of at most 64 characters, random channel tokens stored only as hashes, verified resource IDs, expiry, and message-number deduplication.
- External Calendar change signals mark provider mappings for reconciliation; they never overwrite an internal schedule.

## Verification commands

The final run should include:

```text
uv run --project backend ruff check backend/src backend/tests
uv run --project backend mypy backend/src
uv run --project backend pytest backend/tests
uv run --project backend alembic -c backend/alembic.ini current
uv run --project backend python scripts/export_openapi.py
uv run --project backend python scripts/check_contracts_drift.py
pnpm lint
pnpm typecheck
pnpm build
```

Targeted local connector evidence covers token encryption/tamper rejection, narrow scopes, sheet mapping/fingerprints, signed callback tenant resolution, explicit Gmail capture, stale sheet source, tenant isolation, approved exact write/idempotency, bounded 429 retry, ambiguous outcome suppression, disconnect invalidation, Calendar watch registration, and webhook rejection/deduplication.

Recorded local result on 2 November 2026: Ruff and mypy passed, the complete backend suite passed with 102 tests, OpenAPI drift was zero, frontend lint/typecheck/build passed, and the P11 migration passed empty-database upgrade plus populated-database downgrade/upgrade verification.

## Live acceptance checklist (not yet executed)

Use an isolated Google Workspace test account and synthetic files only. Record consent scopes, token refresh/revocation, an explicitly selected Gmail message/attachment, Sheets preview/commit and approved export, Calendar create/update with each intended notification mode, watch renewal/expiry, external edit discrepancy, 429/backoff, network ambiguity, duplicate delivery, disconnect, and manual fallback. Revoke and delete the test credentials after evidence capture. Do not use a personal mailbox, production spreadsheet, real student record, or real attendee.
