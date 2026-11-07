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
    assert interpretation["usage_metadata"]["calls"] == 1
    assert interpretation["usage_metadata"]["provider"] == "fixture"
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


@pytest.mark.asyncio
async def test_cached_model_interpretation_flow_and_proposal_invalidation(client: AsyncClient, monkeypatch):
    from placementos.core.config import settings
    from placementos.workers.source_tasks import extract_source_text_task

    monkeypatch.setattr(extract_source_text_task, "delay", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "MODEL_INTERPRETER_MODE", "cached")

    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    institution_id = login.json()["user"]["institution_id"]
    company = await client.post("/api/v1/companies", json={"name": f"Nexora-{uuid.uuid4().hex[:8]}"})
    drive = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2026-2027",
            "title": "Associate Software Engineer",
        },
    )
    drive_id = drive.json()["id"]

    sample_jd_text = (
        "Nexora Dynamics - Campus Recruitment 2026-2027\n\n"
        "Position: Associate Software Engineer (Platform & AI Systems)\n"
        "Location: Bengaluru / Hyderabad (Hybrid: 3 days in office, 2 days remote)\n"
        "Employment Type: Full-time\n\n"
        "About the Role:\n"
        "We are seeking high-caliber engineering graduates to join our Core Platform engineering group. You will develop distributed cloud systems and AI orchestration pipelines using Python, TypeScript, and Go.\n\n"
        "Eligibility & Academic Requirements:\n"
        "- Permitted Engineering Disciplines: B.Tech / B.E. in Computer Science Engineering (CSE), Information Technology (IT), or Electronics & Communication Engineering (ECE).\n"
        "- Academic Cutoff: Minimum aggregate CGPA of 7.50 out of 10.0 (or equivalent percentage) across all completed semesters.\n"
        "- Backlog Policy: Maximum 0 active backlogs at the time of campus assessment and joining.\n"
        "- Target Cohort: Class of 2027 graduating batch only.\n\n"
        "Compensation & Benefits:\n"
        "- Fixed Compensation: INR 16,50,000 per annum\n"
        "- Performance Variable / Joining Bonus: INR 2,00,000\n"
        "- Total CTC: 18.5 LPA (Eighteen Lakh Fifty Thousand per annum)\n\n"
        "Important Dates & Instructions:\n"
        "- Campus Registration Deadline: 2026-11-25\n"
        "- Online Assessment Schedule: First week of December 2026\n"
    )

    source = await client.post(
        f"/api/v1/drives/{drive_id}/sources/pasted",
        json={"title": "Nexora Campus JD", "raw_text": sample_jd_text},
    )
    artifact_id = source.json()["id"]
    await SourceJobService.run_extraction(uuid.UUID(artifact_id), uuid.UUID(institution_id))

    # Request interpretation in cached mode
    interp_res = await client.post(
        f"/api/v1/drives/{drive_id}/interpretations",
        json={"source_artifact_id": artifact_id, "mode": "cached"},
    )
    assert interp_res.status_code == 201
    interp = interp_res.json()
    assert interp["revision_number"] == 1
    assert interp["reviewed_facts"]["company_name"] in {"Nexora Dynamics", "Nexora"}
    assert interp["reviewed_facts"]["eligibility_draft"]["minimum_cgpa"] == "7.50"
    assert len(interp["evidence"]) >= 1

    # Resolve deadline clarification
    clarification = interp["clarifications"][0]
    await client.post(
        f"/api/v1/clarifications/{clarification['id']}/resolve",
        json={"value": "2026-11-25T18:00:00+05:30", "rationale": "Confirmed by placement officer"},
    )

    # Compile policy and create proposal
    pol_res = await client.post(
        f"/api/v1/drives/{drive_id}/policies",
        json={"interpretation_id": interp["id"], "explicitly_not_required": []},
    )
    assert pol_res.status_code == 201
    policy_id = pol_res.json()["id"]

    prop_res = await client.post(f"/api/v1/policies/{policy_id}/submit-review")
    assert prop_res.status_code == 201
    proposal_id = prop_res.json()["id"]

    # Now create revision #2 of interpretation (supersedes revision #1)
    interp2_res = await client.post(
        f"/api/v1/drives/{drive_id}/interpretations",
        json={
            "source_artifact_id": artifact_id,
            "mode": "manual",
            "manual_facts": {
                **interp["reviewed_facts"],
                "company_name": "Nexora Global",
            },
            "rationale": "Coordinator verified legal entity name",
        },
    )
    assert interp2_res.status_code == 201
    assert interp2_res.json()["revision_number"] == 2

    # Attempting to approve the stale proposal from revision #1 must fail closed (INV-05)
    stale_decision = await client.post(
        f"/api/v1/proposals/{proposal_id}/decisions",
        json={
            "expected_revision": 1,
            "expected_hash": prop_res.json()["canonical_hash"],
            "decision": "approved",
            "comment": "Attempting approval on superseded interpretation",
        },
    )
    assert stale_decision.status_code == 409
    assert stale_decision.json()["error"]["code"] == "PROPOSAL_STALE"

