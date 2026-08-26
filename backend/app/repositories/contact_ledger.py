"""
app/repositories/contact_ledger.py — Contact ledger repository.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.contact_ledger import ContactLedgerEntry
from app.repositories.base import BaseRepository


class ContactLedgerRepository(BaseRepository[ContactLedgerEntry]):
    """Customer contact counting and recording."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ContactLedgerEntry)

    def count_contacts(self, customer_id: uuid.UUID, since: datetime) -> int:
        """Return how many contacts were sent to ``customer_id`` since ``since``."""
        stmt = (
            select(func.count())
            .select_from(ContactLedgerEntry)
            .where(
                ContactLedgerEntry.customer_id == customer_id,
                ContactLedgerEntry.sent_at >= since,
            )
        )
        return int(self._session.scalar(stmt) or 0)

    def record_contact(
        self,
        *,
        customer_id: uuid.UUID,
        channel: str,
        case_id: uuid.UUID,
        action_id: uuid.UUID,
        sent_at: datetime | None = None,
        entry_id: uuid.UUID | None = None,
    ) -> ContactLedgerEntry:
        """Insert a contact ledger row."""
        entry = ContactLedgerEntry(
            id=entry_id or uuid.uuid4(),
            customer_id=customer_id,
            channel=channel,
            sent_at=sent_at or utcnow(),
            case_id=case_id,
            action_id=action_id,
        )
        return self.add(entry)
