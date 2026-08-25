"""
app/repositories/outcomes.py — Outcome aggregate repository.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.outcomes import Outcome
from app.repositories.base import BaseRepository


class OutcomeRepository(BaseRepository[Outcome]):
    """Outcome recording and lookup."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Outcome)

    def record(self, outcome: Outcome) -> Outcome:
        """Persist an outcome row."""
        return self.add(outcome)

    def get_for_action(self, action_id: uuid.UUID) -> Outcome | None:
        """Return the outcome linked to ``action_id``, if any."""
        stmt = select(Outcome).where(Outcome.action_id == action_id).limit(1)
        return self._session.scalars(stmt).first()
