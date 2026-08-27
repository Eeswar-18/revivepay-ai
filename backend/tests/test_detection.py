"""
tests/test_detection.py — Behavioural tests for the revenue-at-risk detection module.

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
from app.core.detection import ProviderEvent, detect_and_create_case
from app.core.executor.clock import clock
from app.db import Base
from app.models.cases import Case
from app.models.customers import Customer
from app.models.enums import CaseState, CaseType
from app.models.merchants import Merchant
from app.models.transactions import Transaction


def _enable_fk(dbapi_connection: object, _connection_record: object) -> None:
    """Enable foreign key constraints for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _seed_merchant_customer(session: Session) -> tuple[Merchant, Customer]:
    """Seed a merchant and customer for testing."""
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
    return merchant, customer


def _seed_transaction(
    session: Session, merchant: Merchant, customer: Customer, amount_minor: int
) -> Transaction:
    """Seed a transaction for testing."""
    transaction = Transaction(
        id=uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount_minor=amount_minor,
        currency="INR",
        created_at=datetime.now(UTC),
        payment_method="upi",
        rail="RAIL_UPI",
        status="failed",
        failure_code="TEST_FAILURE",
        failure_class="INSUFFICIENT_FUNDS",
        failure_message_raw="Test failure",
        attempt_no=1,
        is_subscription=False,
        subscription_cycle=None,
        checkout_stage="payment",
        device="mobile_web",
        original_transaction_id=None,
        is_test=True,
    )
    session.add(transaction)
    session.flush()
    return transaction


def _create_session() -> tuple[Session, Engine]:
    """Create an in-memory SQLite session and engine for testing."""
    # Start the virtual clock for use in detection
    clock.start()
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


def test_valid_payment_event_creates_case() -> None:
    """A valid payment_failed event creates a Case with correct initial state."""
    session, engine = _create_session()
    try:
        merchant, customer = _seed_merchant_customer(session)
        transaction = _seed_transaction(session, merchant, customer, amount_minor=10000)
        event_id = transaction.id
        occurred_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        event = ProviderEvent(
            event_type="payment_failed",
            transaction_id=event_id,
            merchant_id=merchant.id,
            customer_id=customer.id,
            occurred_at=occurred_at,
            amount_minor=10000,  # Rs 100.00
        )

        case = detect_and_create_case(session, event)

        # Check that the case was persisted and has the expected attributes
        assert isinstance(case, Case)
        assert case.merchant_id == merchant.id
        assert case.customer_id == customer.id
        assert case.transaction_id == event_id
        assert case.case_type == CaseType.FAILED_PAYMENT
        assert case.state == CaseState.DETECTED
        assert case.amount_at_risk_minor == 10000
        assert case.recovered_amount_minor == 0
        assert case.attempts_used == 0
        assert case.priority_score == 0.0
        # Recovery deadline should be 7 days after occurred_at
        expected_deadline = occurred_at + timedelta(days=7)
        assert case.recovery_deadline_at == expected_deadline
        # detected_at should be set by the virtual clock (we can't predict the exact value, but it should be close to clock.now())
        # We'll just check that it's not None and is a datetime.
        assert case.detected_at is not None
        # The ID should be set by the database
        assert case.id is not None
    finally:
        session.close()
        engine.dispose()


def test_abandoned_checkout_event_creates_correct_case_type() -> None:
    """A checkout_abandoned event results in CaseType.ABANDONED_CHECKOUT."""
    session, engine = _create_session()
    try:
        merchant, customer = _seed_merchant_customer(session)
        # For abandoned checkout, there is no transaction, so transaction_id is None
        occurred_at = datetime(2024, 1, 1, tzinfo=UTC)
        event = ProviderEvent(
            event_type="checkout_abandoned",
            transaction_id=None,
            merchant_id=merchant.id,
            customer_id=customer.id,
            occurred_at=occurred_at,
            amount_minor=5000,  # Rs 50.00
        )
        case = detect_and_create_case(session, event)
        assert case.case_type == CaseType.ABANDONED_CHECKOUT
    finally:
        session.close()
        engine.dispose()


def test_mandate_debit_failed_event_creates_correct_case_type() -> None:
    """A mandate_debit_failed event results in CaseType.SUBSCRIPTION_DUNNING."""
    session, engine = _create_session()
    try:
        merchant, customer = _seed_merchant_customer(session)
        transaction = _seed_transaction(session, merchant, customer, amount_minor=50000)
        event_id = transaction.id
        occurred_at = datetime(2024, 1, 1, tzinfo=UTC)
        event = ProviderEvent(
            event_type="mandate_debit_failed",
            transaction_id=event_id,
            merchant_id=merchant.id,
            customer_id=customer.id,
            occurred_at=occurred_at,
            amount_minor=50000,  # Rs 500.00
        )
        case = detect_and_create_case(session, event)
        assert case.case_type == CaseType.SUBSCRIPTION_DUNNING
    finally:
        session.close()
        engine.dispose()


def test_instrument_expiring_event_creates_correct_case_type() -> None:
    """An instrument_expiring event results in CaseType.INSTRUMENT_EXPIRY."""
    session, engine = _create_session()
    try:
        merchant, customer = _seed_merchant_customer(session)
        # For instrument expiry, there is no transaction, so transaction_id is None
        occurred_at = datetime(2024, 1, 1, tzinfo=UTC)
        event = ProviderEvent(
            event_type="instrument_expiring",
            transaction_id=None,
            merchant_id=merchant.id,
            customer_id=customer.id,
            occurred_at=occurred_at,
            amount_minor=0,  # No amount at risk for instrument expiry? We allow zero.
        )
        case = detect_and_create_case(session, event)
        assert case.case_type == CaseType.INSTRUMENT_EXPIRY
    finally:
        session.close()
        engine.dispose()


