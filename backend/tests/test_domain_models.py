"""
tests/test_domain_models.py — Tests for SQLAlchemy domain models.

Verifies that models can be instantiated, saved to the database, and
retrieved with correct relationships and constraints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Action,
    Case,
    Customer,
    Decision,
    Event,
    Merchant,
    Outcome,
)
from app.models.enums import ActionStatus, ActionType, CaseState, CaseType, PolicyVerdict


def _seed_merchant_and_customer(session: Session) -> tuple[Merchant, Customer]:
    """Insert a merchant and customer required by case foreign keys."""
    merchant = Merchant(
        id=uuid.uuid4(),
        name="Test Merchant",
        currency="INR",
        risk_appetite="balanced",
        max_retries_default=3,
        contact_budget_per_week=100_00,
        mdr_bps=200,
        autonomous_amount_ceiling_minor=50_000_00,
    )
    customer = Customer(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        email_hash="a" * 64,
        phone_hash="b" * 64,
        region="IN-KA",
        segment="OCCASIONAL",
        lifetime_txn_count=5,
        lifetime_success_rate=0.8,
        prior_recovery_successes=1,
        prior_declines=0,
        do_not_contact=False,
        mandate_active=False,
        preferred_method="upi",
        consented_instruments_json={"upi": True},
    )
    session.add_all([merchant, customer])
    session.flush()
    return merchant, customer


def test_create_case_minimal(test_engine):
    """A Case can be created with minimal required fields."""
    with Session(test_engine) as session:
        merchant, customer = _seed_merchant_and_customer(session)
        deadline = datetime.now(UTC) + timedelta(days=7)
        case = Case(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            customer_id=customer.id,
            case_type=CaseType.FAILED_PAYMENT,
            amount_at_risk_minor=100_50,
            state=CaseState.DETECTED,
            attempts_used=0,
            priority_score=0.5,
            recovery_deadline_at=deadline,
            recovered_amount_minor=0,
        )
        session.add(case)
        session.commit()
        session.refresh(case)

        assert isinstance(case.id, uuid.UUID)
        assert case.state == CaseState.DETECTED
        assert case.amount_at_risk_minor == 100_50
        assert case.case_type == CaseType.FAILED_PAYMENT
        assert case.merchant_id == merchant.id
        assert case.customer_id == customer.id
        # SQLite drops tzinfo on round-trip; compare absolute instant.
        assert case.recovery_deadline_at.replace(tzinfo=UTC) == deadline


def test_case_relationships(test_engine):
    """Case-linked Event, Decision (proposal+verdict), Action, Outcome work correctly."""
    with Session(test_engine) as session:
        merchant, customer = _seed_merchant_and_customer(session)

        case = Case(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            customer_id=customer.id,
            case_type=CaseType.FAILED_PAYMENT,
            amount_at_risk_minor=500_00,
            state=CaseState.DETECTED,
            attempts_used=0,
            priority_score=0.7,
            recovery_deadline_at=datetime.now(UTC) + timedelta(days=1),
            recovered_amount_minor=0,
        )
        session.add(case)

        event = Event(
            id=uuid.uuid4(),
            event_type="payment_failed",
            customer_id=customer.id,
            merchant_id=merchant.id,
            occurred_at=datetime.now(UTC),
            payload_json={"reason": "insufficient_funds"},
        )
        session.add(event)

        # Decision merges former Proposal + PolicyVerdictRecord fields.
        decision = Decision(
            id=uuid.uuid4(),
            case_id=case.id,
            seq=1,
            features_json={"failure_count": 1},
            feature_version="v1",
            risk_model_version="rm-v1",
            p_calibrated=0.72,
            candidate_scores_json={"RETRY_SAME_RAIL": 1200},
            llm_provider="mock",
            llm_model="mock-v1",
            prompt_version="p1",
            prompt_hash="c" * 64,
            raw_llm_output='{"action":"RETRY_SAME_RAIL"}',
            proposal_json={
                "action_type": ActionType.RETRY_SAME_RAIL,
                "schedule_offset_hours": 24,
                "justification": "High probability of recovery on second attempt",
                "feature_citations": {"failure_count": 1},
            },
            llm_confidence=0.81,
            llm_self_probability=0.7,
            validation_status="valid",
            validation_errors_json={},
            policy_version="pol-v1",
            policy_verdict=PolicyVerdict.APPROVE,
            applied_rules_json={"rule_name": "allow_single_retry"},
            violated_rules_json={},
            chosen_action=ActionType.RETRY_SAME_RAIL,
            chosen_params_json={"schedule_offset_hours": 24},
            expected_net_value_minor=1200,
            decision_latency_ms=15,
            seed=42,
            fallback_used=False,
        )
        session.add(decision)

        action = Action(
            id=uuid.uuid4(),
            case_id=case.id,
            decision_id=decision.id,
            idempotency_key=str(uuid.uuid4()),
            action_type=ActionType.RETRY_SAME_RAIL,
            params_json={"schedule_offset_hours": 24},
            adapter="simulated",
            state=ActionStatus.PENDING,
            scheduled_for=datetime.now(UTC) + timedelta(hours=24),
            attempt_no=1,
            cost_minor=0,
        )
        session.add(action)

        outcome = Outcome(
            id=uuid.uuid4(),
            action_id=action.id,
            success=True,
            amount_recovered_minor=500_00,
            customer_reaction="none",
            env_version="env-v1",
            env_seed=42,
            case_id=case.id,
        )
        session.add(outcome)

        session.commit()

        events = session.scalars(
            select(Event).where(
                Event.merchant_id == merchant.id,
                Event.customer_id == customer.id,
            )
        ).all()
        decisions = session.scalars(select(Decision).where(Decision.case_id == case.id)).all()
        actions = session.scalars(select(Action).where(Action.case_id == case.id)).all()
        outcomes = session.scalars(select(Outcome).where(Outcome.case_id == case.id)).all()

        assert len(events) == 1
        assert len(decisions) == 1
        assert len(actions) == 1
        assert len(outcomes) == 1

        stored_decision = decisions[0]
        # Former Proposal properties (must not shrink coverage)
        assert stored_decision.proposal_json is not None
        assert stored_decision.proposal_json["action_type"] == ActionType.RETRY_SAME_RAIL
        assert stored_decision.proposal_json["schedule_offset_hours"] == 24
        assert (
            stored_decision.proposal_json["justification"]
            == "High probability of recovery on second attempt"
        )
        assert stored_decision.proposal_json["feature_citations"] == {"failure_count": 1}
        assert stored_decision.chosen_action == ActionType.RETRY_SAME_RAIL
        # Former PolicyVerdictRecord properties (must not shrink coverage)
        assert stored_decision.policy_verdict == PolicyVerdict.APPROVE
        assert stored_decision.applied_rules_json["rule_name"] == "allow_single_retry"
        assert stored_decision.policy_version == "pol-v1"
        assert stored_decision.violated_rules_json == {}

        assert actions[0].decision_id == stored_decision.id
        assert outcomes[0].success is True
        assert outcomes[0].amount_recovered_minor == 500_00
        assert outcomes[0].action_id == actions[0].id


def test_case_amount_constraint(test_engine):
    """Negative amounts are rejected by the database constraint."""
    from sqlalchemy.exc import IntegrityError

    with Session(test_engine) as session:
        merchant, customer = _seed_merchant_and_customer(session)
        case = Case(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            customer_id=customer.id,
            case_type=CaseType.FAILED_PAYMENT,
            amount_at_risk_minor=-10_00,
            state=CaseState.DETECTED,
            attempts_used=0,
            priority_score=0.0,
            recovery_deadline_at=datetime.now(UTC),
            recovered_amount_minor=0,
        )
        session.add(case)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
