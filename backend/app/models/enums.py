"""
app/models/enums.py — Enumerations for the RevivePay AI domain.
"""

from __future__ import annotations

from enum import StrEnum


class CaseState(StrEnum):
    """The lifecycle states of a revenue-at-risk Case."""

    DETECTED = "DETECTED"
    FEATURISED = "FEATURISED"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    AWAITING_OUTCOME = "AWAITING_OUTCOME"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


class ActionType(StrEnum):
    """The interventions the agent may propose.

    These members are exactly the keys of the ``interventions`` mapping in
    ``backend/app/sim/world_config.yaml``, which is pre-registered and
    hash-committed.  That file is the source of truth for this taxonomy.

    The action space MUST stay identical to the set of interventions the
    held-out environment can grade.  If the agent could propose an action the
    world does not model, the evaluation would contain cells with undefined
    outcomes and the reported uplift would no longer be falsifiable.  The
    bijection is enforced by ``backend/tests/test_taxonomy_alignment.py``.

    Two actions from the pre-world draft of this enum were deliberately
    removed rather than renamed:

    * ``ESCALATE_HUMAN`` — escalation is not an intervention, it is a policy
      outcome.  It lives in :class:`PolicyVerdict` as ``ESCALATE``.
    * ``NO_ACTION_WAIT`` — waiting is not a distinct intervention either.  It
      is ``STOP`` for this attempt, optionally paired with a
      :class:`DelayBand` when the case is rescheduled.

    Timing is likewise NOT encoded here (the old ``RETRY_NOW`` /
    ``RETRY_SCHEDULED`` split).  An intervention and its delay are separate
    dimensions of one decision: ``(ActionType, DelayBand)``.
    """

    STOP = "STOP"
    RETRY_SAME_RAIL = "RETRY_SAME_RAIL"
    RETRY_ALTERNATE_RAIL = "RETRY_ALTERNATE_RAIL"
    EMAIL_NUDGE = "EMAIL_NUDGE"
    SMS_NUDGE = "SMS_NUDGE"
    WHATSAPP_NUDGE = "WHATSAPP_NUDGE"
    REQUEST_NEW_INSTRUMENT = "REQUEST_NEW_INSTRUMENT"
    AGENT_CALL = "AGENT_CALL"


class CaseType(StrEnum):
    """The type of revenue-at-risk event."""

    FAILED_PAYMENT = "FAILED_PAYMENT"
    ABANDONED_CHECKOUT = "ABANDONED_CHECKOUT"
    SUBSCRIPTION_DUNNING = "SUBSCRIPTION_DUNNING"
    INSTRUMENT_EXPIRY = "INSTRUMENT_EXPIRY"


class FailureClass(StrEnum):
    """Classification of payment failures.

    The first eight members are exactly the keys of the ``failure_classes``
    mapping in ``backend/app/sim/world_config.yaml``, which is pre-registered
    and hash-committed.  That file is the source of truth; these members
    mirror it as literals so decision-side code never has to read the
    held-out config to name a failure.  Enforced by
    ``backend/tests/test_taxonomy_alignment.py``.

    ``UNKNOWN`` is deliberately NOT a world config key.  It represents a raw
    gateway message that the deterministic classifier could not map to a
    known class, and exists so the policy layer has an explicit fail-closed
    branch instead of guessing.  The alignment test therefore compares
    ``set(FailureClass) - {UNKNOWN}`` against the config keys.
    """

    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    BANK_DOWNTIME = "BANK_DOWNTIME"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    AUTH_FAILURE = "AUTH_FAILURE"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    RISK_DECLINE = "RISK_DECLINE"
    CARD_EXPIRED = "CARD_EXPIRED"
    HARD_DECLINE = "HARD_DECLINE"
    UNKNOWN = "UNKNOWN"


class DelayBand(StrEnum):
    """How long to wait before the intervention fires.

    Exactly the keys of ``retry_delay_bands`` in ``world_config.yaml``.
    Timing is a separate decision dimension from :class:`ActionType`; the
    world grades the pair.
    """

    IMMEDIATE = "IMMEDIATE"
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"
    EXTENDED = "EXTENDED"


class CustomerSegment(StrEnum):
    """Behavioural/value segment of a customer.

    Exactly the keys of ``customer_segments`` in ``world_config.yaml``.

    This is an OBSERVABLE feature: the segment label, its lifetime value and
    its churn sensitivity are all readable by decision-side code (they are
    mirrored in ``app/config/economics.yaml``).  What stays hidden is the
    per-customer latent patience and the true success multipliers.
    """

    NEW = "NEW"
    OCCASIONAL = "OCCASIONAL"
    LOYAL = "LOYAL"
    HIGH_VALUE = "HIGH_VALUE"


class AmountBand(StrEnum):
    """Coarse transaction-size bucket.

    Exactly the keys of ``amount_bands`` in ``world_config.yaml``.  The
    numeric thresholds are mirrored independently in
    ``app/core/banding.py``; ``test_taxonomy_alignment.py`` asserts that
    ``amount_band_for()`` only ever returns a member of this enum.
    """

    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    XLARGE = "XLARGE"


class Rail(StrEnum):
    """Payment rail a transaction is attempted on.

    Exactly the ``id`` values of the ``rails`` LIST in ``world_config.yaml``
    (note: that section is a list of mappings, not a mapping).

    Rail is distinct from ``Transaction.payment_method``: card traffic splits
    across ``RAIL_A`` and ``RAIL_B``, and without that split
    ``ActionType.RETRY_ALTERNATE_RAIL`` would be meaningless for the largest
    slice of volume.  Rail-specific downtime windows in the world config are
    keyed by these ids.
    """

    RAIL_A = "RAIL_A"
    RAIL_B = "RAIL_B"
    RAIL_UPI = "RAIL_UPI"
    RAIL_NETBANKING = "RAIL_NETBANKING"


class PolicyVerdict(StrEnum):
    """The outcome of the policy kernel's evaluation of a proposal."""

    APPROVE = "APPROVE"
    MODIFY = "MODIFY"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class ActionStatus(StrEnum):
    """The execution status of an action."""

    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class OutcomeStatus(StrEnum):
    """The final ground-truth outcome recorded by the environment."""

    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
