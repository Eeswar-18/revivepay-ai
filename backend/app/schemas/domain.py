"""
app/schemas/domain.py — Pydantic v2 schemas for the RevivePay AI domain.

This file defines the validation and serialization schemas for Cases, Events,
Proposals, Actions, and Outcomes. It supports both API interaction and
internal decision pipeline validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActionStatus, ActionType, CaseState, OutcomeStatus, PolicyVerdict


class DomainBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Case ──────────────────────────────────────────────────────────────────


class CaseBase(DomainBase):
    external_id: str = Field(..., max_length=255)
    amount: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    customer_id: str = Field(..., max_length=255)
    merchant_id: str = Field(..., max_length=255)
    expires_at: datetime


class CaseCreate(CaseBase):
    pass


class CaseUpdate(DomainBase):
    status: CaseState | None = None
    expires_at: datetime | None = None


class CaseRead(CaseBase):
    id: uuid.UUID
    status: CaseState
    detected_at: datetime
    last_updated_at: datetime


# ── Event ─────────────────────────────────────────────────────────────────


class EventBase(DomainBase):
    event_type: str = Field(..., max_length=100)
    payload: dict[str, Any]


class EventCreate(EventBase):
    case_id: uuid.UUID


class EventRead(EventBase):
    id: uuid.UUID
    case_id: uuid.UUID
    created_at: datetime


# ── Proposal ──────────────────────────────────────────────────────────────


class ProposalBase(DomainBase):
    action_type: ActionType
    schedule_offset_hours: int = Field(..., ge=0)
    justification: str
    feature_citations: dict[str, Any]


class ProposalCreate(ProposalBase):
    case_id: uuid.UUID


class ProposalRead(ProposalBase):
    id: uuid.UUID
    case_id: uuid.UUID
    created_at: datetime


# ── Policy Verdict ─────────────────────────────────────────────────────────


class PolicyVerdictBase(DomainBase):
    verdict: PolicyVerdict
    rule_name: str = Field(..., max_length=255)
    policy_hash: str = Field(..., min_length=64, max_length=64)
    reason: str


class PolicyVerdictCreate(PolicyVerdictBase):
    proposal_id: uuid.UUID


class PolicyVerdictRead(PolicyVerdictBase):
    id: uuid.UUID
    proposal_id: uuid.UUID
    created_at: datetime


# ── Action ─────────────────────────────────────────────────────────────────


class ActionBase(DomainBase):
    action_type: ActionType
    scheduled_at: datetime


class ActionCreate(ActionBase):
    case_id: uuid.UUID
    proposal_id: uuid.UUID
    idempotency_key: str = Field(..., max_length=255)


class ActionRead(ActionBase):
    id: uuid.UUID
    case_id: uuid.UUID
    proposal_id: uuid.UUID
    idempotency_key: str
    status: ActionStatus
    executed_at: datetime | None
    created_at: datetime


# ── Outcome ────────────────────────────────────────────────────────────────


class OutcomeBase(DomainBase):
    status: OutcomeStatus
    recovery_amount: float = Field(0.0, ge=0)


class OutcomeCreate(OutcomeBase):
    case_id: uuid.UUID
    action_id: uuid.UUID | None = None


class OutcomeRead(OutcomeBase):
    id: uuid.UUID
    case_id: uuid.UUID
    action_id: uuid.UUID | None
    recorded_at: datetime
