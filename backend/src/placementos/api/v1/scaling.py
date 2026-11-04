"""P13 tenant operating-policy API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import get_db
from placementos.core.dependencies import require_capability
from placementos.schemas.scaling import OperatingPolicyResponse, OperatingPolicyRevisionCreate
from placementos.services.scaling import current_operating_policy, revise_operating_policy
from placementos.services.session import AuthContext

router = APIRouter(prefix="/institution", tags=["Institution scaling policy"])


@router.get("/operating-policy", response_model=OperatingPolicyResponse)
async def get_operating_policy(
    auth: AuthContext = Depends(require_capability("ops:view")),
    session: AsyncSession = Depends(get_db),
) -> OperatingPolicyResponse:
    return OperatingPolicyResponse.model_validate(
        await current_operating_policy(session, auth.institution_id),
        from_attributes=True,
    )


@router.put("/operating-policy", response_model=OperatingPolicyResponse)
async def update_operating_policy(
    payload: OperatingPolicyRevisionCreate,
    auth: AuthContext = Depends(require_capability("config:manage")),
    session: AsyncSession = Depends(get_db),
) -> OperatingPolicyResponse:
    return OperatingPolicyResponse.model_validate(
        await revise_operating_policy(session, auth, payload),
        from_attributes=True,
    )
