"""Durable P05 cohort snapshot, evaluation, and freshness services."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import async_session_maker
from placementos.core.errors import BadRequestException, ConflictException, NotFoundException
from placementos.models.academic import AcademicRecordRevision
from placementos.models.eligibility import EligibilityResult, EvaluationCohortMember, EvaluationRun
from placementos.models.identity import AuditLog, Membership, StudentProfile
from placementos.models.intelligence import EligibilityPolicyVersion
from placementos.services.eligibility_engine import (
    ENGINE_VERSION,
    AcademicFacts,
    InvalidEligibilityPolicy,
    canonical_hash,
    evaluate,
    input_fingerprint,
    validate_policy,
)

DEFAULT_NORMALIZATION_VERSION = "institution-normalization-v1"
EVALUATION_CHUNK_SIZE = 250


def _facts(revision: AcademicRecordRevision | None) -> AcademicFacts:
    if revision is None:
        return AcademicFacts(None, None, None, None, None, False)
    return AcademicFacts(
        branch=revision.branch,
        cgpa=revision.cgpa,
        cgpa_scale=revision.cgpa_scale,
        graduation_year=revision.graduation_year,
        active_backlogs=revision.active_backlogs,
        is_verified=revision.is_verified,
        academic_revision_id=str(revision.id),
    )


class EligibilityRunService:
    """Coordinates persistence around the pure eligibility engine."""

    @staticmethod
    async def create_run(
        session: AsyncSession,
        *,
        institution_id: uuid.UUID,
        drive_id: uuid.UUID,
        policy: EligibilityPolicyVersion,
        created_by_membership_id: uuid.UUID,
        normalization_version: str = DEFAULT_NORMALIZATION_VERSION,
    ) -> tuple[EvaluationRun, bool]:
        if policy.drive_id != drive_id or policy.institution_id != institution_id:
            raise NotFoundException("Approved policy not found for this drive")
        if policy.status != "approved":
            raise ConflictException("Eligibility evaluation requires an approved policy")
        try:
            validate_policy(policy.policy_payload)
        except InvalidEligibilityPolicy as exc:
            raise BadRequestException(f"Invalid approved policy: {exc}") from exc

        profiles = (
            await session.execute(
                select(StudentProfile, Membership)
                .join(Membership, Membership.id == StudentProfile.membership_id)
                .where(
                    StudentProfile.institution_id == institution_id,
                    Membership.institution_id == institution_id,
                    Membership.role == "student",
                    Membership.is_active.is_(True),
                )
                .order_by(StudentProfile.id)
                .with_for_update(of=StudentProfile)
            )
        ).all()
        if not profiles:
            raise BadRequestException("The institution has no active student cohort to evaluate")

        frozen = [
            {
                "student_profile_id": str(profile.id),
                "membership_id": str(membership.id),
                "academic_revision_id": (
                    str(profile.current_academic_revision_id)
                    if profile.current_academic_revision_id is not None
                    else None
                ),
            }
            for profile, membership in profiles
        ]
        cohort_fingerprint = canonical_hash(frozen)
        run_fingerprint = canonical_hash(
            {
                "institution_id": str(institution_id),
                "drive_id": str(drive_id),
                "policy_id": str(policy.id),
                "policy_hash": policy.canonical_hash,
                "cohort_fingerprint": cohort_fingerprint,
                "normalization_version": normalization_version,
                "engine_version": ENGINE_VERSION,
            }
        )
        existing = (
            await session.execute(
                select(EvaluationRun).where(
                    EvaluationRun.institution_id == institution_id,
                    EvaluationRun.run_fingerprint == run_fingerprint,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing, False

        run = EvaluationRun(
            institution_id=institution_id,
            drive_id=drive_id,
            policy_id=policy.id,
            policy_hash=policy.canonical_hash,
            engine_version=ENGINE_VERSION,
            normalization_version=normalization_version,
            cohort_fingerprint=cohort_fingerprint,
            run_fingerprint=run_fingerprint,
            status="queued",
            total_count=len(frozen),
            created_by_membership_id=created_by_membership_id,
        )
        session.add(run)
        await session.flush()
        for item in frozen:
            session.add(
                EvaluationCohortMember(
                    institution_id=institution_id,
                    evaluation_run_id=run.id,
                    student_profile_id=uuid.UUID(item["student_profile_id"]),
                    membership_id=uuid.UUID(item["membership_id"]),
                    academic_revision_id=(
                        uuid.UUID(item["academic_revision_id"])
                        if item["academic_revision_id"] is not None
                        else None
                    ),
                    member_fingerprint=canonical_hash(item),
                )
            )
        await session.flush()
        return run, True

    @staticmethod
    async def execute_run(run_id: uuid.UUID, institution_id: uuid.UUID) -> EvaluationRun:
        started = time.perf_counter()
        async with async_session_maker() as session:
            session.info["institution_id"] = institution_id
            run = (
                await session.execute(
                    select(EvaluationRun)
                    .where(
                        EvaluationRun.id == run_id,
                        EvaluationRun.institution_id == institution_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if not run:
                raise NotFoundException(f"Evaluation run '{run_id}' not found")
            if run.status == "completed":
                return run
            if run.status not in {"queued", "processing", "failed"}:
                raise ConflictException(f"Evaluation run cannot execute from '{run.status}'")
            run.status = "processing"
            run.started_at = run.started_at or datetime.now(UTC)
            run.error_code = None
            run.error_detail = None
            await session.commit()

        try:
            async with async_session_maker() as session:
                session.info["institution_id"] = institution_id
                run = (
                    await session.execute(
                        select(EvaluationRun)
                        .where(
                            EvaluationRun.id == run_id,
                            EvaluationRun.institution_id == institution_id,
                        )
                        .with_for_update()
                    )
                ).scalar_one()
                # Another delivery may have completed the run after this task first
                # observed it as queued/processing. Do not repeat completion audit work.
                if run.status == "completed":
                    return run
                policy = (
                    await session.execute(
                        select(EligibilityPolicyVersion).where(
                            EligibilityPolicyVersion.id == run.policy_id,
                            EligibilityPolicyVersion.institution_id == institution_id,
                        )
                    )
                ).scalar_one()
                if policy.canonical_hash != run.policy_hash:
                    raise InvalidEligibilityPolicy("Frozen policy hash does not match its persisted revision")
                validate_policy(policy.policy_payload)

                counts = {"eligible": 0, "ineligible": 0, "needs_review": 0}
                offset = 0
                while True:
                    members = (
                        await session.execute(
                            select(EvaluationCohortMember)
                            .where(EvaluationCohortMember.evaluation_run_id == run.id)
                            .order_by(EvaluationCohortMember.student_profile_id)
                            .offset(offset)
                            .limit(EVALUATION_CHUNK_SIZE)
                        )
                    ).scalars().all()
                    if not members:
                        break
                    revision_ids = [
                        item.academic_revision_id for item in members if item.academic_revision_id
                    ]
                    revisions = (
                        (
                            await session.execute(
                                select(AcademicRecordRevision).where(
                                    AcademicRecordRevision.id.in_(revision_ids)
                                )
                            )
                        ).scalars().all()
                        if revision_ids
                        else []
                    )
                    revision_map = {item.id: item for item in revisions}
                    member_ids = [item.student_profile_id for item in members]
                    existing_results = {
                        item.student_profile_id: item
                        for item in (
                            await session.execute(
                                select(EligibilityResult).where(
                                    EligibilityResult.evaluation_run_id == run.id,
                                    EligibilityResult.student_profile_id.in_(member_ids),
                                )
                            )
                        ).scalars().all()
                    }
                    for member in members:
                        facts = _facts(
                            revision_map.get(member.academic_revision_id)
                            if member.academic_revision_id is not None
                            else None
                        )
                        decision = evaluate(policy.policy_payload, facts)
                        counts[decision.outcome] += 1
                        fingerprint = input_fingerprint(
                            run.policy_hash,
                            facts,
                            run.normalization_version,
                            run.engine_version,
                        )
                        previous = existing_results.get(member.student_profile_id)
                        if previous:
                            if (
                                previous.input_fingerprint != fingerprint
                                or previous.outcome != decision.outcome
                            ):
                                raise ConflictException(
                                    "Persisted eligibility result conflicts with frozen inputs"
                                )
                            continue
                        session.add(
                            EligibilityResult(
                                institution_id=institution_id,
                                evaluation_run_id=run.id,
                                cohort_member_id=member.id,
                                student_profile_id=member.student_profile_id,
                                academic_revision_id=member.academic_revision_id,
                                outcome=decision.outcome,
                                predicate_results=decision.findings_payload(),
                                reason_codes=list(decision.reason_codes),
                                facts_snapshot=facts.canonical_payload(),
                                student_explanation=decision.student_explanation,
                                input_fingerprint=fingerprint,
                            )
                        )
                    await session.flush()
                    offset += len(members)
                run.status = "completed"
                run.eligible_count = counts["eligible"]
                run.ineligible_count = counts["ineligible"]
                run.needs_review_count = counts["needs_review"]
                run.duration_ms = max(1, int((time.perf_counter() - started) * 1000))
                run.completed_at = datetime.now(UTC)
                session.add(
                    AuditLog(
                        institution_id=institution_id,
                        actor_membership_id=run.created_by_membership_id,
                        action="eligibility:run_completed",
                        target_type="evaluation_run",
                        target_id=str(run.id),
                        payload={
                            "policy_id": str(run.policy_id),
                            "cohort_fingerprint": run.cohort_fingerprint,
                            "total_count": run.total_count,
                            "eligible_count": run.eligible_count,
                            "ineligible_count": run.ineligible_count,
                            "needs_review_count": run.needs_review_count,
                            "engine_version": run.engine_version,
                            "duration_ms": run.duration_ms,
                        },
                    )
                )
                await session.execute(
                    update(EvaluationRun)
                    .where(
                        EvaluationRun.institution_id == institution_id,
                        EvaluationRun.drive_id == run.drive_id,
                        EvaluationRun.id != run.id,
                        EvaluationRun.is_stale.is_(False),
                    )
                    .values(is_stale=True, stale_reason="A newer evaluation completed for this drive")
                )
                await session.commit()
                return run
        except Exception as exc:
            async with async_session_maker() as session:
                session.info["institution_id"] = institution_id
                run = (
                    await session.execute(
                        select(EvaluationRun)
                        .where(EvaluationRun.id == run_id, EvaluationRun.institution_id == institution_id)
                        .with_for_update()
                    )
                ).scalar_one_or_none()
                if run:
                    run.status = "failed"
                    run.error_code = "EVALUATION_FAILED"
                    run.error_detail = str(exc)[:1000]
                    run.completed_at = datetime.now(UTC)
                    await session.commit()
            raise

    @staticmethod
    async def refresh_freshness(session: AsyncSession, run: EvaluationRun) -> EvaluationRun:
        if run.is_stale or run.status != "completed":
            return run
        current_policy = (
            await session.execute(
                select(EligibilityPolicyVersion.id).where(
                    EligibilityPolicyVersion.drive_id == run.drive_id,
                    EligibilityPolicyVersion.institution_id == run.institution_id,
                    EligibilityPolicyVersion.status == "approved",
                )
            )
        ).scalar_one_or_none()
        if current_policy != run.policy_id:
            run.is_stale = True
            run.stale_reason = "The approved policy changed"
            await session.flush()
            return run

        frozen = {
            item.student_profile_id: (item.membership_id, item.academic_revision_id)
            for item in (
                await session.execute(
                    select(EvaluationCohortMember).where(EvaluationCohortMember.evaluation_run_id == run.id)
                )
            ).scalars().all()
        }
        current = {
            profile.id: (membership.id, profile.current_academic_revision_id)
            for profile, membership in (
                await session.execute(
                    select(StudentProfile, Membership)
                    .join(Membership, Membership.id == StudentProfile.membership_id)
                    .where(
                        StudentProfile.institution_id == run.institution_id,
                        Membership.role == "student",
                        Membership.is_active.is_(True),
                    )
                )
            ).all()
        }
        if frozen != current:
            run.is_stale = True
            run.stale_reason = "The active roster or a verified academic revision changed"
            await session.flush()
        return run

    @staticmethod
    async def mark_student_runs_stale(
        session: AsyncSession, institution_id: uuid.UUID, student_profile_id: uuid.UUID
    ) -> None:
        run_ids = select(EvaluationCohortMember.evaluation_run_id).where(
            EvaluationCohortMember.institution_id == institution_id,
            EvaluationCohortMember.student_profile_id == student_profile_id,
        )
        await session.execute(
            update(EvaluationRun)
            .where(
                EvaluationRun.institution_id == institution_id,
                EvaluationRun.id.in_(run_ids),
                EvaluationRun.is_stale.is_(False),
            )
            .values(is_stale=True, stale_reason="A verified academic revision changed")
        )

    @staticmethod
    async def mark_institution_runs_stale(session: AsyncSession, institution_id: uuid.UUID) -> None:
        await session.execute(
            update(EvaluationRun)
            .where(EvaluationRun.institution_id == institution_id, EvaluationRun.is_stale.is_(False))
            .values(is_stale=True, stale_reason="The active student roster changed")
        )

    @staticmethod
    async def mark_drive_runs_stale(session: AsyncSession, institution_id: uuid.UUID, drive_id: uuid.UUID) -> None:
        await session.execute(
            update(EvaluationRun)
            .where(
                EvaluationRun.institution_id == institution_id,
                EvaluationRun.drive_id == drive_id,
                EvaluationRun.is_stale.is_(False),
            )
            .values(is_stale=True, stale_reason="The approved eligibility policy changed")
        )
