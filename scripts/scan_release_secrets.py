"""Scan release files and durable checkpoints for high-risk secret material."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from placementos.core.config import settings

FILE_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "nonempty_smtp_password": re.compile(
        r"^PLACEMENTOS_SMTP_PASSWORD[\t ]*=[\t ]*[^\s$][^\r\n]*$", re.MULTILINE
    ),
}
CHECKPOINT_PATTERNS = {
    "session_token": re.compile(r"session[_-]?token", re.IGNORECASE),
    "csrf_token": re.compile(r"csrf[_-]?token", re.IGNORECASE),
    "password": re.compile(r"password", re.IGNORECASE),
    "provider_secret": re.compile(r"(?:client|smtp|s3)[_-]?secret", re.IGNORECASE),
    "signed_url": re.compile(r"(?:signed|presigned)[_-]?url", re.IGNORECASE),
    "message_or_recipient_content": re.compile(r"(?:message_body|recipient_email|document_text)", re.IGNORECASE),
}


def release_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True,
        capture_output=True,
    )
    return [Path(item.decode()) for item in result.stdout.split(b"\0") if item]


def scan_files() -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for file_path in release_files():
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for name, pattern in FILE_PATTERNS.items():
            if pattern.search(content):
                findings.append({"category": name, "path": file_path.as_posix()})
    return findings


def scan_checkpoints() -> tuple[int, list[str]]:
    with (
        psycopg.connect(settings.WORKFLOW_DATABASE_URL) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            """
            SELECT checkpoint::text || metadata::text AS content
            FROM workflow_checkpoints.checkpoints
            UNION ALL
            SELECT encode(blob, 'escape') AS content
            FROM workflow_checkpoints.checkpoint_writes
            """
        )
        values = [row[0] for row in cursor.fetchall()]
    categories = sorted(
        name
        for name, pattern in CHECKPOINT_PATTERNS.items()
        if any(pattern.search(value) for value in values)
    )
    return len(values), categories


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/evidence/p10-secret-scan.json")
    args = parser.parse_args()
    files = release_files()
    file_findings = scan_files()
    checkpoint_rows, checkpoint_findings = scan_checkpoints()
    report = {
        "scanned_at": datetime.now(UTC).isoformat(),
        "release_files_scanned": len(files),
        "checkpoint_rows_scanned": checkpoint_rows,
        "file_findings": file_findings,
        "checkpoint_findings": checkpoint_findings,
        "passed": not file_findings and not checkpoint_findings,
        "scope_note": "Known synthetic development credentials are not classified as production secrets.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
