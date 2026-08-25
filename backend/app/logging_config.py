"""
app/logging_config.py — Structured JSON logging configuration.

Uses python-json-logger to emit every log record as a single JSON object.
Call configure_logging() once at application startup (in create_app).
"""

from __future__ import annotations

import logging
import sys
from typing import Literal

from pythonjsonlogger.json import JsonFormatter as _JsonFormatter

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger to emit structured JSON to stdout.

    Args:
        level: One of DEBUG | INFO | WARNING | ERROR | CRITICAL.
               Matches the LOG_LEVEL setting in config.py.
    """
    # Remove any handlers already attached to the root logger (e.g., from
    # uvicorn's default setup) so we don't get duplicate records.
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    formatter = _JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Suppress noisy third-party loggers that are not actionable at INFO.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
