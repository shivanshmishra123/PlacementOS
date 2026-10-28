"""Global Pytest Fixtures for Backend Testing."""

import pytest
from httpx import ASGITransport, AsyncClient

from placementos.main import app


@pytest.fixture
async def client():
    """Async HTTP test client bound to FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
