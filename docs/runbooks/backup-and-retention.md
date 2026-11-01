# Backup, restore, deletion, and retention runbook

PlacementOS targets an RPO of 24 hours and an RTO of 8 hours for a configured pilot. These are objectives, not guarantees, until the institution selects encrypted backup storage, retention values, owners, and a recurring restore schedule.

## Backup scope

- PostgreSQL application records, Alembic version, audit history, outbox/jobs, and the private `workflow_checkpoints` schema.
- Every accepted/quarantined object version, generated export, and restricted evidence object required by retained records.
- The authorized deletion/tombstone ledger needed to reapply deletions after restore.
- Configuration versions, not live secret values. Secrets and encryption keys remain in the approved secret/KMS service.

Backups must be encrypted, access-scoped, region-approved, monitored, and expired using `BACKUP_RETENTION_DAYS`. Database and object snapshots from the same recovery point must be associated by an immutable backup identifier.

## Restore procedure

1. Declare an incident/recovery identifier and isolate a new database and private object bucket. Never restore over the active environment.
2. Restore PostgreSQL, including `workflow_checkpoints`, and verify the Alembic head and table counts.
3. Restore objects and compare content hashes/version references.
4. Reapply every deletion/tombstone recorded after the backup point before allowing any user or worker access.
5. Keep API, worker, beat, mail, and external writes disabled. Reconcile pending/claimed/unknown dispatch, jobs, workflow commands, leases, and waiting graph versions.
6. Run readiness, authorization, secret-leak, and synthetic acceptance checks. The incident owner explicitly authorizes promotion through the deployment process.
7. Record observed RPO/RTO and destroy the isolated restore only after evidence is retained.

The local drill is automated by:

```text
uv run --project backend python scripts/backup_restore_drill.py
```

It creates a validated temporary database and bucket, restores database/objects/checkpoints, compares counts and hashes, reapplies a synthetic tombstone only in the restored bucket, records evidence, then removes the isolated targets. It never deletes an application object except the exact synthetic fixture it creates.

## Retention and deletion

- Real-data operation is blocked until `RETENTION_POLICY_ID`, record/backup days, and an authorized deletion owner are configured.
- Retention applies to originals, revisions, extracted text, retained model data, checkpoints, exports, communications, logs, and backups.
- A content hash is still personal data when it can be linked back to a student.
- Deletion is an authorized workflow. Preserve the minimum nonpersonal audit structure while removing applicable payloads and object versions.
- Restoring an old snapshot never revives deleted data: reapply the tombstone ledger before exposure.
