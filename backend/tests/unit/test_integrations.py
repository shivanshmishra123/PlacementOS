"""Pure P11 connector boundary tests."""

import base64
import uuid

import pytest
from cryptography.exceptions import InvalidTag

from placementos.core.errors import NotFoundException
from placementos.services.integrations import (
    FEATURE_SCOPES,
    TokenCipher,
    _sheet_fingerprint,
    _sheet_to_csv,
    build_webhook_channel_id,
    verified_webhook_institution,
)


def test_token_cipher_round_trip_and_random_nonce() -> None:
    cipher = TokenCipher()
    first = cipher.encrypt("secret-refresh-token")
    second = cipher.encrypt("secret-refresh-token")
    assert first != second
    assert "secret-refresh-token" not in first
    assert cipher.decrypt(first) == "secret-refresh-token"


def test_token_cipher_rejects_tampering() -> None:
    cipher = TokenCipher()
    envelope = bytearray(base64.urlsafe_b64decode(cipher.encrypt("token")))
    envelope[-1] ^= 1
    with pytest.raises(InvalidTag):
        cipher.decrypt(base64.urlsafe_b64encode(envelope).decode())


def test_google_feature_scopes_are_narrow_and_separate() -> None:
    assert FEATURE_SCOPES["gmail_intake"] == {"https://www.googleapis.com/auth/gmail.readonly"}
    assert "https://mail.google.com/" not in FEATURE_SCOPES["gmail_intake"]
    assert FEATURE_SCOPES["sheets_import"] != FEATURE_SCOPES["sheets_export"]
    assert FEATURE_SCOPES["calendar_events"] == {
        "https://www.googleapis.com/auth/calendar.events.owned"
    }


def test_sheet_mapping_is_deterministic_and_preserves_unknown_backlog() -> None:
    values = [
        ["Roll No", "Name", "College Email", "Department", "CGPA", "Batch", "Backlogs"],
        ["A-001", "A Student", "a@example.edu", "CSE", "8.20", "2027", ""],
    ]
    csv_text, identifiers = _sheet_to_csv(values, {})
    assert identifiers == ["A-001"]
    assert "student_identifier" in csv_text
    assert "A-001" in csv_text
    assert _sheet_fingerprint(values, "sheet-1", "Roster!A:G") == _sheet_fingerprint(
        values, "sheet-1", "Roster!A:G"
    )


def test_webhook_channel_id_is_signed_before_tenant_scope_resolution() -> None:
    institution_id = uuid.uuid4()
    channel_id = build_webhook_channel_id(institution_id)
    assert verified_webhook_institution(channel_id) == institution_id
    with pytest.raises(NotFoundException):
        verified_webhook_institution(channel_id[:-1] + ("0" if channel_id[-1] != "0" else "1"))
