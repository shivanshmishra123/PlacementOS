"""P05 deterministic eligibility runs and personal explanations API."""

from __future__ import annotations

import uuid
from typing import Literal, cast

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import ConflictException, NotFoundException
from placementos.models.eligibility import (
    EligibilityResult,
    EligibilityReviewRequest,
    EvaluationRun,
)
from placementos.models.identity import StudentProfile, User
from placementos.models.intelligence import EligibilityPolicyVersion
from placementos.models.recruitment import Company, Drive
from placementos.schemas.eligibility import (
    EligibilityResultResponse,
    EvaluationRunCreate,
    EvaluationRunResponse,
    PredicateFindingResponse,
    ReviewRequestCreate,
    ReviewRequestResponse,
    StudentEligibilityResponse,
)
from placementos.services.audit import record_audit
from placementos.services.authorization import load_authorized_drive
from placementos.services.eligibility_runs import EligibilityRunService
from placementos.services.session import AuthContext

router = APIRouter(tags=["Deterministic Eligibility"])


async def _result_responses(
    session: AsyncSession,
    run_id: uuid.UUID,
    outcome: str | None = None,
) -> list[EligibilityResultResponse]:
    query = (
        select(EligibilityResult, StudentProfile, User)
        .join(StudentProfile, StudentProfile.id == EligibilityResult.student_profile_id)
        .join(User, User.id == StudentProfile.user_id)
        .where(EligibilityResult.evaluation_run_id == run_id)
        .order_by(StudentProfile.student_identifier)
    )
    if outcome:
        query = query.where(EligibilityResult.outcome == outcome)
    rows = (await session.execute(query)).all()
    return [
        EligibilityResultResponse(
            id=result.id,
            evaluation_run_id=result.evaluation_run_id,
            student_profile_id=result.student_profile_id,
            student_identifier=profile.student_identifier,
            student_name=user.full_name,
            academic_revision_id=result.academic_revision_id,
            outcome=cast(Literal["eligible", "ineligible", "needs_review"], result.outcome),
            predicate_results=[PredicateFindingResponse(**item) for item in result.predicate_results],
            reason_codes=result.reason_codes,
            student_explanation=result.student_explanation,
            input_fingerprint=result.input_fingerprint,
            created_at=result.created_at,
        )
        for result, profile, user in rows
    ]


async def _run_response(
    session: AsyncSession,
    run: EvaluationRun,
    *,
    include_results: bool = False,
    outcome: str | None = None,
) -> EvaluationRunResponse:
    policy = (
        await session.execute(
            select(EligibilityPolicyVersion).where(EligibilityPolicyVersion.id == run.policy_id)
        )
    ).scalar_one()
    results = await _result_responses(session, run.id, outcome) if include_results else []
    return EvaluationRunResponse(
        id=run.id,
        drive_id=run.drive_id,
        policy_id=run.policy_id,
        policy_version=policy.version_number,
        policy_hash=run.policy_hash,
        engine_version=run.engine_version,
        normalization_version=run.normalization_version,
        cohort_fingerprint=run.cohort_fingerprint,
        status=run.status,
        is_stale=run.is_stale,
        stale_reason=run.stale_reason,
        total_count=run.total_count,
        eligible_count=run.eligible_count,
        ineligible_count=run.ineligible_count,
        needs_review_count=run.needs_review_count,
        duration_ms=run.duration_ms,
        error_code=run.error_code,
        error_detail=run.error_detail,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        results=results,
    )


