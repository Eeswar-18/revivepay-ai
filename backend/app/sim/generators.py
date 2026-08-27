"""
app/sim/generators.py — Deterministic synthetic population generator.

THIS MODULE IS PART OF THE HELD-OUT SIMULATION.  No module outside
``app/sim/`` may import it.  That constraint is enforced by the universal
held-out boundary check in ``backend/tests/test_architecture.py``.

Generates synthetic merchants, customers, and failed transactions for use
in training-data seeding and evaluation harness runs.  All randomness comes
exclusively from the ``rng`` argument supplied by the caller — there is no
module-level RNG, no call to ``numpy.random.seed``, and no use of the
``random`` standard-library module.  Reproducibility is entirely the
caller's responsibility.

Output is plain frozen dataclasses.  The caller is responsible for
persistence; generators.py has no database dependency.

Key design constraints:
- Integer paise for all monetary amounts (never float, never Decimal).
- No real PII.  Customer identifiers are synthetic; email/phone values are
  hashed from deterministic seeds, never from real data.
- ``customer_patience`` is a held-out latent trait.  It is present on
  ``SyntheticCustomer`` (the generator produces it because the world needs
  it to build ``ActionContext``) but MUST NOT be written to the ORM
  ``Customer`` table.  The ORM model deliberately has no patience column.
- Failure-class weights are module constants, not read from
  ``world_config.yaml``.  They are observable business priors, not
  held-out ground truth, following the same rationale as ``banding.py``.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Population weights — module constants, NOT read from world_config.yaml.
# These mirror the observable priors from that file (segment weights, rail
# weights, amount-band weights) or are synthetic priors (failure-class
# weights) that a merchant could estimate from its own gateway data.
# ---------------------------------------------------------------------------

# Customer segments and their sampling probabilities.
# Mirrors world_config.yaml section 6 customer_segments[*].weight.
_SEGMENT_NAMES: list[str] = ["NEW", "OCCASIONAL", "LOYAL", "HIGH_VALUE"]
_SEGMENT_WEIGHTS: list[float] = [0.30, 0.40, 0.22, 0.08]

# Payment rails and their sampling probabilities.
# Mirrors world_config.yaml section 10 rails[*].weight.
_RAIL_NAMES: list[str] = ["RAIL_A", "RAIL_B", "RAIL_UPI", "RAIL_NETBANKING"]
_RAIL_WEIGHTS: list[float] = [0.40, 0.25, 0.25, 0.10]

# Rail → canonical payment_method string.
_RAIL_TO_PAYMENT_METHOD: dict[str, str] = {
    "RAIL_A": "card",
    "RAIL_B": "card",
    "RAIL_UPI": "upi",
    "RAIL_NETBANKING": "netbanking",
}

# Amount-band weights and their paise ranges (inclusive lower, inclusive upper).
# Mirrors world_config.yaml section 7 amount_bands[*].weight and max_minor.
# XLARGE upper bound is synthetic (Rs 5_00_000 = 5_00_00_000 paise) — the
# band is open-ended in the config; we cap it for uniform draws.
_BAND_NAMES: list[str] = ["MICRO", "SMALL", "MEDIUM", "LARGE", "XLARGE"]
_BAND_WEIGHTS: list[float] = [0.34, 0.38, 0.20, 0.065, 0.015]
_BAND_RANGES: list[tuple[int, int]] = [
    (100, 10_000),  # MICRO:  Rs 1 – Rs 100
    (10_001, 100_000),  # SMALL:  Rs 100.01 – Rs 1,000
    (100_001, 1_000_000),  # MEDIUM: Rs 1,000.01 – Rs 10,000
    (1_000_001, 5_000_000),  # LARGE:  Rs 10,000.01 – Rs 50,000
    (5_000_001, 50_000_000),  # XLARGE: Rs 50,000.01 – Rs 5,00,000 (synthetic cap)
]

# Failure-class weights.  These are synthetic observable priors that a
# merchant could estimate from gateway decline codes.  They are NOT ground-
# truth probabilities and NOT read from world_config.yaml.
_FAILURE_CLASS_NAMES: list[str] = [
    "INSUFFICIENT_FUNDS",
    "BANK_DOWNTIME",
    "NETWORK_TIMEOUT",
    "AUTH_FAILURE",
    "LIMIT_EXCEEDED",
    "RISK_DECLINE",
    "CARD_EXPIRED",
    "HARD_DECLINE",
]
_FAILURE_CLASS_WEIGHTS: list[float] = [0.28, 0.08, 0.12, 0.15, 0.07, 0.10, 0.10, 0.10]

# Merchant risk appetite options.
_RISK_APPETITES: list[str] = ["conservative", "balanced", "aggressive"]
_RISK_APPETITE_WEIGHTS: list[float] = [0.25, 0.55, 0.20]

# Preferred payment methods (independent of rail — per-customer default).
_PREFERRED_METHODS: list[str] = ["card", "upi", "netbanking", "wallet"]
_PREFERRED_METHOD_WEIGHTS: list[float] = [0.45, 0.30, 0.15, 0.10]

# Indian region codes — synthetic, no real personal data.
_REGIONS: list[str] = [
    "IN-MH",
    "IN-KA",
    "IN-TN",
    "IN-DL",
    "IN-GJ",
    "IN-WB",
    "IN-TS",
    "IN-RJ",
    "IN-UP",
    "IN-KL",
]

# Checkout stages.
_CHECKOUT_STAGES: list[str] = ["cart", "checkout", "payment", "confirmation"]
_CHECKOUT_WEIGHTS: list[float] = [0.10, 0.20, 0.60, 0.10]

# Device types.
_DEVICES: list[str] = ["mobile_web", "mobile_app", "desktop_web", "desktop_app"]
_DEVICE_WEIGHTS: list[float] = [0.45, 0.30, 0.20, 0.05]


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticMerchant:
    """A fully-specified synthetic merchant, ready for ORM insertion.

    All fields correspond 1-to-1 with ``app.models.merchants.Merchant``
    columns.
    """

    id: uuid.UUID
    name: str
    currency: str
    risk_appetite: str
    max_retries_default: int
    contact_budget_per_week: int  # COUNT, not money — see Merchant model comment
    mdr_bps: int
    autonomous_amount_ceiling_minor: int  # integer paise
    created_at: datetime


@dataclass(frozen=True)
class SyntheticCustomer:
    """A fully-specified synthetic customer.

    ``customer_patience`` is held-out latent truth.  It must be used when
    building ``app.sim.environment.ActionContext`` but must NEVER be written
    to the ORM ``Customer`` table, which has no patience column by design.
    """

    id: uuid.UUID
    merchant_id: uuid.UUID
    email_hash: str  # SHA-256 of a synthetic address, never real PII
    phone_hash: str  # SHA-256 of a synthetic number, never real PII
    region: str
    segment: str  # one of CustomerSegment enum values
    customer_patience: float  # HELD-OUT — do NOT write to Customer ORM row
    created_at: datetime
    lifetime_txn_count: int
    lifetime_success_rate: float
    prior_recovery_successes: int
    prior_declines: int
    do_not_contact: bool
    preferred_method: str
    consented_instruments_json: dict[str, Any]


@dataclass(frozen=True)
class SyntheticTransaction:
    """A fully-specified synthetic failed transaction.

    All fields correspond 1-to-1 with ``app.models.transactions.Transaction``
    columns (including the new ``rail`` column added in Step 4 ITEM 1).
    """

    id: uuid.UUID
    merchant_id: uuid.UUID
    customer_id: uuid.UUID
    amount_minor: int  # integer paise, never float
    currency: str
    created_at: datetime
    payment_method: str
    rail: str  # one of Rail enum values
    card_network: str | None
    issuer_id: str | None
    status: str  # always "failed" for synthetic training data
    failure_code: str
    failure_class: str  # one of FailureClass enum values (no UNKNOWN in generated data)
    failure_message_raw: str
    attempt_no: int
    is_subscription: bool
    subscription_cycle: str | None
    checkout_stage: str
    device: str
    original_transaction_id: uuid.UUID | None
    is_test: bool  # always True — simulated data must be visibly labelled


@dataclass(frozen=True)
class SyntheticPopulation:
    """The complete generated dataset: merchants, customers, transactions.

    Attributes
    ----------
    merchants:
        List of synthetic merchants.
    customers:
        List of synthetic customers.  ``customer_patience`` on each entry
        is held-out truth; strip it before ORM insertion.
    transactions:
        List of synthetic failed transactions that will become Cases.
    seed:
        The numpy seed used to produce this population, for audit trail.
    """

    merchants: list[SyntheticMerchant]
    customers: list[SyntheticCustomer]
    transactions: list[SyntheticTransaction]
    seed: int | None  # None if the caller used an unseeded generator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_uuid(rng: np.random.Generator) -> uuid.UUID:
    """Generate a UUID from the RNG by drawing two independent uint64 halves.

    ``numpy.random.Generator.integers`` is bounded to int64 (max 2**63-1).
    A UUID requires 128 bits of randomness, so we draw two 64-bit values and
    pack them together.  Using ``dtype=np.uint64`` avoids signed-integer
    overflow; the two halves are combined into a 128-bit Python int.
    """
    hi = int(rng.integers(0, 2**64, dtype=np.uint64))
    lo = int(rng.integers(0, 2**64, dtype=np.uint64))
    return uuid.UUID(int=(hi << 64) | lo)


def _sha256_hex(value: str) -> str:
    """Return the 64-character SHA-256 hex digest of *value* (UTF-8 encoded)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _choice(options: list[str], weights: list[float], rng: np.random.Generator) -> str:
    """Draw one element from *options* with the given *weights*."""
    cumulative = np.cumsum(weights)
    cumulative = cumulative / cumulative[-1]  # normalise in case of float drift
    idx = int(np.searchsorted(cumulative, rng.random()))
    return options[min(idx, len(options) - 1)]


