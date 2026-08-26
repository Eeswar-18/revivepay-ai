"""
app/models/transactions.py — Transaction models.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow


class Transaction(Base):
    """A transaction entity."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("merchants.id"))
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    payment_method: Mapped[str] = mapped_column(String(50))  # card|upi|netbanking|wallet|emandate
    # Payment rail, one of app.models.enums.Rail (RAIL_A|RAIL_B|RAIL_UPI|RAIL_NETBANKING).
    # Distinct from payment_method: card traffic splits across RAIL_A and RAIL_B, and
    # without that split ActionType.RETRY_ALTERNATE_RAIL would be meaningless for the
    # largest slice of volume. Rail-specific downtime windows are keyed by these ids.
    rail: Mapped[str] = mapped_column(String(50))
    card_network: Mapped[str | None] = mapped_column(String(50), nullable=True)
    issuer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50)
    )  # created|authorized|captured|failed|refunded|disputed
    failure_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_message_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_no: Mapped[int] = mapped_column()
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_cycle: Mapped[str | None] = mapped_column(String(50), nullable=True)
    checkout_stage: Mapped[str] = mapped_column(String(50))
    device: Mapped[str] = mapped_column(String(50))
    original_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id"), nullable=True
    )
    is_test: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (CheckConstraint("amount_minor >= 0", name="check_amount_minor_positive"),)
