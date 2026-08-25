"""
app/models/actions.py — Action models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class Action(Base):
    """An action entity."""

    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"))
    decision_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("decisions.id"))
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    action_type: Mapped[str] = mapped_column(String(50))
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    adapter: Mapped[str] = mapped_column(String(50))  # simulated|razorpay_test
    state: Mapped[str] = mapped_column(
        String(50)
    )  # pending|executing|executed|failed|cancelled|superseded
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_no: Mapped[int] = mapped_column()
    cost_minor: Mapped[int] = mapped_column(BigInteger)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
