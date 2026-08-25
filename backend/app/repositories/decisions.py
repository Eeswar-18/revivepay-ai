"""
app/repositories/decisions.py — Decision aggregate repository.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.decisions import Decision
from app.repositories.base import BaseRepository


class DecisionRepository(BaseRepository[Decision]):
    """Decision queries scoped to a case."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Decision)

    def get_latest_for_case(self, case_id: uuid.UUID) -> Decision | None:
        """Return the highest-seq decision for ``case_id``, if any."""
        stmt = (
            select(Decision)
            .where(Decision.case_id == case_id)
            .order_by(Decision.seq.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def list_for_case(self, case_id: uuid.UUID) -> list[Decision]:
        """Return all decisions for ``case_id`` in ascending sequence order."""
        stmt = select(Decision).where(Decision.case_id == case_id).order_by(Decision.seq.asc())
        return list(self._session.scalars(stmt).all())
