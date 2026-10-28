"""Tests for Institution, Membership, and Scoped Student Identity (P02-T01).

Verifies:
- Scoped uniqueness: The same student number is valid in two different institutions without collision.
- Intentionally duplicate student number within the same institution triggers integrity error.
- Institutional isolation and membership role/capability assignments.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import async_session_maker
from placementos.models.identity import (
    DriveAssignment,
    Institution,
    Membership,
    StudentProfile,
    User,
)


@pytest.fixture
async def db_session():
    """Create an isolated transaction session for testing."""
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_scoped_student_identifier_uniqueness_across_institutions(db_session: AsyncSession):
    """Verify INV-06: The exact same student identifier (e.g.

    2024-CS-001) is valid in two different institutions without leakage,
    while duplicate identifiers within the SAME institution are rejected.
    """
    # 1. Create two distinct institutions
    inst_apex = Institution(
        slug=f"apex-{uuid.uuid4().hex[:6]}",
        name="Apex Institute of Technology",
        domain="apex.edu",
    )
    inst_beacon = Institution(
        slug=f"beacon-{uuid.uuid4().hex[:6]}",
        name="Beacon Engineering College",
        domain="beacon.edu",
    )
    db_session.add_all([inst_apex, inst_beacon])
    await db_session.flush()

    # 2. Create users for both students
    user_apex = User(
        email=f"student.apex.{uuid.uuid4().hex[:6]}@apex.edu",
        full_name="Aarav Sharma",
    )
    user_beacon = User(
        email=f"student.beacon.{uuid.uuid4().hex[:6]}@beacon.edu",
        full_name="Aditi Rao",
    )
    db_session.add_all([user_apex, user_beacon])
    await db_session.flush()

    # 3. Create student profiles with the IDENTICAL student_identifier in both institutions
    shared_identifier = "2024-CS-001"

    profile_apex = StudentProfile(
        institution_id=inst_apex.id,
        user_id=user_apex.id,
        student_identifier=shared_identifier,
    )
    profile_beacon = StudentProfile(
        institution_id=inst_beacon.id,
        user_id=user_beacon.id,
        student_identifier=shared_identifier,
    )
    db_session.add_all([profile_apex, profile_beacon])
    await db_session.flush()

    # 4. Assert both records exist independently in their respective institutional scopes
    res_apex = await db_session.execute(
        select(StudentProfile).where(
            StudentProfile.institution_id == inst_apex.id,
            StudentProfile.student_identifier == shared_identifier,
        )
    )
    found_apex = res_apex.scalar_one()
    assert found_apex.id == profile_apex.id
    assert found_apex.user_id == user_apex.id

    res_beacon = await db_session.execute(
        select(StudentProfile).where(
            StudentProfile.institution_id == inst_beacon.id,
            StudentProfile.student_identifier == shared_identifier,
        )
    )
    found_beacon = res_beacon.scalar_one()
    assert found_beacon.id == profile_beacon.id
    assert found_beacon.user_id == user_beacon.id
    assert found_apex.id != found_beacon.id

    # 5. Negative Test: Creating a second student in Apex with the SAME student identifier must fail
    user_collision = User(
        email=f"collision.{uuid.uuid4().hex[:6]}@apex.edu",
        full_name="Duplicate Roll Number Student",
    )
    db_session.add(user_collision)
    await db_session.flush()

    profile_duplicate = StudentProfile(
        institution_id=inst_apex.id,
        user_id=user_collision.id,
        student_identifier=shared_identifier,
    )
    db_session.add(profile_duplicate)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_institutional_membership_and_capabilities(db_session: AsyncSession):
    """Verify membership binding, role assignments, and capabilities."""
    institution = Institution(
        slug=f"apex-members-{uuid.uuid4().hex[:6]}",
        name="Apex Tech",
        domain="apex.edu",
    )
    db_session.add(institution)
    await db_session.flush()

    coordinator = User(
        email=f"coord.{uuid.uuid4().hex[:6]}@apex.edu",
        full_name="Priya Sharma",
    )
    db_session.add(coordinator)
    await db_session.flush()

    coord_caps = ["drive:create", "drive:edit", "rule:approve", "proposal:decide"]
    membership = Membership(
        institution_id=institution.id,
        user_id=coordinator.id,
        role="placement_coordinator",
        capabilities=coord_caps,
    )
    db_session.add(membership)
    await db_session.flush()

    # Query back membership
    res = await db_session.execute(
        select(Membership).where(
            Membership.institution_id == institution.id,
            Membership.user_id == coordinator.id,
        )
    )
    loaded_membership = res.scalar_one()
    assert loaded_membership.role == "placement_coordinator"
    assert loaded_membership.capabilities == coord_caps
    assert loaded_membership.is_active is True

    # Test DriveAssignment linking
    drive_id = uuid.uuid4()
    assignment = DriveAssignment(
        institution_id=institution.id,
        membership_id=loaded_membership.id,
        drive_id=drive_id,
        assigned_role="lead_coordinator",
    )
    db_session.add(assignment)
    await db_session.flush()

    res_assign = await db_session.execute(
        select(DriveAssignment).where(
            DriveAssignment.membership_id == loaded_membership.id,
            DriveAssignment.drive_id == drive_id,
        )
    )
    loaded_assign = res_assign.scalar_one()
    assert loaded_assign.assigned_role == "lead_coordinator"
