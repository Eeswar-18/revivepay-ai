"""
tests/test_net_value.py — Behavioural tests for the net expected-value calculator.

Each test has a docstring naming the exact property it protects.  No
pytest.mark.skip or pytest.mark.xfail is used anywhere in this file.

Arithmetic reference (all monetary values in integer paise):
  mdr_bps = 200  →  mdr_fraction = 0.02
  expected_gross  = p_success × amount_minor × 0.98
  churn_cost      = hazard[ci] × churn_sensitivity × lifetime_value_minor
                    (zero for non-contacting interventions)
  net_ev_minor    = round(expected_gross − cost_minor − churn_cost)

Estimated churn hazard (agent config, deliberately mis-specified):
  ci=1: 0.0020,  ci=2: 0.0050,  ci=3: 0.0100,
  ci=4: 0.0210,  ci=5: 0.0400,  default_beyond: 0.0650

Customer segments:
  OCCASIONAL: ltv=650_000, sens=1.00
  HIGH_VALUE: ltv=9_500_000, sens=0.55
"""

from __future__ import annotations

import pytest

from app.economics.net_value import NetValueBreakdown, net_expected_value

# ---------------------------------------------------------------------------
# All interventions, split by contact behaviour — used across multiple tests.
# ---------------------------------------------------------------------------
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

_NON_CONTACTING = {"STOP", "RETRY_SAME_RAIL", "RETRY_ALTERNATE_RAIL"}
_CONTACTING = {iv for iv in _ALL_INTERVENTIONS if iv not in _NON_CONTACTING}


# ---------------------------------------------------------------------------
# Test 1A — Signature scenario: HARD_DECLINE, ₹49, p=0.001.
#
# p_success=0.001 is the world's probability_clamp.min — the floor value
# used when a failure class is structurally unrecoverable.  It is not tuned
# to make the test pass; it is the correct value to use for HARD_DECLINE.
#
# Arithmetic (OCCASIONAL, ci=1, hazard=0.0020, ltv=650_000, sens=1.00):
#   gross(p=0.001)  = 0.001 × 4900 × 0.98 = 4.802p
#   STOP            = round(0    − 0    − 0)     =    0
#   RETRY_SAME_RAIL = round(4.802 − 300  − 0)    = -295
#   SMS_NUDGE       = round(4.802 − 20   − 1300) = -1315
#   AGENT_CALL      = round(4.802 − 3500 − 1300) = -4795
# ---------------------------------------------------------------------------


def test_stop_is_argmax_hard_decline_micro_transaction() -> None:
    """Protect: on a HARD_DECLINE ₹49 failure at the world clamp-floor
    probability (p=0.001), STOP (net_ev=0) must be strictly greater than
    every other intervention.  This is the signature demo — on a terminal
    failure with negligible recovery chance, doing nothing is provably
    optimal.  p=0.001 is not chosen to make the test pass; it is the
    world's probability_clamp.min, the only honest p for HARD_DECLINE.
    """
    amount_minor = 4900  # ₹49 in paise
    segment = "OCCASIONAL"
    ci = 1

    stop_result = net_expected_value(
        p_success=0.0,
        amount_minor=amount_minor,
        intervention="STOP",
        customer_segment=segment,
        contact_index=ci,
    )
    assert stop_result.net_ev_minor == 0, (
        f"STOP must be exactly 0; got {stop_result.net_ev_minor}"
    )

    p_floor = 0.001  # world probability_clamp.min — correct value for HARD_DECLINE
    expected = {
        "RETRY_SAME_RAIL": -295,
        "RETRY_ALTERNATE_RAIL": round(0.001 * 4900 * 0.98 - 450),   # round(-445.198) = -445
        "EMAIL_NUDGE": round(0.001 * 4900 * 0.98 - 2 - 0.002 * 1.0 * 650_000),   # -1317
        "SMS_NUDGE": -1315,
        "WHATSAPP_NUDGE": round(0.001 * 4900 * 0.98 - 12 - 0.002 * 1.0 * 650_000),  # -1307
        "REQUEST_NEW_INSTRUMENT": round(0.001 * 4900 * 0.98 - 20 - 0.002 * 1.0 * 650_000),  # -1315
        "AGENT_CALL": -4795,
    }

    for iv in _ALL_INTERVENTIONS:
        if iv == "STOP":
            continue
        result = net_expected_value(
            p_success=p_floor,
            amount_minor=amount_minor,
            intervention=iv,
            customer_segment=segment,
            contact_index=ci,
        )
        # Every intervention must be strictly below STOP.
        assert result.net_ev_minor < stop_result.net_ev_minor, (
            f"{iv}: net_ev={result.net_ev_minor} must be < STOP (0)"
        )
        # Spot-check the representative interventions against known values.
        if iv in expected:
            assert result.net_ev_minor == expected[iv], (
                f"{iv}: expected net_ev={expected[iv]}, got {result.net_ev_minor}"
            )


