"""
app/repositories/errors.py — Domain exceptions raised by repositories.

Callers never see raw SQLAlchemy exceptions from the repository layer.
"""

from __future__ import annotations

import uuid


class NotFoundError(Exception):
    """The requested entity does not exist."""

    def __init__(self, message: str, *, entity: str | None = None, entity_id: object = None) -> None:
        super().__init__(message)
        self.entity = entity
        self.entity_id = entity_id


class ConflictError(Exception):
    """A uniqueness or concurrency conflict (e.g. duplicate idempotency key)."""

    def __init__(self, message: str, *, existing_id: uuid.UUID) -> None:
        super().__init__(message)
        self.existing_id = existing_id


class IllegalStateTransition(Exception):
    """A Case state transition that is not permitted by the lifecycle machine."""

    def __init__(
        self,
        message: str,
        *,
        case_id: uuid.UUID,
        from_state: str,
        to_state: str,
    ) -> None:
        super().__init__(message)
        self.case_id = case_id
        self.from_state = from_state
        self.to_state = to_state
