"""
app/errors.py — Application error hierarchy and RFC 7807 exception handlers.

All API error responses conform to RFC 7807 (application/problem+json) with:
    type, title, status, detail, request_id

Secret values are never included in any error response body.
The 500 handler logs the full traceback server-side but returns a generic message
to the client.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"


# ---------------------------------------------------------------------------
# AppError hierarchy
# ---------------------------------------------------------------------------


class AppError(Exception):
    """Base class for all application-level errors.

    Subclasses map to specific HTTP status codes via the registered handler.
    """

    status_code: int = 500
    title: str = "Internal Server Error"
    type_uri: str = "about:blank"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    """The requested resource does not exist."""

    status_code = 404
    title = "Not Found"
    type_uri = "urn:revivepay:error:not-found"


class ConflictError(AppError):
    """The request conflicts with existing state (e.g., duplicate idempotency key)."""

    status_code = 409
    title = "Conflict"
    type_uri = "urn:revivepay:error:conflict"


class PolicyViolationError(AppError):
    """The policy kernel rejected the action."""

    status_code = 403
    title = "Policy Violation"
    type_uri = "urn:revivepay:error:policy-violation"


class ValidationFailedError(AppError):
    """Domain-level validation failed (distinct from HTTP request validation)."""

    status_code = 422
    title = "Validation Failed"
    type_uri = "urn:revivepay:error:validation-failed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_request_id(request: Request) -> str:
    """Extract the request ID from the response headers set by middleware."""
    return request.headers.get("X-Request-Id", "unknown")


def _problem_response(
    *,
    status: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    request_id: str = "unknown",
    extra: dict[str, object] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail,
        "request_id": request_id,
    }
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status,
        content=body,
        media_type=PROBLEM_MEDIA_TYPE,
    )


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle AppError subclasses, mapping them to appropriate HTTP status codes."""
    assert isinstance(exc, AppError)
    return _problem_response(
        status=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        type_uri=exc.type_uri,
        request_id=_get_request_id(request),
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle FastAPI/Pydantic request validation errors as 422 problem+json.

    The field-level errors from Pydantic are included so the caller can identify
    exactly which field failed validation. No secret values are present in these
    messages (they come from request bodies/query params, not from settings).
    """
    assert isinstance(exc, RequestValidationError)
    errors = exc.errors()
    # Each error has loc, msg, type. We format them into a readable list.
    field_errors = [
        {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"], "type": e["type"]}
        for e in errors
    ]
    return _problem_response(
        status=422,
        title="Request Validation Error",
        detail=f"{len(field_errors)} field error(s) in the request.",
        type_uri="urn:revivepay:error:request-validation",
        request_id=_get_request_id(request),
        extra={"errors": field_errors},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all 500 handler.

    Logs the full traceback server-side (never to the client). Returns a
    generic error body with no internal details or secret values.
    """
    request_id = _get_request_id(request)
    logger.error(
        "unhandled_exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
    )
    return _problem_response(
        status=500,
        title="Internal Server Error",
        detail="An unexpected error occurred. Please try again or contact support.",
        type_uri="urn:revivepay:error:internal",
        request_id=request_id,
    )
