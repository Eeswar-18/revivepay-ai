"""
app/models/model_versions.py — Model version models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class ModelVersion(Base):
    """A model version."""

    __tablename__ = "model_versions"

    version: Mapped[str] = mapped_column(String(50), primary_key=True)
    kind: Mapped[str] = mapped_column(String(50))  # risk_model|calibrator
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    training_rows: Mapped[int] = mapped_column(BigInteger)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    artifact_path: Mapped[str] = mapped_column(String)
    feature_version: Mapped[str] = mapped_column(String(50))
