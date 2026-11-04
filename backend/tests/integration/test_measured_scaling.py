"""P13 measured bottleneck, tenant policy, quota, and index acceptance tests."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.models.identity import Institution, Membership, User


@pytest.mark.asyncio
async def test_drive_summary_projection_matches_detail_and_is_tenant_scoped(
    client: AsyncClient,
):
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    suffix = uuid.uuid4().hex[:8]
    company = await client.post("/api/v1/companies", json={"name": f"P13 Summary {suffix}"})
    drive = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2028-2029",
            "title": f"Measured projection {suffix}",
        },
    )
    assert drive.status_code == 201
    drive_id = drive.json()["id"]
    source = await client.post(
        f"/api/v1/drives/{drive_id}/sources/pasted",
        json={"title": "P13 fixture", "raw_text": "Synthetic measured scaling source."},
    )
    assert source.status_code == 201

    summaries = await client.get("/api/v1/drive-summaries?limit=100")
    assert summaries.status_code == 200
    summary = next(item for item in summaries.json()["items"] if item["id"] == drive_id)
    assert summary["company_name"] == drive.json()["company_name"]
    assert summary["academic_year"] == "2028-2029"
    assert summary["current_revision_number"] == drive.json()["current_revision_number"]
    assert summary["source_artifact_count"] == 1

    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_beacon"})
    beacon_summaries = await client.get("/api/v1/drive-summaries?limit=100")
    assert beacon_summaries.status_code == 200
    assert drive_id not in {item["id"] for item in beacon_summaries.json()["items"]}


@pytest.mark.asyncio
async def test_operating_policy_is_revisioned_authorized_and_tenant_scoped(
    client: AsyncClient,
):
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    coordinator_view = await client.get("/api/v1/institution/operating-policy")
    assert coordinator_view.status_code == 200
    forbidden = await client.put(
        "/api/v1/institution/operating-policy",
        json={
            "expected_revision": coordinator_view.json()["revision_number"],
            "onboarding_status": "synthetic_ready",
            "max_open_drives": 100_000,
            "max_students_per_import": 1_000_000,
            "max_export_rows": 1_000_000,
            "change_reason": "Coordinator must not own institution configuration",
        },
    )
    assert forbidden.status_code == 403

    admin_login = await client.post("/api/v1/auth/dev-login", json={"persona": "admin_apex"})
    apex_id = admin_login.json()["user"]["institution_id"]
    current = await client.get("/api/v1/institution/operating-policy")
    update = await client.put(
        "/api/v1/institution/operating-policy",
        json={
            "expected_revision": current.json()["revision_number"],
            "onboarding_status": "synthetic_ready",
            "max_open_drives": 100_000,
            "max_students_per_import": 1_000_000,
            "max_export_rows": 1_000_000,
            "change_reason": "P13 synthetic multi-tenant acceptance capacity",
        },
    )
    assert update.status_code == 200
    assert update.json()["revision_number"] == current.json()["revision_number"] + 1
    stale = await client.put(
        "/api/v1/institution/operating-policy",
        json={
            "expected_revision": current.json()["revision_number"],
            "onboarding_status": "pilot_ready",
            "max_open_drives": 100_000,
            "max_students_per_import": 1_000_000,
            "max_export_rows": 1_000_000,
            "change_reason": "Stale concurrent edit must be rejected",
        },
    )
    assert stale.status_code == 409

    beacon_admin = f"p13.admin.{uuid.uuid4().hex[:8]}@beacon-scale.test"
    beacon_login = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": beacon_admin, "institution_slug": "beacon-state"},
    )
    assert beacon_login.json()["user"]["institution_id"] != apex_id
    assert (await client.get("/api/v1/institution/operating-policy")).status_code == 403


@pytest.mark.asyncio
async def test_custom_tenant_quotas_and_measured_indexes(
    client: AsyncClient,
    admin_db_session: AsyncSession,
):
    suffix = uuid.uuid4().hex[:10]
    slug = f"p13-scale-{suffix}"
    admin_email = f"admin.{suffix}@p13-scale.test"
    initial = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": admin_email, "institution_slug": slug},
    )
    institution_id = uuid.UUID(initial.json()["user"]["institution_id"])
    membership = (
        await admin_db_session.execute(
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.institution_id == institution_id,
                User.email == admin_email,
            )
        )
    ).scalar_one()
    membership.role = "institution_admin"
    membership.capabilities = ["config:manage", "ops:view"]
    await admin_db_session.commit()

    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": admin_email, "institution_slug": slug},
    )
    policy = await client.put(
        "/api/v1/institution/operating-policy",
        json={
            "expected_revision": 0,
            "onboarding_status": "synthetic_ready",
            "max_open_drives": 1,
            "max_students_per_import": 1,
            "max_export_rows": 1,
            "change_reason": "P13 isolated quota boundary fixture",
        },
    )
    assert policy.status_code == 200

    coordinator_email = f"coordinator.{suffix}@p13-scale.test"
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": coordinator_email, "institution_slug": slug},
    )
    coordinator = (
        await admin_db_session.execute(
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.institution_id == institution_id,
                User.email == coordinator_email,
            )
        )
    ).scalar_one()
    coordinator.capabilities = ["drive:create", "student:import"]
    await admin_db_session.commit()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": coordinator_email, "institution_slug": slug},
    )

    company = await client.post("/api/v1/companies", json={"name": f"Quota {suffix}"})
    first = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2028-2029",
            "title": "Within quota",
        },
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2028-2029",
            "title": "Above quota",
        },
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "INSTITUTION_QUOTA_REACHED"

    csv_content = (
        "student_identifier,full_name,email,branch,cgpa,graduation_year\n"
        f"{suffix}-1,One Student,one.{suffix}@test.edu,CSE,8.0,2029\n"
        f"{suffix}-2,Two Student,two.{suffix}@test.edu,CSE,8.0,2029\n"
    )
    imported = await client.post(
        "/api/v1/students/import-preview", json={"csv_content": csv_content}
    )
    assert imported.status_code == 409
    assert imported.json()["error"]["details"]["quota"] == "max_students_per_import"

    assert await admin_db_session.scalar(
        select(Institution.id).where(Institution.id == institution_id)
    )
    indexes = set(
        (
            await admin_db_session.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE indexname LIKE 'ix_drives_inst_%' "
                    "OR indexname = 'ix_drive_assignments_inst_member_drive'"
                )
            )
        ).scalars()
    )
    assert {
        "ix_drives_inst_created_id",
        "ix_drives_inst_creator_created",
        "ix_drives_inst_assignee_created",
        "ix_drive_assignments_inst_member_drive",
    }.issubset(indexes)
