"""
app/repositories/actions.py — Action aggregate repository.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.actions import Action
from app.repositories.base import BaseRepository
from app.repositories.errors import ConflictError


class ActionRepository(BaseRepository[Action]):
    """Action persistence with DB-enforced idempotency."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Action)

    def create_idempotent(self, action: Action) -> Action:
        """Insert ``action`` relying on the UNIQUE idempotency_key constraint.

        Does not pre-check with SELECT. On conflict, raises :class:`ConflictError`
        carrying the existing row's id.
        """
        try:
            with self._session.begin_nested():
                self._session.add(action)
                self._session.flush()
        except IntegrityError as exc:
            existing = self._session.scalars(
                select(Action).where(Action.idempotency_key == action.idempotency_key)
            ).first()
            if existing is None:
                raise ConflictError(
                    "Action insert conflict but existing row not found",
                    existing_id=action.id,
                ) from exc
            raise ConflictError(
                f"Action with idempotency_key already exists: {action.idempotency_key}",
                existing_id=existing.id,
            ) from None
        return action
