"""
app/sim/environment.py — Held-out outcome environment for RevivePay AI.

THIS MODULE IS THE GRADER.  It holds the ground-truth parameters that
determine whether a recovery intervention actually succeeds.  No module
under app/policy/, app/decision/, app/agent/, or app/ml/ may import it.
That constraint is enforced by an AST-based architecture test in
backend/tests/test_architecture.py.

The sole source of randomness is the ``rng`` argument passed to
``World.sample_outcome``.  There is no module-level RNG, no call to
``numpy.random.seed``, and no use of the ``random`` standard-library
module.  Reproducibility is entirely the caller's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from app.core.banding import amount_band_for

# Path to the YAML file that lives next to this module.
_DEFAULT_CONFIG_PATH: Path = Path(__file__).with_name("world_config.yaml")

# Quiet-hours span: 21:00 (inclusive) through 09:00 the next morning (exclusive).
_QUIET_START: int = 21
_QUIET_END: int = 9  # exclusive upper bound for hour-of-day comparison


def _is_quiet_hour(hour: int) -> bool:
    """Return True if *hour* (0-23) falls inside the quiet-hours window."""
    # The window wraps midnight: [21, 22, 23, 0, 1, …, 8]
    return hour >= _QUIET_START or hour < _QUIET_END


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActionContext:
    """All observable inputs the environment needs to evaluate an action.

    Attributes
    ----------
    failure_class:
        Failure class key, e.g. ``"INSUFFICIENT_FUNDS"``.
    amount_minor:
        Transaction amount in integer paise (never float).
    customer_segment:
        Segment key, e.g. ``"NEW"``, ``"LOYAL"``.
    rail:
        Payment rail identifier, e.g. ``"RAIL_A"``, ``"RAIL_UPI"``.
    attempt_index:
        1-based count of retry attempts for this case.
    contact_index:
        1-based count of customer contacts in the rolling window.
    action_time:
        Timezone-aware datetime at which the action is taken.
    customer_patience:
        Normalised patience score for this customer, in [0.0, 1.0].
    """

    failure_class: str
    amount_minor: int
    customer_segment: str
    rail: str
    attempt_index: int
    contact_index: int
    action_time: datetime
    customer_patience: float


@dataclass(frozen=True)
class SampledOutcome:
    """The concrete result drawn from the outcome distribution.

    Attributes
    ----------
    success:
        True if the recovery action succeeded.
    churned:
        True if the customer churned as a result of the contact.
    true_success_probability:
        The ground-truth probability used to draw ``success``.
    true_churn_probability:
        The ground-truth probability used to draw ``churned``.
    """

    success: bool
    churned: bool
    true_success_probability: float
    true_churn_probability: float


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------


class World:
    """Simulated payments world loaded from a YAML configuration file.

    The world answers two questions about any proposed action:

    * ``true_success_probability`` — what is the real chance it recovers
      the payment?
    * ``true_churn_probability`` — what is the real chance this contact
      causes the customer to churn?

    And one sampling question:

    * ``sample_outcome`` — given an RNG, draw concrete boolean outcomes.

    Parameters
    ----------
    config_path:
        Absolute path to the ``world_config.yaml`` file to load.
    """

    def __init__(self, config_path: Path) -> None:
        raw: dict[str, Any] = yaml.safe_load(
            config_path.read_text(encoding="utf-8")
        )
        self._cfg: dict[str, Any] = raw
        self.config_version: str = str(raw["config_version"])

        # Pre-cache frequently accessed sub-dicts for clarity.
        self._failure_classes: dict[str, Any] = raw["failure_classes"]
        self._interventions: dict[str, Any] = raw["interventions"]
        self._multipliers: dict[str, Any] = raw["multipliers"]
        self._delay_bands: dict[str, Any] = raw["retry_delay_bands"]
        # Normalise integer-keyed dicts to str keys so lookup is type-uniform.
        self._attempt_decay: dict[str, float] = {
            str(k): float(v) for k, v in raw["attempt_decay"].items()
        }
        self._risk_penalty: float = float(
            raw["risk_decline_retry_penalty_per_attempt"]
        )
        self._segments: dict[str, Any] = raw["customer_segments"]
        self._amount_bands: dict[str, Any] = raw["amount_bands"]
        self._churn_hazard: dict[str, float] = {
            str(k): float(v) for k, v in raw["churn_hazard_by_contact_index"].items()
        }
        self._quiet_hours: dict[str, Any] = raw["quiet_hours"]
        self._hour_multiplier: dict[int, float] = {
            int(k): float(v)
            for k, v in raw["hour_of_day_response_multiplier"].items()
        }
        self._clamp_min: float = float(raw["probability_clamp"]["min"])
        self._clamp_max: float = float(raw["probability_clamp"]["max"])
        self._patience_range: list[float] = [
            float(x)
            for x in raw["observation"]["latent_customer_patience"][
                "success_multiplier_range"
            ]
        ]
        self._downtime_windows: list[dict[str, Any]] = raw.get(
            "downtime_windows", []
        )

    @classmethod
    def default(cls) -> World:
        """Load the world config that ships next to this module."""
        return cls(_DEFAULT_CONFIG_PATH)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_failure_class(self, name: str) -> dict[str, Any]:
        if name not in self._failure_classes:
            raise KeyError(
                f"Unknown failure_class {name!r}. "
                f"Valid keys: {sorted(self._failure_classes)}"
            )
        return self._failure_classes[name]  # type: ignore[no-any-return]

    def _get_intervention(self, name: str) -> dict[str, Any]:
        if name not in self._interventions:
            raise KeyError(
                f"Unknown intervention {name!r}. "
                f"Valid keys: {sorted(self._interventions)}"
            )
        return self._interventions[name]  # type: ignore[no-any-return]

    def _get_segment(self, name: str) -> dict[str, Any]:
        if name not in self._segments:
            raise KeyError(
                f"Unknown customer_segment {name!r}. "
                f"Valid keys: {sorted(self._segments)}"
            )
        return self._segments[name]  # type: ignore[no-any-return]

    def _get_delay_band(self, name: str) -> dict[str, Any]:
        if name not in self._delay_bands:
            raise KeyError(
                f"Unknown delay_band {name!r}. "
                f"Valid keys: {sorted(self._delay_bands)}"
            )
        return self._delay_bands[name]  # type: ignore[no-any-return]

    def _get_multiplier(
        self, failure_class: str, intervention: str, delay_band: str
    ) -> float:
        try:
            fc_mult = self._multipliers[failure_class]
        except KeyError as exc:
            raise KeyError(
                f"No multiplier table for failure_class {failure_class!r}"
            ) from exc
        try:
            iv_mult = fc_mult[intervention]
        except KeyError as exc:
            raise KeyError(
                f"No multiplier row for intervention {intervention!r} "
                f"under failure_class {failure_class!r}"
            ) from exc
        try:
            return float(iv_mult[delay_band])
        except KeyError as exc:
            raise KeyError(
                f"No multiplier cell for delay_band {delay_band!r} "
                f"under {failure_class!r}/{intervention!r}"
            ) from exc

    def _attempt_decay_factor(self, attempt_index: int) -> float:
        key = str(attempt_index) if str(attempt_index) in self._attempt_decay else "default_beyond"
        return self._attempt_decay[key]

    def _churn_hazard_for_index(self, contact_index: int) -> float:
        key = (
            str(contact_index)
            if str(contact_index) in self._churn_hazard
            else "default_beyond"
        )
        return self._churn_hazard[key]

    # ------------------------------------------------------------------
    # Public probability methods
    # ------------------------------------------------------------------

    def true_success_probability(
        self,
        ctx: ActionContext,
        intervention: str,
        delay_band: str,
    ) -> float:
        """Compute the ground-truth probability that *intervention* recovers
        the payment described by *ctx* when scheduled into *delay_band*.

        The computation follows a strict, non-reorderable pipeline described
        in the step 2 specification.

        Parameters
        ----------
        ctx:
            Full action context (failure class, amount, segment, etc.).
        intervention:
            Intervention key, e.g. ``"RETRY_SAME_RAIL"``.
        delay_band:
            Delay band key, e.g. ``"IMMEDIATE"``, ``"LONG"``.

        Returns
        -------
        float
            Probability in [probability_clamp.min, probability_clamp.max],
            except ``STOP`` which always returns exactly ``0.0``.

        Raises
        ------
        KeyError
            On any unrecognised failure class, intervention, segment or band.
        """
        # Step 1 — STOP is a special case: return exactly 0.0 with no clamping.
        if intervention == "STOP":
            return 0.0

        # Validate all inputs so unknown keys fail loudly.
        self._get_failure_class(ctx.failure_class)
        self._get_intervention(intervention)
        self._get_segment(ctx.customer_segment)
        self._get_delay_band(delay_band)

        # Step 2 — base retry success for this failure class.
        p: float = float(
            self._failure_classes[ctx.failure_class]["base_retry_success"]
        )

        # Step 3 — multiply by the (failure_class × intervention × delay_band) cell.
        p *= self._get_multiplier(ctx.failure_class, intervention, delay_band)

        # Step 4 — attempt decay.
        p *= self._attempt_decay_factor(ctx.attempt_index)

        # Step 5 — RISK_DECLINE retry stacking penalty (retry interventions only).
        if ctx.failure_class == "RISK_DECLINE" and intervention in (
            "RETRY_SAME_RAIL",
            "RETRY_ALTERNATE_RAIL",
        ):
            p *= self._risk_penalty ** (ctx.attempt_index - 1)

        # Step 6 — customer segment success multiplier.
        p *= float(self._segments[ctx.customer_segment]["success_multiplier"])

        # Step 7 — amount band success multiplier.
        band_name = amount_band_for(ctx.amount_minor)
        p *= float(self._amount_bands[band_name]["success_multiplier"])

        # Step 8 — time-of-day and quiet-hours effects (contacts_customer only).
        iv_cfg = self._interventions[intervention]
        if iv_cfg["contacts_customer"]:
            hour = ctx.action_time.hour
            p *= self._hour_multiplier[hour]
            if _is_quiet_hour(hour):
                p *= float(self._quiet_hours["success_multiplier"])

        # Step 9 — latent customer patience linear mapping.
        lo, hi = self._patience_range[0], self._patience_range[1]
        patience_multiplier = lo + ctx.customer_patience * (hi - lo)
        p *= patience_multiplier

        # Step 10 — rail downtime penalty (RETRY_SAME_RAIL only).
        if intervention == "RETRY_SAME_RAIL":
            severity = self.active_downtime_severity(ctx.rail, ctx.action_time)
            if severity is not None:
                p *= 1.0 - severity

        # Clamp and return.
        return float(np.clip(p, self._clamp_min, self._clamp_max))

    def true_churn_probability(
        self,
        ctx: ActionContext,
        intervention: str,
    ) -> float:
        """Compute the ground-truth probability that this contact causes churn.

        Returns ``0.0`` immediately for interventions that do not contact
        the customer.  Otherwise the hazard is scaled by segment sensitivity
        and quiet-hours multiplier, then clamped to 0.5.

        Parameters
        ----------
        ctx:
            Full action context.
        intervention:
            Intervention key.

        Returns
        -------
        float
            Churn probability in [0.0, 0.5].

        Raises
        ------
        KeyError
            On an unrecognised intervention or customer segment.
        """
        iv_cfg = self._get_intervention(intervention)
        if not iv_cfg["contacts_customer"]:
            return 0.0

        seg = self._get_segment(ctx.customer_segment)

        # Base hazard for this contact index.
        hazard: float = self._churn_hazard_for_index(ctx.contact_index)

        # Scale by segment churn sensitivity.
        hazard *= float(seg["churn_sensitivity"])

        # Quiet-hours triples annoyance.
        if _is_quiet_hour(ctx.action_time.hour):
            hazard *= float(self._quiet_hours["churn_hazard_multiplier"])

        # Cap at 0.5 — churn is never a certainty.
        return min(hazard, 0.5)

    def sample_outcome(
        self,
        ctx: ActionContext,
        intervention: str,
        delay_band: str,
        rng: np.random.Generator,
    ) -> SampledOutcome:
        """Draw a concrete outcome for *intervention* using *rng*.

        The draw order is fixed: success first, then churned.  This ensures
        the RNG state advances identically regardless of the resulting values,
        which is required for reproducible cross-strategy comparisons.

        Parameters
        ----------
        ctx:
            Full action context.
        intervention:
            Intervention key.
        delay_band:
            Delay band key.
        rng:
            Caller-supplied numpy Generator.  The caller owns the seed.

        Returns
        -------
        SampledOutcome
            Concrete boolean outcomes plus the probabilities used to draw them.
        """
        p_success = self.true_success_probability(ctx, intervention, delay_band)
        p_churn = self.true_churn_probability(ctx, intervention)

        # Always draw in this exact order so the sequence is deterministic.
        success = bool(rng.random() < p_success)
        churned = bool(rng.random() < p_churn)

        return SampledOutcome(
            success=success,
            churned=churned,
            true_success_probability=p_success,
            true_churn_probability=p_churn,
        )

    def active_downtime_severity(
        self,
        rail: str,
        at: datetime,
    ) -> float | None:
        """Return the severity of the first downtime window active for *rail*
        at virtual time *at*, or ``None`` if no window is active.

        Parameters
        ----------
        rail:
            Rail identifier, e.g. ``"RAIL_A"``.
        at:
            Timezone-aware datetime to check.

        Returns
        -------
        float | None
            Severity multiplier in (0, 1], or ``None``.
        """
        local_time: time = at.timetz().replace(tzinfo=None)

        for window in self._downtime_windows:
            if window["rail"] != rail:
                continue

            recurrence: str = window["recurrence"]

            # For weekly recurrence, also check the day of week.
            if recurrence == "weekly" and at.weekday() != int(window["weekday"]):
                continue

            # Build the window start and end as time objects (local).
            start = time(
                hour=int(window["start_hour"]),
                minute=int(window["start_minute"]),
            )
            duration_minutes: int = int(window["duration_minutes"])
            # Compute end time by building a datetime delta from midnight.
            start_dt = datetime(2000, 1, 1, start.hour, start.minute)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            end = end_dt.time()

            in_window: bool
            if end_dt.day == start_dt.day:
                # Window does not cross midnight.
                in_window = start <= local_time < end
            else:
                # Window crosses midnight: active from start until end-of-day
                # OR from midnight until end.
                in_window = local_time >= start or local_time < end

            if in_window:
                return float(window["severity"])

        return None
