"""
app/repositories/transactions.py — Transaction aggregate repository.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transactions import Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Transaction lookup helpers."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Transaction)

    def get_failed_since(self, timestamp: datetime) -> list[Transaction]:
        """Return transactions with status ``failed`` created at or after ``timestamp``."""
        stmt = (
            select(Transaction)
            .where(
                Transaction.status == "failed",
                Transaction.created_at >= timestamp,
            )
            .order_by(Transaction.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def get_by_merchant(self, merchant_id: uuid.UUID, *, limit: int = 100) -> list[Transaction]:
        """Return transactions for a merchant, newest first."""
        stmt = (
            select(Transaction)
            .where(Transaction.merchant_id == merchant_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())
