"""P09 complete scheduling, results, reporting, and closure acceptance tests."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.test_communications_dispatch import _create_proposal, _publish_drive
from tests.integration.test_participation import _setup_evaluated_drive

from placementos.models.eligibility import EligibilityResult, EvaluationRun
from placementos.models.participation import Registration
from placementos.models.recruitment import Drive
from placementos.services.eligibility_engine import canonical_hash


async def _published_registered_student(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> tuple[dict[str, str], str]:
    context = await _setup_evaluated_drive(client, monkeypatch)
    await _publish_drive(client, context)
    participants = await client.get(f"/api/v1/drives/{context['drive_id']}/participants")
    student_id = next(
        item["student_profile_id"]
        for item in participants.json()["items"]
        if item["student_identifier"] == context["student_identifier"]
    )
    drive = await admin_db_session.get(Drive, uuid.UUID(context["drive_id"]))
    evaluation = await admin_db_session.get(EvaluationRun, uuid.UUID(context["run_id"]))
    result = (
        await admin_db_session.execute(
            select(EligibilityResult).where(
                EligibilityResult.evaluation_run_id == evaluation.id,
                EligibilityResult.student_profile_id == uuid.UUID(student_id),
            )
        )
    ).scalar_one()
    admin_db_session.add(
        Registration(
            institution_id=drive.institution_id,
            drive_id=drive.id,
            student_profile_id=uuid.UUID(student_id),
            state="submitted",
            submitted_drive_revision_id=drive.published_drive_revision_id,
            submitted_policy_id=evaluation.policy_id,
            submitted_evaluation_run_id=evaluation.id,
            submitted_eligibility_result_id=result.id,
            submitted_at=datetime.now(UTC),
            concurrency_revision=1,
        )
    )
    await admin_db_session.commit()
    return context, student_id


async def _create_and_publish_session(
    client: AsyncClient,
    context: dict[str, str],
    student_id: str,
    *,
    start_at: datetime,
    end_at: datetime,
) -> tuple[dict, dict]:
    rounds = await client.get(f"/api/v1/drives/{context['drive_id']}/rounds")
    if rounds.json():
        round_item = rounds.json()[0]
    else:
        created = await client.post(
            f"/api/v1/drives/{context['drive_id']}/rounds",
            json={
                "sequence_number": 1,
                "name": "Technical interview",
                "round_type": "interview",
                "requires_previous_round_outcome": False,
            },
        )
        assert created.status_code == 200, created.text
        round_item = created.json()
    response = await client.post(
        f"/api/v1/rounds/{round_item['id']}/sessions",
        json={
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "timezone": "Asia/Kolkata",
            "capacity": 1,
            "venue": f"Room-{context['drive_id']}",
            "panel_members": [f"Panel-{context['drive_id']}"],
            "student_profile_ids": [student_id],
        },
    )
    assert response.status_code == 200, response.text
    item = response.json()
    proposed = await client.post(
        f"/api/v1/session-revisions/{item['current_revision_id']}/publication-proposals"
    )
    assert proposed.status_code == 200, proposed.text
    proposal = proposed.json()
    approved = await client.post(
        f"/api/v1/schedule-proposals/{proposal['id']}/decisions",
        json={
            "expected_revision": proposal["revision_number"],
            "expected_hash": proposal["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200, approved.text
    return round_item, item


@pytest.mark.asyncio
async def test_p09_complete_local_lifecycle_preserves_revisions_and_closes(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context, student_id = await _published_registered_student(client, admin_db_session, monkeypatch)
    start = datetime.now(UTC) + timedelta(days=3)
    round_item, item = await _create_and_publish_session(
        client,
        context,
        student_id,
        start_at=start,
        end_at=start + timedelta(hours=1),
    )

    # A draft is private; only the approved revision is visible to the assigned student.
    client.cookies.clear()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": context["student_email"], "institution_slug": "apex-tech"},
    )
    own_view = await client.get("/api/v1/student/schedule-results")
    assert own_view.status_code == 200
    assert [row["session_id"] for row in own_view.json()] == [item["id"]]
    assert own_view.json()[0]["outcome"] is None

    # Another student in the same tenant cannot inspect the assignment/result.
    client.cookies.clear()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": context["review_email"], "institution_slug": "apex-tech"},
    )
    assert (await client.get("/api/v1/student/schedule-results")).json() == []

    client.cookies.clear()
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    attendance = await client.post(
        f"/api/v1/sessions/{item['id']}/attendance",
        json={"items": [{"student_profile_id": student_id, "status": "absent"}]},
    )
    assert attendance.status_code == 200
    # Attendance is independent: absence did not invent a rejection.
    client.cookies.clear()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": context["student_email"], "institution_slug": "apex-tech"},
    )
    assert (await client.get("/api/v1/student/schedule-results")).json()[0]["outcome"] is None

    client.cookies.clear()
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    first = await client.post(
        f"/api/v1/rounds/{round_item['id']}/outcomes",
        json={
            "student_profile_id": student_id,
            "outcome": "advanced",
            "source_type": "employer_email",
            "source_reference": "synthetic://employer/result-1",
        },
    )
    proposal = await client.post(f"/api/v1/outcomes/{first.json()['id']}/publication-proposals")
    await client.post(
        f"/api/v1/result-proposals/{proposal.json()['id']}/decisions",
        json={
            "expected_revision": proposal.json()["revision_number"],
            "expected_hash": proposal.json()["canonical_hash"],
            "decision": "approved",
        },
    )
    correction = await client.post(
        f"/api/v1/rounds/{round_item['id']}/outcomes",
        json={
            "student_profile_id": student_id,
            "outcome": "waitlisted",
            "source_type": "employer_email",
            "source_reference": "synthetic://employer/correction-2",
            "note": "Employer correction",
        },
    )
    assert correction.json()["revision_number"] == 2

    # The internal correction remains invisible until its exact revision is approved.
    client.cookies.clear()
    await client.post(
        "/api/v1/auth/dev-login",
        json={"email": context["student_email"], "institution_slug": "apex-tech"},
    )
    assert (await client.get("/api/v1/student/schedule-results")).json()[0]["outcome"][
        "outcome"
    ] == "advanced"

    client.cookies.clear()
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    correction_proposal = await client.post(
        f"/api/v1/outcomes/{correction.json()['id']}/publication-proposals"
    )
    await client.post(
        f"/api/v1/result-proposals/{correction_proposal.json()['id']}/decisions",
        json={
            "expected_revision": correction_proposal.json()["revision_number"],
            "expected_hash": correction_proposal.json()["canonical_hash"],
            "decision": "approved",
        },
    )
    assert (await client.post(f"/api/v1/sessions/{item['id']}/complete")).status_code == 200
    assert (
        await client.post(
            f"/api/v1/drives/{context['drive_id']}/registration-close",
            json={"reason": "Deadline reached"},
        )
    ).status_code == 200

    frozen = await client.post(
        f"/api/v1/drives/{context['drive_id']}/reports",
        json={"report_kind": "operational", "reason": "Pre-close review"},
    )
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["snapshot_hash"] == canonical_hash(frozen.json()["snapshot_payload"])
    grant = await client.post(f"/api/v1/reports/{frozen.json()['id']}/export-grants")
    csv_response = await client.get(grant.json()["download_url"])
    assert csv_response.status_code == 200
    assert context["student_identifier"] in csv_response.text

    # Even an approved-but-not-executed delivery blocks closure until reviewed/cancelled.
    communication = await _create_proposal(client, context)
    approved_communication = await client.post(
        f"/api/v1/communication-proposals/{communication['id']}/decisions",
        json={
            "expected_revision": communication["revision_number"],
            "expected_hash": communication["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved_communication.status_code == 200
    delivery_block = await client.post(
        f"/api/v1/drives/{context['drive_id']}/close",
        json={"reason": "Must not hide queued delivery"},
    )
    assert delivery_block.status_code == 409
    codes = {row["code"] for row in delivery_block.json()["error"]["details"]["blockers"]}
    assert "ACTIVE_OR_UNKNOWN_DELIVERY" in codes
    batches = await client.get("/api/v1/dispatch-batches")
    batch = next(row for row in batches.json() if row["proposal_id"] == communication["id"])
    assert (
        await client.post(
            f"/api/v1/dispatch-batches/{batch['id']}/cancel",
            json={"reason": "Reviewed and cancelled before drive closure"},
        )
    ).status_code == 200

    closed = await client.post(
        f"/api/v1/drives/{context['drive_id']}/close",
        json={"reason": "All scheduled work and results reviewed"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["report_kind"] == "closure"
    blocked_change = await client.post(
        f"/api/v1/drives/{context['drive_id']}/rounds",
        json={"sequence_number": 2, "name": "Blocked", "round_type": "interview"},
    )
    assert blocked_change.status_code == 409
    reopened = await client.post(
        f"/api/v1/drives/{context['drive_id']}/reopen",
        json={"reason": "Employer supplied a documented correction"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["report_kind"] == "reopen"
    cancelled = await client.post(
        f"/api/v1/drives/{context['drive_id']}/cancel",
        json={"reason": "Employer cancelled after the documented reopen"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["report_kind"] == "cancellation"
    client.cookies.clear()
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_beacon"})
    assert (await client.get(f"/api/v1/drives/{context['drive_id']}/rounds")).status_code == 404


@pytest.mark.asyncio
async def test_half_open_conflict_and_stale_schedule_approval(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context, student_id = await _published_registered_student(client, admin_db_session, monkeypatch)
    start = datetime.now(UTC) + timedelta(days=4)
    round_item, first = await _create_and_publish_session(
        client, context, student_id, start_at=start, end_at=start + timedelta(hours=1)
    )
    drafts_before = await client.get(f"/api/v1/drives/{context['drive_id']}/communication-drafts")
    old_notice = next(
        row for row in drafts_before.json() if row["communication_kind"] == "interview_schedule"
    )
    revised_start = start + timedelta(minutes=5)
    revised_end = start + timedelta(hours=1, minutes=5)
    revised = await client.post(
        f"/api/v1/sessions/{first['id']}/revisions",
        json={
            "start_at": revised_start.isoformat(),
            "end_at": revised_end.isoformat(),
            "timezone": "Asia/Kolkata",
            "capacity": 1,
            "venue": f"Room-{context['drive_id']}",
            "panel_members": [f"Panel-{context['drive_id']}"],
            "student_profile_ids": [student_id],
            "change_reason": "Employer shifted the session by five minutes",
        },
    )
    revised_proposal = await client.post(
        f"/api/v1/session-revisions/{revised.json()['current_revision_id']}/publication-proposals"
    )
    assert revised_proposal.json()["payload"]["exact_notifications"]
    assert (
        await client.post(
            f"/api/v1/schedule-proposals/{revised_proposal.json()['id']}/decisions",
            json={
                "expected_revision": revised_proposal.json()["revision_number"],
                "expected_hash": revised_proposal.json()["canonical_hash"],
                "decision": "approved",
            },
        )
    ).status_code == 200
    drafts_after = await client.get(f"/api/v1/drives/{context['drive_id']}/communication-drafts")
    schedule_notices = [
        row
        for row in drafts_after.json()
        if row["communication_kind"] == "interview_schedule"
        or row["communication_kind"] == "schedule_correction"
    ]
    assert (
        next(row for row in schedule_notices if row["id"] == old_notice["id"])["state"] == "stale"
    )
    assert any(row["state"] == "draft" for row in schedule_notices)
    # A touching interval is allowed by half-open semantics.
    _, adjacent = await _create_and_publish_session(
        client,
        context,
        student_id,
        start_at=revised_end,
        end_at=revised_end + timedelta(hours=1),
    )
    assert adjacent["id"] != first["id"]

    overlap = await client.post(
        f"/api/v1/rounds/{round_item['id']}/sessions",
        json={
            "start_at": (start + timedelta(minutes=30)).isoformat(),
            "end_at": (start + timedelta(minutes=45)).isoformat(),
            "timezone": "Asia/Kolkata",
            "capacity": 1,
            "venue": f"Room-{context['drive_id']}",
            "panel_members": [f"Panel-{context['drive_id']}"],
            "student_profile_ids": [student_id],
        },
    )
    proposal = await client.post(
        f"/api/v1/session-revisions/{overlap.json()['current_revision_id']}/publication-proposals"
    )
    conflict = await client.post(
        f"/api/v1/schedule-proposals/{proposal.json()['id']}/decisions",
        json={
            "expected_revision": proposal.json()["revision_number"],
            "expected_hash": proposal.json()["canonical_hash"],
            "decision": "approved",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["details"]["conflicts"]
    stale_hash = await client.post(
        f"/api/v1/schedule-proposals/{proposal.json()['id']}/decisions",
        json={
            "expected_revision": proposal.json()["revision_number"],
            "expected_hash": "0" * 64,
            "decision": "rejected",
        },
    )
    assert stale_hash.status_code == 409
