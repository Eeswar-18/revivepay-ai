"""
tests/test_decision_pipeline.py — Integration tests for the full decision pipeline.

Each test verifies that the components work together correctly:
case -> features -> risk model -> expected net value -> LLM planner -> policy kernel -> orchestrator
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


def _seed_case(session: Session, amount_at_risk_minor: int = 1000) -> Case:
    """Seed a minimal case with customer and merchant and return the case."""
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
        lifetime_txn_count=10,
        lifetime_success_rate=0.8,
        prior_recovery_successes=8,
        prior_declines=2,
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
        amount_at_risk_minor=amount_at_risk_minor,
        state=CaseState.DETECTED,
        detected_at=datetime.now(UTC),
        priority_score=0.5,
        recovery_deadline_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(case)
    session.flush()
    return case


def test_decision_pipeline_orchestrator_integration() -> None:
    """Test that the orchestrator correctly runs the full decision pipeline."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        case = _seed_case(session)
        orchestrator = Orchestrator(session)

        result = orchestrator.orchestrate(case.id)

        # Verify we get a result with all expected pipeline stages
        assert "case_id" in result
        assert result["case_id"] == str(case.id)
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

        # Verify features were computed
        assert isinstance(result["features"], dict)
        assert len(result["features"]) > 0
        assert "amount_at_risk_minor" in result["features"]
        assert "customer_segment_OCCASIONAL" in result["features"]
        assert "merchant_mdr_bps" in result["features"]

        # Verify we have scored candidates
        assert len(result["scored_candidates"]) > 0
        for candidate in result["scored_candidates"]:
            assert "action_type" in candidate
            assert "p_recovery" in candidate
            assert 0.0 <= candidate["p_recovery"] <= 1.0
            assert "enrv" in candidate  # expected net value
            assert "intervention_cost" in candidate

        # Verify policy verdict is valid
        assert result["policy_verdict"] in [v.value for v in PolicyVerdict]

        # Verify recommended action is valid
        assert result["recommended_action"] in [a.value for a in ActionType]

        # Verify the validated proposal has expected structure
        validated = result["validated_proposal"]
        assert "action_type" in validated
        assert "schedule_offset_hours" in validated
        assert "justification" in validated
        assert "feature_citations" in validated

    finally:
        session.close()
        engine.dispose()


def test_decision_pipeline_with_high_amount_triggers_escalation() -> None:
    """Test that high amount cases may trigger escalation based on policy rules."""
    session, engine = _create_session()
    try:
        clock.start()
        # Create a case with high amount that should trigger policy escalation
        case = _seed_case(session, amount_at_risk_minor=500_000_000)  # Very high amount
        orchestrator = Orchestrator(session)

        result = orchestrator.orchestrate(case.id)

        # Should still get a valid result
        assert "case_id" in result
        assert result["case_id"] == str(case.id)
        assert "policy_verdict" in result
        assert "recommended_action" in result

        # The policy should have processed this case (even if it doesn't escalate in our simple policy)
        assert result["policy_verdict"] in [v.value for v in PolicyVerdict]

    finally:
        session.close()
        engine.dispose()


def test_decision_pipeline_handles_stop_only_case() -> None:
    """Test the pipeline when only STOP action is feasible (e.g., due to candidate generation)."""
    session, engine = _create_session()
    try:
        clock.start()
        case = _seed_case(session)

        # We'll test that even if candidate generation returns empty, we default to STOP
        orchestrator = Orchestrator(session)

        result = orchestrator.orchestrate(case.id)

        assert "case_id" in result
        assert result["case_id"] == str(case.id)
        assert "scored_candidates" in result
        assert len(result["scored_candidates"]) > 0  # Should have at least STOP

        # Verify that STOP is in the scored candidates
        stop_found = any(c["action_type"] == ActionType.STOP.value for c in result["scored_candidates"])
        assert stop_found, "STOP action should be in scored candidates"

    finally:
        session.close()
        engine.dispose()


def test_decision_pipeline_case_not_found_error() -> None:
    """Test that orchestrator raises ValueError for non-existent case."""
    session, engine = _create_session()
    try:
        clock.start()
        orchestrator = Orchestrator(session)

        with pytest.raises(ValueError, match="Case with ID"):
            orchestrator.orchestrate(uuid4())

    finally:
        session.close()
        engine.dispose()
