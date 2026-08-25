"""
app/models/outcomes.py — Outcome models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class Outcome(Base):
    """An outcome entity."""

    __tablename__ = "outcomes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    action_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("actions.id"), unique=True)
    success: Mapped[bool] = mapped_column(Boolean)
    amount_recovered_minor: Mapped[int] = mapped_column(BigInteger)
    customer_reaction: Mapped[str] = mapped_column(
        String(50)
    )  # none|declined|unsubscribed|complaint
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    env_version: Mapped[str] = mapped_column(String(50))
    env_seed: Mapped[int] = mapped_column()
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"))
