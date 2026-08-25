"""
tests/test_domain_schemas.py — Tests for Pydantic domain schemas.

Verifies that schemas correctly validate incoming data and serialize
SQLAlchemy model instances via from_attributes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.models import Case
from app.models.enums import CaseState, CaseType
from app.schemas import CaseCreate, CaseRead


def test_case_create_validation_success():
    """CaseCreate validates valid input data."""
    merchant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    data = {
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "case_type": CaseType.FAILED_PAYMENT,
        "amount_at_risk_minor": 100_50,
        "state": CaseState.DETECTED,
        "priority_score": 0.5,
        "recovery_deadline_at": datetime.now(UTC) + timedelta(days=1),
        "recovered_amount_minor": 0,
    }
    schema = CaseCreate(**data)
    assert schema.merchant_id == merchant_id
    assert schema.amount_at_risk_minor == 100_50


def test_case_create_validation_error():
    """CaseCreate raises ValidationError on invalid input."""
    data = {
        "merchant_id": uuid.uuid4(),
        "customer_id": uuid.uuid4(),
        "case_type": CaseType.FAILED_PAYMENT,
        "amount_at_risk_minor": -50,  # Invalid: negative
        "state": CaseState.DETECTED,
        "priority_score": 0.1,
        "recovery_deadline_at": datetime.now(UTC),
    }
    with pytest.raises(ValidationError) as excinfo:
        CaseCreate(**data)

    errors = excinfo.value.errors()
    assert any(e["loc"] == ("amount_at_risk_minor",) for e in errors)


def test_case_read_from_model():
    """CaseRead can be instantiated from a SQLAlchemy Case model instance."""
    now = datetime.now(UTC)
    case_model = Case(
        id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        case_type=CaseType.FAILED_PAYMENT,
        detected_at=now,
        amount_at_risk_minor=999_99,
        state=CaseState.DETECTED,
        attempts_used=0,
        priority_score=0.1,
        recovery_deadline_at=now + timedelta(hours=1),
        recovered_amount_minor=0,
    )

    schema = CaseRead.model_validate(case_model)

    assert schema.id == case_model.id
    assert schema.state == CaseState.DETECTED
    assert schema.amount_at_risk_minor == 999_99
    assert schema.case_type == CaseType.FAILED_PAYMENT