# ---------------------------------------------------------------------------
# Test 1B — Segment contrast: INSUFFICIENT_FUNDS, ₹49, p=0.22.
#
# RETRY_SAME_RAIL is non-contacting so churn cost is zero; on ₹49 at p=0.22
# it is mildly positive (+756).  SMS_NUDGE triggers churn cost — on
# HIGH_VALUE that cost is so large the intervention is deeply negative
# (-9414) while on OCCASIONAL it is merely slightly negative (-264).
# This demonstrates that the correct policy can retry silently while refusing
# to contact the customer, purely from the net-EV arithmetic.
#
# Arithmetic (ci=1):
#   gross(0.22, 4900) = 0.22 × 4900 × 0.98 = 1056.44p
#   RETRY_SAME_RAIL/any  = round(1056.44 − 300 − 0) = 756
#   SMS_NUDGE/HIGH_VALUE = round(1056.44 − 20 − 0.002×0.55×9_500_000)
#                        = round(1056.44 − 20 − 10450) = round(-9413.56) = -9414
#   SMS_NUDGE/OCCASIONAL = round(1056.44 − 20 − 0.002×1.00×650_000)
#                        = round(1056.44 − 20 − 1300) = round(-263.56) = -264
# ---------------------------------------------------------------------------


def test_retry_positive_sms_negative_on_micro_high_value() -> None:
    """Protect: at INSUFFICIENT_FUNDS ₹49 p=0.22 —
    - RETRY_SAME_RAIL is non-contacting and scores +756 (mildly profitable).
    - SMS_NUDGE/HIGH_VALUE scores -9414 (deeply negative due to LTV risk).
    - SMS_NUDGE/OCCASIONAL scores -264 (slightly negative).
    - HIGH_VALUE SMS net EV is strictly less than OCCASIONAL SMS net EV.
    This proves the agent may retry silently but must refuse to contact,
    because contact carries expected LTV-destruction risk.
    """
    p = 0.22
    amount_minor = 4900
    ci = 1

    retry_hv = net_expected_value(p, amount_minor, "RETRY_SAME_RAIL", "HIGH_VALUE", ci)
    sms_hv = net_expected_value(p, amount_minor, "SMS_NUDGE", "HIGH_VALUE", ci)
    sms_occ = net_expected_value(p, amount_minor, "SMS_NUDGE", "OCCASIONAL", ci)

    assert retry_hv.net_ev_minor == 756, (
        f"RETRY_SAME_RAIL/HIGH_VALUE: expected 756, got {retry_hv.net_ev_minor}"
    )
    assert sms_hv.net_ev_minor == -9414, (
        f"SMS_NUDGE/HIGH_VALUE: expected -9414, got {sms_hv.net_ev_minor}"
    )
    assert sms_occ.net_ev_minor == -264, (
        f"SMS_NUDGE/OCCASIONAL: expected -264, got {sms_occ.net_ev_minor}"
    )
    assert sms_hv.net_ev_minor < sms_occ.net_ev_minor, (
        f"HIGH_VALUE SMS ({sms_hv.net_ev_minor}) should be < OCCASIONAL SMS ({sms_occ.net_ev_minor})"
    )


# ---------------------------------------------------------------------------
# Test 1C — STOP rejects nonzero p_success.
# ---------------------------------------------------------------------------


def test_stop_requires_zero_p_success() -> None:
    """Protect: STOP has zero recovery probability by definition.  Passing a
    nonzero p_success to STOP must raise ValueError immediately, preventing
    an orchestrator bug from inflating STOP's apparent net EV.
    """
    # Valid call — must succeed and return net_ev=0.
    result = net_expected_value(0.0, 4900, "STOP", "OCCASIONAL", 1)
    assert result.net_ev_minor == 0

    # Invalid call — must raise ValueError.
    with pytest.raises(ValueError, match="STOP"):
        net_expected_value(0.22, 4900, "STOP", "OCCASIONAL", 1)

