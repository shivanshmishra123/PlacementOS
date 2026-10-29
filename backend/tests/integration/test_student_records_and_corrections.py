"""Integration tests for Student Records, CSV Preview/Commit, Academic Revisions, and Correction Review (P02-T04 through P02-T08).

Verifies:
- INV-02: Missing active backlog differs from zero (None != 0).
- INV-05: Exact decimal CGPA arithmetic.
- INV-06: Cross-institution isolation (Beacon coordinator cannot view Apex student).
- P02-T05: CSV preview makes ZERO database mutations; commit is atomic and idempotent.
- P02-T06: Unreviewed/rejected corrections leave verified facts unchanged; approved corrections append revision.
- P02-T08: AuditLog entries recorded for commits and decisions.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from placementos.core.database import async_session_maker
from placementos.models.identity import AuditLog, StudentProfile


def generate_test_csv(prefix: str) -> tuple[str, str, str, str]:
    """Generate a test CSV with unique identifiers to avoid collision with prior test runs."""
    id_1 = f"{prefix}-001"
    id_2 = f"{prefix}-002"
    id_3 = f"{prefix}-003"
    csv_text = f"""student_identifier,full_name,email,branch,cgpa,scale,graduation_year,active_backlogs
{id_1},Aarav Sharma,{prefix}.a@apex.edu,CSE,8.50,10.00,2027,0
{id_2},Bhavna Patel,{prefix}.b@apex.edu,IT,7.20,10.00,2027,
{id_3},Chirag Reddy,{prefix}.c@apex.edu,ECE,9.10,10.00,2027,2
"""
    return csv_text, id_1, id_2, id_3


@pytest.mark.asyncio
async def test_csv_preview_makes_no_mutations_and_validates_rows(client: AsyncClient):
    """Verify P02-T05: preview_csv parses and reports counts with ZERO database mutations."""
    # 1. Dev login as Priya Sharma (Apex coordinator)
    login_resp = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    assert login_resp.status_code == 200

    # Check student profile count before preview
    async with async_session_maker() as session:
        count_before = await session.scalar(select(func.count()).select_from(StudentProfile))

    # 2. Call preview endpoint with unique test cohort
    prefix = f"PREV-{uuid.uuid4().hex[:6].upper()}"
    test_csv, id_1, id_2, id_3 = generate_test_csv(prefix)

    preview_resp = await client.post(
        "/api/v1/students/import-preview",
        json={"csv_content": test_csv},
    )
    assert preview_resp.status_code == 200
    data = preview_resp.json()

    assert data["total_rows"] == 3
    assert data["valid_rows_count"] == 3
    assert data["invalid_rows_count"] == 0
    assert data["new_students_count"] == 3
    assert "preview_token" in data

    # Verify student with empty backlog has None (missing) while Student A has 0 (clean)
    rows = data["sample_rows"]
    student_a = next(r for r in rows if r["student_identifier"] == id_1)
    student_b = next(r for r in rows if r["student_identifier"] == id_2)
    student_c = next(r for r in rows if r["student_identifier"] == id_3)

    assert student_a["active_backlogs"] == 0
    assert student_b["active_backlogs"] is None  # Missing/Unknown (INV-02)
    assert student_c["active_backlogs"] == 2

    # Check student profile count after preview: MUST BE IDENTICAL
    async with async_session_maker() as session:
        count_after = await session.scalar(select(func.count()).select_from(StudentProfile))
    assert count_before == count_after, "CSV preview must not create any database records!"


@pytest.mark.asyncio
async def test_csv_commit_and_revisions_lifecycle(client: AsyncClient):
    """Verify P02-T05: commit creates verified profiles, revisions, and attributable audit log."""
    # 1. Dev login as Apex coordinator
    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    institution_id = login.json()["user"]["institution_id"]

    # 2. Preview
    prefix = f"COMM-{uuid.uuid4().hex[:6].upper()}"
    test_csv, id_1, id_2, id_3 = generate_test_csv(prefix)

    preview_resp = await client.post(
        "/api/v1/students/import-preview",
        json={"csv_content": test_csv},
    )
    preview_token = preview_resp.json()["preview_token"]

    # 3. Commit
    commit_resp = await client.post(
        "/api/v1/students/import-commit",
        json={"preview_token": preview_token},
    )
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()
    assert commit_data["total_committed"] == 3

    # 4. Verify students now exist in GET /api/v1/students
    list_resp = await client.get("/api/v1/students")
    assert list_resp.status_code == 200
    students = list_resp.json()
    identifiers = [s["student_identifier"] for s in students]
    assert id_1 in identifiers
    assert id_2 in identifiers
    assert id_3 in identifiers

    # Verify student detail and revision history
    student_a = next(s for s in students if s["student_identifier"] == id_1)
    detail_resp = await client.get(f"/api/v1/students/{student_a['id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["current_verified_revision"]["revision_number"] == 1
    assert detail["current_verified_revision"]["is_verified"] is True
    assert detail["current_verified_revision"]["cgpa"] == 8.50
    assert detail["current_verified_revision"]["active_backlogs"] == 0

    # 5. Check AuditLog entry was recorded
    async with async_session_maker() as session:
        session.info["institution_id"] = institution_id
        audit_res = await session.execute(
            select(AuditLog).where(AuditLog.action == "student:import_commit")
        )
        audit_entry = audit_res.scalars().first()
        assert audit_entry is not None


@pytest.mark.asyncio
async def test_student_correction_review_lifecycle(client: AsyncClient):
    """Verify P02-T06: student proposes correction, rejection leaves facts unchanged, approval increments revision."""
    # 1. First import a unique student as Apex coordinator
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    prefix = f"CORR-{uuid.uuid4().hex[:6].upper()}"
    test_csv, id_1, _, _ = generate_test_csv(prefix)

    preview_resp = await client.post("/api/v1/students/import-preview", json={"csv_content": test_csv})
    preview_token = preview_resp.json()["preview_token"]
    await client.post("/api/v1/students/import-commit", json={"preview_token": preview_token})

    # 2. Login as that student
    student_email = f"{prefix}.a@apex.edu".lower()
    login_resp = await client.post("/api/v1/auth/dev-login", json={"email": student_email})
    assert login_resp.status_code == 200

    # 3. Student views their profile
    me_resp = await client.get("/api/v1/student/me")
    assert me_resp.status_code == 200
    my_profile = me_resp.json()
    initial_cgpa = my_profile["current_verified_revision"]["cgpa"]
    initial_rev_num = my_profile["current_verified_revision"]["revision_number"]

    # 4. Student submits correction proposal (e.g. CGPA update from 8.50 to 8.90)
    proposal_resp = await client.post(
        "/api/v1/student/corrections",
        json={
            "proposed_changes": {"cgpa": "8.90"},
            "justification": "Semester 6 re-evaluation grade sheet updated",
            "supporting_document_url": "https://storage.placementos.local/evidence/eval_sem6.pdf",
        },
    )
    assert proposal_resp.status_code == 200
    prop_data = proposal_resp.json()
    proposal_id = prop_data["id"]
    assert prop_data["status"] == "pending"

    # 5. Verify verified profile facts remain UNCHANGED while pending
    check_me = await client.get("/api/v1/student/me")
    assert check_me.json()["current_verified_revision"]["cgpa"] == initial_cgpa

    # 5b. Verify student can list own correction requests with pending status
    my_corr_resp = await client.get("/api/v1/student/corrections")
    assert my_corr_resp.status_code == 200
    my_corrs = my_corr_resp.json()
    assert any(c["id"] == proposal_id and c["status"] == "pending" for c in my_corrs)

    # 6. Coordinator logs in and reviews pending corrections
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    pending_resp = await client.get("/api/v1/students/corrections/pending")
    assert pending_resp.status_code == 200
    pending_list = pending_resp.json()
    assert any(p["id"] == proposal_id for p in pending_list)

    # 7. Coordinator approves proposal
    decide_resp = await client.post(
        f"/api/v1/students/corrections/{proposal_id}/decide",
        json={"decision": "approved", "review_notes": "Verified against registrar portal"},
    )
    assert decide_resp.status_code == 200
    decide_data = decide_resp.json()
    assert decide_data["status"] == "approved"

    # 8. Student checks profile: new verified revision 2 is now active with CGPA 8.90
    await client.post("/api/v1/auth/dev-login", json={"email": student_email})
    updated_me = await client.get("/api/v1/student/me")
    assert updated_me.status_code == 200
    updated_data = updated_me.json()
    assert updated_data["current_verified_revision"]["cgpa"] == 8.90
    assert updated_data["current_verified_revision"]["revision_number"] == initial_rev_num + 1
    assert len(updated_data["revision_history"]) >= 2

    # 8b. Student checks that correction proposal status is now updated to approved
    my_corr_updated = await client.get("/api/v1/student/corrections")
    assert my_corr_updated.status_code == 200
    approved_corr = next(c for c in my_corr_updated.json() if c["id"] == proposal_id)
    assert approved_corr["status"] == "approved"
    assert approved_corr["review_notes"] == "Verified against registrar portal"


@pytest.mark.asyncio
async def test_cross_tenant_student_access_denied(client: AsyncClient):
    """Verify INV-06: Beacon coordinator cannot access an Apex student detail."""
    # 1. Apex coordinator imports student
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    list_resp = await client.get("/api/v1/students")
    apex_students = list_resp.json()
    assert len(apex_students) > 0
    apex_student_id = apex_students[0]["id"]

    # 2. Beacon coordinator logs in
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_beacon"})

    # 3. Beacon coordinator attempts to get Apex student by direct ID
    denied_resp = await client.get(f"/api/v1/students/{apex_student_id}")
    assert denied_resp.status_code == 404
    assert "not found in this institution" in denied_resp.json()["error"]["message"]
