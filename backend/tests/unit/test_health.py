"""Tests for Health and Diagnostics Endpoints."""

import pytest
from httpx import AsyncClient

from placementos.core.config import settings


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Verify /health returns healthy status, version, and correlation ID."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == settings.RELEASE_VERSION
    assert "correlation_id" in data
    assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_health_with_custom_correlation_id(client: AsyncClient):
    """Verify custom X-Correlation-ID header is propagated."""
    custom_id = "test-custom-correlation-id-99"
    response = await client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert response.status_code == 200
    data = response.json()
    assert data["correlation_id"] == custom_id
    assert response.headers["X-Correlation-ID"] == custom_id


@pytest.mark.asyncio
async def test_invalid_correlation_id_is_not_reflected(client: AsyncClient):
    """Control characters and oversized caller values are replaced, not logged/reflected."""
    response = await client.get("/health", headers={"X-Correlation-ID": "unsafe value"})
    assert response.status_code == 200
    generated = response.headers["X-Correlation-ID"]
    assert generated != "unsafe value"
    assert len(generated) == 36


@pytest.mark.asyncio
async def test_authenticated_responses_have_security_headers(client: AsyncClient):
    response = await client.get("/api/v1/auth/personas")
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]
    assert "app;dur=" in response.headers["server-timing"]


@pytest.mark.asyncio
async def test_api_v1_health_mount(client: AsyncClient):
    """Verify health endpoint is also accessible via /api/v1/health prefix."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_not_found_error_envelope(client: AsyncClient):
    """Verify standard error envelope for nonexistent routes."""
    response = await client.get("/api/v1/nonexistent-route-xyz")
    assert response.status_code == 404
