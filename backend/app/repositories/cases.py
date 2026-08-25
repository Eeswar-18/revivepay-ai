"""
app/repositories/cases.py — Case aggregate repository.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.enums import CaseState
from app.repositories.base import BaseRepository
from app.repositories.errors import IllegalStateTransition, NotFoundError

# Terminal / inactive states — excluded from get_open_cases.
_CLOSED_LIKE: frozenset[str] = frozenset(
    {
        CaseState.CLOSED,
        CaseState.RECOVERED,
        CaseState.FAILED,
        CaseState.BLOCKED,
        CaseState.EXPIRED,
        CaseState.STOPPED,
    }
)

# Legal transitions from ARCHITECTURE.md case lifecycle state machine.
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    CaseState.DETECTED: frozenset({CaseState.FEATURISED, CaseState.EXPIRED, CaseState.STOPPED}),
    CaseState.FEATURISED: frozenset({CaseState.PROPOSED, CaseState.EXPIRED, CaseState.STOPPED}),
    CaseState.PROPOSED: frozenset(
        {CaseState.APPROVED, CaseState.BLOCKED, CaseState.ESCALATED, CaseState.STOPPED}
    ),
    CaseState.APPROVED: frozenset({CaseState.SCHEDULED, CaseState.BLOCKED, CaseState.STOPPED}),
    CaseState.ESCALATED: frozenset({CaseState.APPROVED, CaseState.BLOCKED, CaseState.STOPPED}),
    CaseState.SCHEDULED: frozenset({CaseState.EXECUTING, CaseState.STOPPED}),
    CaseState.EXECUTING: frozenset({CaseState.AWAITING_OUTCOME, CaseState.FAILED, CaseState.STOPPED}),
    CaseState.AWAITING_OUTCOME: frozenset(
        {CaseState.RECOVERED, CaseState.FAILED, CaseState.EXPIRED, CaseState.STOPPED}
    ),
    CaseState.RECOVERED: frozenset({CaseState.CLOSED}),
    CaseState.FAILED: frozenset({CaseState.CLOSED}),
    CaseState.BLOCKED: frozenset({CaseState.CLOSED}),
    CaseState.EXPIRED: frozenset({CaseState.CLOSED}),
    CaseState.STOPPED: frozenset({CaseState.CLOSED}),
    CaseState.CLOSED: frozenset(),
}


class CaseRepository(BaseRepository[Case]):
    """Case queries and guarded state transitions."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Case)

    def get_open_cases(self, merchant_id: uuid.UUID, limit: int = 100) -> list[Case]:
        """Return non-terminal cases for a merchant, newest first."""
        stmt = (
            select(Case)
            .where(
                Case.merchant_id == merchant_id,
                Case.state.notin_(_CLOSED_LIKE),
            )
            .order_by(Case.detected_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def get_by_transaction(self, transaction_id: uuid.UUID) -> Case | None:
        """Return the case linked to ``transaction_id``, if any."""
        stmt = select(Case).where(Case.transaction_id == transaction_id).limit(1)
        return self._session.scalars(stmt).first()

    def list_by_state(self, state: CaseState | str, *, limit: int = 100) -> list[Case]:
        """Return cases in the given lifecycle state."""
        state_value = state.value if isinstance(state, CaseState) else state
        stmt = select(Case).where(Case.state == state_value).limit(limit)
        return list(self._session.scalars(stmt).all())

    def transition_state(self, case_id: uuid.UUID, new_state: CaseState | str) -> Case:
        """Apply a legal state transition or raise :class:`IllegalStateTransition`."""
        case = self.get(case_id)
        if case is None:
            raise NotFoundError(
                f"Case {case_id} not found",
                entity="Case",
                entity_id=case_id,
            )
        target = new_state.value if isinstance(new_state, CaseState) else new_state
        current = case.state
        allowed = _ALLOWED_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise IllegalStateTransition(
                f"Illegal transition {current} → {target} for case {case_id}",
                case_id=case_id,
                from_state=current,
                to_state=target,
            )
        case.state = target
        self._session.flush()
        return case
