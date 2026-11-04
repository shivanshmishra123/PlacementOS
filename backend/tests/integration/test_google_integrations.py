"""P11 Google connector lifecycle, isolation, and controlled-write tests."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.models.identity import Membership, User
from placementos.models.integrations import (
    IntegrationConnection,
    IntegrationWebhookChannel,
    IntegrationWebhookEvent,
)
from placementos.models.lifecycle import (
    DriveReportRevision,
    RecruitmentRound,
    RecruitmentSession,
    SessionRevision,
)
from placementos.models.recruitment import Company, Drive
from placementos.services.integrations import (
    CalendarWatchResult,
    GmailSelectedContent,
    GoogleGatewayError,
    ProviderWriteResult,
    SheetValues,
    build_webhook_channel_id,
    execute_integration_operation,
    token_cipher,
)
from placementos.services.jd_intelligence import canonical_hash

ALL_SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar.events.owned",
]


class FakeGoogleGateway:
    def __init__(self) -> None:
        self.values = [
            [
                "student_identifier",
                "full_name",
                "email",
                "branch",
                "cgpa",
                "graduation_year",
                "active_backlogs",
            ],
            ["P11-001", "P11 Student", "p11.student@apex.edu", "CSE", "8.50", "2027", "0"],
        ]
        self.sheet_writes = 0
        self.calendar_writes = 0

    async def sheet_values(self, spreadsheet_id: str, selected_range: str) -> SheetValues:
        return SheetValues(values=self.values, provider_version="sheet-etag-1")

    async def selected_gmail_content(
        self, message_id: str, attachment_id: str | None
    ) -> GmailSelectedContent:
        return GmailSelectedContent(
            message_id=message_id,
            attachment_id=attachment_id,
            thread_id="thread-1",
            history_id="history-1",
            sender="recruiter@example.com",
            subject="Explicitly selected JD",
            received_at=datetime.now(UTC),
            filename="selected-jd.txt",
            media_type="text/plain",
            content=b"Role: Software Engineer\nMinimum CGPA: 7.50",
        )

    async def write_sheet(
        self, spreadsheet_id: str, target_range: str, values: list[list]
    ) -> ProviderWriteResult:
        self.sheet_writes += 1
        assert values[0] == ["metric", "value"]
        return ProviderWriteResult(
            resource_id=f"{spreadsheet_id}:{target_range}",
            provider_version="sheet-write-etag-1",
            request_id="request-sheet-1",
            evidence={"updated_cells": len(values) * 2},
        )

    async def watch_calendar(
        self,
        calendar_id: str,
        channel_id: str,
        channel_token: str,
        webhook_address: str,
    ) -> CalendarWatchResult:
        assert calendar_id == "primary"
        assert len(channel_id) <= 64
        assert len(channel_token) >= 32
        assert webhook_address.endswith("/api/v1/integrations/google/calendar/webhook")
        return CalendarWatchResult(
            resource_id="calendar-watch-resource",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )

    async def upsert_calendar_event(
        self,
        calendar_id: str,
        event_id: str,
        event: dict,
        send_updates: str,
        provider_version: str | None,
    ) -> ProviderWriteResult:
        self.calendar_writes += 1
        assert calendar_id == "primary"
        assert event_id.startswith("plos")
        assert event["visibility"] == "private"
        assert send_updates == "none"
        assert provider_version is None
        return ProviderWriteResult(
            resource_id=event_id,
            provider_version='"calendar-etag-1"',
            request_id="calendar-request-1",
            evidence={"status": "confirmed"},
        )

    async def revoke(self, token: str) -> None:
        assert token in {"test-refresh-token", "test-access-token"}


class FailingWriteGateway(FakeGoogleGateway):
    def __init__(self, *, retryable: bool = False, uncertain: bool = False) -> None:
        super().__init__()
        self.retryable = retryable
        self.uncertain = uncertain

    async def write_sheet(
        self, spreadsheet_id: str, target_range: str, values: list[list]
    ) -> ProviderWriteResult:
        self.sheet_writes += 1
        raise GoogleGatewayError(
            "GOOGLE_RATE_LIMITED" if self.retryable else "GOOGLE_NETWORK_UNCERTAIN",
            "simulated isolated-provider failure",
            retryable=self.retryable,
            uncertain=self.uncertain,
        )


async def _setup(
    client: AsyncClient, session: AsyncSession
) -> tuple[dict, IntegrationConnection, DriveReportRevision]:
    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    assert login.status_code == 200
    me = login.json()["user"]
    membership = (
        await session.execute(
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .where(
                User.email == me["email"],
                Membership.institution_id == uuid.UUID(me["institution_id"]),
            )
        )
    ).scalar_one()
    suffix = uuid.uuid4().hex[:10]
    company = Company(
        institution_id=membership.institution_id,
        name=f"P11 Company {suffix}",
    )
    session.add(company)
    await session.flush()
    drive = Drive(
        institution_id=membership.institution_id,
        company_id=company.id,
        title=f"P11 Drive {suffix}",
        status="published",
        created_by_membership_id=membership.id,
        assigned_coordinator_membership_id=membership.id,
    )
    session.add(drive)
    await session.flush()
    snapshot = {"drive": {"title": drive.title}, "counts": {"registered": 1}}
    report = DriveReportRevision(
        institution_id=membership.institution_id,
        drive_id=drive.id,
        revision_number=1,
        report_kind="operational",
        status="frozen",
        snapshot_payload=snapshot,
        snapshot_hash=canonical_hash(snapshot),
        reason="P11 controlled export fixture",
        created_by_membership_id=membership.id,
    )
    session.add(report)
    connection = IntegrationConnection(
        institution_id=membership.institution_id,
        owner_membership_id=membership.id,
        external_account_id=f"google-{suffix}",
        external_account_email=me["email"],
        granted_scopes=ALL_SCOPES,
        access_token_ciphertext=token_cipher.encrypt("test-access-token"),
        refresh_token_ciphertext=token_cipher.encrypt("test-refresh-token"),
        access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(connection)
    await session.commit()
    return {"membership": membership, "drive": drive}, connection, report


async def _approve_sheet_export(
    client: AsyncClient,
    context: dict,
    connection: IntegrationConnection,
    report: DriveReportRevision,
) -> uuid.UUID:
    proposal = await client.post(
        f"/api/v1/integrations/drives/{context['drive'].id}/sheets/export-proposals",
        json={
            "connection_id": str(connection.id),
            "report_id": str(report.id),
            "spreadsheet_id": f"sheet-write-{uuid.uuid4().hex[:8]}",
            "target_range": "Closure!A1",
        },
    )
    assert proposal.status_code == 201, proposal.text
    body = proposal.json()
    approved = await client.post(
        f"/api/v1/integrations/proposals/{body['id']}/decisions",
        json={
            "expected_revision": body["revision_number"],
            "expected_hash": body["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200, approved.text
    return uuid.UUID(approved.json()["id"])


@pytest.mark.asyncio
async def test_explicit_gmail_capture_and_sheet_preview_detect_source_change(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context, connection, _report = await _setup(client, admin_db_session)
    fake = FakeGoogleGateway()
    monkeypatch.setattr(
        "placementos.services.integrations.get_google_gateway", lambda _token=None: fake
    )
    monkeypatch.setattr(
        "placementos.services.integrations.storage_service.store_accepted_bytes",
        lambda data, institution_id, purpose, extension, content_type: (
            f"accepted/{institution_id}/{purpose}/fixture{extension}",
            hashlib.sha256(data).hexdigest(),
            len(data),
        ),
    )
    monkeypatch.setattr(
        "placementos.workers.source_tasks.extract_source_text_task.delay", lambda *_args: None
    )

    capture = await client.post(
        f"/api/v1/integrations/drives/{context['drive'].id}/gmail-source-captures",
        json={"connection_id": str(connection.id), "message_id": "explicit-message-1"},
    )
    assert capture.status_code == 201, capture.text
    assert capture.json()["subject"] == "Explicitly selected JD"

    preview = await client.post(
        "/api/v1/integrations/sheets/import-previews",
        json={
            "connection_id": str(connection.id),
            "spreadsheet_id": "sheet-1",
            "selected_range": "Roster!A:G",
        },
    )
    assert preview.status_code == 201, preview.text
    assert preview.json()["report"]["valid_rows_count"] == 1
    fake.values[1][4] = "9.00"
    stale = await client.post(
        f"/api/v1/integrations/sheets/import-previews/{preview.json()['id']}/commit"
    )
    assert stale.status_code == 409


@pytest.mark.asyncio
async def test_approved_sheet_write_is_exact_and_duplicate_execution_is_safe(
    client: AsyncClient, admin_db_session: AsyncSession
) -> None:
    context, connection, report = await _setup(client, admin_db_session)
    operation_id = await _approve_sheet_export(client, context, connection, report)
    fake = FakeGoogleGateway()
    first = await execute_integration_operation(
        operation_id, context["membership"].institution_id, gateway=fake
    )
    second = await execute_integration_operation(
        operation_id, context["membership"].institution_id, gateway=fake
    )
    assert (first, second) == ("succeeded", "succeeded")
    assert fake.sheet_writes == 1


@pytest.mark.asyncio
async def test_rate_limit_is_bounded_and_unknown_write_is_not_blindly_retried(
    client: AsyncClient, admin_db_session: AsyncSession
) -> None:
    context, connection, report = await _setup(client, admin_db_session)
    retry_operation = await _approve_sheet_export(client, context, connection, report)
    retrying = FailingWriteGateway(retryable=True)
    assert (
        await execute_integration_operation(
            retry_operation, context["membership"].institution_id, gateway=retrying
        )
        == "queued"
    )
    succeeding = FakeGoogleGateway()
    assert (
        await execute_integration_operation(
            retry_operation, context["membership"].institution_id, gateway=succeeding
        )
        == "succeeded"
    )

    second_context, second_connection, second_report = await _setup(client, admin_db_session)
    unknown_operation = await _approve_sheet_export(
        client, second_context, second_connection, second_report
    )
    uncertain = FailingWriteGateway(uncertain=True)
    assert (
        await execute_integration_operation(
            unknown_operation,
            second_context["membership"].institution_id,
            gateway=uncertain,
        )
        == "unknown"
    )
    assert (
        await execute_integration_operation(
            unknown_operation,
            second_context["membership"].institution_id,
            gateway=FakeGoogleGateway(),
        )
        == "unknown"
    )
    assert uncertain.sheet_writes == 1


@pytest.mark.asyncio
async def test_disconnect_invalidates_approved_queued_write(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    context, connection, report = await _setup(client, admin_db_session)
    operation_id = await _approve_sheet_export(client, context, connection, report)
    monkeypatch.setattr(
        "placementos.services.integrations.get_google_gateway",
        lambda _token=None: FakeGoogleGateway(),
    )
    disconnected = await client.post(f"/api/v1/integrations/connections/{connection.id}/disconnect")
    assert disconnected.status_code == 204
    assert (
        await execute_integration_operation(
            operation_id,
            context["membership"].institution_id,
            gateway=FakeGoogleGateway(),
        )
        == "stale"
    )


@pytest.mark.asyncio
async def test_calendar_webhook_requires_signed_channel_and_deduplicates(
    client: AsyncClient, admin_db_session: AsyncSession
) -> None:
    context, connection, _report = await _setup(client, admin_db_session)
    token = "calendar-channel-token-with-at-least-32-bytes"
    channel_id = build_webhook_channel_id(context["membership"].institution_id)
    admin_db_session.add(
        IntegrationWebhookChannel(
            institution_id=context["membership"].institution_id,
            connection_id=connection.id,
            channel_id=channel_id,
            resource_id="calendar-resource-1",
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
        )
    )
    await admin_db_session.commit()
    headers = {
        "X-Goog-Channel-ID": channel_id,
        "X-Goog-Channel-Token": token,
        "X-Goog-Resource-ID": "calendar-resource-1",
        "X-Goog-Resource-State": "exists",
        "X-Goog-Message-Number": "42",
    }
    assert (
        await client.post("/api/v1/integrations/google/calendar/webhook", headers=headers)
    ).status_code == 204
    assert (
        await client.post("/api/v1/integrations/google/calendar/webhook", headers=headers)
    ).status_code == 204
    count = await admin_db_session.scalar(
        select(func.count())
        .select_from(IntegrationWebhookEvent)
        .where(IntegrationWebhookEvent.channel_id == channel_id)
    )
    assert count == 1

    invalid = dict(headers)
    invalid_suffix = "1" if channel_id[-1] != "1" else "2"
    invalid["X-Goog-Channel-ID"] = channel_id[:-1] + invalid_suffix
    assert (
        await client.post("/api/v1/integrations/google/calendar/webhook", headers=invalid)
    ).status_code == 404


@pytest.mark.asyncio
async def test_calendar_watch_registration_uses_server_generated_channel(
    client: AsyncClient, admin_db_session: AsyncSession, monkeypatch
) -> None:
    _context, connection, _report = await _setup(client, admin_db_session)
    monkeypatch.setattr(
        "placementos.services.integrations.settings.INTEGRATION_WEBHOOK_BASE_URL",
        "https://placement.test",
    )
    monkeypatch.setattr(
        "placementos.services.integrations.get_google_gateway",
        lambda _token=None: FakeGoogleGateway(),
    )
    response = await client.post(
        f"/api/v1/integrations/connections/{connection.id}/calendar-watches",
        json={"calendar_id": "primary"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["resource_id"] == "calendar-watch-resource"
    assert len(response.json()["channel_id"]) <= 64


@pytest.mark.asyncio
async def test_approved_calendar_event_uses_published_revision_and_stable_mapping(
    client: AsyncClient, admin_db_session: AsyncSession
) -> None:
    context, connection, _report = await _setup(client, admin_db_session)
    membership = context["membership"]
    drive = context["drive"]
    round_item = RecruitmentRound(
        institution_id=membership.institution_id,
        drive_id=drive.id,
        sequence_number=1,
        name="Technical interview",
        round_type="interview",
        requires_previous_round_outcome=False,
        created_by_membership_id=membership.id,
    )
    admin_db_session.add(round_item)
    await admin_db_session.flush()
    recruitment_session = RecruitmentSession(
        institution_id=membership.institution_id,
        drive_id=drive.id,
        round_id=round_item.id,
        status="published",
        created_by_membership_id=membership.id,
    )
    admin_db_session.add(recruitment_session)
    await admin_db_session.flush()
    revision = SessionRevision(
        institution_id=membership.institution_id,
        drive_id=drive.id,
        session_id=recruitment_session.id,
        round_id=round_item.id,
        revision_number=1,
        start_at=datetime.now(UTC) + timedelta(days=2),
        end_at=datetime.now(UTC) + timedelta(days=2, hours=1),
        timezone="Asia/Kolkata",
        capacity=10,
        panel_members=[],
        created_by_membership_id=membership.id,
    )
    admin_db_session.add(revision)
    await admin_db_session.flush()
    recruitment_session.current_revision_id = revision.id
    recruitment_session.published_revision_id = revision.id
    await admin_db_session.commit()

    proposed = await client.post(
        f"/api/v1/integrations/session-revisions/{revision.id}/calendar-proposals",
        json={
            "connection_id": str(connection.id),
            "calendar_id": "primary",
            "send_updates": "none",
        },
    )
    assert proposed.status_code == 201, proposed.text
    body = proposed.json()
    assert body["payload"]["event_id"] == f"plos{recruitment_session.id.hex}"
    approved = await client.post(
        f"/api/v1/integrations/proposals/{body['id']}/decisions",
        json={
            "expected_revision": body["revision_number"],
            "expected_hash": body["canonical_hash"],
            "decision": "approved",
        },
    )
    assert approved.status_code == 200, approved.text
    fake = FakeGoogleGateway()
    assert (
        await execute_integration_operation(
            uuid.UUID(approved.json()["id"]), membership.institution_id, gateway=fake
        )
        == "succeeded"
    )
    assert fake.calendar_writes == 1


@pytest.mark.asyncio
async def test_cross_tenant_connection_id_is_hidden(
    client: AsyncClient, admin_db_session: AsyncSession
) -> None:
    _context, connection, _report = await _setup(client, admin_db_session)
    client.cookies.clear()
    assert (
        await client.post("/api/v1/auth/dev-login", json={"persona": "coord_beacon"})
    ).status_code == 200
    response = await client.post(
        "/api/v1/integrations/sheets/import-previews",
        json={
            "connection_id": str(connection.id),
            "spreadsheet_id": "hidden-sheet",
            "selected_range": "Roster!A:G",
        },
    )
    assert response.status_code == 404
