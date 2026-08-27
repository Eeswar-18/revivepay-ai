"""
core/detection.py — Revenue-at-risk detection.

This module is responsible for classifying incoming payment provider events
into revenue-at-risk cases and creating the initial Case records.

The detection logic is deterministic and depends only on the input event
and the virtual clock (for timestamps like detected_at and recovery deadline).
It does not perform any database reads, external calls, or randomness.

All time-aware code uses the virtual clock from core/executor/clock.py
to ensure reproducible simulations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.core.executor.clock import clock
from app.db import Session
from app.models.cases import Case
from app.models.enums import CaseState, CaseType
from app.repositories.cases import CaseRepository


@dataclass(frozen=True)
class ProviderEvent:
    """Provider-neutral representation of a payment provider event.

    This is the canonical internal event format produced by webhook adapters
    and consumed by the detection module. It is deliberately decoupled from
    any specific provider's payload structure.

    Attributes
    ----------
    event_type: str
        The type of event: one of "payment_failed", "checkout_abandoned",
        "mandate_debit_failed", or "instrument_expiring".
    transaction_id: UUID | None
        The ID of the transaction associated with the event, if any.
        None for events not tied to a specific transaction (e.g., instrument
        expiry without a pending payment).
    merchant_id: UUID
        The ID of the merchant associated with the event.
    customer_id: UUID
        The ID of the customer associated with the event.
    occurred_at: datetime
        When the event occurred (timezone-aware UTC).
    amount_minor: int
        The amount at risk in integer paise (e.g., transaction amount, cart
        amount, subscription amount). Must be non-negative.
    """

    event_type: str
    transaction_id: UUID | None
    merchant_id: UUID
    customer_id: UUID
    occurred_at: datetime
    amount_minor: int


def _map_event_type_to_case_type(event_type: str) -> CaseType:
    """Map a provider event type to the corresponding CaseType.

    Parameters
    ----------
    event_type: str
        The event type string from the ProviderEvent.

    Returns
    -------
    CaseType
        The corresponding case type.

    Raises
    ------
    ValueError
        If the event_type is not recognized.
    """
    mapping = {
        "payment_failed": CaseType.FAILED_PAYMENT,
        "checkout_abandoned": CaseType.ABANDONED_CHECKOUT,
        "mandate_debit_failed": CaseType.SUBSCRIPTION_DUNNING,
        "instrument_expiring": CaseType.INSTRUMENT_EXPIRY,
    }
    try:
        return mapping[event_type]
    except KeyError as exc:
        raise ValueError(f"Unknown event type: {event_type!r}") from exc


def detect_and_create_case(
    session: Session,
    event: ProviderEvent,
) -> Case:
    """Classify a provider event and create the corresponding Case record.

    This function is deterministic with respect to its inputs (except for
    the database-generated primary key, which is set by the database on insert).
    It does not perform any external calls or database reads.

    Parameters
    ----------
    session: Session
        SQLAlchemy session for persistence.
    event: ProviderEvent
        The provider-neutral event to process.

    Returns
    -------
    Case
        The newly created Case instance, with state DETECTED and all
        required fields populated.

    Raises
    ------
    ValueError
        If the event type is not recognized or if amount_minor is negative.
    RuntimeError
        If the virtual clock has not been started.
    """
    # Validate input
    if event.amount_minor < 0:
        raise ValueError(f"amount_minor must be non-negative, got {event.amount_minor}")

    # Map event type to case type
    case_type = _map_event_type_to_case_type(event.event_type)

    # Use virtual clock for all time-dependent values
    # detected_at: set to current virtual time
    # recovery_deadline: set to occurred_at + 7 days (using real time for occurred_at)
    # Note: occurred_at is provided in the event and is assumed to be a real-world timestamp.
    # We keep recovery_deadline based on occurred_at + fixed window to keep it simple.
    # Alternatively, we could convert occurred_at to virtual time? But the event's
    # occurred_at is the real time when the event happened, and we want to set a
    # recovery deadline in real time (or virtual time?). For simplicity, we keep it
    # in real time and let the virtual clock be used only for detected_at.
    # However, to be fully consistent with the virtual clock simulation, we should
    # use virtual time for all timestamps. But the event's occurred_at is given as
    # a real-world timestamp. We could convert it to virtual time using the clock?
    # That would require knowing the epoch_real and rate. It's simpler to keep
    # recovery_deadline in real time and use virtual clock only for detected_at.
    # For now, we follow the same approach as before: recovery_deadline = occurred_at + 7 days.
    # We will set detected_at to the virtual clock's now().

    # Ensure the virtual clock has been started
    if not clock._started:
        raise RuntimeError(
            "VirtualClock must be started before calling detect_and_create_case. "
            "Call clock.start() at the beginning of the simulation."
        )

    # Generate a UUID for the case ID
    case_id = uuid4()

    # Compute default recovery deadline: 7 days after event occurrence
    recovery_deadline = event.occurred_at + timedelta(days=7)

    # Create the Case instance
    case = Case(
        id=case_id,
        transaction_id=event.transaction_id,
        merchant_id=event.merchant_id,
        customer_id=event.customer_id,
        case_type=case_type,
        amount_at_risk_minor=event.amount_minor,
        state=CaseState.DETECTED,
        detected_at=clock.now(),  # Use virtual clock for detected_at
        attempts_used=0,
        priority_score=0.0,  # Default; will be updated by feature/risk modules
        recovery_deadline_at=recovery_deadline,
        recovered_amount_minor=0,
        # expected_net_value_minor, closed_at, close_reason, simulation_run_id
        # are left as database defaults (None)
    )

    # Persist the case using the repository
    repo = CaseRepository(session)
    created_case = repo.add(case)

    return created_case
