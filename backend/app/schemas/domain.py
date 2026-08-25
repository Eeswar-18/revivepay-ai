"""
app/schemas/domain.py — Pydantic v2 schemas aligned to current ORM models.

Monetary fields are int ``*_minor`` with ``ge=0`` where non-negative is required.
No float currency. Enums are imported from ``app.models.enums``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ActionStatus,
    ActionType,
    CaseState,
    CaseType,
    FailureClass,
    PolicyVerdict,
)


class DomainBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Merchant ───────────────────────────────────────────────────────────────


class MerchantBase(DomainBase):
    name: str = Field(..., max_length=255)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    risk_appetite: str = Field(..., max_length=50)
    max_retries_default: int = 3
    contact_budget_per_week: int = Field(..., ge=0)
    mdr_bps: int
    autonomous_amount_ceiling_minor: int = Field(..., ge=0)


class MerchantCreate(MerchantBase):
    id: uuid.UUID | None = None


class MerchantRead(MerchantBase):
    id: uuid.UUID
    created_at: datetime


# ── Customer ───────────────────────────────────────────────────────────────


class CustomerBase(DomainBase):
    merchant_id: uuid.UUID
    email_hash: str = Field(..., min_length=64, max_length=64)
    phone_hash: str = Field(..., min_length=64, max_length=64)
    region: str = Field(..., max_length=50)
    lifetime_txn_count: int = 0
    lifetime_success_rate: float
    prior_recovery_successes: int = 0
    prior_declines: int = 0
    do_not_contact: bool = False
    unsubscribed_at: datetime | None = None
    mandate_active: bool = False
    mandate_expires_at: datetime | None = None
    preferred_method: str = Field(..., max_length=50)
    consented_instruments_json: dict[str, object]


class CustomerCreate(CustomerBase):
    id: uuid.UUID | None = None


class CustomerRead(CustomerBase):
    id: uuid.UUID
    created_at: datetime


# ── Transaction ────────────────────────────────────────────────────────────


class TransactionBase(DomainBase):
    merchant_id: uuid.UUID
    customer_id: uuid.UUID
    amount_minor: int = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    payment_method: str = Field(..., max_length=50)
    card_network: str | None = Field(default=None, max_length=50)
    issuer_id: str | None = Field(default=None, max_length=50)
    status: str = Field(..., max_length=50)
    failure_code: str | None = Field(default=None, max_length=50)
    failure_class: FailureClass | None = None
    failure_message_raw: str | None = Field(default=None, max_length=255)
    attempt_no: int
    is_subscription: bool = False
    subscription_cycle: str | None = Field(default=None, max_length=50)
    checkout_stage: str = Field(..., max_length=50)
    device: str = Field(..., max_length=50)
    original_transaction_id: uuid.UUID | None = None
    is_test: bool = True


class TransactionCreate(TransactionBase):
    id: uuid.UUID | None = None


class TransactionRead(TransactionBase):
    id: uuid.UUID
    created_at: datetime


# ── Case ───────────────────────────────────────────────────────────────────


class CaseBase(DomainBase):
    transaction_id: uuid.UUID | None = None
    merchant_id: uuid.UUID
    customer_id: uuid.UUID
    case_type: CaseType
    amount_at_risk_minor: int = Field(..., ge=0)
    state: CaseState = CaseState.DETECTED
    attempts_used: int = 0
    priority_score: float
    expected_net_value_minor: int | None = Field(default=None, ge=0)
    recovery_deadline_at: datetime
    recovered_amount_minor: int = Field(default=0, ge=0)
    closed_at: datetime | None = None
    close_reason: str | None = Field(default=None, max_length=255)
    simulation_run_id: uuid.UUID | None = None


class CaseCreate(CaseBase):
    id: uuid.UUID | None = None


class CaseUpdate(DomainBase):
    state: CaseState | None = None
    recovery_deadline_at: datetime | None = None
    expected_net_value_minor: int | None = Field(default=None, ge=0)
    recovered_amount_minor: int | None = Field(default=None, ge=0)
    closed_at: datetime | None = None
    close_reason: str | None = None


class CaseRead(CaseBase):
    id: uuid.UUID
    detected_at: datetime


# ── Event ──────────────────────────────────────────────────────────────────


class EventBase(DomainBase):
    event_type: str = Field(..., max_length=100)
    transaction_id: uuid.UUID | None = None
    customer_id: uuid.UUID
    merchant_id: uuid.UUID
    occurred_at: datetime
    payload_json: dict[str, object]
    processed_at: datetime | None = None


class EventCreate(EventBase):
    id: uuid.UUID | None = None


class EventRead(EventBase):
    id: uuid.UUID
    ingested_at: datetime


# ── Decision ───────────────────────────────────────────────────────────────


class DecisionBase(DomainBase):
    case_id: uuid.UUID
    seq: int = Field(..., ge=1)
    features_json: dict[str, object]
    feature_version: str = Field(..., max_length=50)
    risk_model_version: str = Field(..., max_length=50)
    p_calibrated: float
    candidate_scores_json: dict[str, object]
    llm_provider: str = Field(..., max_length=50)
    llm_model: str = Field(..., max_length=50)
    prompt_version: str = Field(..., max_length=50)
    prompt_hash: str = Field(..., min_length=64, max_length=64)
    raw_llm_output: str | None = None
    proposal_json: dict[str, object] | None = None
    llm_confidence: float | None = None
    llm_self_probability: float | None = None
    validation_status: str = Field(..., max_length=50)
    validation_errors_json: dict[str, object]
    policy_version: str = Field(..., max_length=50)
    policy_verdict: PolicyVerdict
    applied_rules_json: dict[str, object]
    violated_rules_json: dict[str, object]
    chosen_action: ActionType | None = None
    chosen_params_json: dict[str, object] | None = None
    expected_net_value_minor: int = Field(..., ge=0)
    decision_latency_ms: int = Field(..., ge=0)
    seed: int
    fallback_used: bool


class DecisionCreate(DecisionBase):
    id: uuid.UUID | None = None


class DecisionRead(DecisionBase):
    id: uuid.UUID
    created_at: datetime


# ── Action ─────────────────────────────────────────────────────────────────


class ActionBase(DomainBase):
    case_id: uuid.UUID
    decision_id: uuid.UUID
    idempotency_key: str = Field(..., max_length=255)
    action_type: ActionType
    params_json: dict[str, object]
    adapter: str = Field(..., max_length=50)
    state: ActionStatus = ActionStatus.PENDING
    scheduled_for: datetime | None = None
    executed_at: datetime | None = None
    attempt_no: int = Field(..., ge=1)
    cost_minor: int = Field(..., ge=0)
    response_json: dict[str, object] | None = None
    error_message: str | None = Field(default=None, max_length=255)


class ActionCreate(ActionBase):
    id: uuid.UUID | None = None


class ActionRead(ActionBase):
    id: uuid.UUID
    created_at: datetime


# ── Outcome ────────────────────────────────────────────────────────────────


class OutcomeBase(DomainBase):
    action_id: uuid.UUID
    case_id: uuid.UUID
    success: bool
    amount_recovered_minor: int = Field(..., ge=0)
    customer_reaction: str = Field(..., max_length=50)
    env_version: str = Field(..., max_length=50)
    env_seed: int


class OutcomeCreate(OutcomeBase):
    id: uuid.UUID | None = None


class OutcomeRead(OutcomeBase):
    id: uuid.UUID
    recorded_at: datetime


# ── Audit ──────────────────────────────────────────────────────────────────


class AuditLogEntryBase(DomainBase):
    actor: str = Field(..., max_length=50)
    event_type: str = Field(..., max_length=50)
    case_id: uuid.UUID | None = None
    decision_id: uuid.UUID | None = None
    action_id: uuid.UUID | None = None
    payload_json: dict[str, object]


class AuditLogEntryCreate(AuditLogEntryBase):
    id: uuid.UUID | None = None


class AuditLogEntryRead(AuditLogEntryBase):
    seq: int
    id: uuid.UUID
    ts: datetime
    prev_hash: str
    hash: str
