"""
tests/test_domain_schemas.py — Tests for Pydantic domain schemas.

Verifies that schemas correctly validate incoming data and serialize
domain models (SQLAlchemy entities) to JSON.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.models import Case
from app.models.enums import CaseState
from app.schemas import CaseCreate, CaseRead


def test_case_create_validation_success():
    """CaseCreate validates valid input data."""
    data = {
        "external_id": "ext_123",
        "amount": 100.50,
        "currency": "USD",
        "customer_id": "cust_456",
        "merchant_id": "merch_789",
        "expires_at": datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
    }
    schema = CaseCreate(**data)
    assert schema.external_id == "ext_123"
    assert schema.amount == 100.50


def test_case_create_validation_error():
    """CaseCreate raises ValidationError on invalid input."""
    data = {
        "external_id": "ext_123",
        "amount": -50.0,  # Invalid: negative
        "currency": "US",  # Invalid: too short
        "customer_id": "cust_456",
        "merchant_id": "merch_789",
        "expires_at": datetime.now(UTC).replace(tzinfo=None),
    }
    with pytest.raises(ValidationError) as excinfo:
        CaseCreate(**data)

    errors = excinfo.value.errors()
    assert any(e["loc"] == ("amount",) for e in errors)
    assert any(e["loc"] == ("currency",) for e in errors)


def test_case_read_from_model():
    """CaseRead can be instantiated from a SQLAlchemy model instance."""
    now = datetime.now(UTC).replace(tzinfo=None)
    case_model = Case(
        id=uuid.uuid4(),
        external_id="ext_999",
        status=CaseState.DETECTED,
        amount=999.99,
        currency="GBP",
        customer_id="c_9",
        merchant_id="m_9",
        detected_at=now,
        expires_at=now + timedelta(hours=1),
        last_updated_at=now,
    )

    # Use model_validate (Pydantic v2) or from_orm (if enabled)
    schema = CaseRead.model_validate(case_model)

    assert schema.id == case_model.id
    assert schema.status == CaseState.DETECTED
    assert schema.amount == 999.99
    assert schema.currency == "GBP"
