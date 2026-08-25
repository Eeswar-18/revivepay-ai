"""
app/models/other.py — Other models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Uuid
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


class ContactLedgerEntry(Base):
    """Contact ledger entry."""

    __tablename__ = "contact_ledger"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"))
    channel: Mapped[str] = mapped_column(String(50))  # email|sms|whatsapp
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"))
    action_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("actions.id"))
