"""P10 release-gate checks for operational projections and capability boundaries."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_coordinator_can_inspect_honest_synthetic_readiness(client: AsyncClient):
    login = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    assert login.status_code == 200

    response = await client.get("/api/v1/operations/pilot-readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "synthetic_demo_only"
    assert payload["real_data_pilot_ready"] is False
    assert payload["synthetic_demo_ready"] is True
    assert "oidc_identity" in payload["blockers"]
    serialized = response.text.lower()
    assert "secret_key" not in serialized
    assert "smtp_password" not in serialized
    assert "s3_secret_access_key" not in serialized


@pytest.mark.asyncio
async def test_operational_health_is_aggregate_and_student_is_denied(client: AsyncClient):
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    response = await client.get("/api/v1/operations/health")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "generated_at",
        "outbox",
        "dispatch",
        "jobs",
        "workflows",
        "approvals",
        "exception_cases",
        "alerts",
    }
    serialized = response.text.lower()
    for forbidden in ("recipient", "message_body", "document_text", "smtp_password", "object_key"):
        assert forbidden not in serialized

    await client.post("/api/v1/auth/dev-login", json={"persona": "student_a_apex"})
    denied = await client.get("/api/v1/operations/health")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"
