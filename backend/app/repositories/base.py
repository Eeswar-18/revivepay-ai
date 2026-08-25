"""
app/repositories/base.py — Generic BaseRepository for ORM aggregates.
"""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Base
from app.repositories.errors import NotFoundError

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Thin typed CRUD wrapper around a SQLAlchemy model class."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    def add(self, entity: ModelT) -> ModelT:
        """Persist ``entity`` and flush so generated fields are available."""
        self._session.add(entity)
        self._session.flush()
        return entity

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        """Return the entity with the given primary key, or ``None``."""
        return self._session.get(self._model, entity_id)

    def get_or_raise(self, entity_id: uuid.UUID) -> ModelT:
        """Return the entity or raise :class:`NotFoundError`."""
        entity = self.get(entity_id)
        if entity is None:
            raise NotFoundError(
                f"{self._model.__name__} {entity_id} not found",
                entity=self._model.__name__,
                entity_id=entity_id,
            )
        return entity

    def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """Return a page of entities ordered by insertion (primary key)."""
        stmt = select(self._model).limit(limit).offset(offset)
        return list(self._session.scalars(stmt).all())

    def delete(self, entity: ModelT) -> None:
        """Delete ``entity`` and flush."""
        self._session.delete(entity)
        self._session.flush()
