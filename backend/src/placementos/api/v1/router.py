"""PlacementOS API v1 Master Router."""

from fastapi import APIRouter

from placementos.api.v1.auth import router as auth_router
from placementos.api.v1.drives import router as drives_router
from placementos.api.v1.eligibility import router as eligibility_router
from placementos.api.v1.health import router as health_router
from placementos.api.v1.intelligence import router as intelligence_router
from placementos.api.v1.participation import router as participation_router
from placementos.api.v1.sources import router as sources_router
from placementos.api.v1.students import router as students_router

api_v1_router = APIRouter()

# Mount health & diagnostics endpoints
api_v1_router.include_router(health_router)
# Mount authentication endpoints
api_v1_router.include_router(auth_router)
# Mount student records and corrections endpoints
api_v1_router.include_router(students_router)
# Mount recruitment drives & companies endpoints
api_v1_router.include_router(drives_router)
# Mount source intake, upload sessions & extractions endpoints
api_v1_router.include_router(sources_router)
# Mount P04 JD interpretation, clarification, policy, and approval routes
api_v1_router.include_router(intelligence_router)
# Mount P05 deterministic evaluation and personal explanation routes
api_v1_router.include_router(eligibility_router)
# Mount P06 student documents, publication, readiness, and registration routes
api_v1_router.include_router(participation_router)
