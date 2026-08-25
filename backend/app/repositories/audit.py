"""
app/repositories/audit.py — Append-only hash-chained audit log repository.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import (
    GENESIS_PREV_HASH,
    AuditLogEntry,
    compute_audit_hash,
)
from app.models.base import utcnow
from app.repositories.base import BaseRepository


class AuditEntryPayload(TypedDict, total=False):
    """Fields supplied by callers of :meth:`AuditRepository.append`."""

    id: uuid.UUID
    ts: datetime
    actor: str
    event_type: str
    case_id: uuid.UUID | None
    decision_id: uuid.UUID | None
    action_id: uuid.UUID | None
    payload_json: dict[str, object]


class AuditRepository(BaseRepository[AuditLogEntry]):
    """Gapless, hash-chained audit append."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditLogEntry)

    def append(self, entry_payload: AuditEntryPayload) -> AuditLogEntry:
        """Append one audit entry with prev_hash chaining and gapless seq."""
        max_seq = self._session.scalar(select(func.max(AuditLogEntry.seq)))
        next_seq = 1 if max_seq is None else int(max_seq) + 1

        prev_entry: AuditLogEntry | None = None
        if max_seq is not None:
            prev_entry = self._session.get(AuditLogEntry, max_seq)

        prev_hash = GENESIS_PREV_HASH if prev_entry is None else prev_entry.hash
        entry_id = entry_payload.get("id") or uuid.uuid4()
        ts = entry_payload.get("ts") or utcnow()
        actor = str(entry_payload["actor"])
        event_type = str(entry_payload["event_type"])
        case_id = entry_payload.get("case_id")
        decision_id = entry_payload.get("decision_id")
        action_id = entry_payload.get("action_id")
        payload_json: dict[str, object] = dict(entry_payload.get("payload_json") or {})

        digest = compute_audit_hash(
            seq=next_seq,
            prev_hash=prev_hash,
            entry_id=entry_id,
            ts=ts,
            actor=actor,
            event_type=event_type,
            case_id=case_id,
            decision_id=decision_id,
            action_id=action_id,
            payload_json=payload_json,
        )

        entry = AuditLogEntry(
            seq=next_seq,
            id=entry_id,
            ts=ts,
            actor=actor,
            event_type=event_type,
            case_id=case_id,
            decision_id=decision_id,
            action_id=action_id,
            payload_json=payload_json,
            prev_hash=prev_hash,
            hash=digest,
        )
        self._session.add(entry)
        self._session.flush()
        return entry
