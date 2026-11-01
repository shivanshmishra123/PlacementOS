"""Controlled Google Workspace connectors for P11.

Provider reads are explicit and scoped. Provider writes consume immutable approved
proposals and are idempotent at the database boundary.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import secrets
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.database import async_session_maker
from placementos.core.errors import BadRequestException, ConflictException, NotFoundException
from placementos.models.communications import OutboxEvent
from placementos.models.identity import Institution, Membership, StudentProfile, User
from placementos.models.integrations import (
    GmailSourceCapture,
    IntegrationAttempt,
    IntegrationConnection,
    IntegrationOperation,
    IntegrationWebhookChannel,
    IntegrationWebhookEvent,
    OAuthAuthorizationState,
    ProviderResourceMapping,
    SheetImportPreview,
)
from placementos.models.intelligence import ActionProposal, ApprovalDecision
from placementos.models.lifecycle import (
    DriveReportRevision,
    RecruitmentRound,
    RecruitmentSession,
    SessionAssignment,
    SessionRevision,
)
from placementos.models.recruitment import Drive
from placementos.models.storage import SourceArtifact
from placementos.schemas.integrations import (
    CalendarProposalCreate,
    GoogleAuthorizationCreate,
    SheetExportProposalCreate,
    SheetImportPreviewCreate,
)
from placementos.services.audit import record_audit
from placementos.services.jd_intelligence import canonical_hash
from placementos.services.parsers import DocumentScanner, MalwareScanner
from placementos.services.session import AuthContext
from placementos.services.source_jobs import SourceJobService
from placementos.services.storage import storage_service
from placementos.services.student_import import StudentImportService

GOOGLE_OPENID_SCOPES = {"openid", "email"}
FEATURE_SCOPES: dict[str, set[str]] = {
    "gmail_intake": {"https://www.googleapis.com/auth/gmail.readonly"},
    "sheets_import": {"https://www.googleapis.com/auth/spreadsheets.readonly"},
    "sheets_export": {"https://www.googleapis.com/auth/spreadsheets"},
    "calendar_events": {"https://www.googleapis.com/auth/calendar.events.owned"},
}


def build_webhook_channel_id(institution_id: uuid.UUID) -> str:
    institution = base64.urlsafe_b64encode(institution_id.bytes).decode().rstrip("=")
    nonce = secrets.token_hex(4)
    body = f"{institution}.{nonce}"
    signature = hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()[
        :32
    ]
    return f"{body}.{signature}"


def verified_webhook_institution(channel_id: str) -> uuid.UUID:
    try:
        institution, nonce, signature = channel_id.split(".", 2)
        body = f"{institution}.{nonce}"
        expected = hmac.new(
            settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256
        ).hexdigest()[:32]
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        raw = base64.urlsafe_b64decode(institution + "=" * (-len(institution) % 4))
        return uuid.UUID(bytes=raw)
    except (ValueError, AttributeError, TypeError) as exc:
        raise NotFoundException("Webhook channel not found") from exc


class GoogleGatewayError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        uncertain: bool = False,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.uncertain = uncertain
        self.request_id = request_id


class TokenCipher:
    """AES-GCM envelope for OAuth tokens and short-lived PKCE verifiers."""

    def __init__(self) -> None:
        configured = settings.INTEGRATION_TOKEN_ENCRYPTION_KEY.strip()
        if configured:
            try:
                raw = base64.urlsafe_b64decode(configured + "=" * (-len(configured) % 4))
            except ValueError as exc:
                raise RuntimeError(
                    "INTEGRATION_TOKEN_ENCRYPTION_KEY is not valid base64url"
                ) from exc
            if len(raw) != 32:
                raise RuntimeError("INTEGRATION_TOKEN_ENCRYPTION_KEY must decode to 32 bytes")
            self.key = raw
        elif settings.ENVIRONMENT == "production":
            raise RuntimeError("Production connector tokens require an external encryption key")
        else:
            # Development-only deterministic key; production validation rejects this path.
            self.key = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()

    def encrypt(self, plaintext: str) -> str:
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self.key).encrypt(nonce, plaintext.encode("utf-8"), b"placementos:p11")
        return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, envelope: str) -> str:
        raw = base64.urlsafe_b64decode(envelope.encode("ascii"))
        return AESGCM(self.key).decrypt(raw[:12], raw[12:], b"placementos:p11").decode("utf-8")


token_cipher = TokenCipher()


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: list[str]


@dataclass
class GoogleIdentity:
    subject: str
    email: str


@dataclass
class GmailSelectedContent:
    message_id: str
    attachment_id: str | None
    thread_id: str | None
    history_id: str | None
    sender: str | None
    subject: str | None
    received_at: datetime | None
    filename: str
    media_type: str
    content: bytes


@dataclass
class SheetValues:
    values: list[list[Any]]
    provider_version: str | None = None


@dataclass
class ProviderWriteResult:
    resource_id: str
    provider_version: str | None
    request_id: str | None
    evidence: dict[str, Any]


@dataclass
class CalendarWatchResult:
    resource_id: str
    expires_at: datetime | None


class GoogleWorkspaceGateway:
    """Narrow REST adapter; it exposes no generic request or discovery method."""

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token
        self.timeout = settings.GOOGLE_API_TIMEOUT_SECONDS

    async def exchange_code(self, code: str, verifier: str) -> OAuthTokens:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                settings.GOOGLE_OAUTH_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                    "code_verifier": verifier,
                },
            )
        return self._tokens(response)

    async def refresh(self, refresh_token: str) -> OAuthTokens:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                settings.GOOGLE_OAUTH_TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                },
            )
        return self._tokens(response, refresh=True)

    async def revoke(self, token: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    settings.GOOGLE_OAUTH_REVOKE_URL,
                    data={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GoogleGatewayError(
                "GOOGLE_REVOCATION_UNCONFIRMED",
                "Google token revocation could not be confirmed",
            ) from exc
        if response.status_code >= 400:
            raise GoogleGatewayError(
                "GOOGLE_REVOCATION_REJECTED",
                "Google rejected token revocation",
            )

    def _tokens(self, response: httpx.Response, *, refresh: bool = False) -> OAuthTokens:
        if response.status_code >= 400:
            data = (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            if refresh and data.get("error") == "invalid_grant":
                raise GoogleGatewayError(
                    "GOOGLE_AUTH_REVOKED", "Google refresh authorization is invalid or revoked"
                )
            raise GoogleGatewayError(
                "OAUTH_TOKEN_EXCHANGE_FAILED", "Google rejected the token request"
            )
        data = response.json()
        expires = data.get("expires_in")
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.now(UTC) + timedelta(seconds=int(expires)) if expires else None,
            scopes=str(data.get("scope", "")).split(),
        )

    async def identity(self) -> GoogleIdentity:
        response = await self._request("GET", "https://openidconnect.googleapis.com/v1/userinfo")
        data = response.json()
        if not data.get("sub") or not data.get("email") or not data.get("email_verified", True):
            raise GoogleGatewayError("GOOGLE_IDENTITY_INVALID", "Google identity is incomplete")
        return GoogleIdentity(subject=str(data["sub"]), email=str(data["email"]).lower())

    async def selected_gmail_content(
        self, message_id: str, attachment_id: str | None
    ) -> GmailSelectedContent:
        response = await self._request(
            "GET",
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{quote(message_id, safe='')}",
            params={"format": "full"},
        )
        message = response.json()
        payload = message.get("payload") or {}
        headers = {
            str(row.get("name", "")).lower(): str(row.get("value", ""))
            for row in payload.get("headers", [])
        }
        chosen: dict[str, Any] | None = None

        def visit(part: dict[str, Any]) -> None:
            nonlocal chosen
            body = part.get("body") or {}
            if attachment_id and body.get("attachmentId") == attachment_id:
                chosen = part
                return
            if not attachment_id and chosen is None and part.get("mimeType") == "text/plain":
                chosen = part
            for child in part.get("parts") or []:
                visit(child)

        visit(payload)
        if attachment_id and chosen is None:
            raise GoogleGatewayError(
                "GMAIL_ATTACHMENT_NOT_FOUND", "Selected attachment was not found"
            )
        chosen = chosen or payload
        body = chosen.get("body") or {}
        provider_attachment_id = body.get("attachmentId")
        encoded = body.get("data")
        if provider_attachment_id and not encoded:
            attachment = await self._request(
                "GET",
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/"
                f"{quote(message_id, safe='')}/attachments/{quote(provider_attachment_id, safe='')}",
            )
            encoded = attachment.json().get("data")
        if encoded:
            content = _decode_base64url(str(encoded))
        elif not attachment_id and message.get("snippet"):
            content = str(message["snippet"]).encode("utf-8")
        else:
            raise GoogleGatewayError("GMAIL_CONTENT_EMPTY", "Selected Gmail content is empty")
        received_at = None
        if message.get("internalDate"):
            received_at = datetime.fromtimestamp(int(message["internalDate"]) / 1000, UTC)
        filename = str(chosen.get("filename") or f"gmail-{message_id}.txt")
        media_type = str(chosen.get("mimeType") or "text/plain")
        return GmailSelectedContent(
            message_id=message_id,
            attachment_id=attachment_id,
            thread_id=message.get("threadId"),
            history_id=message.get("historyId"),
            sender=headers.get("from"),
            subject=headers.get("subject"),
            received_at=received_at,
            filename=filename,
            media_type=media_type,
            content=content,
        )

    async def sheet_values(self, spreadsheet_id: str, selected_range: str) -> SheetValues:
        response = await self._request(
            "GET",
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{quote(spreadsheet_id, safe='')}/values/{quote(selected_range, safe='')}",
            params={"majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE"},
        )
        return SheetValues(
            values=response.json().get("values") or [],
            provider_version=response.headers.get("etag"),
        )

    async def write_sheet(
        self, spreadsheet_id: str, target_range: str, values: list[list[Any]]
    ) -> ProviderWriteResult:
        response = await self._request(
            "POST",
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{quote(spreadsheet_id, safe='')}/values:batchUpdate",
            json={
                "valueInputOption": "RAW",
                "includeValuesInResponse": False,
                "data": [{"range": target_range, "majorDimension": "ROWS", "values": values}],
            },
            write=True,
        )
        data = response.json()
        return ProviderWriteResult(
            resource_id=f"{spreadsheet_id}:{target_range}",
            provider_version=response.headers.get("etag"),
            request_id=response.headers.get("x-request-id"),
            evidence={"updated_cells": data.get("totalUpdatedCells", 0)},
        )

    async def upsert_calendar_event(
        self,
        calendar_id: str,
        event_id: str,
        event: dict[str, Any],
        send_updates: str,
        provider_version: str | None,
    ) -> ProviderWriteResult:
        base = (
            f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id, safe='')}/events"
        )
        headers = {"If-Match": provider_version} if provider_version else None
        if provider_version:
            response = await self._request(
                "PUT",
                f"{base}/{quote(event_id, safe='')}",
                params={"sendUpdates": send_updates},
                headers=headers,
                json=event,
                write=True,
            )
        else:
            response = await self._request(
                "POST",
                base,
                params={"sendUpdates": send_updates},
                json={"id": event_id, **event},
                write=True,
            )
        data = response.json()
        return ProviderWriteResult(
            resource_id=str(data.get("id", event_id)),
            provider_version=str(data.get("etag") or response.headers.get("etag") or "") or None,
            request_id=response.headers.get("x-request-id"),
            evidence={"html_link": data.get("htmlLink"), "status": data.get("status")},
        )

    async def watch_calendar(
        self,
        calendar_id: str,
        channel_id: str,
        channel_token: str,
        webhook_address: str,
    ) -> CalendarWatchResult:
        response = await self._request(
            "POST",
            "https://www.googleapis.com/calendar/v3/calendars/"
            f"{quote(calendar_id, safe='')}/events/watch",
            json={
                "id": channel_id,
                "type": "web_hook",
                "address": webhook_address,
                "token": channel_token,
            },
            write=True,
        )
        data = response.json()
        expires_at = None
        if data.get("expiration"):
            expires_at = datetime.fromtimestamp(int(data["expiration"]) / 1000, UTC)
        return CalendarWatchResult(resource_id=str(data["resourceId"]), expires_at=expires_at)

    async def _request(
        self, method: str, url: str, *, write: bool = False, **kwargs
    ) -> httpx.Response:
        if not self.access_token:
            raise GoogleGatewayError("GOOGLE_TOKEN_MISSING", "Google access token is unavailable")
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise GoogleGatewayError(
                "GOOGLE_NETWORK_UNCERTAIN" if write else "GOOGLE_NETWORK_FAILED",
                "Google request outcome is uncertain" if write else "Google request failed",
                retryable=not write,
                uncertain=write,
            ) from exc
        request_id = response.headers.get("x-request-id")
        if response.status_code in {401, 403}:
            raise GoogleGatewayError(
                "GOOGLE_AUTH_REVOKED", "Google authorization is invalid or revoked"
            )
        if response.status_code == 412:
            raise GoogleGatewayError(
                "GOOGLE_VERSION_CONFLICT", "Google resource changed externally"
            )
        if response.status_code == 429:
            raise GoogleGatewayError(
                "GOOGLE_RATE_LIMITED",
                "Google rate limit reached",
                retryable=True,
                request_id=request_id,
            )
        if response.status_code >= 500:
            raise GoogleGatewayError(
                "GOOGLE_PROVIDER_UNCERTAIN" if write else "GOOGLE_PROVIDER_UNAVAILABLE",
                "Google provider returned an unavailable response",
                retryable=not write,
                uncertain=write,
                request_id=request_id,
            )
        if response.status_code >= 400:
            raise GoogleGatewayError(
                "GOOGLE_REQUEST_REJECTED",
                "Google rejected the scoped request",
                request_id=request_id,
            )
        return response


def get_google_gateway(access_token: str | None = None) -> GoogleWorkspaceGateway:
    return GoogleWorkspaceGateway(access_token)


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _scope_set(features: Sequence[str]) -> set[str]:
    scopes = set(GOOGLE_OPENID_SCOPES)
    for feature in features:
        scopes.update(FEATURE_SCOPES[feature])
    return scopes


async def create_google_authorization(
    session: AsyncSession, auth: AuthContext, payload: GoogleAuthorizationCreate
) -> tuple[str, datetime]:
    if not settings.GOOGLE_CONNECTORS_ENABLED:
        raise ConflictException("Google connectors are disabled in this environment")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ConflictException("Google OAuth credentials are not configured")
    raw_state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    scopes = sorted(_scope_set(payload.features))
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    session.add(
        OAuthAuthorizationState(
            institution_id=auth.institution_id,
            membership_id=auth.membership_id,
            state_hash=hashlib.sha256(raw_state.encode()).hexdigest(),
            code_verifier_ciphertext=token_cipher.encrypt(verifier),
            requested_features=payload.features,
            requested_scopes=scopes,
            redirect_after=payload.redirect_after,
            expires_at=expires_at,
        )
    )
    await session.commit()
    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": raw_state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{settings.GOOGLE_OAUTH_AUTHORIZE_URL}?{query}", expires_at


async def complete_google_authorization(
    session: AsyncSession, auth: AuthContext, state: str, code: str
) -> tuple[IntegrationConnection, str]:
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    row = (
        await session.execute(
            select(OAuthAuthorizationState)
            .where(
                OAuthAuthorizationState.state_hash == state_hash,
                OAuthAuthorizationState.institution_id == auth.institution_id,
                OAuthAuthorizationState.membership_id == auth.membership_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if not row or row.consumed_at or row.expires_at <= now:
        raise BadRequestException("Google OAuth state is invalid, expired, or already used")
    row.consumed_at = now
    verifier = token_cipher.decrypt(row.code_verifier_ciphertext)
    tokens = await get_google_gateway().exchange_code(code, verifier)
    granted = set(tokens.scopes)
    if not set(row.requested_scopes).issubset(granted):
        raise BadRequestException(
            "Google did not grant every requested connector scope",
            details={"missing_scopes": sorted(set(row.requested_scopes) - granted)},
        )
    identity = await get_google_gateway(tokens.access_token).identity()
    connection = (
        await session.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.institution_id == auth.institution_id,
                IntegrationConnection.provider == "google",
                IntegrationConnection.external_account_id == identity.subject,
            )
        )
    ).scalar_one_or_none()
    if connection:
        connection.owner_membership_id = auth.membership_id
        connection.status = "active"
        connection.granted_scopes = sorted(granted)
        connection.access_token_ciphertext = token_cipher.encrypt(tokens.access_token)
        if tokens.refresh_token:
            connection.refresh_token_ciphertext = token_cipher.encrypt(tokens.refresh_token)
        connection.access_token_expires_at = tokens.expires_at
        connection.connection_revision += 1
        connection.disconnected_at = None
        connection.last_error_code = None
    else:
        connection = IntegrationConnection(
            institution_id=auth.institution_id,
            owner_membership_id=auth.membership_id,
            external_account_id=identity.subject,
            external_account_email=identity.email,
            granted_scopes=sorted(granted),
            access_token_ciphertext=token_cipher.encrypt(tokens.access_token),
            refresh_token_ciphertext=(
                token_cipher.encrypt(tokens.refresh_token) if tokens.refresh_token else None
            ),
            access_token_expires_at=tokens.expires_at,
        )
        session.add(connection)
    await session.flush()
    record_audit(
        session,
        auth,
        "integration:connected",
        "integration_connection",
        connection.id,
        {
            "provider": "google",
            "scopes": sorted(granted),
            "connection_revision": connection.connection_revision,
        },
    )
    await session.commit()
    return connection, row.redirect_after


async def load_connection(
    session: AsyncSession,
    auth: AuthContext,
    connection_id: uuid.UUID,
    *,
    required_any: set[str] | None = None,
    for_update: bool = False,
) -> IntegrationConnection:
    statement = select(IntegrationConnection).where(
        IntegrationConnection.id == connection_id,
        IntegrationConnection.institution_id == auth.institution_id,
    )
    if for_update:
        statement = statement.with_for_update()
    connection = (await session.execute(statement)).scalar_one_or_none()
    if not connection:
        raise NotFoundException("Integration connection not found")
    if connection.status != "active":
        raise ConflictException("Integration connection is not active")
    if required_any and not required_any.intersection(connection.granted_scopes):
        raise ConflictException(
            "Integration connection lacks the required scope",
            details={"required_any": sorted(required_any)},
        )
    return connection


async def valid_access_token(session: AsyncSession, connection: IntegrationConnection) -> str:
    now = datetime.now(UTC)
    if (
        not connection.access_token_expires_at
        or connection.access_token_expires_at > now + timedelta(minutes=1)
    ):
        return token_cipher.decrypt(connection.access_token_ciphertext)
    if not connection.refresh_token_ciphertext:
        connection.status = "expired"
        connection.last_error_code = "GOOGLE_REFRESH_TOKEN_MISSING"
        connection.last_error_at = now
        await session.commit()
        raise ConflictException("Google connection requires reconnection")
    try:
        refreshed = await get_google_gateway().refresh(
            token_cipher.decrypt(connection.refresh_token_ciphertext)
        )
    except GoogleGatewayError as exc:
        connection.status = "expired" if exc.code == "GOOGLE_AUTH_REVOKED" else connection.status
        connection.last_error_code = exc.code
        connection.last_error_at = now
        await session.commit()
        raise ConflictException("Google connection could not be refreshed") from exc
    connection.access_token_ciphertext = token_cipher.encrypt(refreshed.access_token)
    if refreshed.refresh_token:
        connection.refresh_token_ciphertext = token_cipher.encrypt(refreshed.refresh_token)
    connection.access_token_expires_at = refreshed.expires_at
    await session.flush()
    return refreshed.access_token


async def disconnect_connection(
    session: AsyncSession, auth: AuthContext, connection: IntegrationConnection
) -> None:
    now = datetime.now(UTC)
    provider_revocation = "not_available"
    encrypted_token = connection.refresh_token_ciphertext or connection.access_token_ciphertext
    if encrypted_token:
        try:
            await get_google_gateway().revoke(token_cipher.decrypt(encrypted_token))
            provider_revocation = "confirmed"
        except GoogleGatewayError:
            # Local authority is removed even when the provider cannot confirm revocation.
            provider_revocation = "unconfirmed"
    connection.status = "disconnected"
    connection.granted_scopes = []
    connection.access_token_ciphertext = token_cipher.encrypt("")
    connection.refresh_token_ciphertext = None
    connection.access_token_expires_at = None
    connection.connection_revision += 1
    connection.disconnected_at = now
    operations = (
        await session.execute(
            select(IntegrationOperation).where(
                IntegrationOperation.connection_id == connection.id,
                IntegrationOperation.status.in_(["queued", "claimed"]),
            )
        )
    ).scalars()
    for operation in operations:
        operation.status = "stale"
        operation.last_error_code = "CONNECTION_REVOKED"
    channels = (
        await session.execute(
            select(IntegrationWebhookChannel).where(
                IntegrationWebhookChannel.connection_id == connection.id,
                IntegrationWebhookChannel.status == "active",
            )
        )
    ).scalars()
    for channel in channels:
        channel.status = "stopped"
    record_audit(
        session,
        auth,
        "integration:disconnected",
        "integration_connection",
        connection.id,
        {
            "connection_revision": connection.connection_revision,
            "provider_revocation": provider_revocation,
        },
    )
    await session.commit()


async def register_calendar_watch(
    session: AsyncSession,
    auth: AuthContext,
    connection: IntegrationConnection,
    calendar_id: str,
) -> IntegrationWebhookChannel:
    if not settings.INTEGRATION_WEBHOOK_BASE_URL:
        raise ConflictException("Calendar webhooks are not configured in this environment")
    token = secrets.token_urlsafe(32)
    channel_id = build_webhook_channel_id(auth.institution_id)
    address = (
        settings.INTEGRATION_WEBHOOK_BASE_URL.rstrip("/")
        + "/api/v1/integrations/google/calendar/webhook"
    )
    access_token = await valid_access_token(session, connection)
    result = await get_google_gateway(access_token).watch_calendar(
        calendar_id, channel_id, token, address
    )
    channel = IntegrationWebhookChannel(
        institution_id=auth.institution_id,
        connection_id=connection.id,
        channel_id=channel_id,
        resource_id=result.resource_id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=result.expires_at,
    )
    session.add(channel)
    await session.flush()
    record_audit(
        session,
        auth,
        "integration:calendar_watch_registered",
        "integration_webhook_channel",
        channel.id,
        {
            "calendar_id": calendar_id,
            "expires_at": result.expires_at.isoformat() if result.expires_at else None,
        },
    )
    await session.commit()
    return channel


async def capture_gmail_source(
    session: AsyncSession,
    auth: AuthContext,
    *,
    drive_id: uuid.UUID,
    connection: IntegrationConnection,
    message_id: str,
    attachment_id: str | None,
) -> tuple[GmailSourceCapture, uuid.UUID]:
    existing = (
        await session.execute(
            select(GmailSourceCapture).where(
                GmailSourceCapture.connection_id == connection.id,
                GmailSourceCapture.message_id == message_id,
                GmailSourceCapture.attachment_id == attachment_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        artifact = await session.get(SourceArtifact, existing.source_artifact_id)
        if not artifact:
            raise ConflictException("Captured Gmail source artifact is missing")
        job = await SourceJobService.create_extraction_job(session, artifact)
        return existing, job.id
    token = await valid_access_token(session, connection)
    selected = await get_google_gateway(token).selected_gmail_content(message_id, attachment_id)
    if len(selected.content) > settings.MAX_UPLOAD_BYTES:
        raise BadRequestException("Selected Gmail content exceeds the configured upload limit")
    extension = ".txt"
    if "." in selected.filename:
        extension = "." + selected.filename.rsplit(".", 1)[1].lower()
    canonical_type = DocumentScanner.scan_bytes(selected.content, extension.lstrip("."))
    scan_status = MalwareScanner.scan(selected.content)
    media_type = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text": "text/plain",
    }[canonical_type]
    accepted_key, content_hash, byte_size = storage_service.store_accepted_bytes(
        selected.content,
        auth.institution_id,
        "jd_intake",
        extension,
        media_type,
    )
    artifact = SourceArtifact(
        institution_id=auth.institution_id,
        drive_id=drive_id,
        source_kind="gmail_message" if not attachment_id else "gmail_attachment",
        object_key=accepted_key,
        file_name=selected.filename,
        media_type=media_type,
        file_size_bytes=byte_size,
        hash_sha256=content_hash,
        scan_status=scan_status,
        acceptance_status="accepted",
        created_by_membership_id=auth.membership_id,
    )
    session.add(artifact)
    await session.flush()
    capture = GmailSourceCapture(
        institution_id=auth.institution_id,
        connection_id=connection.id,
        drive_id=drive_id,
        source_artifact_id=artifact.id,
        message_id=message_id,
        attachment_id=attachment_id,
        thread_id=selected.thread_id,
        sender=selected.sender,
        subject=selected.subject,
        received_at=selected.received_at,
        provider_history_id=selected.history_id,
        content_hash=content_hash,
        captured_by_membership_id=auth.membership_id,
    )
    session.add(capture)
    job = await SourceJobService.create_extraction_job(session, artifact)
    record_audit(
        session,
        auth,
        "source:gmail_captured",
        "source_artifact",
        artifact.id,
        {
            "drive_id": str(drive_id),
            "message_id": message_id,
            "attachment_selected": bool(attachment_id),
        },
    )
    await session.commit()
    return capture, job.id


def _sheet_fingerprint(values: list[list[Any]], spreadsheet_id: str, selected_range: str) -> str:
    return canonical_hash(
        {"spreadsheet_id": spreadsheet_id, "selected_range": selected_range, "values": values}
    )


def _sheet_to_csv(values: list[list[Any]], mapping: dict[str, str]) -> tuple[str, list[str]]:
    if not values:
        raise BadRequestException("Selected Sheets range is empty")
    raw_headers = [str(value).strip() for value in values[0]]
    if not raw_headers:
        raise BadRequestException("Selected Sheets range has no header row")
    normalized = {header.lower().replace(" ", "_"): header for header in raw_headers}
    canonical_fields = list(StudentImportService.HEADER_ALIASES)
    resolved: dict[str, str] = {}
    for canonical in canonical_fields:
        requested = mapping.get(canonical)
        if requested:
            if requested not in raw_headers:
                raise BadRequestException(f"Mapped Sheets column '{requested}' was not found")
            resolved[canonical] = requested
            continue
        aliases = [canonical, *StudentImportService.HEADER_ALIASES[canonical]]
        for alias in aliases:
            match = normalized.get(alias.lower().replace(" ", "_"))
            if match:
                resolved[canonical] = match
                break
    output = io.StringIO()
    fieldnames = list(resolved)
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    identifiers: list[str] = []
    for raw_row in values[1:]:
        by_header = {
            header: str(raw_row[index]) if index < len(raw_row) else ""
            for index, header in enumerate(raw_headers)
        }
        row = {canonical: by_header[source] for canonical, source in resolved.items()}
        if row.get("student_identifier"):
            identifiers.append(row["student_identifier"].strip())
        writer.writerow(row)
    return output.getvalue(), identifiers


async def create_sheet_import_preview(
    session: AsyncSession,
    auth: AuthContext,
    payload: SheetImportPreviewCreate,
) -> SheetImportPreview:
    connection = await load_connection(
        session,
        auth,
        payload.connection_id,
        required_any={
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
        },
    )
    token = await valid_access_token(session, connection)
    sheet = await get_google_gateway(token).sheet_values(
        payload.spreadsheet_id, payload.selected_range
    )
    csv_text, identifiers = _sheet_to_csv(sheet.values, payload.mapping)
    report = await StudentImportService.preview_csv(auth.institution_id, csv_text, session)
    profiles = (
        await session.execute(
            select(StudentProfile).where(
                StudentProfile.institution_id == auth.institution_id,
                StudentProfile.student_identifier.in_(identifiers),
            )
        )
    ).scalars()
    expected = {
        profile.student_identifier: str(profile.current_academic_revision_id)
        if profile.current_academic_revision_id
        else None
        for profile in profiles
    }
    row = SheetImportPreview(
        institution_id=auth.institution_id,
        connection_id=connection.id,
        spreadsheet_id=payload.spreadsheet_id,
        selected_range=payload.selected_range,
        mapping=payload.mapping,
        source_fingerprint=_sheet_fingerprint(
            sheet.values, payload.spreadsheet_id, payload.selected_range
        ),
        preview_token=report.preview_token,
        expected_academic_revisions=expected,
        report={
            "total_rows": report.total_rows,
            "valid_rows_count": report.valid_rows_count,
            "invalid_rows_count": report.invalid_rows_count,
            "new_students_count": report.new_students_count,
            "updating_students_count": report.updating_students_count,
            "sample_rows": report.sample_rows,
            "invalid_rows": report.invalid_rows,
            "provider_version": sheet.provider_version,
        },
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        created_by_membership_id=auth.membership_id,
    )
    session.add(row)
    await session.flush()
    record_audit(
        session,
        auth,
        "integration:sheets_import_previewed",
        "sheet_import_preview",
        row.id,
        {
            "spreadsheet_id": payload.spreadsheet_id,
            "range": payload.selected_range,
            "rows": report.total_rows,
        },
    )
    await session.commit()
    return row


async def commit_sheet_import_preview(
    session: AsyncSession, auth: AuthContext, preview_id: uuid.UUID
) -> tuple[SheetImportPreview, dict[str, Any]]:
    preview = (
        await session.execute(
            select(SheetImportPreview)
            .where(
                SheetImportPreview.id == preview_id,
                SheetImportPreview.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not preview:
        raise NotFoundException("Sheets import preview not found")
    if preview.status == "committed":
        return preview, {"message": "Sheets import was already committed", "idempotent": True}
    if preview.status != "previewed" or preview.expires_at <= datetime.now(UTC):
        raise ConflictException("Sheets import preview is stale or expired")
    connection = await load_connection(
        session,
        auth,
        preview.connection_id,
        required_any={
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
        },
    )
    token = await valid_access_token(session, connection)
    sheet = await get_google_gateway(token).sheet_values(
        preview.spreadsheet_id, preview.selected_range
    )
    current_fingerprint = _sheet_fingerprint(
        sheet.values, preview.spreadsheet_id, preview.selected_range
    )
    if current_fingerprint != preview.source_fingerprint:
        preview.status = "stale"
        await session.commit()
        raise ConflictException("The selected Sheets range changed after preview")
    identifiers = list(preview.expected_academic_revisions)
    profiles = (
        await session.execute(
            select(StudentProfile).where(
                StudentProfile.institution_id == auth.institution_id,
                StudentProfile.student_identifier.in_(identifiers),
            )
        )
    ).scalars()
    current = {
        profile.student_identifier: str(profile.current_academic_revision_id)
        if profile.current_academic_revision_id
        else None
        for profile in profiles
    }
    changed = [
        identifier
        for identifier, expected in preview.expected_academic_revisions.items()
        if current.get(identifier) != expected
    ]
    if changed:
        preview.status = "stale"
        await session.commit()
        raise ConflictException(
            "Verified academic records changed after Sheets preview",
            details={"changed_student_identifiers": changed},
        )
    preview.status = "committing"
    await session.flush()
    result = await StudentImportService.commit_preview(
        preview.preview_token,
        auth.institution_id,
        auth.membership_id,
        auth.user_id,
        session,
    )
    preview.status = "committed"
    preview.committed_at = datetime.now(UTC)
    record_audit(
        session,
        auth,
        "integration:sheets_import_committed",
        "sheet_import_preview",
        preview.id,
        {"spreadsheet_id": preview.spreadsheet_id, "result": result},
    )
    await session.commit()
    return preview, result


def _safe_sheet_cell(value: Any) -> Any:
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    return value


async def create_sheet_export_proposal(
    session: AsyncSession,
    auth: AuthContext,
    drive_id: uuid.UUID,
    payload: SheetExportProposalCreate,
) -> ActionProposal:
    connection = await load_connection(
        session,
        auth,
        payload.connection_id,
        required_any={"https://www.googleapis.com/auth/spreadsheets"},
    )
    report = await session.get(DriveReportRevision, payload.report_id)
    if not report or report.institution_id != auth.institution_id or report.drive_id != drive_id:
        raise NotFoundException("Drive report not found")
    values: list[list[Any]] = [["metric", "value"]]
    for key, value in sorted(report.snapshot_payload.items()):
        rendered = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
        values.append([_safe_sheet_cell(key), _safe_sheet_cell(rendered)])
    exact = {
        "connection_id": str(connection.id),
        "spreadsheet_id": payload.spreadsheet_id,
        "target_range": payload.target_range,
        "value_input_option": "RAW",
        "values": values,
        "values_hash": canonical_hash({"values": values}),
        "report_id": str(report.id),
        "report_snapshot_hash": report.snapshot_hash,
    }
    return await _create_write_proposal(
        session,
        auth,
        drive_id=drive_id,
        action_type="sheets_export_write",
        target_type="drive_report_revision",
        target_id=report.id,
        connection=connection,
        exact_payload=exact,
        dependencies={
            "report_snapshot_hash": report.snapshot_hash,
            "connection_revision": connection.connection_revision,
        },
    )


async def create_calendar_event_proposal(
    session: AsyncSession,
    auth: AuthContext,
    revision: SessionRevision,
    payload: CalendarProposalCreate,
) -> ActionProposal:
    connection = await load_connection(
        session,
        auth,
        payload.connection_id,
        required_any={"https://www.googleapis.com/auth/calendar.events.owned"},
    )
    recruitment_session = await session.get(RecruitmentSession, revision.session_id)
    round_item = await session.get(RecruitmentRound, revision.round_id)
    if (
        not recruitment_session
        or recruitment_session.published_revision_id != revision.id
        or not round_item
    ):
        raise ConflictException("Calendar writes require the currently published session revision")
    attendees = (
        (
            await session.execute(
                select(User.email)
                .join(StudentProfile, StudentProfile.user_id == User.id)
                .join(SessionAssignment, SessionAssignment.student_profile_id == StudentProfile.id)
                .where(
                    SessionAssignment.session_revision_id == revision.id,
                    SessionAssignment.status == "published",
                )
                .order_by(User.email)
            )
        )
        .scalars()
        .all()
    )
    event_id = "plos" + revision.session_id.hex
    event = {
        "summary": round_item.name,
        "location": revision.venue,
        "description": "PlacementOS approved recruitment session",
        "start": {"dateTime": revision.start_at.isoformat(), "timeZone": revision.timezone},
        "end": {"dateTime": revision.end_at.isoformat(), "timeZone": revision.timezone},
        "attendees": [{"email": email} for email in attendees],
        "visibility": "private",
    }
    exact = {
        "connection_id": str(connection.id),
        "calendar_id": payload.calendar_id,
        "event_id": event_id,
        "event": event,
        "send_updates": payload.send_updates,
        "session_revision_id": str(revision.id),
        "event_hash": canonical_hash({"event": event}),
    }
    return await _create_write_proposal(
        session,
        auth,
        drive_id=revision.drive_id,
        action_type="calendar_event_upsert",
        target_type="session_revision",
        target_id=revision.id,
        connection=connection,
        exact_payload=exact,
        dependencies={
            "session_revision": revision.revision_number,
            "event_hash": exact["event_hash"],
            "connection_revision": connection.connection_revision,
        },
    )


async def _create_write_proposal(
    session: AsyncSession,
    auth: AuthContext,
    *,
    drive_id: uuid.UUID,
    action_type: str,
    target_type: str,
    target_id: uuid.UUID,
    connection: IntegrationConnection,
    exact_payload: dict[str, Any],
    dependencies: dict[str, Any],
) -> ActionProposal:
    existing = (
        await session.execute(
            select(ActionProposal).where(
                ActionProposal.institution_id == auth.institution_id,
                ActionProposal.action_type == action_type,
                ActionProposal.target_type == target_type,
                ActionProposal.target_id == target_id,
                ActionProposal.state == "pending_approval",
            )
        )
    ).scalar_one_or_none()
    envelope_hash = canonical_hash(
        {
            "institution_id": str(auth.institution_id),
            "action_type": action_type,
            "target_type": target_type,
            "target_id": str(target_id),
            "payload": exact_payload,
            "dependencies": dependencies,
        }
    )
    if existing and existing.canonical_hash == envelope_hash:
        return existing
    if existing:
        existing.state = "stale"
    revision_number = (
        int(
            await session.scalar(
                select(func.coalesce(func.max(ActionProposal.revision_number), 0)).where(
                    ActionProposal.institution_id == auth.institution_id,
                    ActionProposal.action_type == action_type,
                    ActionProposal.target_type == target_type,
                    ActionProposal.target_id == target_id,
                )
            )
            or 0
        )
        + 1
    )
    proposal = ActionProposal(
        institution_id=auth.institution_id,
        drive_id=drive_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        revision_number=revision_number,
        schema_version=1,
        payload=exact_payload,
        dependencies=dependencies,
        canonical_hash=envelope_hash,
        state="pending_approval",
        requested_by_membership_id=auth.membership_id,
        execution_expires_at=datetime.now(UTC) + timedelta(hours=24),
        execution_bounds={"max_operations": 1},
        sender_connection_revision=str(connection.connection_revision),
    )
    session.add(proposal)
    await session.flush()
    record_audit(
        session,
        auth,
        "integration:write_proposed",
        "action_proposal",
        proposal.id,
        {"action_type": action_type, "target_type": target_type, "target_id": str(target_id)},
    )
    await session.commit()
    return proposal


async def decide_integration_proposal(
    session: AsyncSession,
    auth: AuthContext,
    proposal: ActionProposal,
    *,
    expected_revision: int,
    expected_hash: str,
    decision: str,
    comment: str | None,
) -> IntegrationOperation | None:
    proposal = (
        await session.execute(
            select(ActionProposal)
            .where(
                ActionProposal.id == proposal.id,
                ActionProposal.institution_id == auth.institution_id,
            )
            .with_for_update()
        )
    ).scalar_one()
    if proposal.state != "pending_approval":
        existing = (
            await session.execute(
                select(IntegrationOperation).where(IntegrationOperation.proposal_id == proposal.id)
            )
        ).scalar_one_or_none()
        if proposal.state == "approved" and decision == "approved" and existing:
            return existing
        raise ConflictException("Integration proposal is no longer pending")
    if proposal.revision_number != expected_revision or proposal.canonical_hash != expected_hash:
        raise ConflictException("Integration proposal revision or hash changed")
    connection = await load_connection(
        session, auth, uuid.UUID(proposal.payload["connection_id"]), for_update=True
    )
    if int(proposal.dependencies["connection_revision"]) != connection.connection_revision:
        proposal.state = "stale"
        await session.commit()
        raise ConflictException("Integration connection changed after proposal creation")
    now = datetime.now(UTC)
    if proposal.execution_expires_at and proposal.execution_expires_at <= now:
        proposal.state = "expired"
        await session.commit()
        raise ConflictException("Integration proposal execution window expired")
    session.add(
        ApprovalDecision(
            institution_id=auth.institution_id,
            proposal_id=proposal.id,
            proposal_hash=proposal.canonical_hash,
            decision=decision,
            comment=comment,
            decided_by_membership_id=auth.membership_id,
            permission_context={"capability": "proposal:decide", "integration_write": True},
        )
    )
    proposal.state = decision if decision != "revision_requested" else "revision_requested"
    operation = None
    if decision == "approved":
        operation = IntegrationOperation(
            institution_id=auth.institution_id,
            drive_id=proposal.drive_id,
            connection_id=connection.id,
            proposal_id=proposal.id,
            operation_key=f"integration:{proposal.id}",
            operation_kind=proposal.action_type,
            exact_payload=proposal.payload,
            dependency_fingerprint=proposal.canonical_hash,
            connection_revision=connection.connection_revision,
            status="queued",
        )
        session.add(operation)
        await session.flush()
        session.add(
            OutboxEvent(
                institution_id=auth.institution_id,
                event_key=f"integration.execute:{operation.id}",
                event_type="integration.execute",
                aggregate_type="integration_operation",
                aggregate_id=operation.id,
                payload={
                    "operation_id": str(operation.id),
                    "institution_id": str(auth.institution_id),
                },
                status="pending",
                next_attempt_at=now,
            )
        )
    record_audit(
        session,
        auth,
        "integration:proposal_decided",
        "action_proposal",
        proposal.id,
        {"decision": decision, "operation_id": str(operation.id) if operation else None},
    )
    await session.commit()
    return operation


async def receive_calendar_webhook(
    session: AsyncSession,
    *,
    channel_id: str,
    channel_token: str,
    resource_id: str,
    resource_state: str,
    message_number: str,
) -> IntegrationWebhookEvent | None:
    channel = (
        await session.execute(
            select(IntegrationWebhookChannel).where(
                IntegrationWebhookChannel.channel_id == channel_id,
                IntegrationWebhookChannel.status == "active",
            )
        )
    ).scalar_one_or_none()
    if not channel or not hmac.compare_digest(
        channel.token_hash, hashlib.sha256(channel_token.encode()).hexdigest()
    ):
        raise NotFoundException("Webhook channel not found")
    if channel.expires_at and channel.expires_at <= datetime.now(UTC):
        channel.status = "expired"
        await session.commit()
        raise NotFoundException("Webhook channel not found")
    if channel.resource_id != resource_id:
        raise BadRequestException("Webhook resource does not match its channel")
    existing = (
        await session.execute(
            select(IntegrationWebhookEvent).where(
                IntegrationWebhookEvent.channel_id == channel_id,
                IntegrationWebhookEvent.message_number == message_number,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return None
    event = IntegrationWebhookEvent(
        institution_id=channel.institution_id,
        connection_id=channel.connection_id,
        channel_id=channel_id,
        message_number=message_number,
        resource_id=resource_id,
        resource_state=resource_state,
        payload={},
    )
    session.add(event)
    mappings = (
        await session.execute(
            select(ProviderResourceMapping).where(
                ProviderResourceMapping.connection_id == channel.connection_id,
                ProviderResourceMapping.provider_resource_type == "google_calendar_event",
            )
        )
    ).scalars()
    for mapping in mappings:
        mapping.status = "external_change_pending_reconciliation"
    await session.commit()
    return event


async def relay_pending_integration_operations(limit: int = 100) -> int:
    """Publish committed integration work; duplicate publication is safe at claim."""
    from placementos.workers.integration_tasks import execute_integration_operation_task

    async with async_session_maker() as discovery:
        institution_ids = (
            (await discovery.execute(select(Institution.id).where(Institution.is_active.is_(True))))
            .scalars()
            .all()
        )
    published = 0
    now = datetime.now(UTC)
    for institution_id in institution_ids:
        if published >= limit:
            break
        async with async_session_maker() as session:
            session.info["institution_id"] = str(institution_id)
            rows = (
                (
                    await session.execute(
                        select(OutboxEvent)
                        .where(
                            OutboxEvent.institution_id == institution_id,
                            OutboxEvent.aggregate_type == "integration_operation",
                            OutboxEvent.next_attempt_at <= now,
                            or_(
                                OutboxEvent.status == "pending",
                                OutboxEvent.status == "published",
                            ),
                        )
                        .order_by(OutboxEvent.created_at)
                        .limit(limit - published)
                        .with_for_update(skip_locked=True)
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                operation = await session.get(IntegrationOperation, row.aggregate_id)
                if not operation or operation.status != "queued":
                    row.status = "processed"
                    continue
                try:
                    execute_integration_operation_task.delay(str(operation.id), str(institution_id))
                    row.status = "published"
                    row.published_at = now
                    row.publish_attempts += 1
                    row.next_attempt_at = now + timedelta(seconds=30)
                    row.last_error = None
                    published += 1
                except Exception as exc:
                    row.publish_attempts += 1
                    row.last_error = str(exc)[:1000]
                    row.next_attempt_at = now + timedelta(seconds=min(300, 2**row.publish_attempts))
            await session.commit()
    return published


async def execute_integration_operation(
    operation_id: uuid.UUID,
    institution_id: uuid.UUID,
    *,
    gateway: GoogleWorkspaceGateway | None = None,
) -> str:
    """Claim and execute an exact approved Google write once."""
    now = datetime.now(UTC)
    async with async_session_maker() as session:
        session.info["institution_id"] = str(institution_id)
        operation = (
            await session.execute(
                select(IntegrationOperation)
                .where(
                    IntegrationOperation.id == operation_id,
                    IntegrationOperation.institution_id == institution_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not operation:
            return "not_found"
        if operation.status in {"succeeded", "failed", "unknown", "stale", "cancelled"}:
            return operation.status
        if (
            operation.status == "claimed"
            and operation.lease_expires_at
            and operation.lease_expires_at > now
        ):
            return "already_claimed"
        if operation.status == "claimed":
            started = (
                await session.execute(
                    select(IntegrationAttempt).where(
                        IntegrationAttempt.operation_id == operation.id,
                        IntegrationAttempt.status == "started",
                    )
                )
            ).scalar_one_or_none()
            if started:
                started.status = "unknown"
                started.completed_at = now
                started.error_code = "CLAIM_EXPIRED_AFTER_PROVIDER_BOUNDARY"
                operation.status = "unknown"
                operation.completed_at = now
                operation.last_error_code = started.error_code
                await session.commit()
                return "unknown"
        proposal = await session.get(ActionProposal, operation.proposal_id)
        connection = await session.get(IntegrationConnection, operation.connection_id)
        drive = await session.get(Drive, operation.drive_id)
        decision = (
            await session.execute(
                select(ApprovalDecision).where(
                    ApprovalDecision.proposal_id == operation.proposal_id
                )
            )
        ).scalar_one_or_none()
        reviewer = (
            await session.get(Membership, decision.decided_by_membership_id) if decision else None
        )
        if (
            not proposal
            or not connection
            or not drive
            or not decision
            or not reviewer
            or not reviewer.is_active
            or "proposal:decide" not in reviewer.capabilities
            or proposal.state != "approved"
            or decision.decision != "approved"
            or proposal.canonical_hash != operation.dependency_fingerprint
            or connection.status != "active"
            or connection.connection_revision != operation.connection_revision
            or drive.operational_hold
            or drive.status in {"cancelled", "archived"}
            or (proposal.execution_expires_at and proposal.execution_expires_at <= now)
        ):
            operation.status = "stale"
            operation.completed_at = now
            operation.last_error_code = "AUTHORIZATION_OR_DEPENDENCY_STALE"
            await session.commit()
            return "stale"
        operation.status = "claimed"
        operation.claimed_at = now
        operation.lease_expires_at = now + timedelta(seconds=60)
        operation.attempt_count += 1
        attempt = IntegrationAttempt(
            institution_id=institution_id,
            operation_id=operation.id,
            attempt_number=operation.attempt_count,
            status="started",
            started_at=now,
        )
        session.add(attempt)
        await session.commit()

    # Provider call happens without a database lock.
    try:
        async with async_session_maker() as token_session:
            token_session.info["institution_id"] = str(institution_id)
            connection = await token_session.get(IntegrationConnection, operation.connection_id)
            if not connection:
                raise GoogleGatewayError(
                    "GOOGLE_CONNECTION_MISSING", "Google connection no longer exists"
                )
            access_token = await valid_access_token(token_session, connection)
        provider = gateway or get_google_gateway(access_token)
        payload = operation.exact_payload
        if operation.operation_kind == "sheets_export_write":
            result = await provider.write_sheet(
                payload["spreadsheet_id"], payload["target_range"], payload["values"]
            )
            local_type = "drive_report_revision"
            local_id = uuid.UUID(payload["report_id"])
            provider_type = "google_sheet_range"
            fingerprint = payload["values_hash"]
        elif operation.operation_kind == "calendar_event_upsert":
            local_type = "session_revision"
            local_id = uuid.UUID(payload["session_revision_id"])
            existing_mapping = None
            async with async_session_maker() as mapping_session:
                mapping_session.info["institution_id"] = str(institution_id)
                existing_mapping = (
                    await mapping_session.execute(
                        select(ProviderResourceMapping).where(
                            ProviderResourceMapping.connection_id == operation.connection_id,
                            ProviderResourceMapping.local_resource_type == local_type,
                            ProviderResourceMapping.local_resource_id == local_id,
                        )
                    )
                ).scalar_one_or_none()
            result = await provider.upsert_calendar_event(
                payload["calendar_id"],
                existing_mapping.provider_resource_id if existing_mapping else payload["event_id"],
                payload["event"],
                payload["send_updates"],
                existing_mapping.provider_version if existing_mapping else None,
            )
            provider_type = "google_calendar_event"
            fingerprint = payload["event_hash"]
        else:
            raise GoogleGatewayError(
                "INTEGRATION_KIND_UNSUPPORTED", "Unsupported integration operation"
            )
    except GoogleGatewayError as exc:
        async with async_session_maker() as failure_session:
            failure_session.info["institution_id"] = str(institution_id)
            current = await failure_session.get(IntegrationOperation, operation_id)
            if not current:
                return "not_found"
            current_attempt = (
                await failure_session.execute(
                    select(IntegrationAttempt).where(
                        IntegrationAttempt.operation_id == operation_id,
                        IntegrationAttempt.attempt_number == operation.attempt_count,
                    )
                )
            ).scalar_one()
            current_attempt.completed_at = datetime.now(UTC)
            current_attempt.error_code = exc.code
            current_attempt.error_detail = str(exc)[:1000]
            current_attempt.provider_request_id = exc.request_id
            current.last_error_code = exc.code
            current.last_error_detail = str(exc)[:1000]
            if exc.uncertain:
                current.status = "unknown"
                current_attempt.status = "unknown"
                current.completed_at = datetime.now(UTC)
            elif exc.retryable and current.attempt_count < 3:
                current.status = "queued"
                current_attempt.status = "failed_retryable"
                retry_outbox = (
                    await failure_session.execute(
                        select(OutboxEvent).where(
                            OutboxEvent.aggregate_type == "integration_operation",
                            OutboxEvent.aggregate_id == operation_id,
                        )
                    )
                ).scalar_one()
                retry_outbox.status = "pending"
                retry_outbox.next_attempt_at = datetime.now(UTC) + timedelta(
                    seconds=2**current.attempt_count
                )
            else:
                current.status = "failed"
                current_attempt.status = "failed"
                current.completed_at = datetime.now(UTC)
            await failure_session.commit()
            return current.status

    async with async_session_maker() as success_session:
        success_session.info["institution_id"] = str(institution_id)
        current = await success_session.get(IntegrationOperation, operation_id)
        if not current:
            return "not_found"
        current_attempt = (
            await success_session.execute(
                select(IntegrationAttempt).where(
                    IntegrationAttempt.operation_id == operation_id,
                    IntegrationAttempt.attempt_number == operation.attempt_count,
                )
            )
        ).scalar_one()
        current.status = "succeeded"
        current.completed_at = datetime.now(UTC)
        current.provider_resource_id = result.resource_id
        current.provider_version = result.provider_version
        current.last_error_code = None
        current.last_error_detail = None
        current_attempt.status = "succeeded"
        current_attempt.completed_at = datetime.now(UTC)
        current_attempt.provider_request_id = result.request_id
        current_attempt.provider_evidence = result.evidence
        mapping = (
            await success_session.execute(
                select(ProviderResourceMapping).where(
                    ProviderResourceMapping.connection_id == current.connection_id,
                    ProviderResourceMapping.local_resource_type == local_type,
                    ProviderResourceMapping.local_resource_id == local_id,
                )
            )
        ).scalar_one_or_none()
        if mapping:
            mapping.provider_resource_id = result.resource_id
            mapping.provider_version = result.provider_version
            mapping.sync_fingerprint = fingerprint
            mapping.status = "current"
        else:
            success_session.add(
                ProviderResourceMapping(
                    institution_id=institution_id,
                    connection_id=current.connection_id,
                    local_resource_type=local_type,
                    local_resource_id=local_id,
                    provider_resource_type=provider_type,
                    provider_resource_id=result.resource_id,
                    provider_version=result.provider_version,
                    sync_fingerprint=fingerprint,
                )
            )
        completed_outbox = (
            await success_session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.aggregate_type == "integration_operation",
                    OutboxEvent.aggregate_id == operation_id,
                )
            )
        ).scalar_one_or_none()
        if completed_outbox:
            completed_outbox.status = "processed"
        await success_session.commit()
    return "succeeded"
