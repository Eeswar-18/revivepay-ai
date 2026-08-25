"""
tests/test_domain_models.py — Tests for SQLAlchemy domain models.

Verifies that models can be instantiated, saved to the database, and
retrieved with correct relationships and constraints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import Action, Case, Event, Outcome, PolicyVerdictRecord, Proposal
from app.models.enums import ActionType, CaseState, OutcomeStatus, PolicyVerdict


def test_create_case_minimal(test_engine):
    """A Case can be created with minimal required fields."""
    with Session(test_engine) as session:
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
        case = Case(
            external_id="ext_123",
            amount=100.50,
            currency="USD",
            customer_id="cust_456",
            merchant_id="merch_789",
            expires_at=expires_at,
        )
        session.add(case)
        session.commit()
        session.refresh(case)

        assert isinstance(case.id, uuid.UUID)
        assert case.external_id == "ext_123"
        assert case.status == CaseState.DETECTED
        assert float(case.amount) == 100.50
        assert case.currency == "USD"
        assert case.expires_at == expires_at


def test_case_relationships(test_engine):
    """Case relationships (Event, Proposal, Action, Outcome) work correctly."""
    with Session(test_engine) as session:
        # 1. Create Case
        case = Case(
            external_id=f"ext_{uuid.uuid4()}",
            amount=500.00,
            currency="INR",
            customer_id="c1",
            merchant_id="m1",
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        )
        session.add(case)

        # 2. Add Event
        event = Event(
            case=case, event_type="PAYMENT_FAILURE", payload={"reason": "insufficient_funds"}
        )
        session.add(event)

        # 3. Add Proposal
        proposal = Proposal(
            case=case,
            action_type=ActionType.RETRY_PAYMENT,
            schedule_offset_hours=24,
            justification="High probability of recovery on second attempt",
            feature_citations={"failure_count": 1},
        )
        session.add(proposal)

        # 4. Add Policy Verdict
        verdict = PolicyVerdictRecord(
            proposal=proposal,
            verdict=PolicyVerdict.APPROVE,
            rule_name="allow_single_retry",
            policy_hash="a" * 64,
            reason="Meets safety criteria",
        )
        session.add(verdict)

        # 5. Add Action
        action = Action(
            case=case,
            proposal=proposal,
            action_type=ActionType.RETRY_PAYMENT,
            idempotency_key=str(uuid.uuid4()),
            scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=24),
        )
        session.add(action)

        # 6. Add Outcome
        outcome = Outcome(
            case=case, action=action, status=OutcomeStatus.RECOVERED, recovery_amount=500.00
        )
        session.add(outcome)

        session.commit()
        session.refresh(case)

        assert len(case.events) == 1
        assert len(case.proposals) == 1
        assert len(case.actions) == 1
        assert len(case.outcomes) == 1
        assert case.proposals[0].verdict.verdict == PolicyVerdict.APPROVE
        assert case.actions[0].outcome.status == OutcomeStatus.RECOVERED


def test_case_amount_constraint(test_engine):
    """Negative amounts are rejected by the database constraint."""
    from sqlalchemy.exc import IntegrityError

    with Session(test_engine) as session:
        case = Case(
            external_id="ext_neg",
            amount=-10.00,
            currency="USD",
            customer_id="c",
            merchant_id="m",
            expires_at=datetime.now(UTC).replace(tzinfo=None),
        )
        session.add(case)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
