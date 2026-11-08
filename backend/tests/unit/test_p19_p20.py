"""Unit tests for Phase 19 (OIDC, ClamAV, Onboarding) and Phase 20 (Telemetry, Redaction, Preflight)."""

from __future__ import annotations

import base64
import json
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from placementos.core.errors import (
    ConflictException,
    UnauthorizedException,
)
from placementos.core.telemetry import (
    RedactedJsonFormatter,
    TelemetryTracker,
    redact_sensitive_data,
)
from placementos.models.identity import Institution
from placementos.services.oidc import OIDCAdapter
from placementos.services.onboarding import bootstrap_institution
from placementos.services.parsers import MalwareDetectedError, MalwareScanner, ParseError
from placementos.services.scanner import EICAR_MARKER, ClamAVScanner

# ---------------------------------------------------------------------------
# P19: ClamAV Malware Scanner Adapter Tests
# ---------------------------------------------------------------------------


def test_clamav_fast_fails_on_eicar_signature():
    """ClamAVScanner immediately identifies EICAR test signature without network."""
    scanner = ClamAVScanner()
    with pytest.raises(MalwareDetectedError, match="Malware signature detected"):
        scanner.scan_bytes(b"Header data " + EICAR_MARKER + b" trailer data")


def test_clamav_clean_stream_response():
    """ClamAVScanner successfully parses 'stream: OK' as clean."""
    scanner = ClamAVScanner(host="127.0.0.1", port=3310)

    # Mock socket
    mock_sock = MagicMock()
    mock_sock.__enter__.return_value = mock_sock
    mock_sock.recv.side_effect = [b"stream: OK\n", b""]

    with patch("placementos.services.scanner.socket.create_connection", return_value=mock_sock):
        result = scanner.scan_bytes(b"Safe, benign file contents")
        assert result == "clamav_clean"
        assert mock_sock.sendall.called


def test_clamav_infected_stream_response():
    """ClamAVScanner raises MalwareDetectedError when daemon detects malware signature."""
    scanner = ClamAVScanner(host="127.0.0.1", port=3310)

    mock_sock = MagicMock()
    mock_sock.__enter__.return_value = mock_sock
    mock_sock.recv.side_effect = [b"stream: Trojan.Generic.12345 FOUND\n", b""]

    with patch("placementos.services.scanner.socket.create_connection", return_value=mock_sock):
        with pytest.raises(MalwareDetectedError, match="Trojan.Generic.12345"):
            scanner.scan_bytes(b"Simulated malicious payload")


def test_clamav_unavailable_fails_closed():
    """ClamAVScanner raises SCANNER_UNAVAILABLE if connection fails."""
    scanner = ClamAVScanner(host="127.0.0.1", port=3310)

    with patch("placementos.services.scanner.socket.create_connection", side_effect=ConnectionRefusedError("Connection refused")):
        with pytest.raises(ParseError) as exc_info:
            scanner.scan_bytes(b"Some file content")
        assert exc_info.value.code == "SCANNER_UNAVAILABLE"


def test_malware_scanner_integration_clamav_mode(monkeypatch):
    """MalwareScanner routes to ClamAVScanner when MALWARE_SCANNER_MODE is 'clamav'."""
    from placementos.core.config import settings

    monkeypatch.setattr(settings, "MALWARE_SCANNER_MODE", "clamav")

    with patch.object(ClamAVScanner, "scan_bytes", return_value="clamav_clean") as mock_scan:
        res = MalwareScanner.scan(b"File data")
        assert res == "clamav_clean"
        assert mock_scan.called


# ---------------------------------------------------------------------------
# P19: OIDC Identity Adapter Tests
# ---------------------------------------------------------------------------


def _create_mock_jwt(payload: dict) -> str:
    """Helper creating a test JWT token."""
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode("utf-8").rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"{header}.{body}.signature"


def test_oidc_authorization_url_generation():
    """OIDCAdapter correctly formats authorization URL with state, nonce, and scopes."""
    adapter = OIDCAdapter(
        issuer_url="https://auth.apex.edu",
        client_id="placementos-client",
        client_secret="secret-123",
    )
    url = adapter.get_authorization_url(
        redirect_uri="https://placement.apex.edu/callback",
        state="state-abc-123",
        nonce="nonce-xyz-789",
    )
    assert url.startswith("https://auth.apex.edu/protocol/openid-connect/auth?")
    assert "client_id=placementos-client" in url
    assert "state=state-abc-123" in url
    assert "nonce=nonce-xyz-789" in url
    assert "scope=openid+email+profile" in url


def test_oidc_verify_id_token_valid():
    """OIDCAdapter parses valid claims and verifies issuer, audience, and nonce."""
    adapter = OIDCAdapter(
        issuer_url="https://auth.apex.edu",
        client_id="placementos-client",
    )
    payload = {
        "sub": "user-uuid-123",
        "email": "priya.sharma@apex.edu",
        "name": "Priya Sharma",
        "iss": "https://auth.apex.edu",
        "aud": "placementos-client",
        "exp": time.time() + 3600,
        "nonce": "test-nonce",
    }
    token = _create_mock_jwt(payload)
    claims = adapter.verify_id_token(token, expected_nonce="test-nonce")
    assert claims["email"] == "priya.sharma@apex.edu"
    assert claims["name"] == "Priya Sharma"


