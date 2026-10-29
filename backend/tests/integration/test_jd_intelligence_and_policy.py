"""P04 end-to-end review, policy, approval, staleness, and authorization tests."""

import uuid

import pytest
from httpx import AsyncClient

from placementos.services.source_jobs import SourceJobService


@pytest.mark.asyncio
async def test_review_clarify_compile_and_approve_exact_policy(client: AsyncClient, monkeypatch):
    from placementos.workers.source_tasks import extract_source_text_task

    monkeypatch.setattr(extract_source_text_task, "delay", lambda *args, **kwargs: None)
    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    institution_id = login.json()["user"]["institution_id"]
    company = await client.post(
        "/api/v1/companies", json={"name": f"Nexora-{uuid.uuid4().hex[:8]}"}
    )
    drive = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2026-2027",
            "title": "Software Development Engineer",
        },
    )
    drive_id = drive.json()["id"]
    source = await client.post(
        f"/api/v1/drives/{drive_id}/sources/pasted",
        json={
            "title": "Nexora JD",
            "raw_text": (
                "Company: Nexora Technologies\nRole: Software Development Engineer\n\n"
                "CSE and Information Technology students graduating in 2027 are eligible.\n\n"
                "Minimum CGPA: 7.50 out of 10 with no active backlogs.\n\n"
                "Registration deadline: 2026-11-05. CTC: 12 LPA."
            ),
        },
    )
    artifact_id = source.json()["id"]
    await SourceJobService.run_extraction(uuid.UUID(artifact_id), uuid.UUID(institution_id))

    interpretation_response = await client.post(
        f"/api/v1/drives/{drive_id}/interpretations",
        json={"source_artifact_id": artifact_id, "mode": "fixture"},
    )
    assert interpretation_response.status_code == 201
    interpretation = interpretation_response.json()
    assert interpretation["reviewed_facts"]["eligibility_draft"]["minimum_cgpa"] == "7.50"
    assert interpretation["reviewed_facts"]["eligibility_draft"]["graduation_years"] == [2027]
    assert interpretation["clarifications"][0]["reason_code"] == "DEADLINE_TIMEZONE_MISSING"

    clarification = interpretation["clarifications"][0]
    resolved = await client.post(
        f"/api/v1/clarifications/{clarification['id']}/resolve",
        json={
            "value": "2026-11-05T17:00:00+05:30",
            "rationale": "Recruiter confirmed 5 PM Asia/Kolkata by attributed call note",
        },
    )
    assert resolved.status_code == 200
    assert all(item["status"] == "resolved" for item in resolved.json()["clarifications"])

    policy_response = await client.post(
        f"/api/v1/drives/{drive_id}/policies",
        json={"interpretation_id": interpretation["id"], "explicitly_not_required": []},
    )
    assert policy_response.status_code == 201
    policy = policy_response.json()
    assert policy["policy_payload"]["cgpa"]["minimum"] == "7.50"
    assert policy["status"] == "draft"

    proposal_response = await client.post(f"/api/v1/policies/{policy['id']}/submit-review")
    assert proposal_response.status_code == 201
    proposal = proposal_response.json()

    stale = await client.post(
        f"/api/v1/proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": "0" * 64,
            "decision": "approved",
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "PROPOSAL_STALE"

    approved = await client.post(
        f"/api/v1/proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "approved",
            "comment": "Evidence and typed criteria reviewed",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["policy_status"] == "approved"

    immutable = await client.post(
        f"/api/v1/interpretations/{interpretation['id']}/corrections",
        json={
            "field_path": "eligibility_draft.minimum_cgpa",
            "corrected_value": "8.00",
            "rationale": "Attempt to edit an approved dependency",
        },
    )
    assert immutable.status_code == 409


@pytest.mark.asyncio
async def test_admin_without_rule_approval_cannot_create_or_approve_drive_work(client: AsyncClient):
    await client.post("/api/v1/auth/dev-login", json={"persona": "admin_apex"})
    response = await client.post("/api/v1/companies", json={"name": "Unauthorized Company"})
    assert response.status_code == 403
