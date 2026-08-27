"""
tests/test_generators.py — Behavioural tests for the synthetic population generator.

Each test has a docstring naming the exact property it protects.  No
pytest.mark.skip or pytest.mark.xfail is used anywhere in this file.

The generator lives inside ``app/sim/`` and is imported here from within
the test suite.  Tests live outside ``app/sim/``, but test files are
explicitly excluded from the architecture ban (they call the held-out
world for grading and evaluation).  The architecture test already asserts
that *application* modules outside ``app/sim/`` cannot import generators.

Arithmetic notes:
  - All monetary amounts are integer paise (never float).
  - ``customer_patience`` is held-out: present on SyntheticCustomer,
    absent from the ORM Customer model.
  - ``is_test`` must always be True on generated transactions.
  - Two generators with the same seed must produce identical populations.
  - A generator with a different seed must produce a different population.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import numpy as np
import pytest

from app.sim.generators import (
    _RAIL_TO_PAYMENT_METHOD,
    SyntheticPopulation,
    generate_population,
)

# ---------------------------------------------------------------------------
# Shared small population used by most tests.
# ---------------------------------------------------------------------------

_N_MERCHANTS = 3
_N_CUSTOMERS = 4
_N_TRANSACTIONS = 5
_SEED = 42


@pytest.fixture(scope="module")
def pop() -> SyntheticPopulation:
    """A small reproducible population (3 merchants × 4 customers × 5 txns)."""
    rng = np.random.default_rng(_SEED)
    return generate_population(_N_MERCHANTS, _N_CUSTOMERS, _N_TRANSACTIONS, rng, seed=_SEED)


# ---------------------------------------------------------------------------
# Test 1 — Counts: generate_population returns the correct number of rows.
# ---------------------------------------------------------------------------


def test_population_counts(pop: SyntheticPopulation) -> None:
    """Protect: generate_population must produce exactly
    n_merchants merchants, n_merchants×n_customers_per_merchant customers,
    and n_merchants×n_customers_per_merchant×n_transactions_per_customer
    transactions.
    """
    assert len(pop.merchants) == _N_MERCHANTS
    assert len(pop.customers) == _N_MERCHANTS * _N_CUSTOMERS
    assert len(pop.transactions) == _N_MERCHANTS * _N_CUSTOMERS * _N_TRANSACTIONS


# ---------------------------------------------------------------------------
# Test 2 — Reproducibility: same seed → identical population.
# ---------------------------------------------------------------------------


def test_same_seed_produces_identical_population() -> None:
    """Protect: two numpy generators initialised with the same seed must
    produce byte-for-byte identical populations.  This is the fundamental
    reproducibility guarantee: training and evaluation use different seeds,
    so any drift in seed→data mapping would corrupt the experimental split.
    """
    rng_a = np.random.default_rng(99)
    rng_b = np.random.default_rng(99)
    pop_a = generate_population(2, 3, 4, rng_a, seed=99)
    pop_b = generate_population(2, 3, 4, rng_b, seed=99)

    # Compare UUIDs — they're the most sensitive indicator of divergence.
    ids_a = [str(m.id) for m in pop_a.merchants]
    ids_b = [str(m.id) for m in pop_b.merchants]
    assert ids_a == ids_b, "merchant IDs diverged between identical seeds"

    cids_a = [str(c.id) for c in pop_a.customers]
    cids_b = [str(c.id) for c in pop_b.customers]
    assert cids_a == cids_b, "customer IDs diverged between identical seeds"

    tids_a = [(str(t.id), t.amount_minor, t.failure_class) for t in pop_a.transactions]
    tids_b = [(str(t.id), t.amount_minor, t.failure_class) for t in pop_b.transactions]
    assert tids_a == tids_b, "transaction data diverged between identical seeds"


# ---------------------------------------------------------------------------
# Test 3 — Different seeds produce different populations.
# ---------------------------------------------------------------------------


def test_different_seeds_produce_different_populations() -> None:
    """Protect: seeds 1 and 2 must produce distinct merchant IDs.  Without
    this check a bug that ignores the seed would pass the reproducibility
    test while making training/eval splits meaningless.
    """
    pop1 = generate_population(2, 2, 2, np.random.default_rng(1), seed=1)
    pop2 = generate_population(2, 2, 2, np.random.default_rng(2), seed=2)
    ids1 = {str(m.id) for m in pop1.merchants}
    ids2 = {str(m.id) for m in pop2.merchants}
    assert ids1 != ids2, "seeds 1 and 2 produced identical merchant IDs"


# ---------------------------------------------------------------------------
# Test 4 — Amounts are always positive integer paise.
# ---------------------------------------------------------------------------


def test_all_amounts_are_positive_integer_paise(pop: SyntheticPopulation) -> None:
    """Protect: amount_minor must be a positive integer (never float, never
    zero or negative).  Storing float paise would violate the project-wide
    financial-safety invariant and corrupt every net-EV calculation.
    """
    for txn in pop.transactions:
        assert isinstance(txn.amount_minor, int), f"amount_minor {txn.amount_minor!r} is not int"
        assert txn.amount_minor > 0, f"amount_minor {txn.amount_minor} must be > 0"


# ---------------------------------------------------------------------------
# Test 5 — All transactions are labelled is_test=True.
# ---------------------------------------------------------------------------


def test_all_transactions_are_labelled_test(pop: SyntheticPopulation) -> None:
    """Protect: every generated transaction must have is_test=True.
    Simulated data must be visibly labelled so it can never be mistaken
    for production traffic in a dashboard or audit log.
    """
    for txn in pop.transactions:
        assert txn.is_test is True, f"transaction {txn.id} has is_test={txn.is_test}"


# ---------------------------------------------------------------------------
# Test 6 — Referential integrity: every customer and transaction references
#           a merchant in the same population.
# ---------------------------------------------------------------------------


def test_referential_integrity(pop: SyntheticPopulation) -> None:
    """Protect: every customer's merchant_id and every transaction's
    merchant_id and customer_id must resolve to an object in the same
    population.  A broken foreign key would cause ORM insertion to fail
    and would make join-based training features impossible.
    """
    merchant_ids = {m.id for m in pop.merchants}
    customer_ids = {c.id for c in pop.customers}

    for c in pop.customers:
        assert c.merchant_id in merchant_ids, (
            f"customer {c.id} references unknown merchant {c.merchant_id}"
        )
    for t in pop.transactions:
        assert t.merchant_id in merchant_ids, (
            f"transaction {t.id} references unknown merchant {t.merchant_id}"
        )
        assert t.customer_id in customer_ids, (
            f"transaction {t.id} references unknown customer {t.customer_id}"
        )


# ---------------------------------------------------------------------------
# Test 7 — Email/phone hashes are exactly 64 hex characters and contain no
#           real PII (verified by checking the pre-image is synthetic).
# ---------------------------------------------------------------------------


def test_hashes_are_64_hex_and_synthetic(pop: SyntheticPopulation) -> None:
    """Protect: email_hash and phone_hash must be 64-character lowercase hex
    strings (SHA-256 output).  They must be derived from a known synthetic
    pattern, never from real email addresses or phone numbers.
    """
    for _i, c in enumerate(pop.customers):
        assert len(c.email_hash) == 64, f"email_hash length {len(c.email_hash)} != 64"
        assert c.email_hash == c.email_hash.lower(), "email_hash must be lowercase hex"
        assert all(ch in "0123456789abcdef" for ch in c.email_hash), "email_hash is not valid hex"
        assert len(c.phone_hash) == 64, f"phone_hash length {len(c.phone_hash)} != 64"

    # Spot-check: the first customer's email_hash must match the known
    # synthetic pattern m00000-c00000000, proving no real data was used.
    first = pop.customers[0]
    expected_email = hashlib.sha256(b"synthetic-m00000-c00000000@sim.revivepay.invalid").hexdigest()
    assert first.email_hash == expected_email, (
        f"email_hash {first.email_hash!r} does not match expected synthetic pattern"
    )


# ---------------------------------------------------------------------------
# Test 8 — customer_patience is in [0.0, 1.0] and NOT an ORM field.
# ---------------------------------------------------------------------------


def test_customer_patience_range_and_not_in_orm(pop: SyntheticPopulation) -> None:
    """Protect: customer_patience must be a float in [0.0, 1.0] on every
    SyntheticCustomer (it feeds ActionContext in the environment).  It must
    also NOT appear as a field on the ORM Customer model — latent patience
    is held-out world truth and must stay physically unreachable from the
    decision pipeline.
    """
    from app.models.customers import Customer as OrmCustomer

    # ORM model must have no patience attribute at all.
    assert not hasattr(OrmCustomer, "customer_patience"), (
        "ORM Customer must not have a customer_patience column"
    )
    assert not hasattr(OrmCustomer, "patience"), "ORM Customer must not have a patience column"

    # SyntheticCustomer must carry patience and it must be in [0, 1].
    for c in pop.customers:
        assert 0.0 <= c.customer_patience <= 1.0, (
            f"customer_patience {c.customer_patience} out of [0, 1]"
        )


# ---------------------------------------------------------------------------
# Test 9 — Segment values are drawn from the known enum set.
# ---------------------------------------------------------------------------


def test_customer_segments_are_valid_enum_values(pop: SyntheticPopulation) -> None:
    """Protect: every generated customer segment must be a member of the
    CustomerSegment enum (NEW, OCCASIONAL, LOYAL, HIGH_VALUE).  An
    out-of-vocabulary segment would cause a KeyError in the economics
    calculator and a foreign-key-equivalent failure in any ML feature lookup.
    """
    from app.models.enums import CustomerSegment

    valid = {s.value for s in CustomerSegment}
    for c in pop.customers:
        assert c.segment in valid, f"customer segment {c.segment!r} not in CustomerSegment enum"


# ---------------------------------------------------------------------------
# Test 10 — Rail values are drawn from the known Rail enum, and the
#            payment_method matches the canonical rail→method mapping.
# ---------------------------------------------------------------------------


def test_transaction_rails_and_payment_methods_are_consistent(
    pop: SyntheticPopulation,
) -> None:
    """Protect: every transaction's rail must be a member of the Rail enum
    and its payment_method must match the canonical rail→method mapping.
    An inconsistency here (e.g. rail=RAIL_UPI, method=card) would make
    RETRY_ALTERNATE_RAIL semantically meaningless and corrupt downtime
    window logic.
    """
    from app.models.enums import Rail

    valid_rails = {r.value for r in Rail}
    for txn in pop.transactions:
        assert txn.rail in valid_rails, f"rail {txn.rail!r} not in Rail enum"
        expected_method = _RAIL_TO_PAYMENT_METHOD[txn.rail]
        assert txn.payment_method == expected_method, (
            f"transaction rail={txn.rail} but payment_method={txn.payment_method!r} "
            f"(expected {expected_method!r})"
        )


# ---------------------------------------------------------------------------
# Test 11 — Failure classes are drawn from the known FailureClass set
#            (no UNKNOWN in generated data).
# ---------------------------------------------------------------------------


def test_failure_classes_are_valid_and_not_unknown(pop: SyntheticPopulation) -> None:
    """Protect: generated transactions must have a known, non-UNKNOWN failure
    class.  UNKNOWN represents an unclassifiable real gateway message; it
    must not appear in synthetic training data because no model should learn
    to expect it as a recoverable class.
    """
    from app.models.enums import FailureClass

    valid = {fc.value for fc in FailureClass} - {FailureClass.UNKNOWN.value}
    for txn in pop.transactions:
        assert txn.failure_class in valid, (
            f"failure_class {txn.failure_class!r} is not a known non-UNKNOWN class"
        )


# ---------------------------------------------------------------------------
# Test 12 — UUIDs are unique across the entire population.
# ---------------------------------------------------------------------------


def test_all_uuids_are_unique(pop: SyntheticPopulation) -> None:
    """Protect: no two objects in the population may share a UUID.  Duplicate
    primary keys would cause ORM insertion to fail (uniqueness constraint)
    and corrupt any cross-table join used in feature engineering.
    """
    all_ids: list[uuid.UUID] = (
        [m.id for m in pop.merchants]
        + [c.id for c in pop.customers]
        + [t.id for t in pop.transactions]
    )
    assert len(all_ids) == len(set(all_ids)), (
        f"UUID collision: {len(all_ids)} objects but only {len(set(all_ids))} unique IDs"
    )


# ---------------------------------------------------------------------------
# Test 13 — SyntheticCustomer fields map to ORM Customer columns (no extras,
#            no missing required columns).
# ---------------------------------------------------------------------------


def test_synthetic_customer_covers_orm_columns(pop: SyntheticPopulation) -> None:
    """Protect: every non-nullable ORM Customer column (except server defaults
    and the patience columns that must NOT exist) must be populated on every
    SyntheticCustomer.  This ensures that blindly iterating over
    pop.customers and inserting each one will not raise a NOT NULL violation.
    """
    required_attrs = [
        "id",
        "merchant_id",
        "email_hash",
        "phone_hash",
        "region",
        "segment",
        "lifetime_txn_count",
        "lifetime_success_rate",
        "prior_recovery_successes",
        "prior_declines",
        "do_not_contact",
        "preferred_method",
        "consented_instruments_json",
    ]
    for c in pop.customers:
        for attr in required_attrs:
            assert hasattr(c, attr), f"SyntheticCustomer missing attribute {attr!r}"
            assert getattr(c, attr) is not None, (
                f"SyntheticCustomer.{attr} is None for customer {c.id}"
            )


# ---------------------------------------------------------------------------
# Test 14 — generate_population rejects invalid count arguments loudly.
# ---------------------------------------------------------------------------


def test_generate_population_rejects_zero_counts() -> None:
    """Protect: passing n_merchants=0 or other non-positive counts must raise
    ValueError immediately.  Silently producing an empty dataset would be a
    difficult-to-diagnose bug in a data pipeline.
    """
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="n_merchants"):
        generate_population(0, 5, 5, rng)

    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="n_customers_per_merchant"):
        generate_population(1, 0, 5, rng)

    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="n_transactions_per_customer"):
        generate_population(1, 1, 0, rng)


# ---------------------------------------------------------------------------
# Test 15 — seed metadata round-trips correctly.
# ---------------------------------------------------------------------------


def test_seed_stored_on_population(pop: SyntheticPopulation) -> None:
    """Protect: the seed passed to generate_population must be preserved
    verbatim on the returned SyntheticPopulation.seed for audit purposes.
    A pipeline that logs the seed for later reproducibility must be able
    to read it back without recomputing it.
    """
    assert pop.seed == _SEED

    # A population generated without an explicit seed must record None.
    rng = np.random.default_rng(7)
    pop_no_seed = generate_population(1, 1, 1, rng)
    assert pop_no_seed.seed is None


# ---------------------------------------------------------------------------
# Test 16 — Merchants have valid, non-empty field values.
# ---------------------------------------------------------------------------


def test_merchant_fields_are_valid(pop: SyntheticPopulation) -> None:
    """Protect: generated merchants must have non-empty names, INR currency,
    positive integer monetary fields, and a valid risk_appetite string.
    """
    valid_appetites = {"conservative", "balanced", "aggressive"}
    for m in pop.merchants:
        assert m.currency == "INR"
        assert m.name.startswith("Merchant-")
        assert m.risk_appetite in valid_appetites
        assert m.contact_budget_per_week >= 1, "contact_budget_per_week must be >= 1"
        assert m.mdr_bps >= 100, "mdr_bps suspiciously low"
        assert isinstance(m.autonomous_amount_ceiling_minor, int), (
            "autonomous_amount_ceiling_minor must be int paise"
        )
        assert m.autonomous_amount_ceiling_minor > 0


# ---------------------------------------------------------------------------
# Test 17 — generate_population can be called with a custom base_time and the
#            transaction timestamps respect the 180-day window.
# ---------------------------------------------------------------------------


def test_transaction_timestamps_within_window() -> None:
    """Protect: all transaction created_at timestamps must fall within the
    180-day window ending at base_time.  A timestamp after base_time would
    mean a transaction 'in the future', which would corrupt time-series
    feature ordering.
    """
    base = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    rng = np.random.default_rng(77)
    p = generate_population(2, 3, 10, rng, base_time=base)

    from datetime import timedelta

    earliest_allowed = base - timedelta(days=180)
    for txn in p.transactions:
        assert txn.created_at <= base, (
            f"transaction {txn.id} created_at {txn.created_at} is after base_time {base}"
        )
        assert txn.created_at >= earliest_allowed, (
            f"transaction {txn.id} created_at {txn.created_at} is before 180-day window"
        )