def test_oidc_verify_id_token_rejects_expired():
    """OIDCAdapter rejects expired ID tokens."""
    adapter = OIDCAdapter(
        issuer_url="https://auth.apex.edu",
        client_id="placementos-client",
    )
    payload = {
        "sub": "user-uuid-123",
        "email": "priya.sharma@apex.edu",
        "iss": "https://auth.apex.edu",
        "aud": "placementos-client",
        "exp": time.time() - 60,  # Expired
    }
    token = _create_mock_jwt(payload)
    with pytest.raises(UnauthorizedException, match="expired"):
        adapter.verify_id_token(token)


def test_oidc_verify_id_token_rejects_mismatched_nonce():
    """OIDCAdapter rejects token when nonce does not match expected value."""
    adapter = OIDCAdapter(
        issuer_url="https://auth.apex.edu",
        client_id="placementos-client",
    )
    payload = {
        "sub": "user-uuid-123",
        "email": "priya.sharma@apex.edu",
        "iss": "https://auth.apex.edu",
        "aud": "placementos-client",
        "exp": time.time() + 3600,
        "nonce": "actual-nonce",
    }
    token = _create_mock_jwt(payload)
    with pytest.raises(UnauthorizedException, match="nonce mismatch"):
        adapter.verify_id_token(token, expected_nonce="different-nonce")


def test_oidc_verify_id_token_rejects_mismatched_audience():
    """OIDCAdapter rejects token when audience does not include client_id."""
    adapter = OIDCAdapter(
        issuer_url="https://auth.apex.edu",
        client_id="placementos-client",
    )
    payload = {
        "sub": "user-uuid-123",
        "email": "priya.sharma@apex.edu",
        "iss": "https://auth.apex.edu",
        "aud": "wrong-client-id",
        "exp": time.time() + 3600,
    }
    token = _create_mock_jwt(payload)
    with pytest.raises(UnauthorizedException, match="audience"):
        adapter.verify_id_token(token)


# ---------------------------------------------------------------------------
# P19: Empty Institution Onboarding Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_institution_clean():
    """bootstrap_institution creates an empty institution with an admin owner without seed data."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    inst, user, mem = await bootstrap_institution(
        mock_session,
        slug="new-university",
        name="New University",
        domain="newuniv.edu",
        admin_email="admin@newuniv.edu",
        admin_name="Dr. Administrator",
    )

    assert inst.slug == "new-university"
    assert inst.domain == "newuniv.edu"
    assert user.email == "admin@newuniv.edu"
    assert mem.role == "institution_admin"
    assert "member:manage" in mem.capabilities
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_bootstrap_institution_rejects_duplicate():
    """bootstrap_institution rejects duplicate slug or domain."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Institution(slug="existing", name="Existing", domain="existing.edu")
    mock_session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(ConflictException, match="already exists"):
        await bootstrap_institution(
            mock_session,
            slug="existing",
            name="Existing",
            domain="existing.edu",
            admin_email="admin@existing.edu",
            admin_name="Dr. Administrator",
        )


# ---------------------------------------------------------------------------
# P20: Observability, Redaction, and Telemetry Tests
# ---------------------------------------------------------------------------


def test_redact_sensitive_keys_and_values():
    """redact_sensitive_data replaces sensitive dictionary keys and auth headers with [REDACTED]."""
    raw_payload = {
        "user_id": "usr-123",
        "api_key": "dummy_test_api_key_sample",
        "password": "super_secret_password",
        "token": "secret_jwt_token_here",
        "authorization_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig",
        "normal_field": "public_text",
        "nested": {
            "client_secret": "sensitive-value",
            "safe_counter": 42,
        },
    }

    cleaned = redact_sensitive_data(raw_payload)

    assert cleaned["user_id"] == "usr-123"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["token"] == "[REDACTED]"
    assert cleaned["authorization_header"] == "[REDACTED]"
    assert cleaned["normal_field"] == "public_text"
    assert cleaned["nested"]["client_secret"] == "[REDACTED]"
    assert cleaned["nested"]["safe_counter"] == 42


def test_redacted_json_formatter():
    """RedactedJsonFormatter produces structured JSON logs without leaking sensitive data."""
    formatter = RedactedJsonFormatter()
    record = logging.LogRecord(
        name="placementos.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Authenticated user with token Bearer abcdef123456",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-uuid-123"

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "placementos.test"
    assert parsed["correlation_id"] == "corr-uuid-123"
    assert "Bearer [REDACTED]" in parsed["message"]
    assert "abcdef123456" not in parsed["message"]


def test_telemetry_tracker_metrics_snapshot():
    """TelemetryTracker computes p50, p95, total calls, and error rates."""
    tracker = TelemetryTracker()

    tracker.record_model_call(1.2, success=True)
    tracker.record_model_call(2.0, success=True)
    tracker.record_model_call(3.5, success=False)
    tracker.record_model_call(0.8, success=True)

    metrics = tracker.get_metrics_snapshot()

    assert metrics["model_calls"]["total"] == 4
    assert metrics["model_calls"]["failed"] == 1
    assert metrics["model_calls"]["error_rate"] == 0.25
    assert metrics["model_calls"]["latency_p50_seconds"] > 0
    assert metrics["model_calls"]["latency_p95_seconds"] >= metrics["model_calls"]["latency_p50_seconds"]
    assert "scanner_status" in metrics
