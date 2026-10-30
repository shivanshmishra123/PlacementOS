"""PlacementOS API v1 Master Router."""

from fastapi import APIRouter

from placementos.api.v1.auth import router as auth_router
from placementos.api.v1.communications import router as communications_router
from placementos.api.v1.drives import router as drives_router
from placementos.api.v1.eligibility import router as eligibility_router
from placementos.api.v1.health import router as health_router
from placementos.api.v1.intelligence import router as intelligence_router
from placementos.api.v1.lifecycle import router as lifecycle_router
from placementos.api.v1.participation import router as participation_router
from placementos.api.v1.sources import router as sources_router
from placementos.api.v1.students import router as students_router
from placementos.api.v1.workflows import router as workflows_router

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
# Mount P07 immutable communications, approvals, and dispatch routes
api_v1_router.include_router(communications_router)
# Mount P08 durable, human-supervised workflow and exception routes
api_v1_router.include_router(workflows_router)
# Mount P09 scheduling, results, reports, and lifecycle completion routes
api_v1_router.include_router(lifecycle_router)
