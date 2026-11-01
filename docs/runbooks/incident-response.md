# Security and privacy incident runbook

1. Stop the affected capability at the narrowest boundary: adapter, worker queue, account connection, object grant, session, or institution. Do not expand access to investigate.
2. Record time, correlation IDs, institution, resource references, current statuses, and the suspected exposure path. Keep private payloads in restricted evidence storage, not ordinary tickets/logs.
3. Preserve append-only audit, provider attempt, outbox, job, and checkpoint evidence. Do not edit historical approvals or outcomes.
4. Revoke compromised sessions/tokens/credentials in their authoritative service. Changed dependencies stale affected unclaimed work.
5. Determine whether an external effect is known, failed, or unknown. Unknown communications are reconciled before any retry.
6. Notify the configured security/incident owners and follow institution notification/legal policy. Repository documentation does not itself establish compliance obligations.
7. Remediate, add a regression test, rotate affected secrets, and run the secret/checkpoint scan. Restore service only after scoped authorization and recovery checks pass.

For suspected cross-tenant or cross-student access, preserve the exact endpoint/object IDs and deny path first. Use synthetic or minimally scoped administrative queries to reproduce; never browse unrelated student records.
