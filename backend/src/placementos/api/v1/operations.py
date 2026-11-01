"""P10 authenticated operational health and pilot-readiness endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.services.operations import operational_snapshot, pilot_readiness_snapshot
from placementos.services.session import AuthContext

router = APIRouter(prefix="/operations", tags=["Operations & pilot readiness"])


@router.get("/pilot-readiness", response_model=dict)
async def get_pilot_readiness(
    auth: AuthContext = Depends(get_current_auth),
) -> dict:
    auth.require_capability("ops:view")
    return pilot_readiness_snapshot(settings)


@router.get("/health", response_model=dict)
async def get_operational_health(
    auth: AuthContext = Depends(get_current_auth),
    session: AsyncSession = Depends(get_db),
) -> dict:
    auth.require_capability("ops:view")
    return await operational_snapshot(session)
