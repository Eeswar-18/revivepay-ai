"""
tests/test_domain_schemas.py — Tests for Pydantic domain schemas.

Verifies that schemas correctly validate incoming data and serialize
domain-model-shaped attribute bags to JSON.

Note: CaseCreate/CaseRead still use the pre-Rescue field layout (external_id,
float amount). Aligning those schemas to the current ORM (amount_*_minor,
state) is Phase 2 Rescue B — this file keeps schema coverage green without
shrinking assertions on the existing schema contracts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models import Case
from app.models.enums import CaseState, CaseType
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
    """CaseRead can be instantiated from a model-like attribute object.

    Also constructs a current ORM Case to confirm the live model shape remains
    usable alongside the (not-yet-aligned) CaseRead schema.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    case_id = uuid.uuid4()
    merchant_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    # Current ORM Case (integer paise / state) — must construct successfully.
    case_model = Case(
        id=case_id,
        merchant_id=merchant_id,
        customer_id=customer_id,
        case_type=CaseType.FAILED_PAYMENT,
        detected_at=now,
        amount_at_risk_minor=999_99,
        state=CaseState.DETECTED,
        attempts_used=0,
        priority_score=0.1,
        recovery_deadline_at=now + timedelta(hours=1),
        recovered_amount_minor=0,
    )
    assert case_model.id == case_id
    assert case_model.state == CaseState.DETECTED
    assert case_model.amount_at_risk_minor == 999_99

    # CaseRead still expects the legacy schema attribute names (Rescue B).
    legacy_shaped = SimpleNamespace(
        id=case_model.id,
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
    schema = CaseRead.model_validate(legacy_shaped)

    assert schema.id == case_model.id
    assert schema.status == CaseState.DETECTED
    assert schema.amount == 999.99
    assert schema.currency == "GBP"
