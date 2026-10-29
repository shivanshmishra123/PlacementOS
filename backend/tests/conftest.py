"""Global Pytest Fixtures for Backend Testing."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from placementos.core.config import settings
from placementos.main import app


@pytest.fixture
async def client():
    """Async HTTP test client bound to FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async def attach_csrf(request):
            if request.method not in {"GET", "HEAD", "OPTIONS", "TRACE"}:
                token = ac.cookies.get("csrf_token")
                if token:
                    request.headers["X-CSRF-Token"] = token

        ac.event_hooks["request"].append(attach_csrf)
        yield ac


@pytest.fixture
async def admin_db_session():
    """Privileged fixture setup session; application tests still use the RLS runtime role."""
    engine = create_async_engine(settings.MIGRATION_DATABASE_URL)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        try:
            yield session
            await session.rollback()
        finally:
            await session.close()
    await engine.dispose()
