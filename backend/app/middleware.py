"""
app/middleware.py — Request-ID tracking and request/response logging middleware.

Every inbound request is assigned a UUID X-Request-Id (accepted from the caller
or generated fresh). The ID is added to the response headers and bound into every
log record emitted during that request's lifetime via a logging.Filter.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-Id"


class _RequestIdFilter(logging.Filter):
    """Inject request_id into every log record produced on this thread/task."""

    def __init__(self, request_id: str) -> None:
        super().__init__()
        self.request_id = request_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self.request_id
        return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that:

    1. Reads X-Request-Id from the inbound request, or generates a UUID4.
    2. Attaches a logging.Filter to the root logger that injects request_id
       into every log record emitted during the request.
    3. Logs the request on entry and the response (method, path, status,
       duration_ms) on exit at INFO level.
    4. Adds X-Request-Id to the response headers.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        log_filter = _RequestIdFilter(request_id)
        root_logger = logging.getLogger()
        root_logger.addFilter(log_filter)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Let exception handlers deal with the error; just record timing.
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "request_error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                },
            )
            raise
        finally:
            root_logger.removeFilter(log_filter)

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "request_complete",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
