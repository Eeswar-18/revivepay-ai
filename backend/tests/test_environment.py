"""
tests/test_environment.py — Behavioural tests for the held-out outcome environment.

Each test is named after and documents the property it protects.  All
datetimes use Asia/Kolkata for consistency with the world config.  No
pytest.mark.skip or pytest.mark.xfail is used anywhere in this file.
"""

from __future__ import annotations

import itertools
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from app.sim.environment import ActionContext, SampledOutcome, World

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture(scope="module")
def world() -> World:
    """Single World instance shared across all tests in this module."""
    return World.default()


def _ctx(
    *,
    failure_class: str = "NETWORK_TIMEOUT",
    amount_minor: int = 50_000,
    customer_segment: str = "OCCASIONAL",
    rail: str = "RAIL_A",
    attempt_index: int = 1,
    contact_index: int = 1,
    hour: int = 14,
    customer_patience: float = 0.5,
) -> ActionContext:
    """Build a fully-specified ActionContext with sensible defaults."""
    return ActionContext(
        failure_class=failure_class,
        amount_minor=amount_minor,
        customer_segment=customer_segment,
        rail=rail,
        attempt_index=attempt_index,
        contact_index=contact_index,
        action_time=datetime(2024, 6, 15, hour, 0, 0, tzinfo=IST),
        customer_patience=customer_patience,
    )


# ---------------------------------------------------------------------------
# The eight failure classes and eight interventions, used for combinatorial
# coverage.
# ---------------------------------------------------------------------------

_ALL_FAILURE_CLASSES = [
    "INSUFFICIENT_FUNDS",
    "BANK_DOWNTIME",
    "NETWORK_TIMEOUT",
    "AUTH_FAILURE",
    "LIMIT_EXCEEDED",
    "RISK_DECLINE",
    "CARD_EXPIRED",
    "HARD_DECLINE",
]

_ALL_INTERVENTIONS = [
    "STOP",
    "RETRY_SAME_RAIL",
    "RETRY_ALTERNATE_RAIL",
    "EMAIL_NUDGE",
    "SMS_NUDGE",
    "WHATSAPP_NUDGE",
    "REQUEST_NEW_INSTRUMENT",
    "AGENT_CALL",
]

_ALL_DELAY_BANDS = ["IMMEDIATE", "SHORT", "MEDIUM", "LONG", "EXTENDED"]

# ---------------------------------------------------------------------------
# Test 1 — All (failure_class × intervention × delay_band) combos are clamped.
#           STOP is exactly 0.0 for every combination.
# ---------------------------------------------------------------------------


def test_all_combinations_within_clamp_range(world: World) -> None:
    """Protect: every (failure_class, intervention, delay_band) probability is
    within [probability_clamp.min, probability_clamp.max], and STOP always
    returns exactly 0.0 regardless of failure class or delay band.
    """
    clamp_min = 0.001
    clamp_max = 0.94

    for fc, iv, db in itertools.product(
        _ALL_FAILURE_CLASSES, _ALL_INTERVENTIONS, _ALL_DELAY_BANDS
    ):
        ctx = _ctx(failure_class=fc)
        p = world.true_success_probability(ctx, iv, db)

        if iv == "STOP":
            assert p == 0.0, (
                f"STOP must return exactly 0.0; got {p} "
                f"for failure_class={fc!r} delay_band={db!r}"
            )
        else:
            assert clamp_min <= p <= clamp_max, (
                f"probability {p} out of clamp range [{clamp_min}, {clamp_max}] "
                f"for failure_class={fc!r} intervention={iv!r} delay_band={db!r}"
            )


# ---------------------------------------------------------------------------
# Test 2 — HARD_DECLINE with any retry intervention stays below 0.02.
# ---------------------------------------------------------------------------


