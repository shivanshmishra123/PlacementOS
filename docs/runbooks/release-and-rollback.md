# Release and rollback runbook

## Release sequence

1. Freeze a reviewed commit and immutable image tag. Build `infra/docker/api.Dockerfile` and `infra/docker/web.Dockerfile`.
2. Inject `.env.pilot` from the institution secret/configuration service. Never commit it. Run `scripts/pilot_preflight.py`; a nonzero result blocks real data.
3. Back up the current database, objects, checkpoints, and tombstone ledger. Verify the last restore drill is within policy.
4. Run the one-shot migration service. Run `scripts/setup_workflow_checkpoints.py` through the checkpoint job.
5. Start API without external writes, then worker/beat. Confirm `/health`, `/ready`, graph compatibility, and aggregate operational state.
6. Start web and the private gateway behind the institution TLS ingress. Run `scripts/release_smoke.py` and the main synthetic acceptance journey.
7. Enable traffic. Live mail/model/provider actions remain disabled until their separate configuration and approval gates are complete.

The supplied `compose.pilot.yaml` publishes only the gateway on loopback for staging validation. PostgreSQL and Redis have no host ports; backend processes use a private network plus a provider-egress network. Replace the template values and place TLS/rate limiting at the approved ingress.

## Rollback

- Prefer rolling application images back while leaving a forward-compatible database at the newest schema.
- Before a database downgrade, prove the previous image cannot use the current schema, back up again, inspect the migration downgrade for data loss, and stop all writers.
- Waiting `drive-lifecycle-v1`/state-schema-1 runs may resume only on a compatible image. Unknown versions remain `incompatible`; never rewrite checkpoints by hand.
- After rollback, run readiness, authorization, operations, dispatch-unknown, outbox-age, and workflow reconciliation checks before restoring traffic.
- A rollback does not unsend mail, retract published data, or erase audit history. Use new attributed revisions/proposals for business corrections.

## Secret rotation and revoked integrations

- Rotate in the external secret service and restart only affected adapters. Do not put old/new values in tickets or logs.
- Revoke affected sessions/connections and stale dependent proposals/operations.
- A revoked provider connection remains blocked until a new connection revision is explicitly configured and exact affected actions are reviewed again.
