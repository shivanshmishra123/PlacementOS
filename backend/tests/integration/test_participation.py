"""P06 publication, document readiness, registration, and hold integration tests."""

import asyncio
import io
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from docx import Document
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.models.eligibility import EligibilityResult, EvaluationCohortMember, EvaluationRun
from placementos.models.identity import Membership, StudentProfile, User
from placementos.models.participation import Registration
from placementos.models.recruitment import Drive
from placementos.services.eligibility_runs import EligibilityRunService
from placementos.services.participation import reconcile_registration_holds
from placementos.services.source_jobs import SourceJobService


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


async def _setup_evaluated_drive(client: AsyncClient, monkeypatch) -> dict[str, str]:
    from placementos.workers.eligibility_tasks import evaluate_eligibility_task
    from placementos.workers.source_tasks import extract_source_text_task

    monkeypatch.setattr(extract_source_text_task, "delay", lambda *args, **kwargs: None)
    monkeypatch.setattr(evaluate_eligibility_task, "delay", lambda *args, **kwargs: None)
    suffix = uuid.uuid4().hex[:8]
    student_email = f"p06-student-{suffix}@apex.edu"
    review_email = f"p06-review-student-{suffix}@apex.edu"
    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    institution_id = login.json()["user"]["institution_id"]
    company = await client.post("/api/v1/companies", json={"name": f"P06-{suffix}"})
    drive = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company.json()["id"],
            "academic_year": "2026-2027",
            "title": "P06 Participation Engineer",
        },
    )
    drive_id = drive.json()["id"]
    source = await client.post(
        f"/api/v1/drives/{drive_id}/sources/pasted",
        json={
            "title": "P06 policy source",
            "raw_text": (
                "Company: P06 Test\nRole: Engineer\nCSE students graduating in 2027 are eligible.\n"
                "Minimum CGPA: 7.50 out of 10 with no active backlogs.\n"
                "Registration deadline: 2026-11-05. CTC: 12 LPA."
            ),
        },
    )
    await SourceJobService.run_extraction(uuid.UUID(source.json()["id"]), uuid.UUID(institution_id))
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
P06-{suffix},P06 Student,{student_email},CSE,8.20,10.00,2027,0
P06-REVIEW-{suffix},P06 Review Student,{review_email},CSE,8.20,10.00,2027,
"""
    preview = await client.post("/api/v1/students/import-preview", json={"csv_content": csv_text})
    committed = await client.post(
        "/api/v1/students/import-commit", json={"preview_token": preview.json()["preview_token"]}
    )
    assert committed.status_code == 200
    queued = await client.post(
        f"/api/v1/drives/{drive_id}/evaluations", json={"policy_id": policy.json()["id"]}
    )
    run_id = queued.json()["id"]
    await EligibilityRunService.execute_run(uuid.UUID(run_id), uuid.UUID(institution_id))
    return {
        "institution_id": institution_id,
        "drive_id": drive_id,
        "run_id": run_id,
        "student_email": student_email,
        "student_identifier": f"P06-{suffix}",
        "review_email": review_email,
    }


@pytest.mark.asyncio
async def test_publication_documents_registration_withdrawal_and_hold(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context = await _setup_evaluated_drive(client, monkeypatch)
    drive_id = context["drive_id"]
    requirements = await client.put(
        f"/api/v1/drives/{drive_id}/document-requirements",
        json={
            "expected_drive_revision": 1,
            "requirements": [
                {
                    "document_type": "resume",
                    "display_label": "Resume",
                    "allowed_extensions": ["docx", "pdf"],
                    "required_stage": "registration",
                },
                {
                    "document_type": "marksheet",
                    "display_label": "Latest marksheet",
                    "allowed_extensions": ["pdf"],
                    "required_stage": "scheduling",
                },
            ],
        },
    )
    assert requirements.status_code == 200
    assert len(requirements.json()) == 2

    now = datetime.now(UTC)
    publication = await client.post(
        f"/api/v1/drives/{drive_id}/publication-proposals",
        json={
            "expected_drive_revision": 1,
            "evaluation_run_id": context["run_id"],
            "registration_start_at": (now - timedelta(minutes=5)).isoformat(),
            "registration_end_at": (now + timedelta(hours=2)).isoformat(),
            "withdrawal_end_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert publication.status_code == 201
    proposal = publication.json()
    stale = await client.post(
        f"/api/v1/publication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": "0" * 64,
            "decision": "approved",
        },
    )
    assert stale.status_code == 409
    approved = await client.post(
        f"/api/v1/publication-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["state"] == "approved"

    client.cookies.clear()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": context["review_email"], "institution_slug": "apex-tech"},
    )
    review_opportunities = await client.get("/api/v1/student/drives")
    review_drive = next(item for item in review_opportunities.json() if item["drive_id"] == drive_id)
    assert review_drive["eligibility_status"] == "needs_review"
    review_draft = await client.post(f"/api/v1/student/drives/{drive_id}/registrations/draft")
    assert review_draft.status_code == 200
    assert review_draft.json()["state"] == "draft"
    review_submission = await client.post(f"/api/v1/student/drives/{drive_id}/registrations")
    assert review_submission.status_code == 409

    client.cookies.clear()
    student_login = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": context["student_email"], "institution_slug": "apex-tech"},
    )
    assert student_login.status_code == 200
    opportunities = await client.get("/api/v1/student/drives")
    assert opportunities.status_code == 200
    opportunity = next(item for item in opportunities.json() if item["drive_id"] == drive_id)
    assert opportunity["eligibility_status"] == "eligible"
    assert opportunity["document_readiness"]["status"] == "pending"
    blocked_submission = await client.post(f"/api/v1/student/drives/{drive_id}/registrations")
    assert blocked_submission.status_code == 409

    corrupt_bytes = b"not a real pdf"
    corrupt_upload = await client.post(
        "/api/v1/student/documents/upload-sessions",
        json={
            "document_type": "resume",
            "original_filename": "corrupt_resume.pdf",
            "content_type": "application/pdf",
            "byte_size": len(corrupt_bytes),
        },
    )
    async with httpx.AsyncClient() as external:
        await external.put(corrupt_upload.json()["upload_url"], content=corrupt_bytes)
    corrupt_complete = await client.post(
        f"/api/v1/student/documents/upload-sessions/{corrupt_upload.json()['id']}/complete"
    )
    assert corrupt_complete.status_code == 400

    resume_bytes = _docx_bytes("P06 Student Resume with verified project and education details")
    upload = await client.post(
        "/api/v1/student/documents/upload-sessions",
        json={
            "document_type": "resume",
            "original_filename": "P06_Student_Resume.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "byte_size": len(resume_bytes),
        },
    )
    assert upload.status_code == 201
    async with httpx.AsyncClient() as external:
        uploaded = await external.put(
            upload.json()["upload_url"],
            content=resume_bytes,
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
        )
    assert uploaded.status_code in {200, 201}
    completed = await client.post(
        f"/api/v1/student/documents/upload-sessions/{upload.json()['id']}/complete"
    )
    assert completed.status_code == 201
    assert completed.json()["structure_status"] == "passed"
    history = await client.get("/api/v1/student/documents")
    assert history.status_code == 200
    assert history.json()[0]["id"] == completed.json()["id"]
    own_download = await client.get(
        f"/api/v1/student/documents/{completed.json()['id']}/download-url"
    )
    assert own_download.status_code == 200
    assert "download_url" in own_download.json()
    client.cookies.clear()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": f"other-student-{uuid.uuid4().hex[:6]}@apex.edu", "institution_slug": "apex-tech"},
    )
    hidden_download = await client.get(
        f"/api/v1/student/documents/{completed.json()['id']}/download-url"
    )
    assert hidden_download.status_code == 404
    client.cookies.clear()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": context["student_email"], "institution_slug": "apex-tech"},
    )

    refreshed = await client.get("/api/v1/student/drives")
    opportunity = next(item for item in refreshed.json() if item["drive_id"] == drive_id)
    resume_finding = next(
        item
        for item in opportunity["document_readiness"]["requirements"]
        if item["document_type"] == "resume"
    )
    assert resume_finding["status"] == "ready"
    assert (
        opportunity["document_readiness"]["status"] == "pending"
    )  # scheduling marksheet remains due later

    submitted, replay = await asyncio.gather(
        client.post(f"/api/v1/student/drives/{drive_id}/registrations"),
        client.post(f"/api/v1/student/drives/{drive_id}/registrations"),
    )
    assert submitted.status_code == 200
    assert replay.status_code == 200
    assert submitted.json()["state"] == "submitted"
    assert replay.json()["id"] == submitted.json()["id"]

    client.cookies.clear()
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    participants = await client.get(f"/api/v1/drives/{drive_id}/participants")
    assert participants.status_code == 200
    own_row = next(
        item
        for item in participants.json()["items"]
        if item["student_identifier"] == context["student_identifier"]
    )
    assert own_row["registration_state"] == "submitted"
    coordinator_documents = await client.get(
        f"/api/v1/drives/{drive_id}/students/{own_row['student_profile_id']}/documents"
    )
    assert coordinator_documents.status_code == 200
    assert coordinator_documents.json()[0]["id"] == completed.json()["id"]
    coordinator_download = await client.get(
        f"/api/v1/drives/{drive_id}/document-revisions/{completed.json()['id']}/download-url"
    )
    assert coordinator_download.status_code == 200
    export = await client.get(f"/api/v1/drives/{drive_id}/participants.csv")
    assert export.status_code == 200
    assert "student_identifier,student_name,eligibility,readiness,registration" in export.text

    # A newly approved non-eligible evaluation retains the registration and creates an explicit hold.
    institution_id = uuid.UUID(context["institution_id"])
    drive = await admin_db_session.get(Drive, uuid.UUID(drive_id))
    published_run = await admin_db_session.get(EvaluationRun, uuid.UUID(context["run_id"]))
    student = (
        await admin_db_session.execute(
            select(StudentProfile)
            .join(User, User.id == StudentProfile.user_id)
            .where(User.email == context["student_email"])
        )
    ).scalar_one()
    membership = await admin_db_session.get(Membership, student.membership_id)
    assert drive and published_run and membership
    held_run = EvaluationRun(
        institution_id=institution_id,
        drive_id=drive.id,
        policy_id=published_run.policy_id,
        policy_hash=published_run.policy_hash,
        engine_version=published_run.engine_version,
        normalization_version=published_run.normalization_version,
        cohort_fingerprint=uuid.uuid4().hex,
        run_fingerprint=uuid.uuid4().hex,
        status="completed",
        is_stale=False,
        total_count=1,
        eligible_count=0,
        ineligible_count=1,
        needs_review_count=0,
        created_by_membership_id=membership.id,
        completed_at=datetime.now(UTC),
    )
    admin_db_session.add(held_run)
    await admin_db_session.flush()
    cohort = EvaluationCohortMember(
        institution_id=institution_id,
        evaluation_run_id=held_run.id,
        student_profile_id=student.id,
        membership_id=student.membership_id,
        academic_revision_id=student.current_academic_revision_id,
        member_fingerprint=uuid.uuid4().hex,
    )
    admin_db_session.add(cohort)
    await admin_db_session.flush()
    result = EligibilityResult(
        institution_id=institution_id,
        evaluation_run_id=held_run.id,
        cohort_member_id=cohort.id,
        student_profile_id=student.id,
        academic_revision_id=student.current_academic_revision_id,
        outcome="ineligible",
        predicate_results=[],
        reason_codes=["CGPA_BELOW_MINIMUM"],
        facts_snapshot={},
        student_explanation="Current approved criteria are not met.",
        input_fingerprint=uuid.uuid4().hex,
    )
    admin_db_session.add(result)
    await admin_db_session.flush()
    await reconcile_registration_holds(
        admin_db_session,
        drive=drive,
        evaluation_run=held_run,
        actor_membership_id=membership.id,
    )
    await admin_db_session.commit()
    registration = (
        await admin_db_session.execute(
            select(Registration).where(
                Registration.drive_id == drive.id,
                Registration.student_profile_id == student.id,
            )
        )
    ).scalar_one()
    assert registration.state == "eligibility_hold"
    assert registration.submitted_at is not None

    # A later eligible reevaluation does not silently restore the hold.
    await reconcile_registration_holds(
        admin_db_session,
        drive=drive,
        evaluation_run=published_run,
        actor_membership_id=membership.id,
    )
    await admin_db_session.commit()
    await admin_db_session.refresh(registration)
    assert registration.state == "eligibility_hold"

    client.cookies.clear()
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    restored = await client.post(
        f"/api/v1/registrations/{registration.id}/coordinator-action",
        json={
            "expected_revision": registration.concurrency_revision,
            "action": "restore",
            "reason": "Current published evaluation is eligible and evidence was reviewed",
        },
    )
    assert restored.status_code == 200
    assert restored.json()["state"] == "submitted"

    client.cookies.clear()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": context["student_email"], "institution_slug": "apex-tech"},
    )
    withdrawn = await client.post(
        f"/api/v1/student/registrations/{registration.id}/withdraw",
        json={
            "expected_revision": restored.json()["concurrency_revision"],
            "reason": "Accepted another offer",
        },
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["state"] == "withdrawn"
