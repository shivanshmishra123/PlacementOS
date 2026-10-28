"""Integration tests for session authentication, dev personas, and authorization context (P02-T02 / P02-T03)."""

import pytest
from httpx import AsyncClient

from placementos.core.config import settings


@pytest.mark.asyncio
async def test_list_synthetic_personas(client: AsyncClient):
    """Verify available dev personas are listed in development mode."""
    response = await client.get("/api/v1/auth/personas")
    assert response.status_code == 200
    personas = response.json()
    assert len(personas) >= 4
    keys = [p["key"] for p in personas]
    assert "coord_apex" in keys
    assert "admin_apex" in keys
    assert "coord_beacon" in keys
    assert "student_a_apex" in keys


@pytest.mark.asyncio
async def test_dev_login_and_session_lifecycle(client: AsyncClient):
    """Verify sign in as coordinator, session cookie issuance, /me resolution, and logout revocation."""
    # 1. Dev login as Priya Sharma (Apex coordinator)
    login_resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"persona": "coord_apex"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["user"]["email"] == "priya.sharma@apex.edu"
    assert data["user"]["role"] == "placement_coordinator"
    assert data["user"]["institution_slug"] == "apex-tech"
    assert "drive:create" in data["user"]["capabilities"]
    assert "csrf_token" in data
    assert "session_token" in data

    # Verify session cookie was set
    assert settings.SESSION_COOKIE_NAME in client.cookies
    session_token = data["session_token"]

    # 2. Access /api/v1/auth/me using authenticated cookie
    me_resp = await client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "priya.sharma@apex.edu"
    assert me_data["role"] == "placement_coordinator"
    assert me_data["institution_slug"] == "apex-tech"

    # 3. Test Bearer token header authorization (alternative to cookie)
    bearer_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert bearer_resp.status_code == 200
    assert bearer_resp.json()["email"] == "priya.sharma@apex.edu"

    # 4. Logout / revocation
    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # 5. Verify revoked session cannot access /me
    # Using expired/revoked bearer token
    unauth_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert unauth_resp.status_code == 401
    assert unauth_resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    """Verify protected endpoints reject requests without active session."""
    client.cookies.clear()
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_production_mode_rejects_dev_login(client: AsyncClient, monkeypatch):
    """Verify production mode strictly forbids dev-login (NFR-09 / INV-10)."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"persona": "coord_apex"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
