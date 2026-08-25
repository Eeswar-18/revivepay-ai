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
    """The types of interventions the agent can take."""

    RETRY_NOW = "RETRY_NOW"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    RETRY_ALTERNATE_RAIL = "RETRY_ALTERNATE_RAIL"
    SEND_RECOVERY_LINK = "SEND_RECOVERY_LINK"
    SEND_DUNNING_REMINDER = "SEND_DUNNING_REMINDER"
    REQUEST_INSTRUMENT_UPDATE = "REQUEST_INSTRUMENT_UPDATE"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"
    STOP_RECOVERY = "STOP_RECOVERY"
    NO_ACTION_WAIT = "NO_ACTION_WAIT"


class CaseType(StrEnum):
    """The type of revenue-at-risk event."""

    FAILED_PAYMENT = "FAILED_PAYMENT"
    ABANDONED_CHECKOUT = "ABANDONED_CHECKOUT"
    SUBSCRIPTION_DUNNING = "SUBSCRIPTION_DUNNING"
    INSTRUMENT_EXPIRY = "INSTRUMENT_EXPIRY"


class FailureClass(StrEnum):
    """Classification of payment failures."""

    TRANSIENT_TECH = "TRANSIENT_TECH"
    ISSUER_SOFT_DECLINE = "ISSUER_SOFT_DECLINE"
    ISSUER_HARD_DECLINE = "ISSUER_HARD_DECLINE"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    MANDATE_ISSUE = "MANDATE_ISSUE"
    RISK_BLOCK = "RISK_BLOCK"
    CUSTOMER_ABANDON = "CUSTOMER_ABANDON"
    CONFIG_ERROR = "CONFIG_ERROR"
    UNKNOWN = "UNKNOWN"


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
