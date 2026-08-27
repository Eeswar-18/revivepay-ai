"""
app/models/cases.py — Case models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import utcnow

if TYPE_CHECKING:
    from app.models.customers import Customer
    from app.models.merchants import Merchant


class Case(Base):
    """A case entity."""

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id"), nullable=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id"))
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"))
    case_type: Mapped[str] = mapped_column(
        String(50)
    )  # failed_payment|abandoned_checkout|subscription_dunning|instrument_expiry
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amount_at_risk_minor: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(String(50))  # CaseState
    attempts_used: Mapped[int] = mapped_column(default=0)
    priority_score: Mapped[float] = mapped_column()
    expected_net_value_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    recovery_deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recovered_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    simulation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )  # simulation_runs FK

    # Relationships
    customer: Mapped[Customer] = relationship()
    merchant: Mapped[Merchant] = relationship()

    __table_args__ = (
        CheckConstraint("amount_at_risk_minor >= 0", name="check_amount_at_risk_positive"),
        CheckConstraint("recovered_amount_minor >= 0", name="check_recovered_amount_positive"),
    )
