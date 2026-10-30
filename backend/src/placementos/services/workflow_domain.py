"""Idempotent domain coordination helpers used by the P08 LangGraph nodes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.errors import ConflictException
from placementos.models.communications import DispatchBatch
from placementos.models.eligibility import EvaluationRun
from placementos.models.identity import Institution, Membership, User
from placementos.models.intelligence import (
    ActionProposal,
    ClarificationTask,
    EligibilityPolicyVersion,
    JDInterpretationRevision,
)
from placementos.models.recruitment import Drive
from placementos.models.storage import SourceArtifact, TextExtraction
from placementos.models.workflow import ExceptionCase, WorkflowRun
from placementos.schemas.communications import CommunicationDraftCreate
from placementos.services.authorization import load_authorized_drive
from placementos.services.communications import (
    create_communication_proposal,
    create_frozen_draft,
)
from placementos.services.eligibility_engine import canonical_hash
from placementos.services.eligibility_runs import EligibilityRunService
from placementos.services.jd_intelligence import (
    DeterministicFixtureJDInterpreter,
    compile_policy,
    validate_evidence,
)
from placementos.services.session import AuthContext
from placementos.services.source_jobs import SourceJobService


async def ensure_case(
    session: AsyncSession,
    run: WorkflowRun,
    *,
    key_suffix: str,
    category: str,
    severity: str,
    resources: list[dict],
    evidence: dict,
    next_action: str,
) -> ExceptionCase:
    case_key = f"workflow:{run.id}:{key_suffix}"
    existing = (
        await session.execute(
            select(ExceptionCase).where(
                ExceptionCase.institution_id == run.institution_id,
                ExceptionCase.case_key == case_key,
            )
        )
    ).scalar_one_or_none()
    if existing:
        if existing.status in {"resolved", "dismissed"}:
            existing.status = "open"
            existing.resolution_history = [
                *existing.resolution_history,
                {
                    "action": "reopened",
                    "at": datetime.now(UTC).isoformat(),
                    "reason": "The deterministic blocking condition still exists.",
                },
            ]
        return existing
    item = ExceptionCase(
        institution_id=run.institution_id,
        drive_id=run.drive_id,
        workflow_run_id=run.id,
        case_key=case_key,
        category=category,
        severity=severity,
        status="open",
        affected_resources=resources,
        evidence=evidence,
        proposed_next_action=next_action,
        owner_membership_id=run.created_by_membership_id,
        resolution_history=[],
    )
    session.add(item)
    await session.flush()
    return item


async def ensure_source_and_extraction(
    session: AsyncSession, run: WorkflowRun, source_artifact_id: uuid.UUID | None
) -> tuple[SourceArtifact | None, TextExtraction | None, ExceptionCase | None]:
    query = select(SourceArtifact).where(
        SourceArtifact.institution_id == run.institution_id,
        SourceArtifact.drive_id == run.drive_id,
        SourceArtifact.acceptance_status == "accepted",
    )
    if source_artifact_id:
        query = query.where(SourceArtifact.id == source_artifact_id)
    artifact = (
        await session.execute(query.order_by(SourceArtifact.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    if not artifact:
        case = await ensure_case(
            session,
            run,
            key_suffix="source-required",
            category="unresolved_input",
            severity="high",
            resources=[{"type": "drive", "id": str(run.drive_id)}],
            evidence={"code": "ACCEPTED_SOURCE_REQUIRED"},
            next_action="Upload or paste a JD source and accept it before resuming.",
        )
        return None, None, case
    extraction = (
        await session.execute(
            select(TextExtraction)
            .where(
                TextExtraction.institution_id == run.institution_id,
                TextExtraction.source_artifact_id == artifact.id,
                TextExtraction.status == "completed",
            )
            .order_by(TextExtraction.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not extraction:
        extraction = await SourceJobService.run_extraction(
            artifact.id, run.institution_id, session=session
        )
    return artifact, extraction, None


async def ensure_interpretation(
    session: AsyncSession,
    run: WorkflowRun,
    artifact: SourceArtifact,
    extraction: TextExtraction,
) -> JDInterpretationRevision:
    existing = (
        await session.execute(
            select(JDInterpretationRevision)
            .where(
                JDInterpretationRevision.institution_id == run.institution_id,
                JDInterpretationRevision.drive_id == run.drive_id,
                JDInterpretationRevision.source_artifact_id == artifact.id,
                JDInterpretationRevision.source_hash == artifact.hash_sha256,
                JDInterpretationRevision.status == "review_ready",
            )
            .order_by(JDInterpretationRevision.revision_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    if settings.MODEL_INTERPRETER_MODE != "fixture" or settings.ENVIRONMENT == "production":
        raise ConflictException("Workflow interpretation requires attributed manual entry")
    adapter = DeterministicFixtureJDInterpreter()
    draft = adapter.interpret(extraction)
    validate_evidence(extraction, draft.evidence)
    next_revision = (
        int(
            await session.scalar(
                select(func.coalesce(func.max(JDInterpretationRevision.revision_number), 0)).where(
                    JDInterpretationRevision.drive_id == run.drive_id
                )
            )
            or 0
        )
        + 1
    )
    item = JDInterpretationRevision(
        institution_id=run.institution_id,
        drive_id=run.drive_id,
        source_artifact_id=artifact.id,
        text_extraction_id=extraction.id,
        revision_number=next_revision,
        schema_version=1,
        status="review_ready",
        mode="fixture",
        adapter_id=adapter.adapter_id,
        model_id=None,
        prompt_version=adapter.prompt_version,
        source_hash=artifact.hash_sha256,
        candidate_facts=draft.facts,
        reviewed_facts=draft.facts,
        evidence=draft.evidence,
        validation_findings=draft.findings,
        usage_metadata=draft.usage,
        created_by_membership_id=run.created_by_membership_id,
    )
    session.add(item)
    await session.flush()
    for spec in draft.clarifications:
        session.add(
            ClarificationTask(
                institution_id=run.institution_id,
                drive_id=run.drive_id,
                interpretation_id=item.id,
                field_path=spec["field_path"],
                question=spec["question"],
                reason_code=spec["reason_code"],
                blocking=spec["blocking"],
                status="open",
            )
        )
    await session.flush()
    return item


async def ensure_policy_and_proposal(
    session: AsyncSession, run: WorkflowRun, interpretation: JDInterpretationRevision
) -> tuple[EligibilityPolicyVersion | None, ActionProposal | None]:
    approved = (
        await session.execute(
            select(EligibilityPolicyVersion)
            .where(
                EligibilityPolicyVersion.institution_id == run.institution_id,
                EligibilityPolicyVersion.drive_id == run.drive_id,
                EligibilityPolicyVersion.status == "approved",
            )
            .order_by(EligibilityPolicyVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if approved:
        return approved, None
    policy = (
        await session.execute(
            select(EligibilityPolicyVersion)
            .where(
                EligibilityPolicyVersion.institution_id == run.institution_id,
                EligibilityPolicyVersion.drive_id == run.drive_id,
                EligibilityPolicyVersion.interpretation_id == interpretation.id,
                EligibilityPolicyVersion.status.in_(["draft", "in_review"]),
            )
            .order_by(EligibilityPolicyVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not policy:
        payload, summary = compile_policy(
            interpretation.reviewed_facts,
            interpretation_id=str(interpretation.id),
            explicitly_not_required=set(),
        )
        next_version = (
            int(
                await session.scalar(
                    select(
                        func.coalesce(func.max(EligibilityPolicyVersion.version_number), 0)
                    ).where(EligibilityPolicyVersion.drive_id == run.drive_id)
                )
                or 0
            )
            + 1
        )
        policy = EligibilityPolicyVersion(
            institution_id=run.institution_id,
            drive_id=run.drive_id,
            interpretation_id=interpretation.id,
            version_number=next_version,
            schema_version=1,
            engine_contract="eligibility-v1",
            status="draft",
            policy_payload=payload,
            human_summary=summary,
            canonical_hash=canonical_hash(payload),
            created_by_membership_id=run.created_by_membership_id,
        )
        session.add(policy)
        await session.flush()
    proposal = (
        await session.execute(
            select(ActionProposal)
            .where(
                ActionProposal.institution_id == run.institution_id,
                ActionProposal.action_type == "approve_eligibility_policy",
                ActionProposal.target_id == policy.id,
                ActionProposal.state == "pending_approval",
            )
            .order_by(ActionProposal.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if proposal:
        return policy, proposal
    exact_payload = {
        "policy_id": str(policy.id),
        "policy_version": policy.version_number,
        "policy": policy.policy_payload,
        "human_summary": policy.human_summary,
    }
    dependencies = {
        "drive_id": str(policy.drive_id),
        "interpretation_id": str(interpretation.id),
        "interpretation_revision": interpretation.revision_number,
        "source_hash": interpretation.source_hash,
        "policy_hash": policy.canonical_hash,
        "clarification_open_count": 0,
    }
    envelope = {
        "schema_version": 1,
        "institution_id": str(run.institution_id),
        "action_type": "approve_eligibility_policy",
        "target_id": str(policy.id),
        "payload": exact_payload,
        "dependencies": dependencies,
    }
    proposal = ActionProposal(
        institution_id=run.institution_id,
        drive_id=run.drive_id,
        action_type="approve_eligibility_policy",
        target_type="eligibility_policy_version",
        target_id=policy.id,
        revision_number=1,
        schema_version=1,
        payload=exact_payload,
        dependencies=dependencies,
        canonical_hash=canonical_hash(envelope),
        state="pending_approval",
        requested_by_membership_id=run.created_by_membership_id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(proposal)
    policy.status = "in_review"
    await session.flush()
    return policy, proposal


async def ensure_evaluation(
    session: AsyncSession, run: WorkflowRun, policy: EligibilityPolicyVersion
) -> EvaluationRun:
    evaluation, _created = await EligibilityRunService.create_run(
        session,
        institution_id=run.institution_id,
        drive_id=run.drive_id,
        policy=policy,
        created_by_membership_id=run.created_by_membership_id,
    )
    await session.commit()
    if evaluation.status != "completed":
        evaluation = await EligibilityRunService.execute_run(evaluation.id, run.institution_id)
    return evaluation


async def coordinator_auth_for_run(session: AsyncSession, run: WorkflowRun) -> AuthContext:
    membership = await session.get(Membership, run.created_by_membership_id)
    if not membership or not membership.is_active:
        raise ConflictException("Workflow owner membership is inactive")
    user = await session.get(User, membership.user_id)
    institution = await session.get(Institution, run.institution_id)
    if not user or not institution:
        raise ConflictException("Workflow owner context is unavailable")
    auth = AuthContext(
        session_id=f"workflow:{run.id}",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        institution_id=run.institution_id,
        institution_slug=institution.slug,
        membership_id=membership.id,
        role=membership.role,
        capabilities=membership.capabilities,
    )
    await load_authorized_drive(session, auth, run.drive_id)
    return auth


async def ensure_announcement_proposal(
    session: AsyncSession, run: WorkflowRun, drive: Drive
) -> tuple[ActionProposal | None, DispatchBatch | None]:
    existing = (
        await session.execute(
            select(ActionProposal)
            .where(
                ActionProposal.institution_id == run.institution_id,
                ActionProposal.drive_id == run.drive_id,
                ActionProposal.action_type == "send_communication",
                ActionProposal.state.in_(["pending_approval", "approved"]),
            )
            .order_by(ActionProposal.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        batch = (
            await session.execute(
                select(DispatchBatch).where(DispatchBatch.proposal_id == existing.id)
            )
        ).scalar_one_or_none()
        return existing, batch
    auth = await coordinator_auth_for_run(session, run)
    draft, snapshot, _recipients = await create_frozen_draft(
        session,
        auth,
        drive,
        CommunicationDraftCreate(
            communication_kind="drive_announcement",
            audience_type="current_eligible",
            reply_to=auth.email,
        ),
    )
    proposal = await create_communication_proposal(
        session,
        auth,
        drive,
        draft,
        snapshot,
        datetime.now(UTC) + timedelta(days=2),
    )
    return proposal, None
