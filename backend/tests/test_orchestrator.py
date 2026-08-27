"""
tests/test_orchestrator.py — Behavioural tests for the orchestrator.

Each test is named after and documents the property it protects.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — register metadata
from app.core.executor.clock import clock
from app.core.orchestrator import Orchestrator
from app.db import Base
from app.models.cases import Case
from app.models.customers import Customer
from app.models.enums import ActionType, CaseState, CaseType, PolicyVerdict
from app.models.merchants import Merchant


def _enable_fk(dbapi_connection: object, _connection_record: object) -> None:
    """Enable foreign key constraints for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _create_session() -> tuple[Session, Engine]:
    """Create an in-memory SQLite session and engine for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _enable_fk)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    return session, engine


def _seed_case(session: Session) -> Case:
    """Seed a minimal case and return it."""
    merchant = Merchant(
        id=uuid4(),
        name="Test Merchant",
        currency="INR",
        risk_appetite="balanced",
        max_retries_default=3,
        contact_budget_per_week=10_000,
        mdr_bps=200,
        autonomous_amount_ceiling_minor=1_000_000,
    )
    session.add(merchant)
    session.flush()

    customer = Customer(
        id=uuid4(),
        merchant_id=merchant.id,
        email_hash="e" * 64,
        phone_hash="p" * 64,
        region="IN-KA",
        segment="OCCASIONAL",
        lifetime_txn_count=0,
        lifetime_success_rate=0.0,
        prior_recovery_successes=0,
        prior_declines=0,
        preferred_method="upi",
        consented_instruments_json={"upi": True},
    )
    session.add(customer)
    session.flush()

    case = Case(
        id=uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        case_type=CaseType.FAILED_PAYMENT,
        amount_at_risk_minor=1000,
        state=CaseState.DETECTED,
        detected_at=datetime.now(UTC),
        priority_score=0.5,  # Required field
        recovery_deadline_at=datetime.now(UTC) + timedelta(days=7),  # Required field
    )
    session.add(case)
    session.flush()
    return case


def test_orchestrator_orchestrate_basic() -> None:
    """Orchestrator runs the full pipeline and returns a decision."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        case = _seed_case(session)
        orchestrator = Orchestrator(session)

        result = orchestrator.orchestrate(case.id)

        # Check that we get a result with expected keys
        assert "case_id" in result
        assert "failure_class" in result
        assert "features" in result
        assert "scored_candidates" in result
        assert "raw_proposal" in result
        assert "validated_proposal" in result
        assert "policy_verdict" in result
        assert "recommended_action" in result
        assert "schedule_offset_hours" in result
        assert "justification" in result
        assert "feature_citations" in result

        # Check that the case_id matches
        assert result["case_id"] == str(case.id)

        # Check that we have some scored candidates
        assert len(result["scored_candidates"]) > 0

        # Check that each scored candidate has the expected fields
        for candidate in result["scored_candidates"]:
            assert "action_type" in candidate
            assert "p_recovery" in candidate
            assert "enrv" in candidate
            assert "intervention_cost" in candidate

        # Check that the validated proposal has the expected fields
        assert "action_type" in result["validated_proposal"]
        assert "schedule_offset_hours" in result["validated_proposal"]
        assert "justification" in result["validated_proposal"]
        assert "feature_citations" in result["validated_proposal"]

        # Check that policy_verdict is a valid PolicyVerdict
        assert result["policy_verdict"] in [v.value for v in PolicyVerdict]

        # Check that recommended_action is a valid ActionType
        assert result["recommended_action"] in [a.value for a in ActionType]

    finally:
        session.close()
        engine.dispose()


def test_orchestrator_orchestrate_with_stop_action() -> None:
    """Orchestrator handles cases where only STOP action is feasible."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        case = _seed_case(session)

        # Modify the case to make it very high amount so only STOP might be feasible
        case.amount_at_risk_minor = 1_000_000_000  # Very high amount
        session.add(case)
        session.flush()

        orchestrator = Orchestrator(session)
        result = orchestrator.orchestrate(case.id)

        # Even with high amount, we should still get a result
        assert "case_id" in result
        assert result["case_id"] == str(case.id)

    finally:
        session.close()
        engine.dispose()


def test_orchestrator_orchestrate_case_not_found() -> None:
    """Orchestrator raises ValueError for non-existent case."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        orchestrator = Orchestrator(session)

        # Try to orchestrate a non-existent case
        with pytest.raises(ValueError, match="Case with ID"):
            orchestrator.orchestrate(uuid4())

    finally:
        session.close()
        engine.dispose()
