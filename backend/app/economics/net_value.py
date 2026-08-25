"""
app/economics/net_value.py — Pure net expected-value calculator.

Computes the agent-side net expected value (NEV) of taking a given
intervention on a given at-risk transaction, using only observable business
parameters from ``app/config/economics.yaml``.

This module:
- performs no I/O beyond loading its configuration once at import time;
- accesses no database;
- uses no randomness;
- must never import from ``app.sim`` in any form.

The formula implemented here is:

    NEV = p_success × amount_minor × (1 − mdr_bps / 10_000)
          − intervention_cost_minor
          − estimated_churn_cost_minor

where::

    estimated_churn_cost_minor =
        0                                              (non-contacting)
        hazard[contact_index] × churn_sensitivity × lifetime_value_minor
                                                       (contacting)

Float intermediates are correct here: an expected value is not settled
funds.  Only ``net_ev_minor`` is rounded to integer paise, and all
decision comparisons use that integer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Configuration loading — once at import time, no further I/O.
# ---------------------------------------------------------------------------

_CONFIG_PATH: Path = Path(__file__).parents[1] / "config" / "economics.yaml"


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


_CFG: dict[str, Any] = _load_config()

_MDR_BPS: int = int(_CFG["mdr_bps"])
_INTERVENTIONS: dict[str, Any] = _CFG["interventions"]
_SEGMENTS: dict[str, Any] = _CFG["customer_segments"]
_CHURN_HAZARD: dict[str, float] = {
    str(k): float(v)
    for k, v in _CFG["estimated_churn_hazard_by_contact_index"].items()
}


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NetValueBreakdown:
    """All components of a net expected-value calculation, fully itemised.

    Every field is individually visible so the case-detail UI can display
    the complete arithmetic to a human and the audit log can record it.
    A single opaque number would make the reasoning unauditable.

    Attributes
    ----------
    expected_gross_recovery_minor:
        ``p_success × amount_minor × (1 − mdr_bps / 10_000)``.
        Float: this is an expectation, not settled funds.
    mdr_deduction_minor:
        The MDR fraction already subtracted inside
        ``expected_gross_recovery_minor``; exposed separately for display.
        ``p_success × amount_minor × (mdr_bps / 10_000)``.
    intervention_cost_minor:
        Direct cost of taking the action, in paise (integer).
    expected_churn_cost_minor:
        Estimated expected lifetime-value loss from the contact, in paise.
        Zero for non-contacting interventions.  Float intermediate.
    net_ev_minor:
        ``round(expected_gross_recovery_minor
                 − intervention_cost_minor
                 − expected_churn_cost_minor)``
        expressed as an integer number of paise.  This is the value that
        decisions and comparisons are made on.
    """

    expected_gross_recovery_minor: float
    mdr_deduction_minor: float
    intervention_cost_minor: int
    expected_churn_cost_minor: float
    net_ev_minor: int


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def net_expected_value(
    p_success: float,
    amount_minor: int,
    intervention: str,
    customer_segment: str,
    contact_index: int,
) -> NetValueBreakdown:
    """Compute the net expected value of taking *intervention*.

    Parameters
    ----------
    p_success:
        Estimated probability that the intervention recovers the payment.
        Must be in [0.0, 1.0].
    amount_minor:
        Transaction amount in integer paise (never float).
    intervention:
        Intervention key, e.g. ``"SMS_NUDGE"``, ``"STOP"``.
    customer_segment:
        Segment key, e.g. ``"OCCASIONAL"``, ``"HIGH_VALUE"``.
    contact_index:
        1-based count of customer contacts in the rolling window.
        Indices beyond the last explicit table entry fall back to
        ``default_beyond``.

    Returns
    -------
    NetValueBreakdown
        All four cost/value components plus the rounded integer ``net_ev_minor``.

    Raises
    ------
    ValueError
        If *intervention* is ``"STOP"`` and *p_success* is not ``0.0``.
        STOP recovers nothing by definition; accepting a nonzero probability
        would allow an orchestrator bug to make STOP appear profitable.
    KeyError
        If *intervention* or *customer_segment* is not present in the
        economics configuration.  Unknown keys fail loudly — a typo must
        never silently produce plausible numbers.
    """
    if intervention not in _INTERVENTIONS:
        raise KeyError(
            f"Unknown intervention {intervention!r}. "
            f"Valid keys: {sorted(_INTERVENTIONS)}"
        )
    if customer_segment not in _SEGMENTS:
        raise KeyError(
            f"Unknown customer_segment {customer_segment!r}. "
            f"Valid keys: {sorted(_SEGMENTS)}"
        )

    # STOP has zero recovery probability by definition — doing nothing recovers
    # nothing.  Accepting a nonzero p_success would make STOP appear profitable
    # and allow an orchestrator bug to silently inflate its score.  Callers must
    # explicitly pass p_success=0.0 when evaluating STOP.
    if intervention == "STOP" and p_success != 0.0:
        raise ValueError(
            f"intervention='STOP' requires p_success=0.0 (STOP recovers nothing); "
            f"got p_success={p_success!r}.  Pass p_success=0.0 explicitly."
        )

    iv_cfg = _INTERVENTIONS[intervention]
    seg_cfg = _SEGMENTS[customer_segment]

    cost_minor: int = int(iv_cfg["cost_minor"])
    contacts_customer: bool = bool(iv_cfg["contacts_customer"])

    # --- Expected gross recovery -------------------------------------------
    # Float intermediate is correct: this is an expectation.
    mdr_fraction: float = _MDR_BPS / 10_000.0
    raw_recovery: float = p_success * amount_minor
    mdr_deduction: float = raw_recovery * mdr_fraction
    expected_gross: float = raw_recovery * (1.0 - mdr_fraction)

    # --- Expected churn cost ------------------------------------------------
    expected_churn_cost: float = 0.0
    if contacts_customer:
        hazard_key = str(contact_index) if str(contact_index) in _CHURN_HAZARD else "default_beyond"
        hazard: float = _CHURN_HAZARD[hazard_key]
        churn_sensitivity: float = float(seg_cfg["churn_sensitivity"])
        lifetime_value_minor: int = int(seg_cfg["lifetime_value_minor"])
        expected_churn_cost = hazard * churn_sensitivity * lifetime_value_minor

    # --- Net EV (integer paise) ---------------------------------------------
    net_ev: int = round(expected_gross - cost_minor - expected_churn_cost)

    return NetValueBreakdown(
        expected_gross_recovery_minor=expected_gross,
        mdr_deduction_minor=mdr_deduction,
        intervention_cost_minor=cost_minor,
        expected_churn_cost_minor=expected_churn_cost,
        net_ev_minor=net_ev,
    )
