"""P10 pilot-readiness and privacy-safe operational projections."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import CLAMAV_ADAPTER_IMPLEMENTED, OIDC_ADAPTER_IMPLEMENTED, Settings
from placementos.models.communications import DispatchOperation, OutboxEvent
from placementos.models.intelligence import ActionProposal
from placementos.models.storage import DomainJob
from placementos.models.workflow import ExceptionCase, WorkflowCommand, WorkflowRun


def pilot_readiness_snapshot(config: Settings) -> dict[str, Any]:
    """Evaluate configuration without exposing any secret values."""
    checks = [
        (
            "oidc_identity",
            OIDC_ADAPTER_IMPLEMENTED
            and config.IDENTITY_MODE == "oidc"
            and bool(config.OIDC_ISSUER_URL and config.OIDC_CLIENT_ID and config.OIDC_MEMBERSHIP_OWNER),
        ),
        ("permissions_review", config.PERMISSIONS_MATRIX_REVIEWED),
        ("academic_configuration", config.ACADEMIC_CONFIGURATION_REVIEWED and config.INSTITUTION_TIMEZONE_CONFIRMED),
        (
            "real_malware_scanner",
            CLAMAV_ADAPTER_IMPLEMENTED and config.MALWARE_SCANNER_MODE == "clamav",
        ),
        (
            "model_policy",
            config.MODEL_POLICY_REVIEWED
            and (
                config.MODEL_INTERPRETER_MODE == "disabled"
                or bool(config.MODEL_PROVIDER_NAME and config.MODEL_ID and config.MODEL_DATA_REGION)
            ),
        ),
        (
            "production_sender",
            config.EMAIL_ADAPTER_MODE == "smtp"
            and config.LIVE_SEND_ENABLED
            and config.PRODUCTION_SENDER_VERIFIED,
        ),
        (
            "private_object_storage",
            config.S3_ENDPOINT_URL.startswith("https://")
            and not config.S3_ACCESS_KEY_ID.startswith("dev_")
            and config.S3_BUCKET_NAME != "placementos-dev",
        ),
        (
            "retention_and_deletion",
            bool(
                config.RETENTION_POLICY_ID
                and config.RECORD_RETENTION_DAYS
                and config.BACKUP_RETENTION_DAYS
                and config.DELETION_OWNER
            ),
        ),
        (
            "backup_restore",
            config.BACKUP_RESTORE_TESTED and bool(config.BACKUP_ENCRYPTION_KEY_ID),
        ),
        ("hosting_region", bool(config.DEPLOYMENT_REGION)),
        (
            "operational_ownership",
            bool(
                config.OPERATIONS_OWNER
                and config.SECURITY_OWNER
                and config.BACKUP_OWNER
                and config.INCIDENT_CONTACT
            ),
        ),
    ]
    implementation_blockers = {
        "oidc_identity": not OIDC_ADAPTER_IMPLEMENTED,
        "real_malware_scanner": not CLAMAV_ADAPTER_IMPLEMENTED,
    }
    results = [
        {
            "key": key,
            "ready": ready,
            "classification": (
                "configured"
                if ready
                else (
                    "implementation_required"
                    if implementation_blockers.get(key, False)
                    else "institution_configuration_required"
                )
            ),
        }
        for key, ready in checks
    ]
    blockers = [item["key"] for item in results if not item["ready"]]
    return {
        "release_version": config.RELEASE_VERSION,
        "environment": config.ENVIRONMENT,
        "synthetic_demo_ready": config.ENVIRONMENT != "production",
        "real_data_pilot_ready": not blockers and config.ENVIRONMENT == "production",
        "status": "real_data_ready" if not blockers and config.ENVIRONMENT == "production" else "synthetic_demo_only",
        "checks": results,
        "blockers": blockers,
        "development_adapters": {
            "identity": config.IDENTITY_MODE == "development_personas",
            "scanner": config.MALWARE_SCANNER_MODE == "development_fixture",
            "model": config.MODEL_INTERPRETER_MODE == "fixture",
            "mail": config.EMAIL_ADAPTER_MODE == "mailpit",
        },
    }


def _age_seconds(value: datetime | None, now: datetime) -> int | None:
    if value is None:
        return None
    return max(0, int((now - value).total_seconds()))


async def operational_snapshot(session: AsyncSession) -> dict[str, Any]:
    """Return aggregate identifiers/counts only; never message, document, or recipient content."""
    now = datetime.now(UTC)
    outbox_counts = dict(
        (
            await session.execute(
                select(OutboxEvent.status, func.count())
                .where(OutboxEvent.status.in_(["pending", "published"]))
                .group_by(OutboxEvent.status)
            )
        ).all()
    )
    oldest_outbox = await session.scalar(
        select(func.min(OutboxEvent.created_at)).where(
            OutboxEvent.status.in_(["pending", "published"])
        )
    )
    dispatch_counts = dict(
        (
            await session.execute(
                select(DispatchOperation.status, func.count())
                .where(DispatchOperation.status.in_(["pending", "claimed", "unknown", "failed"]))
                .group_by(DispatchOperation.status)
            )
        ).all()
    )
    job_counts = dict(
        (
            await session.execute(
                select(DomainJob.status, func.count())
                .where(
                    DomainJob.status.in_(
                        ["queued", "processing", "failed_retryable", "failed_terminal"]
                    )
                )
                .group_by(DomainJob.status)
            )
        ).all()
    )
    workflow_counts = dict(
        (
            await session.execute(
                select(WorkflowRun.status, func.count())
                .where(
                    WorkflowRun.status.in_(
                        [
                            "queued",
                            "running",
                            "waiting_clarification",
                            "waiting_policy_approval",
                            "waiting_publication_approval",
                            "waiting_communication_approval",
                            "waiting_input",
                            "held",
                            "failed",
                            "incompatible",
                        ]
                    )
                )
                .group_by(WorkflowRun.status)
            )
        ).all()
    )
    pending_commands = int(
        await session.scalar(
            select(func.count())
            .select_from(WorkflowCommand)
            .where(WorkflowCommand.status.in_(["pending", "published", "claimed"]))
        )
        or 0
    )
    pending_approvals = int(
        await session.scalar(
            select(func.count())
            .select_from(ActionProposal)
            .where(ActionProposal.state == "pending_approval")
        )
        or 0
    )
    open_cases = int(
        await session.scalar(
            select(func.count())
            .select_from(ExceptionCase)
            .where(ExceptionCase.status.in_(["open", "acknowledged"]))
        )
        or 0
    )
    oldest_age = _age_seconds(oldest_outbox, now)
    alerts: list[dict[str, Any]] = []
    if oldest_age is not None and oldest_age >= 300:
        alerts.append({"code": "OUTBOX_AGE_HIGH", "severity": "warning", "age_seconds": oldest_age})
    if int(dispatch_counts.get("unknown", 0)):
        alerts.append({"code": "UNKNOWN_SENDS", "severity": "critical", "count": int(dispatch_counts["unknown"])})
    if int(job_counts.get("failed_terminal", 0)):
        alerts.append({"code": "TERMINAL_JOBS", "severity": "warning", "count": int(job_counts["failed_terminal"])})
    return {
        "generated_at": now.isoformat(),
        "outbox": {"counts": outbox_counts, "oldest_age_seconds": oldest_age},
        "dispatch": {"counts": dispatch_counts},
        "jobs": {"counts": job_counts},
        "workflows": {"counts": workflow_counts, "pending_commands": pending_commands},
        "approvals": {"pending": pending_approvals},
        "exception_cases": {"open_or_acknowledged": open_cases},
        "alerts": alerts,
    }
