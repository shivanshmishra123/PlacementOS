"""P12 structured exception impact and controlled recovery API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import get_db
from placementos.core.dependencies import require_capability
from placementos.core.errors import NotFoundException
from placementos.models.intelligence import ActionProposal
from placementos.models.recovery import ExceptionImpactAnalysis, RecoveryExecution, RecoveryPlan
from placementos.schemas.recovery import (
    ExceptionImpactCreate,
    ExceptionImpactResponse,
    RecoveryCancellationCreate,
    RecoveryDecisionCreate,
    RecoveryExecutionResponse,
    RecoveryPlanCreate,
    RecoveryPlanResponse,
    RecoveryPlanStepResponse,
)
from placementos.services.authorization import load_authorized_drive
from placementos.services.recovery import (
    cancel_recovery_execution,
    create_impact_analysis,
    create_recovery_plan,
    decide_recovery_plan,
    load_scoped_case,
    plan_steps,
)
from placementos.services.session import AuthContext

router = APIRouter(tags=["Adaptive Exception Recovery"])


async def _plan_response(session: AsyncSession, plan: RecoveryPlan) -> RecoveryPlanResponse:
    steps = await plan_steps(session, plan.id)
    proposal = await session.get(ActionProposal, plan.proposal_id) if plan.proposal_id else None
    return RecoveryPlanResponse(
        id=plan.id,
        case_id=plan.case_id,
        analysis_id=plan.analysis_id,
        proposal_id=plan.proposal_id,
        revision_number=plan.revision_number,
        planner_mode=plan.planner_mode,
        planner_id=plan.planner_id,
        planner_version=plan.planner_version,
        status=plan.status,
        rationale=plan.rationale,
        canonical_hash=plan.canonical_hash,
        approval_hash=proposal.canonical_hash if proposal else "",
        dependency_fingerprint=plan.dependency_fingerprint,
        usage_metadata=plan.usage_metadata,
        steps=[RecoveryPlanStepResponse.model_validate(item) for item in steps],
        created_at=plan.created_at,
    )


async def _load_plan(
    session: AsyncSession, auth: AuthContext, plan_id: uuid.UUID, *, for_update: bool = False
) -> RecoveryPlan:
    statement = select(RecoveryPlan).where(
        RecoveryPlan.id == plan_id,
        RecoveryPlan.institution_id == auth.institution_id,
    )
    if for_update:
        statement = statement.with_for_update()
    plan = (await session.execute(statement)).scalar_one_or_none()
    if not plan:
        raise NotFoundException("Recovery plan not found")
    await load_authorized_drive(session, auth, plan.drive_id)
    return plan


@router.post(
    "/exception-cases/{case_id}/impact-analyses",
    response_model=ExceptionImpactResponse,
    status_code=201,
)
async def analyze_exception_impact(
    case_id: uuid.UUID,
    payload: ExceptionImpactCreate,
    auth: AuthContext = Depends(require_capability("exception:plan")),
    session: AsyncSession = Depends(get_db),
) -> ExceptionImpactAnalysis:
    case = await load_scoped_case(session, auth, case_id, for_update=True)
    return await create_impact_analysis(session, auth, case, payload)


@router.get(
    "/exception-cases/{case_id}/impact-analyses",
    response_model=list[ExceptionImpactResponse],
)
async def list_exception_impact_analyses(
    case_id: uuid.UUID,
    auth: AuthContext = Depends(require_capability("exception:plan")),
    session: AsyncSession = Depends(get_db),
) -> list[ExceptionImpactAnalysis]:
    await load_scoped_case(session, auth, case_id)
    return list(
        (
            await session.execute(
                select(ExceptionImpactAnalysis)
                .where(
                    ExceptionImpactAnalysis.case_id == case_id,
                    ExceptionImpactAnalysis.institution_id == auth.institution_id,
                )
                .order_by(ExceptionImpactAnalysis.revision_number.desc())
            )
        )
        .scalars()
        .all()
    )


@router.post(
    "/impact-analyses/{analysis_id}/recovery-plans",
    response_model=RecoveryPlanResponse,
    status_code=201,
)
async def propose_recovery_plan(
    analysis_id: uuid.UUID,
    payload: RecoveryPlanCreate,
    auth: AuthContext = Depends(require_capability("exception:plan")),
    session: AsyncSession = Depends(get_db),
) -> RecoveryPlanResponse:
    analysis = (
        await session.execute(
            select(ExceptionImpactAnalysis).where(
                ExceptionImpactAnalysis.id == analysis_id,
                ExceptionImpactAnalysis.institution_id == auth.institution_id,
            )
        )
    ).scalar_one_or_none()
    if not analysis:
        raise NotFoundException("Exception impact analysis not found")
    await load_authorized_drive(session, auth, analysis.drive_id)
    plan = await create_recovery_plan(session, auth, analysis, payload)
    return await _plan_response(session, plan)


@router.get("/exception-cases/{case_id}/recovery-plans", response_model=list[RecoveryPlanResponse])
async def list_recovery_plans(
    case_id: uuid.UUID,
    auth: AuthContext = Depends(require_capability("exception:plan")),
    session: AsyncSession = Depends(get_db),
) -> list[RecoveryPlanResponse]:
    await load_scoped_case(session, auth, case_id)
    plans = (
        await session.execute(
            select(RecoveryPlan)
            .where(
                RecoveryPlan.case_id == case_id,
                RecoveryPlan.institution_id == auth.institution_id,
            )
            .order_by(RecoveryPlan.created_at.desc())
        )
    ).scalars()
    return [await _plan_response(session, item) for item in plans]


@router.get("/recovery-plans/{plan_id}", response_model=RecoveryPlanResponse)
async def get_recovery_plan(
    plan_id: uuid.UUID,
    auth: AuthContext = Depends(require_capability("exception:plan")),
    session: AsyncSession = Depends(get_db),
) -> RecoveryPlanResponse:
    return await _plan_response(session, await _load_plan(session, auth, plan_id))


@router.post(
    "/recovery-plans/{plan_id}/decisions",
    response_model=RecoveryExecutionResponse | None,
)
async def decide_plan(
    plan_id: uuid.UUID,
    payload: RecoveryDecisionCreate,
    auth: AuthContext = Depends(require_capability("proposal:decide")),
    session: AsyncSession = Depends(get_db),
) -> RecoveryExecution | None:
    plan = await _load_plan(session, auth, plan_id, for_update=True)
    return await decide_recovery_plan(
        session,
        auth,
        plan,
        expected_revision=payload.expected_revision,
        expected_hash=payload.expected_hash,
        decision=payload.decision,
        comment=payload.comment,
    )


@router.get(
    "/exception-cases/{case_id}/recovery-executions",
    response_model=list[RecoveryExecutionResponse],
)
async def list_recovery_executions(
    case_id: uuid.UUID,
    auth: AuthContext = Depends(require_capability("exception:plan")),
    session: AsyncSession = Depends(get_db),
) -> list[RecoveryExecution]:
    await load_scoped_case(session, auth, case_id)
    return list(
        (
            await session.execute(
                select(RecoveryExecution)
                .where(
                    RecoveryExecution.case_id == case_id,
                    RecoveryExecution.institution_id == auth.institution_id,
                )
                .order_by(RecoveryExecution.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


@router.post(
    "/recovery-executions/{execution_id}/cancel",
    response_model=RecoveryExecutionResponse,
)
async def cancel_execution(
    execution_id: uuid.UUID,
    payload: RecoveryCancellationCreate,
    auth: AuthContext = Depends(require_capability("exception:plan")),
    session: AsyncSession = Depends(get_db),
) -> RecoveryExecution:
    return await cancel_recovery_execution(
        session,
        auth,
        execution_id,
        reason=payload.reason,
    )
