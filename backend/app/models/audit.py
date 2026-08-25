"""
app/models/audit.py — Audit log models and hash-chain helpers.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import utcnow

# Genesis previous-hash for the first audit entry (64 hex zeros).
GENESIS_PREV_HASH = "0" * 64


def compute_audit_hash(
    *,
    seq: int,
    prev_hash: str,
    entry_id: uuid.UUID,
    ts: datetime,
    actor: str,
    event_type: str,
    case_id: uuid.UUID | None,
    decision_id: uuid.UUID | None,
    action_id: uuid.UUID | None,
    payload_json: dict[str, object],
) -> str:
    """Return the SHA-256 hex digest for one audit log entry.

    Pure function: same inputs always produce the same hash. Used by
    AuditRepository.append to build the append-only hash chain.
    """
    canonical = {
        "seq": seq,
        "prev_hash": prev_hash,
        "id": str(entry_id),
        "ts": ts.isoformat(),
        "actor": actor,
        "event_type": event_type,
        "case_id": str(case_id) if case_id is not None else None,
        "decision_id": str(decision_id) if decision_id is not None else None,
        "action_id": str(action_id) if action_id is not None else None,
        "payload_json": payload_json,
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class AuditLogEntry(Base):
    """An audit log entry."""

    __tablename__ = "audit_log"

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str] = mapped_column(String(50))  # agent|policy|executor|human|system
    event_type: Mapped[str] = mapped_column(String(50))
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cases.id"), nullable=True)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("decisions.id"), nullable=True
    )
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("actions.id"), nullable=True
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