def _generate_amount_minor(rng: np.random.Generator) -> int:
    """Draw a transaction amount in integer paise from the band distribution."""
    band = _choice(_BAND_NAMES, _BAND_WEIGHTS, rng)
    idx = _BAND_NAMES.index(band)
    lo, hi = _BAND_RANGES[idx]
    return int(rng.integers(lo, hi + 1))


def _synthetic_email_hash(merchant_idx: int, customer_idx: int) -> str:
    """Deterministic email hash — input is purely synthetic indices, no real PII."""
    synthetic = f"synthetic-m{merchant_idx:05d}-c{customer_idx:08d}@sim.revivepay.invalid"
    return _sha256_hex(synthetic)


def _synthetic_phone_hash(merchant_idx: int, customer_idx: int) -> str:
    """Deterministic phone hash — input is purely synthetic indices, no real PII."""
    synthetic = f"sim-phone-m{merchant_idx:05d}-c{customer_idx:08d}"
    return _sha256_hex(synthetic)


def _generate_merchant(idx: int, rng: np.random.Generator) -> SyntheticMerchant:
    """Generate one synthetic merchant."""
    risk_appetite = _choice(_RISK_APPETITES, _RISK_APPETITE_WEIGHTS, rng)

    # Autonomous ceiling depends on risk appetite: more aggressive → higher ceiling.
    ceiling_choices = {
        "conservative": (50_000, 200_000),  # Rs 500 – Rs 2,000
        "balanced": (200_000, 1_000_000),  # Rs 2,000 – Rs 10,000
        "aggressive": (1_000_000, 5_000_000),  # Rs 10,000 – Rs 50,000
    }
    lo, hi = ceiling_choices[risk_appetite]
    ceiling_minor = int(rng.integers(lo, hi + 1))

    max_retries = int(rng.integers(2, 6))  # 2–5 retries
    contact_budget = int(rng.integers(2, 8))  # 2–7 contacts per week

    # mdr_bps: between 150 and 250 (1.5%–2.5%)
    mdr_bps = int(rng.integers(150, 251))

    # Anchor timestamps at a fixed epoch so the dataset is deterministic.
    created_at = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(
        days=int(rng.integers(0, 180))
    )

    return SyntheticMerchant(
        id=_make_uuid(rng),
        name=f"Merchant-{idx:04d}",
        currency="INR",
        risk_appetite=risk_appetite,
        max_retries_default=max_retries,
        contact_budget_per_week=contact_budget,
        mdr_bps=mdr_bps,
        autonomous_amount_ceiling_minor=ceiling_minor,
        created_at=created_at,
    )