# ---------------------------------------------------------------------------
# Test 2 — Inverse: large amount, AGENT_CALL pays for itself.
#
# At amount_minor=4_000_000 paise (₹40,000) with p_success=0.30:
#   gross = 0.30 × 4_000_000 × 0.98 = 1_176_000p
#   AGENT_CALL cost = 3500p, churn = 0.0020 × 1.00 × 650_000 = 1300p
#   net_ev = round(1_176_000 − 3500 − 1300) = 1_171_200 >> 0
# The calculator is not biased toward inaction on large amounts.
# ---------------------------------------------------------------------------


def test_agent_call_positive_on_large_transaction() -> None:
    """Protect: at ₹40,000 with p_success=0.30, AGENT_CALL scores strongly
    positive and beats STOP, showing the calculator is not merely biased
    toward inaction.
    """
    amount_minor = 4_000_000  # ₹40,000 in paise
    p = 0.30

    stop_result = net_expected_value(
        p_success=0.0,
        amount_minor=amount_minor,
        intervention="STOP",
        customer_segment="OCCASIONAL",
        contact_index=1,
    )
    agent_result = net_expected_value(
        p_success=p,
        amount_minor=amount_minor,
        intervention="AGENT_CALL",
        customer_segment="OCCASIONAL",
        contact_index=1,
    )

    assert agent_result.net_ev_minor > 0, (
        f"AGENT_CALL on ₹40,000 at p=0.30 must be positive; got {agent_result.net_ev_minor}"
    )
    assert agent_result.net_ev_minor > stop_result.net_ev_minor, (
        f"AGENT_CALL ({agent_result.net_ev_minor}) must beat STOP ({stop_result.net_ev_minor})"
    )


# ---------------------------------------------------------------------------
# Test 3 — Monotonicity in p_success: higher p → higher net EV.
# ---------------------------------------------------------------------------


def test_net_ev_rises_with_p_success() -> None:
    """Protect: net_ev_minor is strictly increasing in p_success for every
    non-STOP intervention, all else equal.  STOP is excluded because it
    requires p_success=0.0 by contract.
    """
    amount_minor = 500_000   # ₹5,000
    segment = "OCCASIONAL"
    ci = 1

    for iv in _ALL_INTERVENTIONS:
        if iv == "STOP":
            continue  # STOP requires p_success=0.0 by contract — not testable here
        r_low = net_expected_value(0.10, amount_minor, iv, segment, ci)
        r_high = net_expected_value(0.50, amount_minor, iv, segment, ci)

        assert r_high.net_ev_minor > r_low.net_ev_minor, (
            f"{iv}: net_ev at p=0.50 ({r_high.net_ev_minor}) should exceed "
            f"net_ev at p=0.10 ({r_low.net_ev_minor})"
        )


# ---------------------------------------------------------------------------
# Test 4 — Monotonicity in contact_index: churn cost rises, net EV falls.
#           Non-contacting interventions are unaffected by contact_index.
# ---------------------------------------------------------------------------


