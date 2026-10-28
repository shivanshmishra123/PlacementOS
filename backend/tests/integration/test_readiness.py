"""Integration tests for application readiness and database connectivity."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_readiness_probe_with_database(client: AsyncClient):
    """Verify /ready probe checks live database connectivity and returns ready."""
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] is True
    assert data["redis"] is True
    assert "correlation_id" in data
    assert "X-Correlation-ID" in response.headers
