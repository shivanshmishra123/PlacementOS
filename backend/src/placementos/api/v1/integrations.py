"""P11 controlled Google Workspace connector API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.database import get_db
from placementos.core.dependencies import require_capability
from placementos.core.errors import NotFoundException
from placementos.models.integrations import IntegrationConnection, IntegrationOperation
from placementos.models.intelligence import ActionProposal
from placementos.models.lifecycle import SessionRevision
from placementos.schemas.integrations import (
    CalendarChannelResponse,
    CalendarProposalCreate,
    CalendarWatchCreate,
    GmailCaptureCreate,
    GmailCaptureResponse,
    GoogleAuthorizationCreate,
    GoogleAuthorizationResponse,
    IntegrationConnectionResponse,
    IntegrationDecisionCreate,
    IntegrationOperationResponse,
    IntegrationProposalResponse,
    SheetExportProposalCreate,
    SheetImportCommitResponse,
    SheetImportPreviewCreate,
    SheetImportPreviewResponse,
)
from placementos.services.authorization import load_authorized_drive
from placementos.services.integrations import (
    capture_gmail_source,
    commit_sheet_import_preview,
    complete_google_authorization,
    create_calendar_event_proposal,
    create_google_authorization,
    create_sheet_export_proposal,
    create_sheet_import_preview,
    decide_integration_proposal,
    disconnect_connection,
    load_connection,
    receive_calendar_webhook,
    register_calendar_watch,
    verified_webhook_institution,
)
from placementos.services.session import AuthContext

router = APIRouter(prefix="/integrations", tags=["Google Workspace Integrations"])


def proposal_response(proposal: ActionProposal) -> IntegrationProposalResponse:
    return IntegrationProposalResponse(
        id=proposal.id,
        action_type=proposal.action_type,
        target_type=proposal.target_type,
        target_id=proposal.target_id,
        revision_number=proposal.revision_number,
        state=proposal.state,
        canonical_hash=proposal.canonical_hash,
        payload=proposal.payload,
        dependencies=proposal.dependencies,
    )


@router.post("/google/authorization", response_model=GoogleAuthorizationResponse)
async def begin_google_authorization(
    payload: GoogleAuthorizationCreate,
    auth: AuthContext = Depends(require_capability("integration:manage")),
    session: AsyncSession = Depends(get_db),
) -> GoogleAuthorizationResponse:
    url, expires_at = await create_google_authorization(session, auth, payload)
    return GoogleAuthorizationResponse(authorization_url=url, expires_at=expires_at)


@router.get("/google/callback", response_class=RedirectResponse)
async def google_authorization_callback(
    state: str = Query(min_length=20),
    code: str = Query(min_length=1),
    auth: AuthContext = Depends(require_capability("integration:manage")),
    session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    _connection, redirect_after = await complete_google_authorization(session, auth, state, code)
    separator = "&" if "?" in redirect_after else "?"
    return RedirectResponse(
        url=f"{settings.PUBLIC_WEB_URL}{redirect_after}{separator}google=connected",
        status_code=303,
    )


@router.get("/connections", response_model=list[IntegrationConnectionResponse])
async def list_connections(
    auth: AuthContext = Depends(require_capability("integration:manage")),
    session: AsyncSession = Depends(get_db),
) -> list[IntegrationConnection]:
    return list(
        (
            await session.execute(
                select(IntegrationConnection)
                .where(IntegrationConnection.institution_id == auth.institution_id)
                .order_by(IntegrationConnection.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


@router.post("/connections/{connection_id}/disconnect", status_code=204)
async def disconnect_google_connection(
    connection_id: uuid.UUID,
    auth: AuthContext = Depends(require_capability("integration:manage")),
    session: AsyncSession = Depends(get_db),
) -> Response:
    connection = await load_connection(session, auth, connection_id, for_update=True)
    await disconnect_connection(session, auth, connection)
    return Response(status_code=204)


@router.post(
    "/connections/{connection_id}/calendar-watches",
    response_model=CalendarChannelResponse,
    status_code=201,
)
async def create_calendar_watch(
    connection_id: uuid.UUID,
    payload: CalendarWatchCreate,
    auth: AuthContext = Depends(require_capability("integration:manage")),
    session: AsyncSession = Depends(get_db),
) -> CalendarChannelResponse:
    connection = await load_connection(
        session,
        auth,
        connection_id,
        required_any={"https://www.googleapis.com/auth/calendar.events.owned"},
    )
    channel = await register_calendar_watch(session, auth, connection, payload.calendar_id)
    return CalendarChannelResponse(
        id=channel.id,
        channel_id=channel.channel_id,
        resource_id=channel.resource_id,
        status=channel.status,
        expires_at=channel.expires_at,
    )


@router.post(
    "/drives/{drive_id}/gmail-source-captures",
    response_model=GmailCaptureResponse,
    status_code=201,
)
async def select_gmail_source(
    drive_id: uuid.UUID,
    payload: GmailCaptureCreate,
    auth: AuthContext = Depends(require_capability("integration:manage")),
    session: AsyncSession = Depends(get_db),
) -> GmailCaptureResponse:
    await load_authorized_drive(session, auth, drive_id)
    connection = await load_connection(
        session,
        auth,
        payload.connection_id,
        required_any={"https://www.googleapis.com/auth/gmail.readonly"},
    )
    capture, job_id = await capture_gmail_source(
        session,
        auth,
        drive_id=drive_id,
        connection=connection,
        message_id=payload.message_id,
        attachment_id=payload.attachment_id,
    )
    from placementos.workers.source_tasks import extract_source_text_task

    extract_source_text_task.delay(str(capture.source_artifact_id), str(auth.institution_id))
    return GmailCaptureResponse(
        id=capture.id,
        source_artifact_id=capture.source_artifact_id,
        message_id=capture.message_id,
        attachment_id=capture.attachment_id,
        subject=capture.subject,
        sender=capture.sender,
        content_hash=capture.content_hash,
        extraction_job_id=job_id,
    )


@router.post("/sheets/import-previews", response_model=SheetImportPreviewResponse, status_code=201)
async def preview_sheet_import(
    payload: SheetImportPreviewCreate,
    auth: AuthContext = Depends(require_capability("student:import")),
    session: AsyncSession = Depends(get_db),
) -> SheetImportPreviewResponse:
    preview = await create_sheet_import_preview(session, auth, payload)
    return SheetImportPreviewResponse(
        id=preview.id,
        spreadsheet_id=preview.spreadsheet_id,
        selected_range=preview.selected_range,
        source_fingerprint=preview.source_fingerprint,
        status=preview.status,
        expires_at=preview.expires_at,
        report=preview.report,
    )


@router.post(
    "/sheets/import-previews/{preview_id}/commit", response_model=SheetImportCommitResponse
)
async def commit_sheet_import(
    preview_id: uuid.UUID,
    auth: AuthContext = Depends(require_capability("student:import")),
    session: AsyncSession = Depends(get_db),
) -> SheetImportCommitResponse:
    preview, result = await commit_sheet_import_preview(session, auth, preview_id)
    return SheetImportCommitResponse(preview_id=preview.id, status=preview.status, result=result)


@router.post(
    "/drives/{drive_id}/sheets/export-proposals",
    response_model=IntegrationProposalResponse,
    status_code=201,
)
async def propose_sheet_export(
    drive_id: uuid.UUID,
    payload: SheetExportProposalCreate,
    auth: AuthContext = Depends(require_capability("integration:write")),
    session: AsyncSession = Depends(get_db),
) -> IntegrationProposalResponse:
    await load_authorized_drive(session, auth, drive_id)
    return proposal_response(await create_sheet_export_proposal(session, auth, drive_id, payload))


@router.post(
    "/session-revisions/{revision_id}/calendar-proposals",
    response_model=IntegrationProposalResponse,
    status_code=201,
)
async def propose_calendar_event(
    revision_id: uuid.UUID,
    payload: CalendarProposalCreate,
    auth: AuthContext = Depends(require_capability("integration:write")),
    session: AsyncSession = Depends(get_db),
) -> IntegrationProposalResponse:
    revision = await session.get(SessionRevision, revision_id)
    if not revision or revision.institution_id != auth.institution_id:
        raise NotFoundException("Session revision not found")
    await load_authorized_drive(session, auth, revision.drive_id)
    return proposal_response(await create_calendar_event_proposal(session, auth, revision, payload))


@router.post(
    "/proposals/{proposal_id}/decisions", response_model=IntegrationOperationResponse | None
)
async def decide_google_write(
    proposal_id: uuid.UUID,
    payload: IntegrationDecisionCreate,
    auth: AuthContext = Depends(require_capability("proposal:decide")),
    session: AsyncSession = Depends(get_db),
) -> IntegrationOperation | None:
    proposal = await session.get(ActionProposal, proposal_id)
    if (
        not proposal
        or proposal.institution_id != auth.institution_id
        or proposal.action_type not in {"sheets_export_write", "calendar_event_upsert"}
    ):
        raise NotFoundException("Integration proposal not found")
    await load_authorized_drive(session, auth, proposal.drive_id)
    return await decide_integration_proposal(
        session,
        auth,
        proposal,
        expected_revision=payload.expected_revision,
        expected_hash=payload.expected_hash,
        decision=payload.decision,
        comment=payload.comment,
    )


@router.get("/operations", response_model=list[IntegrationOperationResponse])
async def list_integration_operations(
    auth: AuthContext = Depends(require_capability("integration:manage")),
    session: AsyncSession = Depends(get_db),
) -> list[IntegrationOperation]:
    return list(
        (
            await session.execute(
                select(IntegrationOperation)
                .where(IntegrationOperation.institution_id == auth.institution_id)
                .order_by(IntegrationOperation.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


@router.post("/google/calendar/webhook", status_code=204)
async def google_calendar_webhook(
    x_goog_channel_id: str = Header(alias="X-Goog-Channel-ID"),
    x_goog_channel_token: str = Header(alias="X-Goog-Channel-Token"),
    x_goog_resource_id: str = Header(alias="X-Goog-Resource-ID"),
    x_goog_resource_state: str = Header(alias="X-Goog-Resource-State"),
    x_goog_message_number: str = Header(alias="X-Goog-Message-Number"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    institution_id = verified_webhook_institution(x_goog_channel_id)
    session.info["institution_id"] = str(institution_id)
    await session.execute(
        text("SELECT set_config('app.institution_id', :institution_id, true)"),
        {"institution_id": str(institution_id)},
    )
    await receive_calendar_webhook(
        session,
        channel_id=x_goog_channel_id,
        channel_token=x_goog_channel_token,
        resource_id=x_goog_resource_id,
        resource_state=x_goog_resource_state,
        message_number=x_goog_message_number,
    )
    return Response(status_code=204)