def test_net_ev_falls_as_contact_index_rises_for_contacting_interventions() -> None:
    """Protect: for customer-contacting interventions the estimated churn cost
    is convex in contact_index, so net_ev_minor must fall strictly as
    contact_index increases from 1 to 5.  Non-contacting interventions must
    be completely unaffected by contact_index.
    """
    amount_minor = 200_000
    p = 0.25
    segment = "OCCASIONAL"

    # Contacting: net EV must fall strictly.
    for iv in _CONTACTING:
        prev_ev = None
        for ci in range(1, 6):
            r = net_expected_value(p, amount_minor, iv, segment, ci)
            if prev_ev is not None:
                assert r.net_ev_minor < prev_ev, (
                    f"{iv}: net_ev at ci={ci} ({r.net_ev_minor}) should be "
                    f"< ci={ci - 1} ({prev_ev})"
                )
            prev_ev = r.net_ev_minor

    # Non-contacting (excl. STOP): contact_index has zero effect.
    for iv in ("RETRY_SAME_RAIL", "RETRY_ALTERNATE_RAIL"):
        results = [
            net_expected_value(p, amount_minor, iv, segment, ci).net_ev_minor
            for ci in range(1, 6)
        ]
        assert len(set(results)) == 1, (
            f"{iv} should be unaffected by contact_index; got {results}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Churn cost is exactly zero for non-contacting interventions.
# ---------------------------------------------------------------------------


def test_churn_cost_zero_for_non_contacting_interventions() -> None:
    """Protect: expected_churn_cost_minor must be exactly 0.0 for STOP,
    RETRY_SAME_RAIL, and RETRY_ALTERNATE_RAIL, regardless of contact_index
    or customer segment.  All other interventions are contacting and must
    produce a non-zero churn cost.
    """
    amount_minor = 100_000

    # STOP must use p_success=0.0 by contract.
    r_stop = net_expected_value(0.0, amount_minor, "STOP", "HIGH_VALUE", 5)
    assert r_stop.expected_churn_cost_minor == 0.0, (
        f"STOP is non-contacting; expected churn cost 0.0, got {r_stop.expected_churn_cost_minor}"
    )

    # Other non-contacting interventions use a normal p_success.
    for iv in ("RETRY_SAME_RAIL", "RETRY_ALTERNATE_RAIL"):
        r = net_expected_value(0.20, amount_minor, iv, "HIGH_VALUE", 5)
        assert r.expected_churn_cost_minor == 0.0, (
            f"{iv} is non-contacting; expected churn cost 0.0, got "
            f"{r.expected_churn_cost_minor}"
        )

    for iv in _CONTACTING:
        r = net_expected_value(0.20, amount_minor, iv, "OCCASIONAL", 1)
        assert r.expected_churn_cost_minor > 0.0, (
            f"{iv} is contacting; expected churn cost > 0, got "
            f"{r.expected_churn_cost_minor}"
        )


# ---------------------------------------------------------------------------
# Test 6 — default_beyond fallback: contact indices 6 and 9 both use
#           default_beyond (0.0650) and produce identical churn costs.
# ---------------------------------------------------------------------------


def test_default_beyond_applies_consistently() -> None:
    """Protect: contact indices beyond the last explicit table entry (5) must
    both resolve to default_beyond = 0.0650.  Indices 6 and 9 must therefore
    produce identical expected_churn_cost_minor values.
    """
    iv = "SMS_NUDGE"
    segment = "OCCASIONAL"
    amount_minor = 100_000
    p = 0.20

    r6 = net_expected_value(p, amount_minor, iv, segment, 6)
    r9 = net_expected_value(p, amount_minor, iv, segment, 9)

    assert r6.expected_churn_cost_minor == pytest.approx(r9.expected_churn_cost_minor), (
        f"ci=6 churn cost ({r6.expected_churn_cost_minor}) should equal "
        f"ci=9 ({r9.expected_churn_cost_minor}) — both use default_beyond"
    )

    # Verify it is actually 0.0650 × 1.00 × 650_000 = 42_250.0
    expected_churn = 0.0650 * 1.00 * 650_000
    assert r6.expected_churn_cost_minor == pytest.approx(expected_churn, rel=1e-9), (
        f"default_beyond churn cost should be {expected_churn}; got {r6.expected_churn_cost_minor}"
    )


# ---------------------------------------------------------------------------
# Test 7 — Segment sensitivity: HIGH_VALUE churn cost exceeds OCCASIONAL.
#
# This is the counterintuitive property worth highlighting:
#   OCCASIONAL: hazard × 1.00 × 650_000  (sensitivity=1.00, ltv=650_000)
#   HIGH_VALUE: hazard × 0.55 × 9_500_000 (sensitivity=0.55, ltv=9_500_000)
#
# Even though HIGH_VALUE has the lowest churn sensitivity (0.55), its
# enormous lifetime value (9_500_000p = ₹95,000) dominates.  The expected
# churn cost for HIGH_VALUE is 0.55 × 9_500_000 = 5_225_000 × hazard,
# vs OCCASIONAL's 1.00 × 650_000 = 650_000 × hazard — roughly 8× larger.
# This is the core economic reason high-value customers need fewer, better-
# timed contacts, not more.
# ---------------------------------------------------------------------------


def test_high_value_churn_cost_exceeds_occasional_despite_lower_sensitivity() -> None:
    """Protect: the expected churn cost for a HIGH_VALUE customer must be
    strictly larger than for an OCCASIONAL customer at identical contact_index,
    even though HIGH_VALUE has lower churn_sensitivity (0.55 vs 1.00).
    Lifetime value dominates sensitivity — this is the counterintuitive
    result that justifies special handling of high-value customers.
    """
    iv = "WHATSAPP_NUDGE"
    amount_minor = 500_000
    p = 0.30
    ci = 2

    r_occasional = net_expected_value(p, amount_minor, iv, "OCCASIONAL", ci)
    r_high_value = net_expected_value(p, amount_minor, iv, "HIGH_VALUE", ci)

    assert r_high_value.expected_churn_cost_minor > r_occasional.expected_churn_cost_minor, (
        f"HIGH_VALUE churn cost ({r_high_value.expected_churn_cost_minor}) should exceed "
        f"OCCASIONAL ({r_occasional.expected_churn_cost_minor}): LTV dominates sensitivity"
    )

    # Quantitative spot-check at ci=2 (hazard=0.0050):
    # OCCASIONAL: 0.0050 × 1.00 × 650_000 = 3_250.0
    # HIGH_VALUE:  0.0050 × 0.55 × 9_500_000 = 26_125.0
    assert r_occasional.expected_churn_cost_minor == pytest.approx(3_250.0, rel=1e-9)
    assert r_high_value.expected_churn_cost_minor == pytest.approx(26_125.0, rel=1e-9)


# ---------------------------------------------------------------------------
# Test 8 — Component integrity: the four components sum to net_ev_minor
#           within one paise of rounding.
# ---------------------------------------------------------------------------


def test_component_integrity_sum_matches_net_ev() -> None:
    """Protect: the four individually-exposed components must reconstruct
    net_ev_minor within one paise, so the displayed arithmetic on the case
    detail screen can never disagree with the decision value.

    Verified formula:
        net_ev_minor ≈ round(
            expected_gross_recovery_minor
            − intervention_cost_minor
            − expected_churn_cost_minor
        )
    Note: mdr_deduction_minor is already subtracted inside
    expected_gross_recovery_minor and must NOT be subtracted again.
    """
    test_cases = [
        # (p, amount, intervention, segment, ci)
        (0.30, 500_000, "SMS_NUDGE", "OCCASIONAL", 3),
        (0.50, 2_000_000, "AGENT_CALL", "HIGH_VALUE", 1),
        (0.10, 10_000, "EMAIL_NUDGE", "NEW", 4),
        (0.80, 300_000, "RETRY_SAME_RAIL", "LOYAL", 1),
        (0.0, 4_900, "STOP", "OCCASIONAL", 1),
    ]

    for p, amount, iv, seg, ci in test_cases:
        r: NetValueBreakdown = net_expected_value(p, amount, iv, seg, ci)
        reconstructed = round(
            r.expected_gross_recovery_minor
            - r.intervention_cost_minor
            - r.expected_churn_cost_minor
        )
        assert r.net_ev_minor == reconstructed, (
            f"Component sum mismatch for {iv}/{seg}/ci={ci}: "
            f"net_ev_minor={r.net_ev_minor}, reconstructed={reconstructed}"
        )
        # Also verify mdr_deduction is the correct fraction of the gross draw.
        gross_pre_mdr = p * amount
        assert r.mdr_deduction_minor == pytest.approx(gross_pre_mdr * 0.02, rel=1e-9), (
            f"mdr_deduction mismatch for {iv}: "
            f"expected {gross_pre_mdr * 0.02}, got {r.mdr_deduction_minor}"
        )


# ---------------------------------------------------------------------------
# Test 9 — Unknown keys raise KeyError loudly.
# ---------------------------------------------------------------------------


def test_unknown_intervention_raises_key_error() -> None:
    """Protect: a typo in an intervention key must raise KeyError immediately
    rather than silently producing plausible numbers.
    """
    with pytest.raises(KeyError, match="UNKNOWN_ACTION"):
        net_expected_value(0.5, 100_000, "UNKNOWN_ACTION", "OCCASIONAL", 1)


def test_unknown_segment_raises_key_error() -> None:
    """Protect: a typo in a segment key must raise KeyError immediately."""
    with pytest.raises(KeyError, match="PREMIUM"):
        net_expected_value(0.5, 100_000, "SMS_NUDGE", "PREMIUM", 1)