@router.post("/drives/{drive_id}/evaluations", response_model=EvaluationRunResponse, status_code=202)
async def create_evaluation_run(
    drive_id: uuid.UUID,
    payload: EvaluationRunCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    auth.require_coordinator()
    auth.require_capability("student:read")
    auth.require_capability("eligibility:run")
    await load_authorized_drive(session, auth, drive_id, for_update=True)
    policy_query = select(EligibilityPolicyVersion).where(
        EligibilityPolicyVersion.drive_id == drive_id,
        EligibilityPolicyVersion.institution_id == auth.institution_id,
        EligibilityPolicyVersion.status == "approved",
    )
    if payload.policy_id:
        policy_query = policy_query.where(EligibilityPolicyVersion.id == payload.policy_id)
    policy = (
        await session.execute(policy_query.order_by(EligibilityPolicyVersion.version_number.desc()))
    ).scalars().first()
    if not policy:
        raise ConflictException("An approved eligibility policy is required before evaluation")
    run, created = await EligibilityRunService.create_run(
        session,
        institution_id=auth.institution_id,
        drive_id=drive_id,
        policy=policy,
        created_by_membership_id=auth.membership_id,
    )
    if created:
        record_audit(
            session,
            auth,
            "eligibility:run_queued",
            "evaluation_run",
            run.id,
            {
                "policy_id": str(policy.id),
                "cohort_fingerprint": run.cohort_fingerprint,
                "total_count": run.total_count,
            },
        )
    await session.commit()
    if run.status in {"queued", "failed"}:
        from placementos.workers.eligibility_tasks import evaluate_eligibility_task

        evaluate_eligibility_task.delay(str(run.id), str(auth.institution_id))
    return await _run_response(session, run)


@router.get("/drives/{drive_id}/evaluations", response_model=list[EvaluationRunResponse])
async def list_evaluation_runs(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[EvaluationRunResponse]:
    auth.require_coordinator()
    await load_authorized_drive(session, auth, drive_id)
    runs = (
        await session.execute(
            select(EvaluationRun)
            .where(
                EvaluationRun.drive_id == drive_id,
                EvaluationRun.institution_id == auth.institution_id,
            )
            .order_by(EvaluationRun.created_at.desc())
        )
    ).scalars().all()
    changed = False
    for run in runs:
        was_stale = run.is_stale
        await EligibilityRunService.refresh_freshness(session, run)
        changed = changed or run.is_stale != was_stale
    if changed:
        await session.commit()
    return [await _run_response(session, run) for run in runs]


@router.get("/evaluation-runs/{run_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run(
    run_id: uuid.UUID,
    outcome: Literal["eligible", "ineligible", "needs_review"] | None = Query(None),
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    auth.require_coordinator()
    run = (
        await session.execute(
            select(EvaluationRun).where(
                EvaluationRun.id == run_id,
                EvaluationRun.institution_id == auth.institution_id,
            )
        )
    ).scalar_one_or_none()
    if not run:
        raise NotFoundException(f"Evaluation run '{run_id}' not found")
    await load_authorized_drive(session, auth, run.drive_id)
    was_stale = run.is_stale
    await EligibilityRunService.refresh_freshness(session, run)
    if run.is_stale != was_stale:
        await session.commit()
    return await _run_response(session, run, include_results=True, outcome=outcome)


@router.get("/student/eligibility", response_model=list[StudentEligibilityResponse])
async def get_my_eligibility(
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[StudentEligibilityResponse]:
    auth.require_role("student")
    profile = (
        await session.execute(
            select(StudentProfile).where(
                StudentProfile.institution_id == auth.institution_id,
                StudentProfile.user_id == auth.user_id,
            )
        )
    ).scalar_one_or_none()
    if not profile:
        raise NotFoundException("Student profile not found")
    rows = (
        await session.execute(
            select(EligibilityResult, EvaluationRun, EligibilityPolicyVersion, Drive, Company)
            .join(EvaluationRun, EvaluationRun.id == EligibilityResult.evaluation_run_id)
            .join(EligibilityPolicyVersion, EligibilityPolicyVersion.id == EvaluationRun.policy_id)
            .join(Drive, Drive.id == EvaluationRun.drive_id)
            .join(Company, Company.id == Drive.company_id)
            .where(
                EligibilityResult.institution_id == auth.institution_id,
                EligibilityResult.student_profile_id == profile.id,
                EvaluationRun.status == "completed",
                Drive.status == "published",
            )
            .order_by(EvaluationRun.created_at.desc())
        )
    ).all()
    responses: list[StudentEligibilityResponse] = []
    seen_drives: set[uuid.UUID] = set()
    freshness_changed = False
    for result, run, policy, drive, company in rows:
        if drive.id in seen_drives:
            continue
        seen_drives.add(drive.id)
        was_stale = run.is_stale
        await EligibilityRunService.refresh_freshness(session, run)
        freshness_changed = freshness_changed or run.is_stale != was_stale
        responses.append(
            StudentEligibilityResponse(
                result_id=result.id,
                evaluation_run_id=run.id,
                drive_id=drive.id,
                drive_title=drive.title,
                company_name=company.name,
                policy_version=policy.version_number,
                outcome=cast(Literal["eligible", "ineligible", "needs_review"], result.outcome),
                predicate_results=[PredicateFindingResponse(**item) for item in result.predicate_results],
                reason_codes=result.reason_codes,
                student_explanation=result.student_explanation,
                is_stale=run.is_stale,
                stale_reason=run.stale_reason,
                evaluated_at=result.created_at,
            )
        )
    if freshness_changed:
        await session.commit()
    return responses


@router.post(
    "/student/eligibility/{result_id}/review-request",
    response_model=ReviewRequestResponse,
    status_code=201,
)
async def request_eligibility_review(
    result_id: uuid.UUID,
    payload: ReviewRequestCreate,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> ReviewRequestResponse:
    auth.require_role("student")
    profile = (
        await session.execute(
            select(StudentProfile).where(
                StudentProfile.institution_id == auth.institution_id,
                StudentProfile.user_id == auth.user_id,
            )
        )
    ).scalar_one_or_none()
    if not profile:
        raise NotFoundException("Student profile not found")
    row = (
        await session.execute(
            select(EligibilityResult, EvaluationRun, Drive)
            .join(EvaluationRun, EvaluationRun.id == EligibilityResult.evaluation_run_id)
            .join(Drive, Drive.id == EvaluationRun.drive_id)
            .where(
                EligibilityResult.id == result_id,
                EligibilityResult.institution_id == auth.institution_id,
                EligibilityResult.student_profile_id == profile.id,
                EvaluationRun.status == "completed",
                Drive.status == "published",
            )
        )
    ).one_or_none()
    if not row:
        raise NotFoundException("Eligibility result not found")
    result, run, _drive = row
    latest_run_id = (
        await session.execute(
            select(EvaluationRun.id)
            .where(
                EvaluationRun.institution_id == auth.institution_id,
                EvaluationRun.drive_id == run.drive_id,
                EvaluationRun.status == "completed",
            )
            .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
            .limit(1)
        )
    ).scalar_one()
    if latest_run_id != run.id:
        raise NotFoundException("Eligibility result not found")
    existing = (
        await session.execute(
            select(EligibilityReviewRequest).where(
                EligibilityReviewRequest.eligibility_result_id == result.id,
                EligibilityReviewRequest.student_profile_id == profile.id,
                EligibilityReviewRequest.status == "open",
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictException("An open review request already exists for this result")
    item = EligibilityReviewRequest(
        institution_id=auth.institution_id,
        drive_id=run.drive_id,
        eligibility_result_id=result.id,
        student_profile_id=profile.id,
        requested_by_user_id=auth.user_id,
        reason=payload.reason,
        status="open",
    )
    session.add(item)
    await session.flush()
    record_audit(session, auth, "eligibility:review_requested", "eligibility_result", result.id, {"request_id": str(item.id)})
    await session.commit()
    return ReviewRequestResponse(
        id=item.id,
        drive_id=item.drive_id,
        eligibility_result_id=item.eligibility_result_id,
        student_profile_id=profile.id,
        student_identifier=profile.student_identifier,
        student_name=auth.full_name,
        reason=item.reason,
        status=item.status,
        created_at=item.created_at,
    )


@router.get("/drives/{drive_id}/eligibility-review-requests", response_model=list[ReviewRequestResponse])
async def list_eligibility_review_requests(
    drive_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> list[ReviewRequestResponse]:
    auth.require_coordinator()
    await load_authorized_drive(session, auth, drive_id)
    rows = (
        await session.execute(
            select(EligibilityReviewRequest, StudentProfile, User)
            .join(StudentProfile, StudentProfile.id == EligibilityReviewRequest.student_profile_id)
            .join(User, User.id == StudentProfile.user_id)
            .where(
                EligibilityReviewRequest.institution_id == auth.institution_id,
                EligibilityReviewRequest.drive_id == drive_id,
                EligibilityReviewRequest.status == "open",
            )
            .order_by(EligibilityReviewRequest.created_at)
        )
    ).all()
    return [
        ReviewRequestResponse(
            id=item.id,
            drive_id=item.drive_id,
            eligibility_result_id=item.eligibility_result_id,
            student_profile_id=profile.id,
            student_identifier=profile.student_identifier,
            student_name=user.full_name,
            reason=item.reason,
            status=item.status,
            created_at=item.created_at,
        )
        for item, profile, user in rows
    ]
