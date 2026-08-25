"""
app/models/core.py — SQLAlchemy core domain models.

This file defines the relational entities for the RevivePay AI decision pipeline.
It follows the structure described in ARCHITECTURE.md and DECISIONS.md.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import ActionStatus, ActionType, CaseState, OutcomeStatus, PolicyVerdict


def _generate_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _get_utc_now() -> datetime:
    return datetime.now(UTC)


class Case(Base):
    """The central entity tracking a revenue-at-risk event."""

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_generate_uuid)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[CaseState] = mapped_column(
        Enum(CaseState), default=CaseState.DETECTED, index=True
    )

    amount: Mapped[float] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3))
    customer_id: Mapped[str] = mapped_column(String(255), index=True)
    merchant_id: Mapped[str] = mapped_column(String(255), index=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_get_utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_get_utc_now, onupdate=_get_utc_now
    )

    # Relationships
    events: Mapped[list[Event]] = relationship(
        "Event", back_populates="case", cascade="all, delete-orphan"
    )
    proposals: Mapped[list[Proposal]] = relationship(
        "Proposal", back_populates="case", cascade="all, delete-orphan"
    )
    actions: Mapped[list[Action]] = relationship(
        "Action", back_populates="case", cascade="all, delete-orphan"
    )
    outcomes: Mapped[list[Outcome]] = relationship(
        "Outcome", back_populates="case", cascade="all, delete-orphan"
    )
    audit_entries: Mapped[list[AuditEntry]] = relationship(
        "AuditEntry", back_populates="case", cascade="all, delete-orphan"
    )

    __table_args__ = (CheckConstraint("amount >= 0", name="check_case_amount_positive"),)


class Event(Base):
    """Incoming signals (payment failures, etc.) related to a Case."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_generate_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)

    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_get_utc_now)

    # Relationships
    case: Mapped[Case] = relationship("Case", back_populates="events")


class Proposal(Base):
    """An LLM-generated suggestion for a recovery action."""

    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_generate_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)

    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType))
    schedule_offset_hours: Mapped[int] = mapped_column(Integer)
    justification: Mapped[str] = mapped_column(Text)
    feature_citations: Mapped[dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_get_utc_now)

    # Relationships
    case: Mapped[Case] = relationship("Case", back_populates="proposals")
    verdict: Mapped[PolicyVerdictRecord | None] = relationship(
        "PolicyVerdictRecord",
        back_populates="proposal",
        uselist=False,
        cascade="all, delete-orphan",
    )
    action: Mapped[Action | None] = relationship("Action", back_populates="proposal", uselist=False)


class PolicyVerdictRecord(Base):
    """The result of the deterministic policy kernel's evaluation of a proposal."""

    __tablename__ = "policy_verdicts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_generate_uuid)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("proposals.id"), unique=True, index=True
    )

    verdict: Mapped[PolicyVerdict] = mapped_column(Enum(PolicyVerdict))
    rule_name: Mapped[str] = mapped_column(String(255))
    policy_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_get_utc_now)

    # Relationships
    proposal: Mapped[Proposal] = relationship("Proposal", back_populates="verdict")


class Action(Base):
    """A recovery action that has been approved and scheduled for execution."""

    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_generate_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("proposals.id"), index=True)

    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType))
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[ActionStatus] = mapped_column(Enum(ActionStatus), default=ActionStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_get_utc_now)

    # Relationships
    case: Mapped[Case] = relationship("Case", back_populates="actions")
    proposal: Mapped[Proposal] = relationship("Proposal", back_populates="action")
    outcome: Mapped[Outcome | None] = relationship(
        "Outcome", back_populates="action", uselist=False
    )


class Outcome(Base):
    """The final ground-truth result of a recovery attempt or a Case."""

    __tablename__ = "outcomes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_generate_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), index=True)
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("actions.id"), nullable=True, index=True
    )

    status: Mapped[OutcomeStatus] = mapped_column(Enum(OutcomeStatus))
    recovery_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_get_utc_now)

    # Relationships
    case: Mapped[Case] = relationship("Case", back_populates="outcomes")
    action: Mapped[Action | None] = relationship("Action", back_populates="outcome")

    __table_args__ = (
        CheckConstraint("recovery_amount >= 0", name="check_outcome_recovery_amount_positive"),
    )


class AuditEntry(Base):
    """Append-only, hash-chained audit log entry."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_generate_uuid)
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("cases.id"), nullable=True, index=True
    )

    event_name: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    prev_hash: Mapped[str] = mapped_column(String(64), index=True)
    curr_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_get_utc_now)

    # Relationships
    case: Mapped[Case | None] = relationship("Case", back_populates="audit_entries")

    __table_args__ = (Index("idx_audit_case_time", "case_id", "created_at"),)