def test_negative_amount_minor_raises_value_error() -> None:
    """A negative amount_minor should raise a ValueError."""
    session, engine = _create_session()
    try:
        merchant, customer = _seed_merchant_customer(session)
        event = ProviderEvent(
            event_type="payment_failed",
            transaction_id=uuid4(),  # This transaction doesn't exist, but we expect a ValueError for amount first
            merchant_id=merchant.id,
            customer_id=customer.id,
            occurred_at=datetime(2024, 1, 1, tzinfo=UTC),
            amount_minor=-100,
        )
        with pytest.raises(ValueError, match="amount_minor must be non-negative"):
            detect_and_create_case(session, event)
    finally:
        session.close()
        engine.dispose()


def test_unknown_event_type_raises_value_error() -> None:
    """An unknown event type should raise a ValueError."""
    session, engine = _create_session()
    try:
        merchant, customer = _seed_merchant_customer(session)
        event = ProviderEvent(
            event_type="unknown_event",
            transaction_id=uuid4(),
            merchant_id=merchant.id,
            customer_id=customer.id,
            occurred_at=datetime(2024, 1, 1, tzinfo=UTC),
            amount_minor=1000,
        )
        with pytest.raises(ValueError, match="Unknown event type"):
            detect_and_create_case(session, event)
    finally:
        session.close()
        engine.dispose()


def test_detection_is_deterministic_except_for_db_generated_fields() -> None:
    """Two calls with the same input should produce cases with identical
    attributes except for the database-generated ID and detected_at timestamp.
    """
    session1, engine1 = _create_session()
    session2, engine2 = _create_session()
    try:
        # Use fixed IDs for consistency across sessions
        fixed_merchant_id = uuid4()
        fixed_customer_id = uuid4()
        fixed_transaction_id = uuid4()

        # Session 1
        merchant1 = Merchant(
            id=fixed_merchant_id,
            name="Test Merchant",
            currency="INR",
            risk_appetite="balanced",
            max_retries_default=3,
            contact_budget_per_week=10_000,
            mdr_bps=200,
            autonomous_amount_ceiling_minor=1_000_000,
        )
        session1.add(merchant1)
        session1.flush()
        customer1 = Customer(
            id=fixed_customer_id,
            merchant_id=merchant1.id,
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
        session1.add(customer1)
        session1.flush()
        transaction1 = Transaction(
            id=fixed_transaction_id,
            merchant_id=merchant1.id,
            customer_id=customer1.id,
            amount_minor=4200,
            currency="INR",
            created_at=datetime.now(UTC),
            payment_method="upi",
            rail="RAIL_UPI",
            status="failed",
            failure_code="TEST_FAILURE",
            failure_class="INSUFFICIENT_FUNDS",
            failure_message_raw="Test failure",
            attempt_no=1,
            is_subscription=False,
            subscription_cycle=None,
            checkout_stage="payment",
            device="mobile_web",
            original_transaction_id=None,
            is_test=True,
        )
        session1.add(transaction1)
        session1.flush()

        # Session 2
        merchant2 = Merchant(
            id=fixed_merchant_id,
            name="Test Merchant",
            currency="INR",
            risk_appetite="balanced",
            max_retries_default=3,
            contact_budget_per_week=10_000,
            mdr_bps=200,
            autonomous_amount_ceiling_minor=1_000_000,
        )
        session2.add(merchant2)
        session2.flush()
        customer2 = Customer(
            id=fixed_customer_id,
            merchant_id=merchant2.id,
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
        session2.add(customer2)
        session2.flush()
        transaction2 = Transaction(
            id=fixed_transaction_id,
            merchant_id=merchant2.id,
            customer_id=customer2.id,
            amount_minor=4200,
            currency="INR",
            created_at=datetime.now(UTC),
            payment_method="upi",
            rail="RAIL_UPI",
            status="failed",
            failure_code="TEST_FAILURE",
            failure_class="INSUFFICIENT_FUNDS",
            failure_message_raw="Test failure",
            attempt_no=1,
            is_subscription=False,
            subscription_cycle=None,
            checkout_stage="payment",
            device="mobile_web",
            original_transaction_id=None,
            is_test=True,
        )
        session2.add(transaction2)
        session2.flush()

        occurred_at = datetime(2024, 1, 1, tzinfo=UTC)
        event = ProviderEvent(
            event_type="payment_failed",
            transaction_id=fixed_transaction_id,
            merchant_id=fixed_merchant_id,
            customer_id=fixed_customer_id,
            occurred_at=occurred_at,
            amount_minor=4200,
        )

        case1 = detect_and_create_case(session1, event)
        case2 = detect_and_create_case(session2, event)

        # Compare all attributes except id and detected_at
        assert case1.merchant_id == case2.merchant_id
        assert case1.customer_id == case2.customer_id
        assert case1.transaction_id == case2.transaction_id
        assert case1.case_type == case2.case_type
        assert case1.state == case2.state
        assert case1.amount_at_risk_minor == case2.amount_at_risk_minor
        assert case1.recovered_amount_minor == case2.recovered_amount_minor
        assert case1.attempts_used == case2.attempts_used
        assert case1.priority_score == case2.priority_score
        assert case1.recovery_deadline_at == case2.recovery_deadline_at
        # The ID and detected_at will differ because they are generated by the database
        # and the sessions are separate.
        assert case1.id != case2.id
        # detected_at might be the same if the calls are close enough, but we don't require it to differ.
    finally:
        session1.close()
        engine1.dispose()
        session2.close()
        engine2.dispose()
