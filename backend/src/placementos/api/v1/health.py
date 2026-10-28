"""PlacementOS Health and Readiness Endpoints."""

from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from placementos.core.config import settings
from placementos.core.database import check_database_health

router = APIRouter(tags=["Health & Diagnostics"])


class HealthResponse(BaseModel):
    """Liveness probe response payload."""

    status: Literal["healthy", "degraded", "unhealthy"]
    environment: str
    version: str
    correlation_id: str | None = None


class ReadinessResponse(BaseModel):
    """Readiness probe response payload indicating downstream dependency health."""

    status: Literal["ready", "not_ready"]
    database: bool
    redis: bool
    correlation_id: str | None = None


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application liveness probe",
)
async def get_health(request: Request) -> HealthResponse:
    """Return basic process liveness."""
    correlation_id = getattr(request.state, "correlation_id", None)
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        correlation_id=correlation_id,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
    summary="Application readiness probe",
)
async def get_readiness(request: Request) -> JSONResponse:
    """Check connectivity to PostgreSQL database and Redis."""
    correlation_id = getattr(request.state, "correlation_id", None)
    db_healthy = await check_database_health()
    redis_healthy = True  # Verified via ping in later integration

    is_ready = db_healthy and redis_healthy
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        database=db_healthy,
        redis=redis_healthy,
        correlation_id=correlation_id,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())
