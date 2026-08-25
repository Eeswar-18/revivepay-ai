"""
app/models/metadata.py — Metadata models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class PolicyVersion(Base):
    """A policy version."""

    __tablename__ = "policy_versions"

    version: Mapped[str] = mapped_column(String(50), primary_key=True)
    yaml_text: Mapped[str] = mapped_column(String)
    hash: Mapped[str] = mapped_column(String(64))
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str] = mapped_column(String)


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


class SimulationRun(Base):
    """A simulation run."""

    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    mode: Mapped[str] = mapped_column(String(50))
    seed: Mapped[int] = mapped_column()
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    n_cases: Mapped[int] = mapped_column()
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    world_config_hash: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(50))
    prompt_version: Mapped[str] = mapped_column(String(50))
    git_sha: Mapped[str] = mapped_column(String(40))
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50))  # running|completed|failed
