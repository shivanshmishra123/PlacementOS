"""P07 exact communication proposals, approvals, outbox, and reconciliation APIs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import BadRequestException, ConflictException, NotFoundException
from placementos.models.communications import (
    AudienceRecipient,
    AudienceSnapshot,
    CommunicationDraft,
    DispatchBatch,
    DispatchOperation,
    OutboxEvent,
)
from placementos.models.eligibility import EvaluationRun
from placementos.models.intelligence import ActionProposal, ApprovalDecision
from placementos.schemas.communications import (
    AudienceRecipientResponse,
    CancellationCreate,
    CommunicationDecisionCreate,
    CommunicationDraftCreate,
    CommunicationDraftResponse,
    CommunicationProposalCreate,
    CommunicationProposalResponse,
    DispatchBatchResponse,
    DispatchOperationResponse,
    UnknownOutcomeResolution,
)
from placementos.services.audit import record_audit
from placementos.services.authorization import load_authorized_drive
from placementos.services.communications import (
    create_frozen_draft,
    proposal_envelope,
    sender_connection_revision,
)
from placementos.services.dispatch import reconcile_unknown_operation
from placementos.services.eligibility_engine import canonical_hash
from placementos.services.session import AuthContext

router = APIRouter(tags=["Communications and Dispatch"])


async def _draft_response(
    session: AsyncSession, draft: CommunicationDraft
) -> CommunicationDraftResponse:
    snapshot = (
        await session.execute(
            select(AudienceSnapshot).where(AudienceSnapshot.communication_draft_id == draft.id)
        )
    ).scalar_one()
    recipients = (
        (
            await session.execute(
                select(AudienceRecipient)
                .where(AudienceRecipient.audience_snapshot_id == snapshot.id)
                .order_by(AudienceRecipient.normalized_email)
            )
        )
        .scalars()
        .all()
    )
    return CommunicationDraftResponse(
        id=draft.id,
        drive_id=draft.drive_id,
        revision_number=draft.revision_number,
        communication_kind=draft.communication_kind,
        audience_type=draft.audience_type,
        subject_template=draft.subject_template,
        body_template=draft.body_template,
        sender_email=draft.sender_email,
        reply_to=draft.reply_to,
        state=draft.state,
        content_hash=draft.content_hash,
        audience_snapshot_id=snapshot.id,
        audience_hash=snapshot.canonical_hash,
        included_count=snapshot.included_count,
        excluded_count=snapshot.excluded_count,
        duplicate_count=snapshot.duplicate_count,
        unresolved_count=snapshot.unresolved_count,
        exclusion_summary=snapshot.exclusion_summary,
        recipients=[
            AudienceRecipientResponse(
                id=item.id,
                student_profile_id=item.student_profile_id,
                email=item.email,
                display_name=item.display_name,
                inclusion_reason=item.inclusion_reason,
                rendered_subject=item.rendered_subject,
                rendered_body=item.rendered_body,
                rendered_hash=item.rendered_hash,
            )
            for item in recipients
        ],
        created_at=draft.created_at,
    )


async def _proposal_response(
    session: AsyncSession, proposal: ActionProposal
) -> CommunicationProposalResponse:
    draft = await session.get(CommunicationDraft, proposal.target_id)
    if not draft:
        raise NotFoundException("Communication draft not found")
    decision = (
        await session.execute(
            select(ApprovalDecision).where(ApprovalDecision.proposal_id == proposal.id)
        )
    ).scalar_one_or_none()
    return CommunicationProposalResponse(
        id=proposal.id,
        drive_id=proposal.drive_id,
        draft=await _draft_response(session, draft),
        revision_number=proposal.revision_number,
        canonical_hash=proposal.canonical_hash,
        state=proposal.state,
        payload=proposal.payload,
        dependencies=proposal.dependencies,
        execution_expires_at=proposal.execution_expires_at,
        sender_connection_revision=proposal.sender_connection_revision,
        decision=(
            {
                "decision": decision.decision,
                "comment": decision.comment,
                "decided_by_membership_id": str(decision.decided_by_membership_id),
                "decided_at": decision.created_at.isoformat(),
            }
            if decision
            else None
        ),
        created_at=proposal.created_at,
    )


async def _batch_response(session: AsyncSession, batch: DispatchBatch) -> DispatchBatchResponse:
    rows = (
        await session.execute(
            select(DispatchOperation, AudienceRecipient)
            .join(
                AudienceRecipient, AudienceRecipient.id == DispatchOperation.audience_recipient_id
            )
            .where(DispatchOperation.dispatch_batch_id == batch.id)
            .order_by(AudienceRecipient.normalized_email)
        )
    ).all()
    return DispatchBatchResponse(
        id=batch.id,
        drive_id=batch.drive_id,
        proposal_id=batch.proposal_id,
        communication_draft_id=batch.communication_draft_id,
        status=batch.status,
        total_count=batch.total_count,
        pending_count=batch.pending_count,
        accepted_count=batch.accepted_count,
        delivered_count=batch.delivered_count,
        failed_count=batch.failed_count,
        unknown_count=batch.unknown_count,
        cancelled_count=batch.cancelled_count,
        execution_expires_at=batch.execution_expires_at,
        operations=[
            DispatchOperationResponse(
                id=operation.id,
                operation_key=operation.operation_key,
                recipient=recipient.email,
                recipient_name=recipient.display_name,
                status=operation.status,
                attempt_count=operation.attempt_count,
                provider_message_id=operation.provider_message_id,
                last_error_code=operation.last_error_code,
            )
            for operation, recipient in rows
        ],
        created_at=batch.created_at,
    )


@router.post(
    "/drives/{drive_id}/communication-drafts",
    response_model=CommunicationDraftResponse,
    status_code=201,
)
async def create_communication_draft(
    drive_id: uuid.UUID,
    payload: CommunicationDraftCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> CommunicationDraftResponse:
    auth.require_capability("drive:edit")
    drive = await load_authorized_drive(session, auth, drive_id, for_update=True)
    draft, _snapshot, _recipients = await create_frozen_draft(session, auth, drive, payload)

    older = (
        (
            await session.execute(
                select(ActionProposal)
                .join(CommunicationDraft, CommunicationDraft.id == ActionProposal.target_id)
                .where(
                    ActionProposal.institution_id == auth.institution_id,
                    ActionProposal.drive_id == drive.id,
                    ActionProposal.action_type == "send_communication",
                    CommunicationDraft.communication_kind == draft.communication_kind,
                    ActionProposal.state.in_(["pending_approval", "approved"]),
                    ActionProposal.target_id != draft.id,
                )
                .with_for_update(of=ActionProposal)
            )
        )
        .scalars()
        .all()
    )
    for proposal in older:
        if proposal.state == "pending_approval":
            proposal.state = "stale"
        operations = (
            (
                await session.execute(
                    select(DispatchOperation)
                    .join(DispatchBatch, DispatchBatch.id == DispatchOperation.dispatch_batch_id)
                    .where(
                        DispatchBatch.proposal_id == proposal.id,
                        DispatchOperation.status == "pending",
                    )
                    .with_for_update(of=DispatchOperation)
                )
            )
            .scalars()
            .all()
        )
        for operation in operations:
            operation.status = "cancelled"
            operation.completed_at = datetime.now(UTC)
            operation.last_error_code = "SUPERSEDED_COMMUNICATION"
        batch = (
            await session.execute(
                select(DispatchBatch)
                .where(DispatchBatch.proposal_id == proposal.id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if batch and operations:
            batch.pending_count = max(0, batch.pending_count - len(operations))
            batch.cancelled_count += len(operations)
            if batch.pending_count == 0:
                batch.status = (
                    "cancelled" if batch.cancelled_count == batch.total_count else "partial"
                )
    record_audit(
        session,
        auth,
        "communication:draft_frozen",
        "communication_draft",
        draft.id,
        {"content_hash": draft.content_hash, "audience_type": draft.audience_type},
    )
    await session.commit()
    return await _draft_response(session, draft)


@router.get(
    "/drives/{drive_id}/communication-drafts", response_model=list[CommunicationDraftResponse]
)
async def list_communication_drafts(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[CommunicationDraftResponse]:
    await load_authorized_drive(session, auth, drive_id)
    drafts = (
        (
            await session.execute(
                select(CommunicationDraft)
                .where(
                    CommunicationDraft.institution_id == auth.institution_id,
                    CommunicationDraft.drive_id == drive_id,
                )
                .order_by(CommunicationDraft.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [await _draft_response(session, item) for item in drafts]


@router.post(
    "/communication-drafts/{draft_id}/submit-review",
    response_model=CommunicationProposalResponse,
    status_code=201,
)
async def submit_communication_review(
    draft_id: uuid.UUID,
    payload: CommunicationProposalCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> CommunicationProposalResponse:
    auth.require_capability("drive:edit")
    draft = (
        await session.execute(
            select(CommunicationDraft)
            .where(
                CommunicationDraft.id == draft_id,
                CommunicationDraft.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not draft:
        raise NotFoundException("Communication draft not found")
    drive = await load_authorized_drive(session, auth, draft.drive_id, for_update=True)
    if draft.state != "draft":
        raise ConflictException(f"Communication draft is already {draft.state}")
    now = datetime.now(UTC)
    if payload.execution_expires_at <= now:
        raise BadRequestException("Execution expiry must be in the future")
    snapshot = (
        await session.execute(
            select(AudienceSnapshot).where(AudienceSnapshot.communication_draft_id == draft.id)
        )
    ).scalar_one()
    evaluation = await session.get(EvaluationRun, drive.published_evaluation_run_id)
    if not evaluation or evaluation.status != "completed" or evaluation.is_stale:
        raise ConflictException("Communication review requires a current completed evaluation")
    dependencies = {
        "drive_concurrency_revision": drive.concurrency_revision,
        "published_drive_revision_id": str(drive.published_drive_revision_id),
        "published_evaluation_run_id": str(drive.published_evaluation_run_id),
        "evaluation_run_fingerprint": evaluation.run_fingerprint,
        "policy_id": str(evaluation.policy_id),
        "content_hash": draft.content_hash,
        "audience_hash": snapshot.canonical_hash,
        "sender_connection_revision": sender_connection_revision(),
    }
    envelope = proposal_envelope(
        auth.institution_id, draft, snapshot, dependencies, payload.execution_expires_at
    )
    proposal = ActionProposal(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        action_type="send_communication",
        target_type="communication_draft",
        target_id=draft.id,
        revision_number=draft.revision_number,
        schema_version=1,
        payload=envelope["payload"],
        dependencies=dependencies,
        canonical_hash=canonical_hash(envelope),
        state="pending_approval",
        requested_by_membership_id=auth.membership_id,
        expires_at=payload.execution_expires_at,
        execution_expires_at=payload.execution_expires_at,
        execution_bounds={"max_recipients": snapshot.included_count, "channel": "email"},
        sender_connection_revision=dependencies["sender_connection_revision"],
    )
    session.add(proposal)
    draft.state = "in_review"
    await session.flush()
    record_audit(
        session,
        auth,
        "communication:review_requested",
        "action_proposal",
        proposal.id,
        {"canonical_hash": proposal.canonical_hash, "recipient_count": snapshot.included_count},
    )
    await session.commit()
    return await _proposal_response(session, proposal)


@router.get("/communication-proposals", response_model=list[CommunicationProposalResponse])
async def list_communication_proposals(
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[CommunicationProposalResponse]:
    auth.require_coordinator()
    proposals = (
        (
            await session.execute(
                select(ActionProposal)
                .where(
                    ActionProposal.institution_id == auth.institution_id,
                    ActionProposal.action_type == "send_communication",
                )
                .order_by(ActionProposal.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    visible = []
    for proposal in proposals:
        try:
            await load_authorized_drive(session, auth, proposal.drive_id)
        except NotFoundException:
            continue
        visible.append(await _proposal_response(session, proposal))
    return visible


@router.get("/communication-proposals/{proposal_id}", response_model=CommunicationProposalResponse)
async def get_communication_proposal(
    proposal_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> CommunicationProposalResponse:
    proposal = (
        await session.execute(
            select(ActionProposal).where(
                ActionProposal.id == proposal_id,
                ActionProposal.institution_id == auth.institution_id,
                ActionProposal.action_type == "send_communication",
            )
        )
    ).scalar_one_or_none()
    if not proposal:
        raise NotFoundException("Communication proposal not found")
    await load_authorized_drive(session, auth, proposal.drive_id)
    return await _proposal_response(session, proposal)


@router.post(
    "/communication-proposals/{proposal_id}/decisions",
    response_model=CommunicationProposalResponse,
)
async def decide_communication_proposal(
    proposal_id: uuid.UUID,
    payload: CommunicationDecisionCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> CommunicationProposalResponse:
    auth.require_capability("proposal:decide")
    proposal = (
        await session.execute(
            select(ActionProposal)
            .where(
                ActionProposal.id == proposal_id,
                ActionProposal.institution_id == auth.institution_id,
                ActionProposal.action_type == "send_communication",
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not proposal:
        raise NotFoundException("Communication proposal not found")
    drive = await load_authorized_drive(session, auth, proposal.drive_id, for_update=True)
    if proposal.state != "pending_approval":
        raise ConflictException(f"Communication proposal is already {proposal.state}")
    if (
        proposal.revision_number != payload.expected_revision
        or proposal.canonical_hash != payload.expected_hash
    ):
        raise ConflictException("Communication proposal revision or hash is stale")
    draft = await session.get(CommunicationDraft, proposal.target_id)
    snapshot = (
        await session.execute(
            select(AudienceSnapshot).where(
                AudienceSnapshot.communication_draft_id == proposal.target_id
            )
        )
    ).scalar_one_or_none()
    if not draft or not snapshot or not proposal.execution_expires_at:
        raise ConflictException("Communication proposal evidence is incomplete")
    expected_dependencies = {
        "drive_concurrency_revision": drive.concurrency_revision,
        "published_drive_revision_id": str(drive.published_drive_revision_id),
        "published_evaluation_run_id": str(drive.published_evaluation_run_id),
        "evaluation_run_fingerprint": "",
        "policy_id": "",
        "content_hash": draft.content_hash,
        "audience_hash": snapshot.canonical_hash,
        "sender_connection_revision": sender_connection_revision(),
    }
    evaluation = await session.get(EvaluationRun, drive.published_evaluation_run_id)
    if evaluation:
        expected_dependencies["evaluation_run_fingerprint"] = evaluation.run_fingerprint
        expected_dependencies["policy_id"] = str(evaluation.policy_id)
    envelope = proposal_envelope(
        auth.institution_id, draft, snapshot, expected_dependencies, proposal.execution_expires_at
    )
    if (
        datetime.now(UTC) >= proposal.execution_expires_at
        or drive.status != "published"
        or drive.operational_hold
        or evaluation is None
        or evaluation.status != "completed"
        or evaluation.is_stale
        or expected_dependencies != proposal.dependencies
        or canonical_hash(envelope) != proposal.canonical_hash
    ):
        proposal.state = "stale"
        draft.state = "stale"
        await session.commit()
        raise ConflictException("Communication dependencies changed after review was requested")

    decision = ApprovalDecision(
        institution_id=auth.institution_id,
        proposal_id=proposal.id,
        proposal_hash=proposal.canonical_hash,
        decision=payload.decision,
        comment=payload.comment,
        decided_by_membership_id=auth.membership_id,
        permission_context={
            "capability": "proposal:decide",
            "membership_id": str(auth.membership_id),
        },
    )
    session.add(decision)
    proposal.state = payload.decision
    draft.state = payload.decision
    if payload.decision == "approved":
        batch = DispatchBatch(
            institution_id=auth.institution_id,
            drive_id=drive.id,
            proposal_id=proposal.id,
            communication_draft_id=draft.id,
            audience_snapshot_id=snapshot.id,
            status="queued",
            total_count=snapshot.included_count,
            pending_count=snapshot.included_count,
            approved_at=datetime.now(UTC),
            execution_expires_at=proposal.execution_expires_at,
        )
        session.add(batch)
        await session.flush()
        recipients = (
            (
                await session.execute(
                    select(AudienceRecipient).where(
                        AudienceRecipient.audience_snapshot_id == snapshot.id
                    )
                )
            )
            .scalars()
            .all()
        )
        for recipient in recipients:
            operation = DispatchOperation(
                institution_id=auth.institution_id,
                drive_id=drive.id,
                dispatch_batch_id=batch.id,
                audience_recipient_id=recipient.id,
                operation_key=f"email:{proposal.id}:{recipient.id}",
                status="pending",
            )
            session.add(operation)
            await session.flush()
            session.add(
                OutboxEvent(
                    institution_id=auth.institution_id,
                    event_key=f"dispatch:{operation.id}:attempt:1",
                    event_type="dispatch.operation.requested",
                    aggregate_type="dispatch_operation",
                    aggregate_id=operation.id,
                    payload={"operation_id": str(operation.id), "proposal_id": str(proposal.id)},
                    status="pending",
                    next_attempt_at=datetime.now(UTC),
                )
            )
    record_audit(
        session,
        auth,
        "communication:proposal_decided",
        "action_proposal",
        proposal.id,
        {"decision": payload.decision, "proposal_hash": proposal.canonical_hash},
    )
    await session.commit()
    return await _proposal_response(session, proposal)


@router.get("/dispatch-batches", response_model=list[DispatchBatchResponse])
async def list_dispatch_batches(
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[DispatchBatchResponse]:
    auth.require_coordinator()
    batches = (
        (
            await session.execute(
                select(DispatchBatch)
                .where(DispatchBatch.institution_id == auth.institution_id)
                .order_by(DispatchBatch.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    visible = []
    for batch in batches:
        try:
            await load_authorized_drive(session, auth, batch.drive_id)
        except NotFoundException:
            continue
        visible.append(await _batch_response(session, batch))
    return visible


@router.post("/dispatch-batches/{batch_id}/cancel", response_model=DispatchBatchResponse)
async def cancel_dispatch_batch(
    batch_id: uuid.UUID,
    payload: CancellationCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DispatchBatchResponse:
    auth.require_capability("drive:edit")
    batch = (
        await session.execute(
            select(DispatchBatch)
            .where(
                DispatchBatch.id == batch_id, DispatchBatch.institution_id == auth.institution_id
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not batch:
        raise NotFoundException("Dispatch batch not found")
    await load_authorized_drive(session, auth, batch.drive_id)
    operations = (
        (
            await session.execute(
                select(DispatchOperation)
                .where(
                    DispatchOperation.dispatch_batch_id == batch.id,
                    DispatchOperation.status == "pending",
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    for operation in operations:
        operation.status = "cancelled"
        operation.completed_at = datetime.now(UTC)
        operation.last_error_code = "COORDINATOR_CANCELLED"
        operation.last_error_detail = payload.reason
    batch.pending_count -= len(operations)
    batch.cancelled_count += len(operations)
    if batch.pending_count == 0:
        batch.status = "cancelled" if batch.cancelled_count == batch.total_count else "completed"
    record_audit(
        session,
        auth,
        "dispatch:batch_cancelled",
        "dispatch_batch",
        batch.id,
        {"reason": payload.reason, "cancelled_unclaimed": len(operations)},
    )
    await session.commit()
    return await _batch_response(session, batch)


@router.post(
    "/dispatch-operations/{operation_id}/reconcile", response_model=DispatchOperationResponse
)
async def reconcile_dispatch_operation(
    operation_id: uuid.UUID,
    payload: UnknownOutcomeResolution,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DispatchOperationResponse:
    auth.require_capability("drive:edit")
    row = (
        await session.execute(
            select(DispatchOperation, DispatchBatch, AudienceRecipient)
            .join(DispatchBatch, DispatchBatch.id == DispatchOperation.dispatch_batch_id)
            .join(
                AudienceRecipient, AudienceRecipient.id == DispatchOperation.audience_recipient_id
            )
            .where(
                DispatchOperation.id == operation_id,
                DispatchOperation.institution_id == auth.institution_id,
            )
        )
    ).one_or_none()
    if not row:
        raise NotFoundException("Dispatch operation not found")
    operation, batch, recipient = row
    await load_authorized_drive(session, auth, batch.drive_id)
    await session.close()
    result = await reconcile_unknown_operation(
        operation.id,
        auth.institution_id,
        auth.membership_id,
        payload.resolution,
        payload.evidence,
    )
    if result == "not_unknown":
        raise ConflictException("Only an unknown provider outcome can be reconciled")
    return DispatchOperationResponse(
        id=operation.id,
        operation_key=operation.operation_key,
        recipient=recipient.email,
        recipient_name=recipient.display_name,
        status=result,
        attempt_count=operation.attempt_count,
        provider_message_id=operation.provider_message_id,
        last_error_code=operation.last_error_code,
    )