def _generate_customer(
    merchant: SyntheticMerchant,
    merchant_idx: int,
    customer_idx: int,
    rng: np.random.Generator,
) -> SyntheticCustomer:
    """Generate one synthetic customer belonging to *merchant*."""
    segment = _choice(_SEGMENT_NAMES, _SEGMENT_WEIGHTS, rng)
    region = _REGIONS[int(rng.integers(0, len(_REGIONS)))]
    preferred_method = _choice(_PREFERRED_METHODS, _PREFERRED_METHOD_WEIGHTS, rng)

    # Latent patience: Beta(2.5, 2.5) — held-out, never stored in ORM.
    patience = float(rng.beta(2.5, 2.5))

    lifetime_txn_count = int(rng.integers(1, 201))  # 1–200
    # Success rate bounded away from exact 0/1 to avoid degenerate models.
    lifetime_success_rate = float(np.clip(rng.beta(4.0, 1.5), 0.05, 0.99))

    prior_recovery_successes = int(rng.integers(0, 11))  # 0–10
    prior_declines = int(rng.integers(0, 21))  # 0–20

    # Rare do_not_contact flag (~5% of customers).
    do_not_contact = bool(rng.random() < 0.05)

    # Timestamps: customer created after their merchant.
    customer_created = merchant.created_at + timedelta(days=int(rng.integers(0, 90)))

    return SyntheticCustomer(
        id=_make_uuid(rng),
        merchant_id=merchant.id,
        email_hash=_synthetic_email_hash(merchant_idx, customer_idx),
        phone_hash=_synthetic_phone_hash(merchant_idx, customer_idx),
        region=region,
        segment=segment,
        customer_patience=patience,
        created_at=customer_created,
        lifetime_txn_count=lifetime_txn_count,
        lifetime_success_rate=lifetime_success_rate,
        prior_recovery_successes=prior_recovery_successes,
        prior_declines=prior_declines,
        do_not_contact=do_not_contact,
        preferred_method=preferred_method,
        consented_instruments_json={},
    )


