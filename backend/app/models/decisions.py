"""
app/models/decisions.py — Decision models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class Decision(Base):
    """A decision entity (merged Proposal and PolicyVerdict)."""

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"))
    seq: Mapped[int] = mapped_column()  # 1-based per case
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    feature_version: Mapped[str] = mapped_column(String(50))
    risk_model_version: Mapped[str] = mapped_column(String(50))
    p_calibrated: Mapped[float] = mapped_column()
    candidate_scores_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    llm_provider: Mapped[str] = mapped_column(String(50))
    llm_model: Mapped[str] = mapped_column(String(50))
    prompt_version: Mapped[str] = mapped_column(String(50))
    prompt_hash: Mapped[str] = mapped_column(String(64))
    raw_llm_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposal_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    llm_confidence: Mapped[float | None] = mapped_column(nullable=True)
    llm_self_probability: Mapped[float | None] = mapped_column(nullable=True)
    validation_status: Mapped[str] = mapped_column(String(50))  # valid|repaired|invalid|skipped
    validation_errors_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    policy_version: Mapped[str] = mapped_column(String(50))
    policy_verdict: Mapped[str] = mapped_column(String(50))  # approve|modify|block|escalate
    applied_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    violated_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    chosen_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    chosen_params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    expected_net_value_minor: Mapped[int] = mapped_column(BigInteger)
    decision_latency_ms: Mapped[int] = mapped_column()
    seed: Mapped[int] = mapped_column()
    fallback_used: Mapped[bool] = mapped_column()
