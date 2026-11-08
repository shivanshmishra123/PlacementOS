"""PlacementOS Health and Readiness Endpoints."""

from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from placementos.core.config import settings
from placementos.core.database import check_database_health
from placementos.core.redis import get_redis_client

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
        version=settings.RELEASE_VERSION,
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
    try:
        redis_healthy = bool(await get_redis_client().ping())
    except Exception:
        redis_healthy = False

    is_ready = db_healthy and redis_healthy
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        database=db_healthy,
        redis=redis_healthy,
        correlation_id=correlation_id,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@router.get(
    "/telemetry",
    summary="Platform operational metrics and telemetry",
)
async def get_telemetry(request: Request) -> dict:
    """Return platform operational metrics snapshot without sensitive tenant data (INV-10)."""
    from placementos.core.telemetry import GLOBAL_TELEMETRY

    snapshot = GLOBAL_TELEMETRY.get_metrics_snapshot()
    snapshot["correlation_id"] = getattr(request.state, "correlation_id", None)
    return snapshot


@router.get(
    "/pilot-readiness",
    summary="P21 institutional pilot readiness and signoff gate status",
)
async def get_pilot_readiness(request: Request) -> dict:
    """Return P21-T05 institutional pilot signoff gate status (read-only).

    All six signoff flags must be True and REAL_DATA_ENABLED must be set
    before the platform is permitted to operate with real institutional data.
    This endpoint exposes gate status without disclosing tenant data (INV-10).
    """
    from placementos.core.config import validate_pilot_signoff
    from placementos.services.pilot_readiness import run_security_review

    signoff = validate_pilot_signoff()
    security = run_security_review()

    return {
        "pilot_signoff": signoff,
        "security_review": {
            "total_items": security["total_items"],
            "passed": security["passed"],
            "failed": security["failed"],
            "deferred": security["deferred"],
            "all_critical_items_pass": security["all_critical_items_pass"],
        },
        "shadow_mode_active": not settings.LIVE_SEND_ENABLED
        and not settings.GOOGLE_CONNECTORS_ENABLED,
        "model_interpreter_mode": settings.MODEL_INTERPRETER_MODE,
        "live_send_enabled": settings.LIVE_SEND_ENABLED,
        "google_connectors_enabled": settings.GOOGLE_CONNECTORS_ENABLED,
        "real_data_enabled": settings.REAL_DATA_ENABLED,
        "correlation_id": getattr(request.state, "correlation_id", None),
    }
