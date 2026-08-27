"""
tests/test_features.py — Behavioural tests for the deterministic feature builder.

Each test is named after and documents the property it protects.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — register metadata
from app.core.features import build_features
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


def _seed_merchant(session: Session) -> Merchant:
    """Seed a merchant and return it."""
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
    return merchant


def _seed_customer(session: Session, merchant_id: UUID) -> Customer:
    """Seed a customer and return it."""
    customer = Customer(
        id=uuid4(),
        merchant_id=merchant_id,
        email_hash="e" * 64,
        phone_hash="p" * 64,
        region="IN-KA",
        segment="OCCASIONAL",
        lifetime_txn_count=42,
        lifetime_success_rate=0.75,
        prior_recovery_successes=10,
        prior_declines=5,
        do_not_contact=False,
        unsubscribed_at=None,
        mandate_active=True,
        mandate_expires_at=None,
        preferred_method="upi",
        consented_instruments_json={"upi": True},
    )
    session.add(customer)
    session.flush()
    return customer


def _seed_case(
    session: Session,
    merchant_id: UUID,
    customer_id: UUID,
    amount_minor: int = 10000,
    case_type: CaseType = CaseType.FAILED_PAYMENT,
    occurred_at: datetime | None = None,
    detected_at: datetime | None = None,
) -> Case:
    """Seed a case and return it."""
    if occurred_at is None and detected_at is None:
        # Only set defaults if both are None (for backward compatibility with existing tests)
        occurred_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        detected_at = occurred_at
    elif detected_at is None:
        # If only detected_at is None, default it to occurred_at
        detected_at = occurred_at
    # If occurred_at is explicitly None, we leave it as None to test fallback behavior

    case = Case(
        id=uuid4(),
        merchant_id=merchant_id,
        customer_id=customer_id,
        case_type=case_type,
        amount_at_risk_minor=amount_minor,
        occurred_at=occurred_at,
        detected_at=detected_at,
        state=CaseState.DETECTED,
        attempts_used=0,
        priority_score=0.0,
        recovery_deadline_at=occurred_at + timedelta(days=7)
        if occurred_at is not None
        else detected_at + timedelta(days=7),
        recovered_amount_minor=0,
    )
    session.add(case)
    session.flush()
    return case


def test_build_features_basic() -> None:
    """Feature builder produces expected features for a basic case."""
    session, engine = _create_session()
    try:
        merchant = _seed_merchant(session)
        customer = _seed_customer(session, merchant.id)
        case = _seed_case(session, merchant.id, customer.id, amount_minor=5000)

        features = build_features(session, case.id)

        # Check that we get a dictionary
        assert isinstance(features, dict)
        assert len(features) > 0

        # Check some specific features
        assert features["amount_at_risk_minor"] == 5000
        assert (
            features["amount_band_MICRO"] == 1
        )  # 5000 paise = Rs 50, which is MICRO (up to Rs 100)
        assert features["case_type_FAILED_PAYMENT"] == 1
        assert features["merchant_mdr_bps"] == 200
        assert features["merchant_autonomous_amount_ceiling_minor"] == 1_000_000
        assert features["amount_to_ceiling_ratio"] == 5000 / 1_000_000  # 0.005
        assert features["merchant_risk_appetite_balanced"] == 1
        assert features["customer_lifetime_txn_count"] == 42
        assert features["customer_lifetime_success_rate"] == 0.75
        # prior recovery success rate: 10 / (10 + 5) = 0.666...
        assert abs(features["customer_prior_recovery_success_rate"] - (10 / 15)) < 1e-9
        assert features["customer_do_not_contact"] == 0
        assert features["customer_mandate_active"] == 1
        assert features["customer_segment_OCCASIONAL"] == 1
        assert features["customer_preferred_method_upi"] == 1
        assert features["customer_preferred_method_card"] == 0
        assert features["customer_preferred_method_netbanking"] == 0
        assert features["customer_preferred_method_wallet"] == 0

        # Time-based features (based on occurred_at = 2024-01-01 12:00:00 UTC)
        assert features["hour_of_day"] == 12
        assert features["day_of_week"] == 0  # Monday
        assert features["is_weekend"] == 0
        # Check cyclical encoding approximately
        import math

        expected_hour_sin = math.sin(2 * math.pi * 12 / 24)
        expected_hour_cos = math.cos(2 * math.pi * 12 / 24)
        assert abs(features["hour_of_day_sin"] - expected_hour_sin) < 1e-9
        assert abs(features["hour_of_day_cos"] - expected_hour_cos) < 1e-9
        expected_day_sin = math.sin(2 * math.pi * 0 / 7)
        expected_day_cos = math.cos(2 * math.pi * 0 / 7)
        assert abs(features["day_of_week_sin"] - expected_day_sin) < 1e-9
        assert abs(features["day_of_week_cos"] - expected_day_cos) < 1e-9

    finally:
        session.close()
        engine.dispose()


def test_build_features_different_case_types() -> None:
    """Feature builder handles different case types correctly."""
    session, engine = _create_session()
    try:
        merchant = _seed_merchant(session)
        customer = _seed_customer(session, merchant.id)

        for case_type in [
            CaseType.FAILED_PAYMENT,
            CaseType.ABANDONED_CHECKOUT,
            CaseType.SUBSCRIPTION_DUNNING,
            CaseType.INSTRUMENT_EXPIRY,
        ]:
            case = _seed_case(session, merchant.id, customer.id, case_type=case_type)
            features = build_features(session, case.id)
            assert features[f"case_type_{case_type.value}"] == 1
            # Ensure other case types are 0
            for other_case_type in CaseType:
                if other_case_type != case_type:
                    assert features.get(f"case_type_{other_case_type.value}", 0) == 0
    finally:
        session.close()
        engine.dispose()


def test_build_features_different_amount_bands() -> None:
    """Feature builder correctly computes amount bands."""
    session, engine = _create_session()
    try:
        merchant = _seed_merchant(session)
        customer = _seed_customer(session, merchant.id)

        test_cases = [
            (500, "MICRO"),  # Rs 5
            (5000, "MICRO"),  # Rs 50
            (15000, "SMALL"),  # Rs 150
            (150000, "MEDIUM"),  # Rs 1,500
            (1_500_000, "LARGE"),  # Rs 15,000
            (10_000_000, "XLARGE"),  # Rs 100,000
        ]
        for amount_minor, expected_band in test_cases:
            case = _seed_case(session, merchant.id, customer.id, amount_minor=amount_minor)
            features = build_features(session, case.id)
            assert features[f"amount_band_{expected_band}"] == 1
            # Ensure other bands are 0
            for band in ["MICRO", "SMALL", "MEDIUM", "LARGE", "XLARGE"]:
                if band != expected_band:
                    assert features.get(f"amount_band_{band}", 0) == 0
    finally:
        session.close()
        engine.dispose()


def test_build_features_handles_missing_occurred_at() -> None:
    """Feature builder falls back to detected_at when occurred_at is None."""
    session, engine = _create_session()
    try:
        merchant = _seed_merchant(session)
        customer = _seed_customer(session, merchant.id)
        # Set occurred_at to None explicitly
        occurred_at = None
        detected_at = datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC)
        case = _seed_case(
            session,
            merchant.id,
            customer.id,
            occurred_at=occurred_at,
            detected_at=detected_at,
        )
        # The seed function will set occurred_at to detected_at if occurred_at is None
        # but let's verify our feature builder uses detected_at
        features = build_features(session, case.id)
        # Time-based features should be based on detected_at
        assert features["hour_of_day"] == 14
        assert features["day_of_week"] == 5  # 2024-06-15 is a Saturday
        assert features["is_weekend"] == 1
    finally:
        session.close()
        engine.dispose()


def test_build_features_handles_zero_autonomous_ceiling() -> None:
    """Feature builder handles zero autonomous amount ceiling gracefully."""
    session, engine = _create_session()
    try:
        merchant = _seed_merchant(session)
        # Set autonomous amount ceiling to zero
        merchant.autonomous_amount_ceiling_minor = 0
        session.add(merchant)
        session.flush()
        customer = _seed_customer(session, merchant.id)
        case = _seed_case(session, merchant.id, customer.id, amount_minor=5000)

        features = build_features(session, case.id)
        # Should be zero to avoid division by zero
        assert features["amount_to_ceiling_ratio"] == 0.0
    finally:
        session.close()
        engine.dispose()


def test_build_features_is_deterministic() -> None:
    """Feature builder produces identical output for same input."""
    session1, engine1 = _create_session()
    session2, engine2 = _create_session()
    try:
        # Seed identical data in both sessions
        _seed_merchant(session1)
        _seed_merchant(session2)
        # For simplicity, we'll rely on the fact that the UUIDs are generated randomly,
        # but we can't guarantee they match. Instead, we'll test that each session
        # produces consistent results for its own data, and we'll compare the
        # structure and types of features, not the exact values (since IDs differ).
        # We'll do a simpler test: call build_features twice in the same session
        # with the same case ID and ensure the output is identical.
        merchant = _seed_merchant(session1)
        customer = _seed_customer(session1, merchant.id)
        case = _seed_case(session1, merchant.id, customer.id, amount_minor=7500)

        features1 = build_features(session1, case.id)
        features2 = build_features(session1, case.id)
        assert features1 == features2
    finally:
        session1.close()
        engine1.dispose()
        session2.close()
        engine2.dispose()


def test_build_features_raises_on_nonexistent_case() -> None:
    """Feature builder raises ValueError for non-existent case ID."""
    session, engine = _create_session()
    try:
        with pytest.raises(ValueError, match="Case with ID.*not found"):
            build_features(session, uuid4())
    finally:
        session.close()
        engine.dispose()
