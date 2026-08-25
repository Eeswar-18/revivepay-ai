"""
app/repositories/bandit_stats.py — Bandit statistics repository.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.bandit_stats import BanditStat
from app.models.base import utcnow
from app.repositories.base import BaseRepository


def _cell_key(failure_class: str, intervention: str) -> str:
    return f"{failure_class}:{intervention}"


class BanditStatsRepository(BaseRepository[BanditStat]):
    """Thompson-sampling cell statistics."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, BanditStat)

    def get_or_create(self, failure_class: str, intervention: str) -> BanditStat:
        """Return the bandit cell, creating an uninformative Beta(1,1) prior if needed."""
        key = _cell_key(failure_class, intervention)
        existing = self._session.get(BanditStat, key)
        if existing is not None:
            return existing
        created = BanditStat(cell_key=key, alpha=1.0, beta=1.0, n=0, updated_at=utcnow())
        return self.add(created)

    def update_posterior(
        self,
        failure_class: str,
        intervention: str,
        *,
        success: bool,
    ) -> BanditStat:
        """Update Beta posterior: success increments alpha, failure increments beta."""
        stat = self.get_or_create(failure_class, intervention)
        if success:
            stat.alpha = float(stat.alpha) + 1.0
        else:
            stat.beta = float(stat.beta) + 1.0
        stat.n = int(stat.n) + 1
        stat.updated_at = utcnow()
        self._session.flush()
        return stat
