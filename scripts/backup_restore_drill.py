"""Restore PostgreSQL, objects and checkpoints into isolated temporary targets."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from placementos.core.config import settings

logger = logging.getLogger("placementos.backup_drill")

TABLES = [
    "institutions",
    "student_profiles",
    "drives",
    "action_proposals",
    "dispatch_operations",
    "workflow_runs",
    "exception_cases",
    "integration_connections",
    "institution_operating_policies",
    "audit_logs",
]

INSTITUTION_SCOPED_TABLES = [
    "student_profiles",
    "drives",
    "action_proposals",
    "dispatch_operations",
    "workflow_runs",
    "exception_cases",
    "integration_connections",
    "institution_operating_policies",
]


def docker_postgres(*command: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", *command],
        input=input_bytes,
        capture_output=True,
        check=True,
    )


def count_table(database: str, table: str) -> int:
    query = f"SELECT CASE WHEN to_regclass('public.{table}') IS NULL THEN 0 ELSE (SELECT count(*) FROM {table}) END;"
    result = docker_postgres("psql", "-U", "placementos", "-d", database, "-Atc", query)
    return int(result.stdout.decode().strip())


def count_table_by_institution(database: str, table: str) -> dict[str, int]:
    query = (
        f"SELECT institution_id::text, count(*) FROM {table} "
        "GROUP BY institution_id ORDER BY institution_id;"
    )
    result = docker_postgres("psql", "-U", "placementos", "-d", database, "-AtF", "|", "-c", query)
    return {
        institution_id: int(count)
        for line in result.stdout.decode().splitlines()
        for institution_id, count in [line.split("|", 1)]
    }


def object_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        use_ssl=settings.S3_SECURE,
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(output_path: Path) -> dict[str, object]:
    started_at = datetime.now(UTC)
    started = time.perf_counter()
    suffix = uuid.uuid4().hex[:10]
    restore_database = f"placementos_restore_{suffix}"
    restore_bucket = f"placementos-restore-{suffix}"
    tombstone_key = f"restore-drill/{suffix}.txt"
    s3 = object_client()
    source_bucket = settings.S3_BUCKET_NAME
    created_source_fixture = False

    try:
        try:
            s3.head_bucket(Bucket=source_bucket)
        except ClientError:
            s3.create_bucket(Bucket=source_bucket)
        s3.put_object(Bucket=source_bucket, Key=tombstone_key, Body=b"P10 tombstone restore fixture")
        created_source_fixture = True

        dump = docker_postgres("pg_dump", "-U", "placementos", "-Fc", "-d", "placementos").stdout
        source_counts = {table: count_table("placementos", table) for table in TABLES}
        source_tenant_counts = {
            table: count_table_by_institution("placementos", table)
            for table in INSTITUTION_SCOPED_TABLES
        }

        object_backup: dict[str, bytes] = {}
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=source_bucket):
            for item in page.get("Contents", []):
                key = item["Key"]
                object_backup[key] = s3.get_object(Bucket=source_bucket, Key=key)["Body"].read()

        docker_postgres("createdb", "-U", "placementos", restore_database)
        docker_postgres(
            "pg_restore",
            "-U",
            "placementos",
            "-d",
            restore_database,
            "--no-owner",
            input_bytes=dump,
        )
        restored_counts = {table: count_table(restore_database, table) for table in TABLES}
        restored_tenant_counts = {
            table: count_table_by_institution(restore_database, table)
            for table in INSTITUTION_SCOPED_TABLES
        }

        s3.create_bucket(Bucket=restore_bucket)
        for key, data in object_backup.items():
            s3.put_object(Bucket=restore_bucket, Key=key, Body=data)
        restored_hashes = {
            key: sha256(s3.get_object(Bucket=restore_bucket, Key=key)["Body"].read())
            for key in object_backup
        }
        source_hashes = {key: sha256(data) for key, data in object_backup.items()}

        # Reapply an explicit deletion record only against the isolated restored bucket.
        s3.delete_object(Bucket=restore_bucket, Key=tombstone_key)
        remaining = s3.list_objects_v2(Bucket=restore_bucket, Prefix=tombstone_key).get("KeyCount", 0)
        duration_seconds = round(time.perf_counter() - started, 3)
        passed = (
            source_counts == restored_counts
            and source_tenant_counts == restored_tenant_counts
            and source_hashes == restored_hashes
            and remaining == 0
        )
        report: dict[str, object] = {
            "drill_started_at": started_at.isoformat(),
            "drill_completed_at": datetime.now(UTC).isoformat(),
            "duration_seconds": duration_seconds,
            "rpo_objective_hours": 24,
            "rto_objective_hours": 8,
            "rto_observed_hours": round(duration_seconds / 3600, 6),
            "database_counts_match": source_counts == restored_counts,
            "source_counts": source_counts,
            "restored_counts": restored_counts,
            "tenant_partition_counts_match": source_tenant_counts == restored_tenant_counts,
            "source_tenant_counts": source_tenant_counts,
            "restored_tenant_counts": restored_tenant_counts,
            "object_count": len(object_backup),
            "object_hashes_match": source_hashes == restored_hashes,
            "checkpoint_tables_included_in_database_dump": True,
            "tombstone_reapplied": remaining == 0,
            "pending_work_reconciliation_required_before_promotion": True,
            "passed": passed,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report
    finally:
        try:
            docker_postgres("dropdb", "-U", "placementos", "--if-exists", restore_database)
        except subprocess.CalledProcessError as exc:
            logger.warning("Temporary restore database cleanup failed: %s", exc)
        try:
            listed = s3.list_objects_v2(Bucket=restore_bucket).get("Contents", [])
            if listed:
                s3.delete_objects(
                    Bucket=restore_bucket,
                    Delete={"Objects": [{"Key": item["Key"]} for item in listed]},
                )
            s3.delete_bucket(Bucket=restore_bucket)
        except ClientError as exc:
            logger.warning("Temporary restore bucket cleanup failed: %s", exc)
        if created_source_fixture:
            s3.delete_object(Bucket=source_bucket, Key=tombstone_key)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/evidence/p10-backup-restore.json")
    report = run(Path(parser.parse_args().output))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
