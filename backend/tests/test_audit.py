"""
tests/test_audit.py — Behavioural tests for the audit service.

Each test is named after and documents the property it protects.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — register metadata
from app.core.audit import AuditService
from app.core.executor.clock import clock
from app.db import Base
from app.models.cases import Case
from app.models.customers import Customer
from app.models.enums import CaseState, CaseType
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


def test_audit_service_log_policy_decision() -> None:
    """AuditService logs policy decisions with correct structure."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        case = _seed_case(session)
        service = AuditService(session)

        proposal = {
            "action_type": "RETRY_SAME_RAIL",
            "schedule_offset_hours": 24,
            "justification": "Retry after 24 hours based on amount and segment",
            "feature_citations": {"amount_at_risk_minor": 0.7},
        }

        service.log_policy_decision(
            case_id=case.id,
            action_type="RETRY_SAME_RAIL",
            policy_verdict="APPROVE",
            proposal=proposal,
            rules_evaluated=["R001", "R005"],
        )

        # Verify the entry was written to the audit log
        from app.repositories.audit import AuditRepository

        repo = AuditRepository(session)
        entries = repo.list()
        assert len(entries) == 1

        entry = entries[0]
        assert entry.actor == "policy"
        assert entry.event_type == "policy_decision"
        assert entry.case_id == case.id
        assert entry.action_id is None  # No action executed yet
        assert entry.decision_id is None  # No decision record yet

        # Check payload contents
        payload = entry.payload_json
        assert payload["case_id"] == str(case.id)
        assert payload["action_type"] == "RETRY_SAME_RAIL"
        assert payload["policy_verdict"] == "APPROVE"
        assert payload["proposal"] == proposal
        assert payload["rules_evaluated"] == ["R001", "R005"]
        assert "virtual_clock" in payload

    finally:
        session.close()
        engine.dispose()


def test_audit_service_log_orchestrator_event() -> None:
    """AuditService logs orchestrator lifecycle events."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        case = _seed_case(session)
        service = AuditService(session)

        service.log_orchestrator_event(
            case_id=case.id,
            event_type="detection_complete",
            details={"event_type": "payment_failed", "amount": 1000},
        )

        from app.repositories.audit import AuditRepository

        repo = AuditRepository(session)
        entries = repo.list()
        assert len(entries) == 1

        entry = entries[0]
        assert entry.actor == "orchestrator"
        assert entry.event_type == "orchestrator_detection_complete"
        assert entry.case_id == case.id

        payload = entry.payload_json
        assert payload["case_id"] == str(case.id)
        assert payload["event_type"] == "detection_complete"
        assert payload["details"]["event_type"] == "payment_failed"
        assert payload["details"]["amount"] == 1000
        assert "virtual_clock" in payload

    finally:
        session.close()
        engine.dispose()


def test_audit_service_log_execution_event() -> None:
    """AuditService logs executor action events."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        case = _seed_case(session)
        service = AuditService(session)

        service.log_execution_event(
            case_id=case.id,
            action_id=None,  # No action ID yet for this test
            event_type="execution_completed",
            success=True,
        )

        from app.repositories.audit import AuditRepository

        repo = AuditRepository(session)
        entries = repo.list()
        assert len(entries) == 1

        entry = entries[0]
        assert entry.actor == "executor"
        assert entry.event_type == "execution_execution_completed"
        assert entry.case_id == case.id
        # Check that action_id is None in the database model
        assert entry.action_id is None

        payload = entry.payload_json
        assert payload["case_id"] == str(case.id)
        # In JSON, None gets serialized as null, which becomes Python None when loaded
        assert payload["action_id"] is None
        assert payload["event_type"] == "execution_completed"
        assert payload["success"] is True
        assert payload["error_message"] is None
        assert "virtual_clock" in payload

    finally:
        session.close()
        engine.dispose()


def test_audit_service_log_system_event() -> None:
    """AuditService logs system-level events."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        service = AuditService(session)

        service.log_system_event(
            event_type="virtual_clock_started",
            payload={"rate": 60.0, "epoch": "2024-01-01T00:00:00Z"},
        )

        from app.repositories.audit import AuditRepository

        repo = AuditRepository(session)
        entries = repo.list()
        assert len(entries) == 1

        entry = entries[0]
        assert entry.actor == "system"
        assert entry.event_type == "system_virtual_clock_started"
        assert entry.case_id is None
        assert entry.action_id is None

        payload = entry.payload_json
        assert payload["rate"] == 60.0
        assert payload["epoch"] == "2024-01-01T00:00:00Z"

    finally:
        session.close()
        engine.dispose()


def test_audit_service_hash_chaining() -> None:
    """AuditService maintains hash-chaining through repository."""
    session, engine = _create_session()
    try:
        # Start the virtual clock for this test
        clock.start()
        case = _seed_case(session)
        service = AuditService(session)

        # Log three events
        service.log_policy_decision(
            case_id=case.id,
            action_type="STOP",
            policy_verdict="BLOCK",
            proposal={"action_type": "STOP"},
        )
        service.log_orchestrator_event(
            case_id=case.id,
            event_type="policy_evaluated",
            details={"verdict": "BLOCK"},
        )
        service.log_system_event(event_type="audit_checkpoint")

        from app.repositories.audit import AuditRepository

        repo = AuditRepository(session)
        entries = repo.list()
        assert len(entries) == 3

        # Verify hash chaining
        assert entries[0].prev_hash == "0" * 64  # Genesis
        assert entries[1].prev_hash == entries[0].hash
        assert entries[2].prev_hash == entries[1].hash

        # Verify all hashes are different
        hashes = [e.hash for e in entries]
        assert len(set(hashes)) == 3

    finally:
        session.close()
        engine.dispose()
