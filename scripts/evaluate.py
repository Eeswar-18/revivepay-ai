#!/usr/bin/env python3
"""
Evaluation harness for RevivePay-AI decision pipeline.

This script:
1. Generates a synthetic population using the held-out generators module
2. Runs the decision pipeline on each case
3. Computes baseline metrics for comparison
4. Reports performance metrics
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import app.models  # noqa: F401 — register metadata
import numpy as np
from app.core.executor.clock import clock
from app.core.orchestrator import Orchestrator
from app.db import Base
from app.models.cases import Case
from app.models.customers import Customer
from app.models.enums import CaseState, CaseType
from app.models.merchants import Merchant
from app.sim.generators import SyntheticPopulation, generate_population
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


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


def _seed_synthetic_data(session: Session, population: SyntheticPopulation) -> dict[uuid4, Case]:
    """Seed the database with synthetic data and return mapping from transaction ID to Case."""
    # Add merchants
    for merchant in population.merchants:
        session.add(Merchant(
            id=merchant.id,
            name=merchant.name,
            currency=merchant.currency,
            risk_appetite=merchant.risk_appetite,
            max_retries_default=merchant.max_retries_default,
            contact_budget_per_week=merchant.contact_budget_per_week,
            mdr_bps=merchant.mdr_bps,
            autonomous_amount_ceiling_minor=merchant.autonomous_amount_ceiling_minor,
            created_at=merchant.created_at,
        ))

    # Flush merchants to get their IDs assigned before adding customers that reference them
    session.flush()

    # Add customers
    for customer in population.customers:
        # Note: We intentionally omit customer_patience as it's held-out truth
        session.add(Customer(
            id=customer.id,
            merchant_id=customer.merchant_id,
            email_hash=customer.email_hash,
            phone_hash=customer.phone_hash,
            region=customer.region,
            segment=customer.segment,
            lifetime_txn_count=customer.lifetime_txn_count,
            lifetime_success_rate=customer.lifetime_success_rate,
            prior_recovery_successes=customer.prior_recovery_successes,
            prior_declines=customer.prior_declines,
            do_not_contact=customer.do_not_contact,
            preferred_method=customer.preferred_method,
            consented_instruments_json=customer.consented_instruments_json,
            created_at=customer.created_at,
        ))

    # Flush customers before adding cases that reference them
    session.flush()

    # Add cases from transactions
    case_map = {}
    for txn in population.transactions:
        case = Case(
            id=txn.id,
            merchant_id=txn.merchant_id,
            customer_id=txn.customer_id,
            case_type=CaseType.FAILED_PAYMENT,  # All synthetic transactions are failed payments
            amount_at_risk_minor=txn.amount_minor,
            state=CaseState.DETECTED,
            detected_at=txn.created_at,
            priority_score=0.5,  # Default priority score
            recovery_deadline_at=txn.created_at + timedelta(days=7),
        )
        session.add(case)
        case_map[txn.id] = case

    session.flush()
    return case_map


def run_baseline_stop(session: Session, case_ids: list[uuid4]) -> dict:
    """Baseline: always choose STOP action."""
    clock.start()
    total_net_value = 0
    total_count = len(case_ids)

    for case_id in case_ids:
        case = session.get(Case, case_id)
        if case is None:
            continue

        # STOP baseline: net value is 0 (no recovery, no cost)
        total_net_value += 0  # STOP has zero net value by definition

    return {
        "name": "Always STOP",
        "total_net_value": total_net_value,
        "average_net_value": total_net_value / total_count if total_count > 0 else 0,
        "total_cases": total_count
    }


def run_decision_pipeline(session: Session, case_ids: list[uuid4]) -> dict:
    """Run the full decision pipeline on all cases."""
    clock.start()
    orchestrator = Orchestrator(session)
    total_net_value = 0
    total_count = len(case_ids)
    policy_verdicts = {}
    recommended_actions = {}

    for case_id in case_ids:
        case = session.get(Case, case_id)
        if case is None:
            continue

        try:
            result = orchestrator.orchestrate(case.id)

            # Extract the expected net value from the chosen action
            chosen_action = result["recommended_action"]
            for candidate in result["scored_candidates"]:
                if candidate["action_type"] == chosen_action:
                    total_net_value += candidate["enrv"]
                    break

            # Track policy verdicts and actions for reporting
            verdict = result["policy_verdict"]
            policy_verdicts[verdict] = policy_verdicts.get(verdict, 0) + 1
            action = result["recommended_action"]
            recommended_actions[action] = recommended_actions.get(action, 0) + 1

        except (ValueError, KeyError) as e:
            print(f"Error processing case {case_id}: {e}")
            # Continue with other cases

    return {
        "name": "Decision Pipeline",
        "total_net_value": total_net_value,
        "average_net_value": total_net_value / total_count if total_count > 0 else 0,
        "total_cases": total_count,
        "policy_verdicts": policy_verdicts,
        "recommended_actions": recommended_actions
    }


def main():
    """Main evaluation function."""
    print("Starting RevivePay-AI evaluation harness...")

    # Start the virtual clock
    clock.start()

    # Create database session
    session, engine = _create_session()

    try:
        # Generate synthetic population
        print("Generating synthetic population...")
        rng = np.random.default_rng(42)  # Fixed seed for reproducibility
        population = generate_population(
            n_merchants=5,
            n_customers_per_merchant=10,
            n_transactions_per_customer=3,
            rng=rng,
            seed=42
        )

        print(f"Generated {len(population.merchants)} merchants, {len(population.customers)} customers, {len(population.transactions)} transactions")

        # Seed the database with synthetic data
        print("Seeding database with synthetic data...")
        case_map = _seed_synthetic_data(session, population)
        case_ids = list(case_map.keys())
        print(f"Seeded {len(case_ids)} cases")

        # Run baselines
        print("\nRunning baselines...")
        stop_baseline = run_baseline_stop(session, case_ids)
        print(f"{stop_baseline['name']}: {stop_baseline['average_net_value']:.2f} net value per case")

        # Run decision pipeline
        print("\nRunning decision pipeline...")
        pipeline_results = run_decision_pipeline(session, case_ids)
        print(f"{pipeline_results['name']}: {pipeline_results['average_net_value']:.2f} net value per case")
        print(f"Policy verdicts: {pipeline_results['policy_verdicts']}")
        print(f"Recommended actions: {pipeline_results['recommended_actions']}")

        # Calculate improvement over baselines
        print("\nPerformance comparison:")
        baseline_names = [stop_baseline['name']]
        baseline_values = [stop_baseline['average_net_value']]

        improvement = pipeline_results['average_net_value'] - max(baseline_values)
        print(f"Decision pipeline vs best baseline: {improvement:+.2f} net value per case")
        if improvement > 0:
            print("[PASS] Decision pipeline outperforms baselines!")
        else:
            print("[FAIL] Decision pipeline underperforms baselines - needs improvement")

    finally:
        session.close()
        engine.dispose()

    print("\nEvaluation complete.")


if __name__ == "__main__":
    main()