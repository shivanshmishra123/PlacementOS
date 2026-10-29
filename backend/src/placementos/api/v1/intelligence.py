"""P04 JD interpretation, clarification, policy review, and exact approval API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ProposalStaleError,
)
from placementos.models.intelligence import (
    ActionProposal,
    ApprovalDecision,
    ClarificationTask,
    EligibilityPolicyVersion,
    JDInterpretationRevision,
    JDReviewCorrection,
)
from placementos.models.storage import SourceArtifact, TextExtraction
from placementos.schemas.intelligence import (
    ClarificationResolve,
    ClarificationResponse,
    DecisionResponse,
    InterpretationCorrectionCreate,
    InterpretationCreate,
    InterpretationResponse,
    PolicyCompileRequest,
    PolicyResponse,
    ProposalDecisionCreate,
    ProposalResponse,
)
from placementos.services.audit import record_audit
from placementos.services.authorization import load_authorized_drive
from placementos.services.jd_intelligence import (
    DeterministicFixtureJDInterpreter,
    canonical_hash,
    compile_policy,
    get_path,
    set_path,
    validate_evidence,
)
from placementos.services.session import AuthContext

router = APIRouter(tags=["JD Intelligence & Policy Review"])


def _clarification_response(item: ClarificationTask) -> ClarificationResponse:
    return ClarificationResponse(
        id=item.id,
        field_path=item.field_path,
        question=item.question,
        reason_code=item.reason_code,
        blocking=item.blocking,
        status=item.status,
        resolution_value=item.resolution_value,
        resolution_reason=item.resolution_reason,
    )


async def _interpretation_response(
    session: AsyncSession, item: JDInterpretationRevision
) -> InterpretationResponse:
    clarifications = (
        await session.execute(
            select(ClarificationTask)
            .where(ClarificationTask.interpretation_id == item.id)
            .order_by(ClarificationTask.created_at)
        )
    ).scalars().all()
    return InterpretationResponse(
        id=item.id,
        drive_id=item.drive_id,
        source_artifact_id=item.source_artifact_id,
        text_extraction_id=item.text_extraction_id,
        revision_number=item.revision_number,
        schema_version=item.schema_version,
        status=item.status,
        mode=item.mode,
        adapter_id=item.adapter_id,
        candidate_facts=item.candidate_facts,
        reviewed_facts=item.reviewed_facts,
        evidence=item.evidence,
        validation_findings=item.validation_findings,
        clarifications=[_clarification_response(task) for task in clarifications],
        created_at=item.created_at,
    )


def _policy_response(item: EligibilityPolicyVersion) -> PolicyResponse:
    return PolicyResponse(
        id=item.id,
        drive_id=item.drive_id,
        interpretation_id=item.interpretation_id,
        version_number=item.version_number,
        schema_version=item.schema_version,
        engine_contract=item.engine_contract,
        status=item.status,
        policy_payload=item.policy_payload,
        human_summary=item.human_summary,
        canonical_hash=item.canonical_hash,
        approved_proposal_id=item.approved_proposal_id,
        created_at=item.created_at,
    )


def _proposal_response(item: ActionProposal) -> ProposalResponse:
    return ProposalResponse(
        id=item.id,
        drive_id=item.drive_id,
        action_type=item.action_type,
        target_type=item.target_type,
        target_id=item.target_id,
        revision_number=item.revision_number,
        payload=item.payload,
        dependencies=item.dependencies,
        canonical_hash=item.canonical_hash,
        state=item.state,
        expires_at=item.expires_at,
        created_at=item.created_at,
    )


async def _load_interpretation(
    session: AsyncSession, auth: AuthContext, interpretation_id: uuid.UUID, *, for_update: bool = False
) -> JDInterpretationRevision:
    statement = select(JDInterpretationRevision).where(
        JDInterpretationRevision.id == interpretation_id,
        JDInterpretationRevision.institution_id == auth.institution_id,
    )
    if for_update:
        statement = statement.with_for_update()
    item = (await session.execute(statement)).scalar_one_or_none()
    if not item:
        raise NotFoundException(f"Interpretation '{interpretation_id}' not found")
    await load_authorized_drive(session, auth, item.drive_id)
    return item


async def _stale_policy_work(session: AsyncSession, interpretation_id: uuid.UUID) -> None:
    policies = (
        await session.execute(
            select(EligibilityPolicyVersion).where(
                EligibilityPolicyVersion.interpretation_id == interpretation_id,
                EligibilityPolicyVersion.status.in_(["draft", "in_review"]),
            )
        )
    ).scalars().all()
    for policy in policies:
        policy.status = "superseded"
        proposals = (
            await session.execute(
                select(ActionProposal).where(
                    ActionProposal.target_id == policy.id,
                    ActionProposal.state == "pending_approval",
                )
            )
        ).scalars().all()
        for proposal in proposals:
            proposal.state = "stale"


async def _ensure_interpretation_mutable(
    session: AsyncSession, interpretation_id: uuid.UUID
) -> None:
    approved = (
        await session.execute(
            select(func.count()).select_from(EligibilityPolicyVersion).where(
                EligibilityPolicyVersion.interpretation_id == interpretation_id,
                EligibilityPolicyVersion.status == "approved",
            )
        )
    ).scalar_one()
    if approved:
        raise ConflictException(
            "This interpretation supports an immutable approved policy; create a new interpretation revision"
        )


@router.post(
    "/drives/{drive_id}/interpretations",
    response_model=InterpretationResponse,
    status_code=201,
)
async def create_interpretation(
    drive_id: uuid.UUID,
    payload: InterpretationCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> InterpretationResponse:
    await load_authorized_drive(session, auth, drive_id, for_update=True)
    artifact = (
        await session.execute(
            select(SourceArtifact).where(
                SourceArtifact.id == payload.source_artifact_id,
                SourceArtifact.drive_id == drive_id,
                SourceArtifact.institution_id == auth.institution_id,
                SourceArtifact.acceptance_status == "accepted",
            )
        )
    ).scalar_one_or_none()
    if not artifact:
        raise NotFoundException("Accepted source artifact not found for this drive")
    extraction = (
        await session.execute(
            select(TextExtraction)
            .where(
                TextExtraction.source_artifact_id == artifact.id,
                TextExtraction.institution_id == auth.institution_id,
                TextExtraction.status == "completed",
            )
            .order_by(TextExtraction.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not extraction:
        raise ConflictException("Source extraction has not completed successfully")

    if payload.mode == "fixture":
        if settings.MODEL_INTERPRETER_MODE != "fixture" or settings.ENVIRONMENT == "production":
            raise ConflictException(
                "The deterministic interpretation fixture is disabled; use attributed manual entry"
            )
        adapter = DeterministicFixtureJDInterpreter()
        draft = adapter.interpret(extraction)
        facts = draft.facts
        evidence = draft.evidence
        clarification_specs = draft.clarifications
        findings = draft.findings
        usage = draft.usage
        adapter_id = adapter.adapter_id
        prompt_version = adapter.prompt_version
    else:
        if not payload.manual_facts or not payload.rationale:
            raise BadRequestException("Manual interpretation requires facts and an attributed rationale")
        facts = payload.manual_facts
        evidence = [entry.model_dump() for entry in payload.manual_evidence]
        if not evidence:
            evidence = [
                {
                    "field_path": field_path,
                    "locator_type": "human_correction",
                    "excerpt": payload.rationale,
                    "attributed_membership_id": str(auth.membership_id),
                }
                for field_path, value in facts.items()
                if value is not None
            ]
        clarification_specs = []
        findings = [
            {
                "code": "MANUAL_FALLBACK",
                "severity": "info",
                "message": payload.rationale,
                "attributed_membership_id": str(auth.membership_id),
            }
        ]
        usage = {"provider": "manual", "calls": 0, "repair_attempts": 0}
        adapter_id = "manual-entry-v1"
        prompt_version = "manual-schema-v1"
    validate_evidence(extraction, evidence)

    next_revision = (
        await session.execute(
            select(func.coalesce(func.max(JDInterpretationRevision.revision_number), 0) + 1).where(
                JDInterpretationRevision.drive_id == drive_id
            )
        )
    ).scalar_one()
    previous = (
        await session.execute(
            select(JDInterpretationRevision).where(
                JDInterpretationRevision.drive_id == drive_id,
                JDInterpretationRevision.status == "review_ready",
            )
        )
    ).scalars().all()
    for old in previous:
        old.status = "superseded"

    item = JDInterpretationRevision(
        institution_id=auth.institution_id,
        drive_id=drive_id,
        source_artifact_id=artifact.id,
        text_extraction_id=extraction.id,
        revision_number=next_revision,
        schema_version=1,
        status="review_ready",
        mode=payload.mode,
        adapter_id=adapter_id,
        model_id=None,
        prompt_version=prompt_version,
        source_hash=artifact.hash_sha256,
        candidate_facts=facts,
        reviewed_facts=facts,
        evidence=evidence,
        validation_findings=findings,
        usage_metadata=usage,
        created_by_membership_id=auth.membership_id,
    )
    session.add(item)
    await session.flush()
    for spec in clarification_specs:
        session.add(
            ClarificationTask(
                institution_id=auth.institution_id,
                drive_id=drive_id,
                interpretation_id=item.id,
                field_path=spec["field_path"],
                question=spec["question"],
                reason_code=spec["reason_code"],
                blocking=spec["blocking"],
                status="open",
            )
        )
    record_audit(
        session,
        auth,
        "jd:interpretation_created",
        "jd_interpretation",
        item.id,
        {"drive_id": str(drive_id), "mode": payload.mode, "revision": next_revision},
    )
    await session.commit()
    return await _interpretation_response(session, item)


@router.get("/drives/{drive_id}/interpretations", response_model=list[InterpretationResponse])
async def list_interpretations(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[InterpretationResponse]:
    await load_authorized_drive(session, auth, drive_id)
    items = (
        await session.execute(
            select(JDInterpretationRevision)
            .where(
                JDInterpretationRevision.drive_id == drive_id,
                JDInterpretationRevision.institution_id == auth.institution_id,
            )
            .order_by(JDInterpretationRevision.revision_number.desc())
        )
    ).scalars().all()
    return [await _interpretation_response(session, item) for item in items]


@router.post(
    "/interpretations/{interpretation_id}/corrections",
    response_model=InterpretationResponse,
)
async def correct_interpretation(
    interpretation_id: uuid.UUID,
    payload: InterpretationCorrectionCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> InterpretationResponse:
    item = await _load_interpretation(session, auth, interpretation_id, for_update=True)
    if item.status != "review_ready":
        raise ConflictException("Only the current review-ready interpretation can be corrected")
    await _ensure_interpretation_mutable(session, item.id)
    previous = get_path(item.reviewed_facts, payload.field_path)
    item.reviewed_facts = set_path(item.reviewed_facts, payload.field_path, payload.corrected_value)
    evidence = payload.evidence.model_dump() if payload.evidence else {
        "field_path": payload.field_path,
        "locator_type": "human_correction",
        "excerpt": payload.rationale,
    }
    item.evidence = [entry for entry in item.evidence if entry.get("field_path") != payload.field_path] + [evidence]
    session.add(
        JDReviewCorrection(
            institution_id=auth.institution_id,
            interpretation_id=item.id,
            field_path=payload.field_path,
            previous_value=previous,
            corrected_value=payload.corrected_value,
            rationale=payload.rationale,
            evidence=evidence,
            corrected_by_membership_id=auth.membership_id,
        )
    )
    await _stale_policy_work(session, item.id)
    record_audit(
        session,
        auth,
        "jd:field_corrected",
        "jd_interpretation",
        item.id,
        {"field_path": payload.field_path, "rationale": payload.rationale},
    )
    await session.commit()
    return await _interpretation_response(session, item)


@router.post(
    "/clarifications/{clarification_id}/resolve",
    response_model=InterpretationResponse,
)
async def resolve_clarification(
    clarification_id: uuid.UUID,
    payload: ClarificationResolve,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> InterpretationResponse:
    task = (
        await session.execute(
            select(ClarificationTask)
            .where(
                ClarificationTask.id == clarification_id,
                ClarificationTask.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not task:
        raise NotFoundException(f"Clarification '{clarification_id}' not found")
    item = await _load_interpretation(session, auth, task.interpretation_id, for_update=True)
    await _ensure_interpretation_mutable(session, item.id)
    if task.status != "open":
        raise ConflictException("Clarification has already been resolved")
    item.reviewed_facts = set_path(item.reviewed_facts, task.field_path, payload.value)
    task.status = "resolved"
    task.resolution_value = payload.value
    task.resolution_reason = payload.rationale
    task.resolved_by_membership_id = auth.membership_id
    task.resolved_at = datetime.now(UTC)
    item.evidence = [entry for entry in item.evidence if entry.get("field_path") != task.field_path] + [
        {
            "field_path": task.field_path,
            "locator_type": "human_correction",
            "excerpt": payload.rationale,
            "attributed_membership_id": str(auth.membership_id),
        }
    ]
    await _stale_policy_work(session, item.id)
    record_audit(
        session,
        auth,
        "jd:clarification_resolved",
        "clarification_task",
        task.id,
        {"field_path": task.field_path, "rationale": payload.rationale},
    )
    await session.commit()
    return await _interpretation_response(session, item)


@router.post("/drives/{drive_id}/policies", response_model=PolicyResponse, status_code=201)
async def create_policy(
    drive_id: uuid.UUID,
    payload: PolicyCompileRequest,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    await load_authorized_drive(session, auth, drive_id, for_update=True)
    interpretation = await _load_interpretation(session, auth, payload.interpretation_id)
    if interpretation.drive_id != drive_id or interpretation.status != "review_ready":
        raise ConflictException("Policy must use the current review-ready interpretation")
    open_tasks = (
        await session.execute(
            select(ClarificationTask).where(
                ClarificationTask.interpretation_id == interpretation.id,
                ClarificationTask.blocking.is_(True),
                ClarificationTask.status == "open",
            )
        )
    ).scalars().all()
    if open_tasks:
        raise ConflictException(
            "Blocking clarifications must be resolved before policy compilation",
            details={"clarification_ids": [str(item.id) for item in open_tasks]},
        )
    policy_payload, summary = compile_policy(
        interpretation.reviewed_facts,
        interpretation_id=str(interpretation.id),
        explicitly_not_required=set(payload.explicitly_not_required),
    )
    next_version = (
        await session.execute(
            select(func.coalesce(func.max(EligibilityPolicyVersion.version_number), 0) + 1).where(
                EligibilityPolicyVersion.drive_id == drive_id
            )
        )
    ).scalar_one()
    item = EligibilityPolicyVersion(
        institution_id=auth.institution_id,
        drive_id=drive_id,
        interpretation_id=interpretation.id,
        version_number=next_version,
        schema_version=1,
        engine_contract="eligibility-v1",
        status="draft",
        policy_payload=policy_payload,
        human_summary=summary,
        canonical_hash=canonical_hash(policy_payload),
        created_by_membership_id=auth.membership_id,
    )
    session.add(item)
    await session.flush()
    record_audit(session, auth, "policy:draft_created", "eligibility_policy", item.id, {"version": next_version})
    await session.commit()
    return _policy_response(item)


@router.get("/drives/{drive_id}/policies", response_model=list[PolicyResponse])
async def list_policies(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[PolicyResponse]:
    await load_authorized_drive(session, auth, drive_id)
    items = (
        await session.execute(
            select(EligibilityPolicyVersion)
            .where(
                EligibilityPolicyVersion.drive_id == drive_id,
                EligibilityPolicyVersion.institution_id == auth.institution_id,
            )
            .order_by(EligibilityPolicyVersion.version_number.desc())
        )
    ).scalars().all()
    return [_policy_response(item) for item in items]


@router.post("/policies/{policy_id}/submit-review", response_model=ProposalResponse, status_code=201)
async def submit_policy_review(
    policy_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> ProposalResponse:
    policy = (
        await session.execute(
            select(EligibilityPolicyVersion)
            .where(
                EligibilityPolicyVersion.id == policy_id,
                EligibilityPolicyVersion.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not policy:
        raise NotFoundException(f"Policy '{policy_id}' not found")
    await load_authorized_drive(session, auth, policy.drive_id)
    if policy.status != "draft":
        raise ConflictException("Only a draft policy can be submitted for review")
    interpretation = await _load_interpretation(session, auth, policy.interpretation_id)
    open_count = (
        await session.execute(
            select(func.count()).select_from(ClarificationTask).where(
                ClarificationTask.interpretation_id == interpretation.id,
                ClarificationTask.blocking.is_(True),
                ClarificationTask.status == "open",
            )
        )
    ).scalar_one()
    if open_count:
        raise ConflictException("Blocking clarifications prevent policy review")
    payload = {
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
        "institution_id": str(auth.institution_id),
        "action_type": "approve_eligibility_policy",
        "target_id": str(policy.id),
        "payload": payload,
        "dependencies": dependencies,
    }
    proposal = ActionProposal(
        institution_id=auth.institution_id,
        drive_id=policy.drive_id,
        action_type="approve_eligibility_policy",
        target_type="eligibility_policy_version",
        target_id=policy.id,
        revision_number=1,
        schema_version=1,
        payload=payload,
        dependencies=dependencies,
        canonical_hash=canonical_hash(envelope),
        state="pending_approval",
        requested_by_membership_id=auth.membership_id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(proposal)
    policy.status = "in_review"
    await session.flush()
    record_audit(session, auth, "policy:review_submitted", "action_proposal", proposal.id, {"policy_id": str(policy.id)})
    await session.commit()
    return _proposal_response(proposal)


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> ProposalResponse:
    item = (
        await session.execute(
            select(ActionProposal).where(
                ActionProposal.id == proposal_id,
                ActionProposal.institution_id == auth.institution_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise NotFoundException(f"Proposal '{proposal_id}' not found")
    await load_authorized_drive(session, auth, item.drive_id)
    return _proposal_response(item)


@router.post("/proposals/{proposal_id}/decisions", response_model=DecisionResponse)
async def decide_proposal(
    proposal_id: uuid.UUID,
    payload: ProposalDecisionCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    auth.require_capability("rule:approve")
    proposal_scope = (
        await session.execute(
            select(ActionProposal.drive_id).where(
                ActionProposal.id == proposal_id,
                ActionProposal.institution_id == auth.institution_id,
            )
        )
    ).scalar_one_or_none()
    if proposal_scope is None:
        raise NotFoundException(f"Proposal '{proposal_id}' not found")
    await load_authorized_drive(session, auth, proposal_scope, for_update=True)
    proposal = (
        await session.execute(
            select(ActionProposal)
            .where(
                ActionProposal.id == proposal_id,
                ActionProposal.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not proposal:
        raise NotFoundException(f"Proposal '{proposal_id}' not found")
    if proposal.state != "pending_approval":
        raise ConflictException(f"Proposal is already '{proposal.state}'")
    if proposal.revision_number != payload.expected_revision or proposal.canonical_hash != payload.expected_hash:
        raise ProposalStaleError(details={"current_revision": proposal.revision_number})
    if proposal.expires_at and proposal.expires_at <= datetime.now(UTC):
        proposal.state = "expired"
        await session.commit()
        raise ConflictException("Proposal has expired")
    envelope = {
        "schema_version": proposal.schema_version,
        "institution_id": str(proposal.institution_id),
        "action_type": proposal.action_type,
        "target_id": str(proposal.target_id),
        "payload": proposal.payload,
        "dependencies": proposal.dependencies,
    }
    if canonical_hash(envelope) != proposal.canonical_hash:
        proposal.state = "stale"
        await session.commit()
        raise ProposalStaleError("Stored proposal envelope no longer matches its fingerprint")
    policy = (
        await session.execute(
            select(EligibilityPolicyVersion)
            .where(
                EligibilityPolicyVersion.id == proposal.target_id,
                EligibilityPolicyVersion.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not policy or policy.status != "in_review" or policy.canonical_hash != proposal.dependencies.get("policy_hash"):
        proposal.state = "stale"
        await session.commit()
        raise ProposalStaleError("Policy or dependencies changed after proposal creation")
    interpretation = await _load_interpretation(session, auth, policy.interpretation_id)
    if interpretation.revision_number != proposal.dependencies.get("interpretation_revision"):
        proposal.state = "stale"
        await session.commit()
        raise ProposalStaleError("Interpretation revision changed")
    open_count = (
        await session.execute(
            select(func.count()).select_from(ClarificationTask).where(
                ClarificationTask.interpretation_id == interpretation.id,
                ClarificationTask.blocking.is_(True),
                ClarificationTask.status == "open",
            )
        )
    ).scalar_one()
    if open_count:
        proposal.state = "stale"
        await session.commit()
        raise ProposalStaleError("A blocking clarification is unresolved")

    decision = ApprovalDecision(
        institution_id=auth.institution_id,
        proposal_id=proposal.id,
        proposal_hash=proposal.canonical_hash,
        decision=payload.decision,
        comment=payload.comment,
        decided_by_membership_id=auth.membership_id,
        permission_context={"capability": "rule:approve", "membership_id": str(auth.membership_id)},
    )
    session.add(decision)
    proposal.state = payload.decision
    if payload.decision == "approved":
        previous_approved = (
            await session.execute(
                select(EligibilityPolicyVersion).where(
                    EligibilityPolicyVersion.drive_id == policy.drive_id,
                    EligibilityPolicyVersion.status == "approved",
                    EligibilityPolicyVersion.id != policy.id,
                )
            )
        ).scalars().all()
        for previous in previous_approved:
            previous.status = "superseded"
        policy.status = "approved"
        policy.approved_proposal_id = proposal.id
    elif payload.decision == "rejected":
        policy.status = "rejected"
    else:
        policy.status = "draft"
    await session.flush()
    record_audit(
        session,
        auth,
        "proposal:decided",
        "action_proposal",
        proposal.id,
        {"decision": payload.decision, "policy_id": str(policy.id)},
    )
    await session.commit()
    return DecisionResponse(
        id=decision.id,
        proposal_id=proposal.id,
        decision=decision.decision,
        comment=decision.comment,
        decided_at=decision.created_at,
        proposal_state=proposal.state,
        policy_status=policy.status,
    )
