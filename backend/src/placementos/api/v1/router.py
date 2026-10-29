"""PlacementOS API v1 Master Router."""

from fastapi import APIRouter

from placementos.api.v1.auth import router as auth_router
from placementos.api.v1.drives import router as drives_router
from placementos.api.v1.health import router as health_router
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
