"""
tests/test_repositories.py — Repository layer behaviour tests.

Uses an in-memory SQLite engine with a fresh schema per test.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, create_engine, event, func, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — register metadata
from app.db import Base
from app.models.actions import Action
from app.models.cases import Case
from app.models.customers import Customer
from app.models.decisions import Decision
from app.models.enums import ActionStatus, ActionType, CaseState, CaseType, PolicyVerdict
from app.models.merchants import Merchant
from app.repositories.actions import ActionRepository
from app.repositories.audit import AuditRepository
from app.repositories.base import BaseRepository
from app.repositories.cases import CaseRepository
from app.repositories.errors import ConflictError, IllegalStateTransition, NotFoundError


def _enable_fk(dbapi_conn: object, _connection_record: object) -> None:
    cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def engine() -> Generator[Engine, None, None]:
    # StaticPool keeps a single connection so create_all is visible to sessions.
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(eng, "connect", _enable_fk)
    with eng.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def session(engine: Engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as sess:
        sess.execute(text("PRAGMA foreign_keys=ON"))
        yield sess
        sess.rollback()


def _seed_merchant_customer(session: Session) -> tuple[Merchant, Customer]:
    merchant = Merchant(
        id=uuid.uuid4(),
        name="Repo Test Merchant",
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
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        email_hash="e" * 64,
        phone_hash="p" * 64,
        region="IN-KA",
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


def _seed_case(session: Session, merchant: Merchant, customer: Customer) -> Case:
    case = Case(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        customer_id=customer.id,
        case_type=CaseType.FAILED_PAYMENT,
        amount_at_risk_minor=500_00,
        state=CaseState.DETECTED,
        attempts_used=0,
        priority_score=0.5,
        recovery_deadline_at=datetime.now(UTC) + timedelta(days=2),
        recovered_amount_minor=0,
    )
    session.add(case)
    session.flush()
    return case


def _seed_decision(session: Session, case: Case) -> Decision:
    decision = Decision(
        id=uuid.uuid4(),
        case_id=case.id,
        seq=1,
        features_json={},
        feature_version="v1",
        risk_model_version="rm1",
        p_calibrated=0.5,
        candidate_scores_json={},
        llm_provider="mock",
        llm_model="mock",
        prompt_version="p1",
        prompt_hash="a" * 64,
        validation_status="valid",
        validation_errors_json={},
        policy_version="pol1",
        policy_verdict=PolicyVerdict.APPROVE,
        applied_rules_json={},
        violated_rules_json={},
        chosen_action=ActionType.RETRY_NOW,
        chosen_params_json={},
        expected_net_value_minor=100,
        decision_latency_ms=1,
        seed=1,
        fallback_used=False,
    )
    session.add(decision)
    session.flush()
    return decision


def test_create_idempotent_conflict_leaves_one_row(session: Session) -> None:
    merchant, customer = _seed_merchant_customer(session)
    case = _seed_case(session, merchant, customer)
    decision = _seed_decision(session, case)
    repo = ActionRepository(session)
    key = "idem-key-shared"
    first = Action(
        id=uuid.uuid4(),
        case_id=case.id,
        decision_id=decision.id,
        idempotency_key=key,
        action_type=ActionType.RETRY_NOW,
        params_json={},
        adapter="simulated",
        state=ActionStatus.PENDING,
        attempt_no=1,
        cost_minor=0,
    )
    second = Action(
        id=uuid.uuid4(),
        case_id=case.id,
        decision_id=decision.id,
        idempotency_key=key,
        action_type=ActionType.RETRY_NOW,
        params_json={},
        adapter="simulated",
        state=ActionStatus.PENDING,
        attempt_no=1,
        cost_minor=0,
    )

    created = repo.create_idempotent(first)
    with pytest.raises(ConflictError) as excinfo:
        repo.create_idempotent(second)

    assert excinfo.value.existing_id == created.id
    count = session.scalar(select(func.count()).select_from(Action))
    assert count == 1


def test_audit_append_hash_chain_and_gapless_seq(session: Session) -> None:
    repo = AuditRepository(session)
    e1 = repo.append({"actor": "system", "event_type": "boot", "payload_json": {"n": 1}})
    e2 = repo.append({"actor": "agent", "event_type": "decide", "payload_json": {"n": 2}})
    e3 = repo.append({"actor": "policy", "event_type": "verdict", "payload_json": {"n": 3}})

    assert e1.seq == 1
    assert e2.seq == 2
    assert e3.seq == 3
    assert e1.prev_hash == "0" * 64
    assert e2.prev_hash == e1.hash
    assert e3.prev_hash == e2.hash
    assert e1.hash != e2.hash != e3.hash


def test_transition_state_illegal_raises_and_does_not_modify(session: Session) -> None:
    merchant, customer = _seed_merchant_customer(session)
    case = _seed_case(session, merchant, customer)
    repo = CaseRepository(session)

    with pytest.raises(IllegalStateTransition):
        repo.transition_state(case.id, CaseState.CLOSED)

    session.refresh(case)
    assert case.state == CaseState.DETECTED


def test_get_or_raise_missing_id(session: Session) -> None:
    repo: BaseRepository[Case] = BaseRepository(session, Case)
    missing = uuid.uuid4()
    with pytest.raises(NotFoundError):
        repo.get_or_raise(missing)
