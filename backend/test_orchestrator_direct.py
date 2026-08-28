#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from uuid import uuid4
from datetime import datetime, timedelta, UTC
from app.models.cases import Case
from app.models.merchants import Merchant
from app.models.customers import Customer
from app.db import Session, init_db, get_session_factory
from app.core.orchestrator import Orchestrator
from app.config import get_settings
import json

# Actually, let me just use the same approach as the tests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base  # Import Base from db module

# Create in-memory database for testing
engine = create_engine("sqlite:///", connect_args={"check_same_thread": False})
init_db(engine=engine)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
session = SessionLocal()

try:
    # Create test data similar to the test fixtures
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
        case_type="FAILED_PAYMENT",
        amount_at_risk_minor=1000,
        state="DETECTED",
        detected_at=datetime.now(UTC),
        priority_score=0.5,
        recovery_deadline_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(case)
    session.flush()

    # Now test the orchestrator
    print("Testing orchestrator...")
    orchestrator = Orchestrator(session)
    result = orchestrator.orchestrate(case.id)
    
    print("Orchestrator result:")
    print(json.dumps(result, indent=2, default=str))
    
finally:
    session.close()
    engine.dispose()
