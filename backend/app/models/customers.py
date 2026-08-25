"""
app/models/customers.py — Customer models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class Customer(Base):
    """A customer entity."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id"))
    email_hash: Mapped[str] = mapped_column(String(64))
    phone_hash: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    lifetime_txn_count: Mapped[int] = mapped_column(default=0)
    lifetime_success_rate: Mapped[float] = mapped_column()
    prior_recovery_successes: Mapped[int] = mapped_column(default=0)
    prior_declines: Mapped[int] = mapped_column(default=0)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mandate_active: Mapped[bool] = mapped_column(Boolean, default=False)
    mandate_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preferred_method: Mapped[str] = mapped_column(String(50))
    consented_instruments_json: Mapped[dict[str, Any]] = mapped_column(JSON)
