"""Durable outbox relay and per-recipient controlled email execution for P07."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select

from placementos.core.config import settings
from placementos.core.database import async_session_maker
from placementos.models.communications import (
    AudienceRecipient,
    AudienceSnapshot,
    CommunicationDraft,
    DispatchAttempt,
    DispatchBatch,
    DispatchOperation,
    OutboxEvent,
)
from placementos.models.eligibility import EvaluationRun
from placementos.models.identity import AuditLog, Institution, Membership, User
from placementos.models.intelligence import ActionProposal, ApprovalDecision
from placementos.models.recruitment import Drive
from placementos.services.communications import contact_revision, sender_connection_revision
from placementos.services.mail import EmailAdapter, FrozenEmail, get_email_adapter

LEASE_SECONDS = 60


async def _refresh_batch(session, batch_id: uuid.UUID) -> None:
    batch = await session.get(DispatchBatch, batch_id)
    if not batch:
        return
    counts = dict(
        (
            await session.execute(
                select(DispatchOperation.status, func.count())
                .where(DispatchOperation.dispatch_batch_id == batch_id)
                .group_by(DispatchOperation.status)
            )
        ).all()
    )
    batch.pending_count = int(counts.get("pending", 0)) + int(counts.get("claimed", 0))
    batch.accepted_count = int(counts.get("provider_accepted", 0))
    batch.delivered_count = int(counts.get("delivered", 0))
    batch.failed_count = int(counts.get("failed", 0))
    batch.unknown_count = int(counts.get("unknown", 0))
    batch.cancelled_count = int(counts.get("cancelled", 0))
    if batch.pending_count:
        batch.status = "processing"
    elif batch.unknown_count:
        batch.status = "partial"
    elif batch.failed_count:
        batch.status = "partial"
    elif batch.cancelled_count and batch.cancelled_count == batch.total_count:
        batch.status = "cancelled"
    else:
        batch.status = "completed"


async def relay_pending_outbox(limit: int = 100) -> int:
    """Publish due durable intents. Duplicate publish remains safe at operation claim."""
    from placementos.workers.dispatch_tasks import dispatch_operation_task

    now = datetime.now(UTC)
    async with async_session_maker() as discovery_session:
        institution_ids = (
            (
                await discovery_session.execute(
                    select(Institution.id).where(Institution.is_active.is_(True))
                )
            )
            .scalars()
            .all()
        )
    published = 0
    for institution_id in institution_ids:
        if published >= limit:
            break
        published += await _relay_tenant_outbox(
            institution_id,
            now=now,
            limit=limit - published,
            task=dispatch_operation_task,
        )
    return published


async def _relay_tenant_outbox(institution_id, *, now: datetime, limit: int, task) -> int:
    """Relay with an explicit tenant scope so row security applies to workers too."""
    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        events = (
            (
                await session.execute(
                    select(OutboxEvent)
                    .join(
                        DispatchOperation,
                        DispatchOperation.id == OutboxEvent.aggregate_id,
                    )
                    .where(
                        OutboxEvent.next_attempt_at <= now,
                        DispatchOperation.status == "pending",
                        or_(
                            OutboxEvent.status == "pending",
                            and_(
                                OutboxEvent.status == "published",
                                OutboxEvent.published_at.is_not(None),
                            ),
                        ),
                    )
                    .order_by(OutboxEvent.created_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        published = 0
        for event in events:
            event.publish_attempts += 1
            try:
                task.delay(str(event.aggregate_id), str(event.institution_id))
                event.status = "published"
                event.published_at = now
                event.next_attempt_at = now + timedelta(seconds=30)
                event.last_error = None
                published += 1
            except Exception as exc:  # broker boundary: retain durable intent
                event.last_error = str(exc)[:1000]
                event.next_attempt_at = now + timedelta(seconds=min(300, 2**event.publish_attempts))
        await session.commit()
        return published


async def _cancel_claim(session, operation: DispatchOperation, code: str, detail: str) -> str:
    operation.status = "cancelled"
    operation.completed_at = datetime.now(UTC)
    operation.last_error_code = code
    operation.last_error_detail = detail
    await _refresh_batch(session, operation.dispatch_batch_id)
    await session.commit()
    return "cancelled"


async def execute_dispatch_operation(
    operation_id: uuid.UUID,
    institution_id: uuid.UUID,
    *,
    adapter: EmailAdapter | None = None,
) -> str:
    """Claim once, send exact frozen bytes, then persist an honest provider outcome."""
    adapter = adapter or get_email_adapter()
    now = datetime.now(UTC)
    attempt_id: uuid.UUID
    message: FrozenEmail
    batch_id: uuid.UUID
    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        operation = (
            await session.execute(
                select(DispatchOperation)
                .where(
                    DispatchOperation.id == operation_id,
                    DispatchOperation.institution_id == institution_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not operation:
            return "not_found"
        if operation.status in {"provider_accepted", "delivered", "failed", "cancelled", "unknown"}:
            return operation.status
        if (
            operation.status == "claimed"
            and operation.lease_expires_at
            and operation.lease_expires_at > now
        ):
            return "already_claimed"
        if operation.status == "claimed":
            unresolved = (
                await session.execute(
                    select(DispatchAttempt).where(
                        DispatchAttempt.dispatch_operation_id == operation.id,
                        DispatchAttempt.status == "started",
                    )
                )
            ).scalar_one_or_none()
            if unresolved:
                unresolved.status = "unknown"
                unresolved.completed_at = now
                unresolved.error_code = "CLAIM_EXPIRED_AFTER_PROVIDER_BOUNDARY"
                operation.status = "unknown"
                operation.completed_at = now
                operation.last_error_code = unresolved.error_code
                await _refresh_batch(session, operation.dispatch_batch_id)
                await session.commit()
                return "unknown"

        batch = await session.get(DispatchBatch, operation.dispatch_batch_id)
        if not batch:
            return await _cancel_claim(
                session, operation, "BATCH_MISSING", "Dispatch batch no longer exists"
            )
        proposal = await session.get(ActionProposal, batch.proposal_id)
        draft = await session.get(CommunicationDraft, batch.communication_draft_id)
        recipient = await session.get(AudienceRecipient, operation.audience_recipient_id)
        drive = await session.get(Drive, operation.drive_id)
        decision = (
            await session.execute(
                select(ApprovalDecision).where(ApprovalDecision.proposal_id == batch.proposal_id)
            )
        ).scalar_one_or_none()
        if not proposal or not draft or not recipient or not drive or not decision:
            return await _cancel_claim(
                session,
                operation,
                "AUTHORIZATION_MISSING",
                "Approved execution evidence is incomplete",
            )
        reviewer = await session.get(Membership, decision.decided_by_membership_id)
        if (
            proposal.state != "approved"
            or decision.decision != "approved"
            or not reviewer
            or not reviewer.is_active
            or "proposal:decide" not in reviewer.capabilities
        ):
            return await _cancel_claim(
                session,
                operation,
                "AUTHORIZATION_REVOKED",
                "The exact approval is no longer executable",
            )
        if (
            now >= batch.execution_expires_at
            or drive.status not in {"published", "active"}
            or drive.operational_hold
            or proposal.sender_connection_revision != sender_connection_revision()
            or proposal.payload.get("content_hash") != draft.content_hash
            or proposal.payload.get("audience_snapshot_id") != str(batch.audience_snapshot_id)
        ):
            return await _cancel_claim(
                session,
                operation,
                "DEPENDENCY_STALE",
                "Execution window or declared dependency changed",
            )
        snapshot = await session.get(AudienceSnapshot, batch.audience_snapshot_id)
        evaluation = await session.get(EvaluationRun, drive.published_evaluation_run_id)
        user = await session.get(User, recipient.user_id)
        if (
            not snapshot
            or proposal.payload.get("audience_hash") != snapshot.canonical_hash
            or not user
            or not user.is_active
            or contact_revision(user) != recipient.contact_revision
            or user.email.strip().lower() != recipient.normalized_email
            or not evaluation
            or evaluation.status != "completed"
            or evaluation.is_stale
            or proposal.dependencies.get("evaluation_run_fingerprint") != evaluation.run_fingerprint
            or proposal.dependencies.get("policy_id") != str(evaluation.policy_id)
        ):
            return await _cancel_claim(
                session, operation, "RECIPIENT_STALE", "Recipient contact or audience changed"
            )
        recipient_domain = recipient.normalized_email.rsplit("@", 1)[-1]
        if settings.EMAIL_ADAPTER_MODE == "mailpit" and recipient_domain not in {
            item.lower() for item in settings.EMAIL_RECIPIENT_ALLOWLIST_DOMAINS
        }:
            return await _cancel_claim(
                session,
                operation,
                "RECIPIENT_NOT_ALLOWLISTED",
                "Development recipient is outside the configured domain allowlist",
            )

        operation.status = "claimed"
        operation.claimed_at = now
        operation.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
        operation.attempt_count += 1
        attempt = DispatchAttempt(
            institution_id=institution_id,
            dispatch_operation_id=operation.id,
            attempt_number=operation.attempt_count,
            status="started",
            adapter_id=adapter.adapter_id,
            started_at=now,
            provider_evidence={},
        )
        session.add(attempt)
        session.add(
            AuditLog(
                institution_id=institution_id,
                action="dispatch:claimed",
                target_type="dispatch_operation",
                target_id=str(operation.id),
                payload={
                    "operation_key": operation.operation_key,
                    "attempt": operation.attempt_count,
                },
            )
        )
        await session.flush()
        attempt_id = attempt.id
        batch_id = batch.id
        message = FrozenEmail(
            operation_key=operation.operation_key,
            sender=draft.sender_email,
            reply_to=draft.reply_to,
            recipient=recipient.normalized_email,
            recipient_name=recipient.display_name,
            subject=recipient.rendered_subject,
            body=recipient.rendered_body,
        )
        await session.commit()

    outcome = adapter.send(message)

    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        operation = (
            await session.execute(
                select(DispatchOperation)
                .where(DispatchOperation.id == operation_id)
                .with_for_update()
            )
        ).scalar_one()
        persisted_attempt = await session.get(DispatchAttempt, attempt_id)
        completed_at = datetime.now(UTC)
        if not persisted_attempt or persisted_attempt.status != "started":
            return operation.status
        persisted_attempt.completed_at = completed_at
        persisted_attempt.status = outcome.status
        persisted_attempt.provider_message_id = outcome.provider_message_id
        persisted_attempt.error_code = outcome.error_code
        persisted_attempt.error_detail = outcome.error_detail
        persisted_attempt.provider_evidence = outcome.evidence or {}
        operation.provider_message_id = outcome.provider_message_id
        operation.last_error_code = outcome.error_code
        operation.last_error_detail = outcome.error_detail
        operation.lease_expires_at = None
        if outcome.status == "provider_accepted":
            operation.status = "provider_accepted"
            operation.completed_at = completed_at
        elif outcome.status == "unknown":
            operation.status = "unknown"
            operation.completed_at = completed_at
        elif (
            outcome.status == "retryable_failure"
            and operation.attempt_count < operation.max_attempts
        ):
            operation.status = "pending"
            operation.claimed_at = None
            session.add(
                OutboxEvent(
                    institution_id=institution_id,
                    event_key=f"dispatch:{operation.id}:attempt:{operation.attempt_count + 1}",
                    event_type="dispatch.operation.requested",
                    aggregate_type="dispatch_operation",
                    aggregate_id=operation.id,
                    payload={
                        "operation_id": str(operation.id),
                        "retry": operation.attempt_count + 1,
                    },
                    status="pending",
                    next_attempt_at=completed_at
                    + timedelta(seconds=min(300, 2**operation.attempt_count)),
                )
            )
        else:
            operation.status = "failed"
            operation.completed_at = completed_at
        await _refresh_batch(session, batch_id)
        session.add(
            AuditLog(
                institution_id=institution_id,
                action="dispatch:attempt_completed",
                target_type="dispatch_operation",
                target_id=str(operation.id),
                payload={
                    "status": operation.status,
                    "attempt": operation.attempt_count,
                    "provider_message_id": outcome.provider_message_id,
                },
            )
        )
        await session.commit()
        return operation.status


async def reconcile_unknown_operation(
    operation_id: uuid.UUID,
    institution_id: uuid.UUID,
    membership_id: uuid.UUID,
    resolution: str,
    evidence: str,
) -> str:
    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        operation = (
            await session.execute(
                select(DispatchOperation)
                .where(
                    DispatchOperation.id == operation_id,
                    DispatchOperation.institution_id == institution_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not operation or operation.status != "unknown":
            return "not_unknown"
        now = datetime.now(UTC)
        if resolution == "provider_accepted":
            operation.status = "provider_accepted"
            operation.completed_at = now
        else:
            operation.status = "pending"
            operation.completed_at = None
            session.add(
                OutboxEvent(
                    institution_id=institution_id,
                    event_key=f"dispatch:{operation.id}:reconciled:{operation.attempt_count + 1}",
                    event_type="dispatch.operation.requested",
                    aggregate_type="dispatch_operation",
                    aggregate_id=operation.id,
                    payload={"operation_id": str(operation.id), "reconciled": True},
                    status="pending",
                    next_attempt_at=now,
                )
            )
        await _refresh_batch(session, operation.dispatch_batch_id)
        session.add(
            AuditLog(
                institution_id=institution_id,
                actor_membership_id=membership_id,
                action="dispatch:unknown_reconciled",
                target_type="dispatch_operation",
                target_id=str(operation.id),
                payload={"resolution": resolution, "evidence": evidence},
            )
        )
        await session.commit()
        return operation.status
