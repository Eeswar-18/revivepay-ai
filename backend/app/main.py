"""
app/main.py — FastAPI application factory and route definitions.

Phase 1 endpoints only: /api/health, /api/version, /api/system/config.
No domain logic, no ML, no LLM calls.

Call create_app() to produce the ASGI application; this is also the entrypoint
for uvicorn:

    uvicorn app.main:app --reload
"""

from __future__ import annotations

import importlib.metadata
import logging
import subprocess
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# API routers
from app.api import cases, customers, decisions, features, merchants
from app.config import Settings, get_settings
from app.core.executor.clock import clock
from app.db import check_db_health, init_db
from app.errors import (
    AppError,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.logging_config import configure_logging
from app.middleware import RequestIdMiddleware

logger = logging.getLogger(__name__)

# Module-level start time for uptime calculation.
_START_TIME = time.monotonic()


def _read_git_sha() -> str | None:
    """Return the current git commit SHA (short), or None if git is unavailable."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=2,
        )
        sha = result.stdout.strip()
        return sha if sha else None
    except Exception:
        return None


def _read_app_version() -> str:
    """Read the package version from pyproject.toml metadata, fallback to '0.1.0'."""
    try:
        return importlib.metadata.version("revivepay-ai-backend")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory.

    Args:
        settings: Optional Settings instance for testing. Defaults to get_settings().

    Returns:
        A configured FastAPI application instance.
    """
    cfg = settings or get_settings()
    configure_logging(cfg.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Startup
        init_db()
        # Start the virtual clock
        clock.start()
        logger.info(
            "application_started",
            extra={
                "app_name": cfg.APP_NAME,
                "version": _read_app_version(),
                "environment": cfg.APP_ENV,
                "llm_provider": cfg.LLM_PROVIDER,
                "virtual_epoch": cfg.VIRTUAL_EPOCH,
                "virtual_clock_rate": cfg.VIRTUAL_CLOCK_RATE,
            },
        )
        yield
        # Shutdown (nothing to clean up in Phase 1)

    app = FastAPI(
        title=cfg.APP_NAME,
        description=(
            "RevivePay AI — autonomous revenue-recovery control plane. "
            "All payment effects are **simulated**. No real money moves."
        ),
        version=_read_app_version(),
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        openapi_tags=[
            {"name": "system", "description": "Health, version, and configuration endpoints."},
        ],
    )

    # ── Middleware (order matters: outermost = first to process) ──────────────
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cfg.FRONTEND_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    # ── Exception handlers ─────────────────────────────────────────────────────
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    # ── Routes ────────────────────────────────────────────────────────────────
    @app.get(
        "/api/health",
        tags=["system"],
        summary="Health check",
        response_description="Service health status",
    )
    def health() -> dict[str, Any]:
        """Return the current health status of the API and its dependencies."""
        db_ok = check_db_health()
        return {
            "status": "ok" if db_ok else "degraded",
            "uptime_seconds": round(time.monotonic() - _START_TIME, 1),
            "database": "ok" if db_ok else "error",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get(
        "/api/version",
        tags=["system"],
        summary="Application version",
        response_description="Version and runtime metadata",
    )
    def version() -> dict[str, Any]:
        """Return version and runtime metadata.

        demo_mode is always true — all payment effects in this system are simulated.
        No production Razorpay integration is active.
        """
        return {
            "app_name": cfg.APP_NAME,
            "version": _read_app_version(),
            "git_sha": _read_git_sha(),
            "llm_provider": cfg.LLM_PROVIDER,
            "environment": cfg.APP_ENV,
            "demo_mode": True,
        }

    @app.get(
        "/api/system/config",
        tags=["system"],
        summary="Redacted configuration",
        response_description="All settings with secrets masked",
    )
    def system_config(request: Request) -> JSONResponse:
        """Return all configuration values with every secret replaced by 'set'/'unset'.

        Secret values are NEVER included. This endpoint is safe to expose to
        authenticated operators for debugging configuration issues.
        """
        _ = request  # available for future auth checks
        return JSONResponse(content=cfg.redacted_summary())

    # Include API routers
    app.include_router(cases.router)
    app.include_router(customers.router)
    app.include_router(merchants.router)
    app.include_router(decisions.router)
    app.include_router(features.router)

    logger.debug("app_created", extra={"frontend_origin": cfg.FRONTEND_ORIGIN})
    return app


# ASGI entry-point for uvicorn.
app = create_app()