def _generate_transaction(
    merchant: SyntheticMerchant,
    customer: SyntheticCustomer,
    base_time: datetime,
    rng: np.random.Generator,
) -> SyntheticTransaction:
    """Generate one synthetic failed transaction for the given merchant/customer."""
    rail = _choice(_RAIL_NAMES, _RAIL_WEIGHTS, rng)
    payment_method = _RAIL_TO_PAYMENT_METHOD[rail]
    failure_class = _choice(_FAILURE_CLASS_NAMES, _FAILURE_CLASS_WEIGHTS, rng)

    amount_minor = _generate_amount_minor(rng)

    # Card-only fields.
    card_network: str | None = None
    issuer_id: str | None = None
    if payment_method == "card":
        card_network = _choice(["VISA", "MASTERCARD", "RUPAY"], [0.40, 0.35, 0.25], rng)
        issuer_id = f"ISSUER_{int(rng.integers(1, 21)):02d}"

    # Transaction timestamp: spread over a 180-day window ending at base_time.
    offset_seconds = int(rng.integers(0, 180 * 24 * 3600))
    created_at = base_time - timedelta(seconds=offset_seconds)

    # Attempt number: mostly 1, occasionally 2 or 3.
    attempt_no = int(rng.choice([1, 2, 3], p=[0.75, 0.18, 0.07]))

    checkout_stage = _choice(_CHECKOUT_STAGES, _CHECKOUT_WEIGHTS, rng)
    device = _choice(_DEVICES, _DEVICE_WEIGHTS, rng)

    # Failure code is a synthetic gateway string derived from failure class.
    failure_code = f"ERR_{failure_class}"
    failure_message_raw = f"[SIM] {failure_class.lower().replace('_', ' ')} decline"

    # Subscription: ~10% of transactions.
    is_subscription = bool(rng.random() < 0.10)
    subscription_cycle: str | None = (
        _choice(["monthly", "quarterly", "annual"], [0.65, 0.25, 0.10], rng)
        if is_subscription
        else None
    )

    return SyntheticTransaction(
        id=_make_uuid(rng),
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount_minor=amount_minor,
        currency="INR",
        created_at=created_at,
        payment_method=payment_method,
        rail=rail,
        card_network=card_network,
        issuer_id=issuer_id,
        status="failed",
        failure_code=failure_code,
        failure_class=failure_class,
        failure_message_raw=failure_message_raw,
        attempt_no=attempt_no,
        is_subscription=is_subscription,
        subscription_cycle=subscription_cycle,
        checkout_stage=checkout_stage,
        device=device,
        original_transaction_id=None,
        is_test=True,  # synthetic data must always be labelled as test
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_population(
    n_merchants: int,
    n_customers_per_merchant: int,
    n_transactions_per_customer: int,
    rng: np.random.Generator,
    base_time: datetime | None = None,
    seed: int | None = None,
) -> SyntheticPopulation:
    """Generate a complete synthetic population of merchants, customers, and
    failed transactions.

    All randomness flows exclusively through *rng*.  The caller is
    responsible for seeding it and for recording the seed in the audit trail.
    This function never calls ``numpy.random.seed`` or uses the ``random``
    standard-library module.

    Parameters
    ----------
    n_merchants:
        Number of synthetic merchants to generate.
    n_customers_per_merchant:
        Number of customers per merchant.  Total customers =
        ``n_merchants × n_customers_per_merchant``.
    n_transactions_per_customer:
        Number of failed transactions per customer.  Total transactions =
        ``n_merchants × n_customers_per_merchant × n_transactions_per_customer``.
    rng:
        Caller-supplied ``numpy.random.Generator``.  All draws are made
        against this object; the caller owns the seed.
    base_time:
        UTC datetime used as the reference point for transaction timestamps.
        Defaults to 2024-07-01 00:00:00 UTC when not supplied.  A fixed
        default makes small test calls deterministic without requiring the
        caller to specify it.
    seed:
        The seed value used to create *rng*, if known.  Stored on the
        returned :class:`SyntheticPopulation` for audit purposes only; it
        is not used to re-seed anything.

    Returns
    -------
    SyntheticPopulation
        Frozen collection of merchants, customers, transactions, and the
        seed metadata.

    Raises
    ------
    ValueError
        If any count argument is less than 1.
    """
    if n_merchants < 1:
        raise ValueError(f"n_merchants must be >= 1; got {n_merchants}")
    if n_customers_per_merchant < 1:
        raise ValueError(f"n_customers_per_merchant must be >= 1; got {n_customers_per_merchant}")
    if n_transactions_per_customer < 1:
        raise ValueError(
            f"n_transactions_per_customer must be >= 1; got {n_transactions_per_customer}"
        )

    if base_time is None:
        base_time = datetime(2024, 7, 1, 0, 0, 0, tzinfo=UTC)

    merchants: list[SyntheticMerchant] = []
    customers: list[SyntheticCustomer] = []
    transactions: list[SyntheticTransaction] = []

    for m_idx in range(n_merchants):
        merchant = _generate_merchant(m_idx, rng)
        merchants.append(merchant)

        for c_idx in range(n_customers_per_merchant):
            customer = _generate_customer(merchant, m_idx, c_idx, rng)
            customers.append(customer)

            for _ in range(n_transactions_per_customer):
                txn = _generate_transaction(merchant, customer, base_time, rng)
                transactions.append(txn)

    return SyntheticPopulation(
        merchants=merchants,
        customers=customers,
        transactions=transactions,
        seed=seed,
    )