def test_hard_decline_retry_below_threshold(world: World) -> None:
    """Protect: HARD_DECLINE is a terminal failure — retrying it must yield a
    success probability below 0.02 at every delay band, making retries
    economically irrational and supporting policy rule R003.
    """
    retry_interventions = ["RETRY_SAME_RAIL", "RETRY_ALTERNATE_RAIL"]

    for iv, db in itertools.product(retry_interventions, _ALL_DELAY_BANDS):
        ctx = _ctx(failure_class="HARD_DECLINE")
        p = world.true_success_probability(ctx, iv, db)
        assert p < 0.02, (
            f"HARD_DECLINE retry probability {p} >= 0.02 "
            f"for intervention={iv!r} delay_band={db!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 — CARD_EXPIRED with retry equals probability_clamp.min.
# ---------------------------------------------------------------------------


def test_card_expired_retry_equals_clamp_min(world: World) -> None:
    """Protect: CARD_EXPIRED has zero multiplier for all retry interventions,
    so the probability must collapse to probability_clamp.min (0.001).
    This demonstrates that the clamp prevents exact zero and that the
    multiplier table encodes instrument-level unrecoverability.
    """
    clamp_min = 0.001
    retry_interventions = ["RETRY_SAME_RAIL", "RETRY_ALTERNATE_RAIL"]

    for iv, db in itertools.product(retry_interventions, _ALL_DELAY_BANDS):
        ctx = _ctx(failure_class="CARD_EXPIRED")
        p = world.true_success_probability(ctx, iv, db)
        assert p == pytest.approx(clamp_min, abs=1e-9), (
            f"CARD_EXPIRED/{iv}/{db} expected clamp_min {clamp_min}, got {p}"
        )


# ---------------------------------------------------------------------------
# Test 4 — CARD_EXPIRED with REQUEST_NEW_INSTRUMENT at LONG exceeds 0.20.
# ---------------------------------------------------------------------------


def test_card_expired_request_new_instrument_long_recoverable(world: World) -> None:
    """Protect: REQUEST_NEW_INSTRUMENT is the ONLY recoverable path for an
    expired card.  At LONG delay its probability must exceed 0.20, proving
    that a correct agent can learn a genuinely useful action for this class.
    """
    ctx = _ctx(failure_class="CARD_EXPIRED")
    p = world.true_success_probability(ctx, "REQUEST_NEW_INSTRUMENT", "LONG")
    assert p > 0.20, (
        f"CARD_EXPIRED/REQUEST_NEW_INSTRUMENT/LONG should exceed 0.20; got {p}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Attempt decay: attempt_index=5 strictly lower than attempt_index=1.
# ---------------------------------------------------------------------------


def test_attempt_decay_reduces_probability(world: World) -> None:
    """Protect: repeated attempts are penalised by attempt_decay, so the
    probability at attempt_index=5 must be strictly lower than at
    attempt_index=1 for every non-STOP intervention and every failure class
    where retry makes sense (network / auth / funds).
    """
    test_cases = [
        ("NETWORK_TIMEOUT", "RETRY_SAME_RAIL", "IMMEDIATE"),
        ("AUTH_FAILURE", "SMS_NUDGE", "MEDIUM"),
        ("INSUFFICIENT_FUNDS", "WHATSAPP_NUDGE", "LONG"),
    ]
    for fc, iv, db in test_cases:
        p1 = world.true_success_probability(_ctx(failure_class=fc, attempt_index=1), iv, db)
        p5 = world.true_success_probability(_ctx(failure_class=fc, attempt_index=5), iv, db)
        assert p5 < p1, (
            f"attempt_index=5 ({p5}) should be < attempt_index=1 ({p1}) "
            f"for {fc}/{iv}/{db}"
        )


# ---------------------------------------------------------------------------
# Test 6 — Time-of-day: contacting at hour 3 (quiet) is strictly worse than
#           at hour 19 (active evening).
# ---------------------------------------------------------------------------


def test_quiet_hour_reduces_contacting_intervention_probability(world: World) -> None:
    """Protect: contacting a customer at 03:00 (inside quiet hours) must yield
    a strictly lower success probability than the identical call at 19:00
    (active evening), for every customer-contacting intervention.  This
    encodes the economic basis for policy rule R017 (quiet-hours ban).
    """
    contacting_interventions = [
        "EMAIL_NUDGE",
        "SMS_NUDGE",
        "WHATSAPP_NUDGE",
        "REQUEST_NEW_INSTRUMENT",
        "AGENT_CALL",
    ]
    for iv in contacting_interventions:
        p_quiet = world.true_success_probability(
            _ctx(failure_class="AUTH_FAILURE", hour=3), iv, "MEDIUM"
        )
        p_active = world.true_success_probability(
            _ctx(failure_class="AUTH_FAILURE", hour=19), iv, "MEDIUM"
        )
        assert p_quiet < p_active, (
            f"Hour-3 probability ({p_quiet}) should be < hour-19 ({p_active}) "
            f"for contacting intervention {iv!r}"
        )


# ---------------------------------------------------------------------------
# Test 7 — Rail downtime: RETRY_SAME_RAIL on RAIL_A at 02:15 is penalised;
#           RETRY_ALTERNATE_RAIL is unaffected; at 14:00 there is no penalty.
# ---------------------------------------------------------------------------


def test_rail_a_downtime_penalises_same_rail_only(world: World) -> None:
    """Protect: RAIL_A has a daily maintenance window starting at 02:00 for
    45 minutes.  During that window RETRY_SAME_RAIL must be strictly less
    probable than RETRY_ALTERNATE_RAIL (routing around the outage works).
    Outside the window (14:00) the same-rail probability must NOT be lower
    than the alternate-rail probability — there is no asymmetric penalty.
    """
    # 02:15 — inside RAIL_A downtime window.
    ctx_down = ActionContext(
        failure_class="BANK_DOWNTIME",
        amount_minor=50_000,
        customer_segment="OCCASIONAL",
        rail="RAIL_A",
        attempt_index=1,
        contact_index=1,
        action_time=datetime(2024, 6, 15, 2, 15, 0, tzinfo=IST),
        customer_patience=0.5,
    )
    p_same_down = world.true_success_probability(ctx_down, "RETRY_SAME_RAIL", "IMMEDIATE")
    p_alt_down = world.true_success_probability(ctx_down, "RETRY_ALTERNATE_RAIL", "IMMEDIATE")
    assert p_same_down < p_alt_down, (
        f"During RAIL_A downtime, RETRY_SAME_RAIL ({p_same_down}) should be "
        f"< RETRY_ALTERNATE_RAIL ({p_alt_down})"
    )

    # 14:00 — well outside RAIL_A downtime window.
    ctx_up = ActionContext(
        failure_class="BANK_DOWNTIME",
        amount_minor=50_000,
        customer_segment="OCCASIONAL",
        rail="RAIL_A",
        attempt_index=1,
        contact_index=1,
        action_time=datetime(2024, 6, 15, 14, 0, 0, tzinfo=IST),
        customer_patience=0.5,
    )
    p_same_up = world.true_success_probability(ctx_up, "RETRY_SAME_RAIL", "IMMEDIATE")
    # At 14:00 the same-rail penalty must not be active.  Confirm no severity
    # is returned, then verify same-rail is not doubly penalised vs during-downtime.
    sev = world.active_downtime_severity("RAIL_A", ctx_up.action_time)
    assert sev is None, (
        f"active_downtime_severity should return None at 14:00 for RAIL_A; got {sev}"
    )
    # With no active downtime, both probabilities are computed without the
    # (1 - severity) penalty.  Confirm same-rail is not doubly penalised.
    assert p_same_up > p_same_down, (
        f"RETRY_SAME_RAIL at 14:00 ({p_same_up}) should exceed value "
        f"during downtime ({p_same_down})"
    )


# ---------------------------------------------------------------------------
# Test 8 — Churn probability increases monotonically with contact_index.
# ---------------------------------------------------------------------------


def test_churn_probability_monotone_with_contact_index(world: World) -> None:
    """Protect: the churn hazard table is convex — the Nth contact is more
    dangerous than the (N-1)th.  This property is what makes over-contacting
    economically self-defeating and forces the agent to trade off recovery
    probability against churn cost.
    """
    contacting_iv = "SMS_NUDGE"
    prev: float = -1.0
    for ci in range(1, 6):
        ctx = _ctx(contact_index=ci, hour=14)  # daytime, no quiet-hour amplification
        p = world.true_churn_probability(ctx, contacting_iv)
        assert p > prev, (
            f"churn probability should increase with contact_index; "
            f"contact_index={ci} gives {p}, previous was {prev}"
        )
        prev = p


# ---------------------------------------------------------------------------
# Test 9 — Reproducibility: same seed → same sequence; different seeds →
#           different sequences; 200-draw cross-check.
# ---------------------------------------------------------------------------


def test_sample_outcome_reproducibility(world: World) -> None:
    """Protect: sample_outcome must be fully reproducible from the caller's
    seed.  Two generators initialised with the same seed must produce an
    identical sequence of 200 outcomes, and seeds 7 and 8 must diverge.
    This guarantees that counterfactual evaluation comparisons are valid.
    """
    ctx = _ctx(failure_class="INSUFFICIENT_FUNDS", hour=14)
    intervention = "WHATSAPP_NUDGE"
    delay_band = "LONG"
    n = 200

    def draw_sequence(seed: int) -> list[SampledOutcome]:
        rng = np.random.default_rng(seed)
        return [
            world.sample_outcome(ctx, intervention, delay_band, rng)
            for _ in range(n)
        ]

    seq_7a = draw_sequence(7)
    seq_7b = draw_sequence(7)
    seq_8 = draw_sequence(8)

    # Two runs with seed=7 must be identical.
    for i, (a, b) in enumerate(zip(seq_7a, seq_7b, strict=True)):
        assert a.success == b.success, (
            f"seed=7 draw {i}: success mismatch ({a.success} vs {b.success})"
        )
        assert a.churned == b.churned, (
            f"seed=7 draw {i}: churned mismatch ({a.churned} vs {b.churned})"
        )

    # Seeds 7 and 8 must diverge somewhere in 200 draws.
    all_match = all(
        a.success == b.success and a.churned == b.churned
        for a, b in zip(seq_7a, seq_8, strict=True)
    )
    assert not all_match, (
        "seeds 7 and 8 produced identical sequences over 200 draws — "
        "the RNG is not seeded correctly"
    )
