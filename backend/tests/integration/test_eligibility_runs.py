"""P05 persisted snapshot, evaluation, staleness, and student privacy tests."""

import uuid

import pytest
from httpx import AsyncClient

from placementos.services.eligibility_runs import EligibilityRunService
from placementos.services.source_jobs import SourceJobService


@pytest.mark.asyncio
async def test_frozen_cohort_run_staleness_and_personal_explanation(
    client: AsyncClient, monkeypatch
):
    from placementos.workers.eligibility_tasks import evaluate_eligibility_task
    from placementos.workers.source_tasks import extract_source_text_task

    monkeypatch.setattr(extract_source_text_task, "delay", lambda *args, **kwargs: None)
    monkeypatch.setattr(evaluate_eligibility_task, "delay", lambda *args, **kwargs: None)
    suffix = uuid.uuid4().hex[:8]
    student_email = f"p05-student-{suffix}@apex.edu"
    other_email = f"p05-other-{suffix}@apex.edu"

    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    institution_id = login.json()["user"]["institution_id"]
    company = await client.post("/api/v1/companies", json={"name": f"P05-{suffix}"})
    drive = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2026-2027",
            "title": "Deterministic eligibility acceptance",
        },
    )
    drive_id = drive.json()["id"]
    source = await client.post(
        f"/api/v1/drives/{drive_id}/sources/pasted",
        json={
            "title": "P05 policy source",
            "raw_text": (
                "Company: P05 Test\nRole: Engineer\nCSE and IT students graduating in 2027 "
                "are eligible.\nMinimum CGPA: 7.50 out of 10 with no active backlogs.\n"
                "Registration deadline: 2026-11-05. CTC: 12 LPA."
            ),
        },
    )
    await SourceJobService.run_extraction(
        uuid.UUID(source.json()["id"]), uuid.UUID(institution_id)
    )
    interpretation_response = await client.post(
        f"/api/v1/drives/{drive_id}/interpretations",
        json={"source_artifact_id": source.json()["id"], "mode": "fixture"},
    )
    interpretation = interpretation_response.json()
    for clarification in interpretation["clarifications"]:
        await client.post(
            f"/api/v1/clarifications/{clarification['id']}/resolve",
            json={"value": "2026-11-05T17:00:00+05:30", "rationale": "Fixture confirmation"},
        )
    policy = await client.post(
        f"/api/v1/drives/{drive_id}/policies",
        json={"interpretation_id": interpretation["id"], "explicitly_not_required": []},
    )
    proposal = await client.post(f"/api/v1/policies/{policy.json()['id']}/submit-review")
    approved = await client.post(
        f"/api/v1/proposals/{proposal.json()['id']}/decisions",
        json={
            "expected_revision": proposal.json()["revision_number"],
            "expected_hash": proposal.json()["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200

    csv_text = f"""student_identifier,full_name,email,branch,cgpa,scale,graduation_year,active_backlogs
P05-A-{suffix},Student A,{student_email},CSE,7.50,10.00,2027,0
P05-B-{suffix},Student B,{other_email},ECE,8.80,10.00,2027,0
P05-E-{suffix},Student E,p05-review-{suffix}@apex.edu,IT,7.90,10.00,2027,
"""
    preview = await client.post("/api/v1/students/import-preview", json={"csv_content": csv_text})
    assert preview.status_code == 200
    committed = await client.post(
        "/api/v1/students/import-commit",
        json={"preview_token": preview.json()["preview_token"]},
    )
    assert committed.status_code == 200

    queued = await client.post(
        f"/api/v1/drives/{drive_id}/evaluations",
        json={"policy_id": policy.json()["id"]},
    )
    assert queued.status_code == 202
    run_id = uuid.UUID(queued.json()["id"])
    duplicate = await client.post(
        f"/api/v1/drives/{drive_id}/evaluations",
        json={"policy_id": policy.json()["id"]},
    )
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == str(run_id)
    await EligibilityRunService.execute_run(run_id, uuid.UUID(institution_id))
    completed = await client.get(f"/api/v1/evaluation-runs/{run_id}")
    assert completed.status_code == 200
    payload = completed.json()
    assert payload["status"] == "completed"
    assert payload["total_count"] == (
        payload["eligible_count"] + payload["ineligible_count"] + payload["needs_review_count"]
    )
    own_result = next(
        item for item in payload["results"] if item["student_identifier"] == f"P05-A-{suffix}"
    )
    other_result = next(
        item for item in payload["results"] if item["student_identifier"] == f"P05-B-{suffix}"
    )
    assert own_result["outcome"] == "eligible"
    assert other_result["outcome"] == "ineligible"

    # A verified revision changes after the frozen run; history remains unchanged and becomes stale.
    changed_csv = f"""student_identifier,full_name,email,branch,cgpa,scale,graduation_year,active_backlogs
P05-A-{suffix},Student A,{student_email},CSE,7.49,10.00,2027,0
"""
    preview2 = await client.post("/api/v1/students/import-preview", json={"csv_content": changed_csv})
    await client.post(
        "/api/v1/students/import-commit",
        json={"preview_token": preview2.json()["preview_token"]},
    )
    historical = await client.get(f"/api/v1/evaluation-runs/{run_id}")
    assert historical.json()["is_stale"] is True
    frozen_own = next(
        item for item in historical.json()["results"] if item["student_identifier"] == f"P05-A-{suffix}"
    )
    assert frozen_own["outcome"] == "eligible"
    assert frozen_own["academic_revision_id"] == own_result["academic_revision_id"]

    current_run = await client.post(
        f"/api/v1/drives/{drive_id}/evaluations",
        json={"policy_id": policy.json()["id"]},
    )
    assert current_run.status_code == 202
    assert current_run.json()["id"] != str(run_id)
    current_run_id = uuid.UUID(current_run.json()["id"])
    await EligibilityRunService.execute_run(current_run_id, uuid.UUID(institution_id))
    current_payload = (await client.get(f"/api/v1/evaluation-runs/{current_run_id}")).json()
    current_own = next(
        item for item in current_payload["results"] if item["student_identifier"] == f"P05-A-{suffix}"
    )
    assert current_own["outcome"] == "ineligible"
    assert "CGPA_BELOW_MINIMUM" in current_own["reason_codes"]

    # Student actions remain hidden until publication, even if a result UUID is retained.
    client.cookies.clear()
    student_login = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": student_email, "institution_slug": "apex-tech"},
    )
    assert student_login.status_code == 200
    assert (await client.get("/api/v1/student/eligibility")).json() == []
    unpublished_review = await client.post(
        f"/api/v1/student/eligibility/{current_own['id']}/review-request",
        json={"reason": "This unpublished result must remain unavailable"},
    )
    assert unpublished_review.status_code == 404

    # Student audience sees published personal results only and cannot address another result by ID.
    client.cookies.clear()
    coordinator_login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    assert coordinator_login.status_code == 200
    published = await client.patch(
        f"/api/v1/drives/{drive_id}",
        json={"status": "published"},
    )
    assert published.status_code == 200
    client.cookies.clear()
    student_login = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": student_email, "institution_slug": "apex-tech"},
    )
    assert student_login.status_code == 200
    personal = await client.get("/api/v1/student/eligibility")
    assert personal.status_code == 200
    assert any(item["result_id"] == current_own["id"] for item in personal.json())
    assert all(item["result_id"] != other_result["id"] for item in personal.json())
    review = await client.post(
        f"/api/v1/student/eligibility/{current_own['id']}/review-request",
        json={"reason": "Please verify the newly imported CGPA evidence"},
    )
    assert review.status_code == 201
    duplicate_review = await client.post(
        f"/api/v1/student/eligibility/{current_own['id']}/review-request",
        json={"reason": "A duplicate open request must not be created"},
    )
    assert duplicate_review.status_code == 409
    hidden = await client.post(
        f"/api/v1/student/eligibility/{other_result['id']}/review-request",
        json={"reason": "This result should remain hidden from another student"},
    )
    assert hidden.status_code == 404
    old_result_review = await client.post(
        f"/api/v1/student/eligibility/{own_result['id']}/review-request",
        json={"reason": "A superseded historical result must not accept new review work"},
    )
    assert old_result_review.status_code == 404

    client.cookies.clear()
    limited = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": f"limited-coordinator-{suffix}@apex.edu", "institution_slug": "apex-tech"},
    )
    assert limited.status_code == 200
    forbidden = await client.post(f"/api/v1/drives/{drive_id}/evaluations", json={})
    assert forbidden.status_code == 403
