"""PlacementOS Standardized Error Handling and Envelope."""

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Inner error payload adhering to Architecture.md Section 9.3."""

    code: str = Field(..., description="Machine-readable uppercase error code.")
    message: str = Field(..., description="Human-readable error explanation.")
    correlation_id: str | None = Field(default=None, description="Request correlation identifier.")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured contextual error details.")


class ErrorResponse(BaseModel):
    """Top-level error response envelope."""

    error: ErrorDetail


class AppException(Exception):
    """Base application exception with machine-readable code and status."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(code="NOT_FOUND", message=message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required", details: dict[str, Any] | None = None):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access forbidden", details: dict[str, Any] | None = None):
        super().__init__(code="FORBIDDEN", message=message, status_code=status.HTTP_403_FORBIDDEN, details=details)


class ConflictError(AppException):
    def __init__(self, code: str = "CONFLICT", message: str = "Resource conflict", details: dict[str, Any] | None = None):
        super().__init__(code=code, message=message, status_code=status.HTTP_409_CONFLICT, details=details)


class ProposalStaleError(ConflictError):
    def __init__(self, message: str = "Action proposal is stale due to changed dependencies", details: dict[str, Any] | None = None):
        super().__init__(code="PROPOSAL_STALE", message=message, details=details)


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request", details: dict[str, Any] | None = None):
        super().__init__(code="BAD_REQUEST", message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class PreconditionFailedError(AppException):
    def __init__(self, message: str = "Precondition failed", details: dict[str, Any] | None = None):
        super().__init__(code="PRECONDITION_FAILED", message=message, status_code=status.HTTP_412_PRECONDITION_FAILED, details=details)


# Convenient aliases
NotFoundError = NotFoundError
UnauthorizedException = UnauthorizedError
ForbiddenException = ForbiddenError
NotFoundException = NotFoundError
ConflictException = ConflictError
BadRequestException = BadRequestError


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Serialize AppException into standard ErrorResponse envelope."""
    correlation_id = getattr(request.state, "correlation_id", None)
    payload = ErrorResponse(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
            details=exc.details,
        )
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unexpected server errors."""
    correlation_id = getattr(request.state, "correlation_id", None)
    payload = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            correlation_id=correlation_id,
            details={},
        )
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())
