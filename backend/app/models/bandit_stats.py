"""
app/models/bandit_stats.py — Bandit statistics models.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class BanditStat(Base):
    """Bandit statistics."""

    __tablename__ = "bandit_stats"

    cell_key: Mapped[str] = mapped_column(
        String(100), primary_key=True
    )  # format "failure_class:action_type"
    alpha: Mapped[float] = mapped_column()
    beta: Mapped[float] = mapped_column()
    n: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
