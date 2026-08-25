"""
tests/test_errors.py — Tests for error handling and RFC 7807 response shape.

Each test that needs custom routes builds a small isolated FastAPI app.
All imports are at module level to avoid Python 3.14's stricter scoping rules.
"""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.errors import (
    AppError,
    NotFoundError,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.logging_config import configure_logging
from app.middleware import RequestIdMiddleware


def _make_isolated_app() -> FastAPI:
    """Return a minimal FastAPI app with all RevivePay exception handlers registered."""
    configure_logging("WARNING")
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]
    return app


# ---------------------------------------------------------------------------
# Validation error → 422 problem+json
# ---------------------------------------------------------------------------


def test_validation_error_returns_422(client: TestClient) -> None:
    """A request with an invalid query parameter returns 422 in problem+json shape."""
    app = _make_isolated_app()

    @app.get("/typed")
    def typed_endpoint(count: int = Query(...)) -> dict[str, int]:
        return {"count": count}

    with TestClient(app, raise_server_exceptions=False) as c:
        # Send a string where an int is required.
        resp = c.get("/typed", params={"count": "not-an-integer"})
        assert resp.status_code == 422
        data = resp.json()
        assert data["status"] == 422
        assert "errors" in data
        assert data["title"] == "Request Validation Error"
        assert "application/problem+json" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Unhandled error → 500 without leaking internals
# ---------------------------------------------------------------------------

_SECRET_INTERNAL_MESSAGE = "super-secret-db-password-do-not-leak"


def test_unhandled_error_returns_500_without_leaking(client: TestClient) -> None:
    """An unhandled exception returns 500 and does NOT include the exception message."""
    app = _make_isolated_app()

    @app.get("/boom")
    def boom_endpoint() -> dict[str, str]:
        raise RuntimeError(_SECRET_INTERNAL_MESSAGE)

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/boom")
        assert resp.status_code == 500
        body_text = resp.text
        # The internal exception message must NOT appear in the response.
        assert _SECRET_INTERNAL_MESSAGE not in body_text
        # But a generic error structure must be present.
        data = resp.json()
        assert data["status"] == 500
        assert data["title"] == "Internal Server Error"


# ---------------------------------------------------------------------------
# AppError subclass → correct status code
# ---------------------------------------------------------------------------


def test_app_error_returns_correct_status(client: TestClient) -> None:
    """NotFoundError is mapped to a 404 problem+json response."""
    app = _make_isolated_app()

    @app.get("/missing")
    def missing_endpoint() -> dict[str, str]:
        raise NotFoundError("The requested resource was not found.")

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/missing")
        assert resp.status_code == 404
        data = resp.json()
        assert data["status"] == 404
        assert data["title"] == "Not Found"
        assert "application/problem+json" in resp.headers.get("content-type", "")
