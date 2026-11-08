"""Production tenant onboarding, institution bootstrap, and verified evidence controls."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.errors import ConflictException, NotFoundException
from placementos.models.academic import AcademicRecordRevision
from placementos.models.identity import Institution, Membership, StudentProfile, User
from placementos.services.audit import record_audit
from placementos.services.session import AuthContext

logger = logging.getLogger(__name__)

INSTITUTION_ADMIN_CAPABILITIES = [
    "member:manage",
    "config:manage",
    "audit:read",
    "ops:view",
    "student:read",
    "student:import",
    "eligibility:run",
    "integration:manage",
]


async def bootstrap_institution(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
    domain: str,
    admin_email: str,
    admin_name: str,
    actor_auth: AuthContext | None = None,
) -> tuple[Institution, User, Membership]:
    """Bootstrap an empty production institution with an administrative owner (P19).

    Production rules:
    - Creates no sample companies, drives, policies, or synthetic students.
    - Ensures clean isolated institution record.
    - Generates administrative user and membership with audit log.
    """
    clean_slug = slug.strip().lower()
    clean_domain = domain.strip().lower()
    clean_email = admin_email.strip().lower()

    # Check for existing institution with slug or domain
    existing = (
        await session.execute(
            select(Institution).where(
                (Institution.slug == clean_slug) | (Institution.domain == clean_domain)
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictException(f"Institution with slug '{clean_slug}' or domain '{clean_domain}' already exists")

    institution = Institution(
        slug=clean_slug,
        name=name.strip(),
        domain=clean_domain,
    )
    session.add(institution)
    await session.flush()

    # Look up or create administrator user
    admin_user = (
        await session.execute(select(User).where(User.email == clean_email))
    ).scalar_one_or_none()
    if not admin_user:
        admin_user = User(
            email=clean_email,
            full_name=admin_name.strip(),
        )
        session.add(admin_user)
        await session.flush()

    # Create admin membership
    membership = Membership(
        institution_id=institution.id,
        user_id=admin_user.id,
        role="institution_admin",
        capabilities=INSTITUTION_ADMIN_CAPABILITIES,
    )
    session.add(membership)
    await session.flush()

    if actor_auth:
        record_audit(
            session,
            actor_auth,
            "institution:bootstrapped",
            "institution",
            institution.id,
            {"slug": clean_slug, "domain": clean_domain, "admin_email": clean_email},
        )

    await session.commit()
    logger.info("Successfully bootstrapped empty production institution %s (%s)", clean_slug, institution.id)
    return institution, admin_user, membership


async def verify_student_academic_records(
    session: AsyncSession,
    *,
    auth: AuthContext,
    student_profile_ids: list[uuid.UUID],
) -> int:
    """Mark student academic records as officially verified by authorized institutional staff (INV-02).

    Unverified student corrections cannot be used for eligibility evaluation without authorized verification.
    """
    auth.require_capability("student:import")
    verified_count = 0

    for profile_id in student_profile_ids:
        profile = (
            await session.execute(
                select(StudentProfile).where(
                    StudentProfile.id == profile_id,
                    StudentProfile.institution_id == auth.institution_id,
                )
            )
        ).scalar_one_or_none()
        if not profile:
            raise NotFoundException(f"Student profile {profile_id} not found in this institution")

        if profile.current_academic_revision_id:
            revision = await session.get(AcademicRecordRevision, profile.current_academic_revision_id)
            if revision and not revision.is_verified:
                revision.is_verified = True
                verified_count += 1

    record_audit(
        session,
        auth,
        "academic:records_verified",
        "student_profiles",
        auth.institution_id,
        {"verified_count": verified_count, "profile_ids": [str(pid) for pid in student_profile_ids]},
    )
    await session.commit()
    return verified_count
