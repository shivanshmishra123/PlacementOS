"""PlacementOS FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from placementos.api.v1.health import router as health_router
from placementos.api.v1.router import api_v1_router
from placementos.core.config import settings
from placementos.core.errors import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
)
from placementos.core.security import BrowserWriteProtectionMiddleware, CorrelationIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan lifecycle hooks."""
    # Startup: initialize connections if needed
    yield
    # Shutdown: clean up resources


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="PlacementOS API",
        description="Campus recruitment operations platform API.",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 1. Register Core Security & Observability Middlewares
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(BrowserWriteProtectionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Global Exception Handlers for Architecture Envelope
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 3. Mount Routers
    # Direct liveness/readiness probes at root
    app.include_router(health_router)
    # API v1 versioned endpoints
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
