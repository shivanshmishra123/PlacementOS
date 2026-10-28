"""PlacementOS API v1 Master Router."""

from fastapi import APIRouter

from placementos.api.v1.auth import router as auth_router
from placementos.api.v1.health import router as health_router
from placementos.api.v1.students import router as students_router

api_v1_router = APIRouter()

# Mount health & diagnostics endpoints
api_v1_router.include_router(health_router)
# Mount authentication endpoints
api_v1_router.include_router(auth_router)
# Mount student records and corrections endpoints
api_v1_router.include_router(students_router)
