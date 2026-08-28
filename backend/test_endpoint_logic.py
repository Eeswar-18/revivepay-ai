#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from uuid import uuid4
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models.cases import Case
from app.models.merchants import Merchant
from app.models.customers import Customer
from app.repositories.cases import CaseRepository
from app.repositories.decisions import DecisionRepository
from app.core.orchestrator import Orchestrator
from app.models.enums import CaseType, CaseState, ActionType, PolicyVerdict
from app.models.decisions import Decision
import json

# Create in-memory database
engine = create_engine("sqlite:///", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
session = SessionLocal()

try:
    # Create test data
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

    # Create case data (like from the API)
    case_data = {
        "merchant_id": str(merchant.id),
        "customer_id": str(customer.id),
        "case_type": "FAILED_PAYMENT",
        "amount_at_risk_minor": 1000
    }
    
    # Validate required fields
    required_fields = ["merchant_id", "customer_id", "case_type", "amount_at_risk_minor"]
    for field in required_fields:
        if field not in case_data:
            print(f"Missing required field: {field}")
            sys.exit(1)

    # Validate case_type
    try:
        case_type = CaseType(case_data["case_type"])
    except ValueError as err:
        print(f"Invalid case_type: {case_data['case_type']}")
        sys.exit(1)

    # Create case instance
    from uuid import UUID
    now = datetime.now(UTC)
    case = Case(
        merchant_id=UUID(case_data["merchant_id"]),
        customer_id=UUID(case_data["customer_id"]),
        case_type=case_type.value,
        amount_at_risk_minor=case_data["amount_at_risk_minor"],
        state=case_data.get("state", CaseState.DETECTED.value),
        detected_at=case_data.get("detected_at", now),
        occurred_at=case_data.get("occurred_at"),
        recovery_deadline_at=case_data.get("recovery_deadline_at", now + timedelta(days=7)),
        recovered_amount_minor=case_data.get("recovered_amount_minor", 0),
        priority_score=case_data.get("priority_score", 0.5),
    )
    
    # Save via repository
    case_repo = CaseRepository(session)
    created_case = case_repo.add(case)
    print(f"Case created: {created_case.id}")

    # Trigger the decision pipeline automatically
    try:
        # Run the orchestrator to process the case through the full decision pipeline
        print("Creating orchestrator...")
        orchestrator = Orchestrator(case_repo._session)
        print("Orchestrator created successfully")
        
        print("Calling orchestrator.orchestrate...")
        pipeline_result = orchestrator.orchestrate(created_case.id)
        print("Orchestrator executed successfully")
        
        print("Pipeline result:")
        print(json.dumps(pipeline_result, indent=2, default=str))
        
        # Create a decision record from the pipeline result
        print("Creating decision record...")
        decision = Decision(
            id=uuid4(),
            case_id=created_case.id,
            seq=1,  # First decision for this case
            features_json=pipeline_result.get("features", {}),
            feature_version="v1",  # TODO: Make this configurable
            risk_model_version="v1",  # TODO: Make this configurable
            p_calibrated=(lambda sc=pipeline_result.get("scored_candidates", []): sc[0].get("p_recovery", 0.0) if sc else 0.0)(),
            candidate_scores_json={
                str(candidate["action_type"]): {
                    "p_recovery": candidate.get("p_recovery", 0.0),
                    "enrv": candidate.get("enrv", 0),
                    "intervention_cost": candidate.get("intervention_cost", 0)
                }
                for candidate in pipeline_result.get("scored_candidates", [])
            },
            llm_provider="mock",
            llm_model="mock",
            prompt_version="p1",
            prompt_hash="a" * 64,
            raw_llm_output=json.dumps(pipeline_result.get("raw_proposal", {})),
            proposal_json=pipeline_result.get("validated_proposal", {}),
            validation_status="valid",  # Assuming validation passed in orchestrator
            validation_errors_json={},
            policy_version="pol-v1",  # TODO: Make this configurable
            policy_verdict=pipeline_result.get("policy_verdict", PolicyVerdict.BLOCK.value),
            applied_rules_json={},  # TODO: Extract from validated proposal if available
            violated_rules_json={},
            chosen_action=pipeline_result.get("recommended_action", ActionType.STOP.value),
            chosen_params_json={},
            expected_net_value_minor=int(sum(
                candidate.get("enrv", 0) for candidate in pipeline_result.get("scored_candidates", [])
                if candidate.get("action_type") == pipeline_result.get("recommended_action")
            ) or 0),
            decision_latency_ms=0,  # TODO: Measure actual latency
            seed=0,  # TODO: Extract from actual seed if available
            fallback_used=False,
        )
        
        # Save the decision
        decision_repo = DecisionRepository(session)
        created_decision = decision_repo.add(decision)
        print(f"Decision created: {created_decision.id}")
        
        print("SUCCESS: Everything worked!")
        
    except Exception as e:
        print(f"ERROR in decision pipeline: {e}")
        import traceback
        traceback.print_exc()
        
finally:
    session.close()
    engine.dispose()
