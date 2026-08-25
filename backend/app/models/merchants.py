"""
app/models/merchants.py — Merchant models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class Merchant(Base):
    """A merchant entity."""

    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    risk_appetite: Mapped[str] = mapped_column(String(50))  # conservative|balanced|aggressive
    max_retries_default: Mapped[int] = mapped_column(default=3)
    contact_budget_per_week: Mapped[int] = mapped_column(BigInteger)  # minor units
    mdr_bps: Mapped[int] = mapped_column()
    autonomous_amount_ceiling_minor: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("contact_budget_per_week >= 0", name="check_budget_positive"),
        CheckConstraint("autonomous_amount_ceiling_minor >= 0", name="check_ceiling_positive"),
    )
