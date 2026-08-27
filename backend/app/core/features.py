from datetime import UTC
from math import cos, pi, sin
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.banding import amount_band_for
from app.models.cases import Case
from app.models.customers import Customer
from app.models.enums import CaseType, FailureClass
from app.models.merchants import Merchant
from app.repositories.base import BaseRepository
from app.repositories.cases import CaseRepository


def build_features(session: Session, case_id: UUID) -> dict[str, Any]:
    """Build a deterministic feature vector for the given Case.

    Parameters
    ----------
    session: Session
        SQLAlchemy session for persistence and queries.
    case_id: UUID
        The ID of the Case to build features for.

    Returns
    -------
    dict[str, Any]
        A dictionary mapping feature names to values.  All values are
        numbers (int or float) or booleans.

    Raises
    ------
    ValueError
        If the Case with the given ID is not found.
    """
    # Fetch the Case, Customer, and Merchant
    case_repo = CaseRepository(session)
    case = case_repo.get(case_id)
    if case is None:
        raise ValueError(f"Case with ID {case_id} not found")

    # Use BaseRepository for Customer and Merchant since we don't have specific repositories
    customer_repo = BaseRepository(session, Customer)
    customer = customer_repo.get(case.customer_id)
    if customer is None:
        # This should not happen if foreign keys are enforced, but we check anyway
        raise ValueError(f"Customer {case.customer_id} not found for Case {case_id}")

    merchant_repo = BaseRepository(session, Merchant)
    merchant = merchant_repo.get(case.merchant_id)
    if merchant is None:
        raise ValueError(f"Merchant {case.merchant_id} not found for Case {case_id}")

    # Determine the timestamp to use for time-based features
    # Prefer occurred_at if available, otherwise fall back to detected_at
    timestamp = case.occurred_at or case.detected_at
    if timestamp is None:
        # This should not happen because detected_at has a default, but we check
        raise ValueError(f"Case {case_id} has no timestamp for feature calculation")

    # Ensure timestamp is timezone-aware (UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    # Initialize features dictionary
    features: dict[str, Any] = {}

    # ── Case-based features ─────────────────────────────────────────────────────
    # Amount at risk (in paise)
    features["amount_at_risk_minor"] = case.amount_at_risk_minor
    # Log-transformed amount (log1p to handle zero)
    features["amount_at_risk_minor_log"] = (
        case.amount_at_risk_minor + 1
    )  # We'll store the log1p value; if we want actual log, we can compute later, but keep as linear for now
    # Amount band (one-hot encoded)
    band = amount_band_for(case.amount_at_risk_minor)
    features[f"amount_band_{band}"] = 1
    # Case type (one-hot encoded)
    features[f"case_type_{case.case_type}"] = 1

    # ── Merchant-based features ────────────────────────────────────────────────
    features["merchant_mdr_bps"] = merchant.mdr_bps
    features["merchant_autonomous_amount_ceiling_minor"] = merchant.autonomous_amount_ceiling_minor
    # Ratio of amount at risk to merchant's autonomous ceiling (avoid division by zero)
    if merchant.autonomous_amount_ceiling_minor > 0:
        features["amount_to_ceiling_ratio"] = (
            case.amount_at_risk_minor / merchant.autonomous_amount_ceiling_minor
        )
    else:
        features["amount_to_ceiling_ratio"] = 0.0
    # Merchant risk appetite (one-hot encoded)
    # risk_appetite is a string; we expect one of: conservative, balanced, aggressive
    risk_appetite = merchant.risk_appetite.lower()
    for appet in ["conservative", "balanced", "aggressive"]:
        features[f"merchant_risk_appetite_{appet}"] = 1 if risk_appetite == appet else 0

    # ── Customer-based features ───────────────────────────────────────────────
    features["customer_lifetime_txn_count"] = customer.lifetime_txn_count
    features["customer_lifetime_success_rate"] = customer.lifetime_success_rate
    # Prior recovery success rate (avoid division by zero)
    total_prior_attempts = customer.prior_recovery_successes + customer.prior_declines
    if total_prior_attempts > 0:
        features["customer_prior_recovery_success_rate"] = (
            customer.prior_recovery_successes / total_prior_attempts
        )
    else:
        features["customer_prior_recovery_success_rate"] = 0.0
    features["customer_do_not_contact"] = int(customer.do_not_contact)
    features["customer_mandate_active"] = int(customer.mandate_active)
    # Customer segment (one-hot encoded)
    features[f"customer_segment_{customer.segment}"] = 1
    # Preferred method (one-hot encoded)
    # We assume common payment methods; adjust if needed
    preferred_methods = ["upi", "card", "netbanking", "wallet"]
    for method in preferred_methods:
        features[f"customer_preferred_method_{method}"] = (
            1 if customer.preferred_method == method else 0
        )

    # ── Time-based features (derived from timestamp) ───────────────────────────
    # Hour of day (0-23)
    hour = timestamp.hour
    features["hour_of_day"] = hour
    # Cyclical encoding of hour to capture circadian patterns
    features["hour_of_day_sin"] = sin(2 * pi * hour / 24)
    features["hour_of_day_cos"] = cos(2 * pi * hour / 24)
    # Day of week (0=Monday, 6=Sunday)
    day_of_week = timestamp.weekday()  # Monday is 0, Sunday is 6
    features["day_of_week"] = day_of_week
    # Cyclical encoding of day of week
    features["day_of_week_sin"] = sin(2 * pi * day_of_week / 7)
    features["day_of_week_cos"] = cos(2 * pi * day_of_week / 7)
    # Is weekend (Saturday or Sunday)
    features["is_weekend"] = 1 if day_of_week >= 5 else 0

    # TODO: Consider adding historical case-based features (requires querying past cases)
    # For example:
    # - count of past cases for this customer in the last 7/30 days
    # - historical success rate of past cases for this customer
    # - time since last case
    # These would require additional queries and may be added in a future iteration.

    return features


def classify_failure(case: Case) -> FailureClass:
    """Deterministically classify the failure reason based on the case.

    This is a placeholder implementation that uses simple heuristics.
    In a real system, this would be a more sophisticated model.
    """
    amount = case.amount_at_risk_minor
    case_type = case.case_type

    # Simple rule-based classification
    if case_type == CaseType.FAILED_PAYMENT:
        if amount < 1000:  # < Rs 10
            return FailureClass.AUTH_FAILURE
        elif amount < 10000:  # < Rs 100
            return FailureClass.NETWORK_TIMEOUT
        elif amount < 100000:  # < Rs 1000
            return FailureClass.LIMIT_EXCEEDED
        else:
            return FailureClass.RISK_DECLINE
    elif case_type == CaseType.ABANDONED_CHECKOUT:
        # For abandoned checkout, we map to a default
        return FailureClass.NETWORK_TIMEOUT
    elif case_type == CaseType.SUBSCRIPTION_DUNNING:
        return FailureClass.AUTH_FAILURE  # placeholder
    elif case_type == CaseType.INSTRUMENT_EXPIRY:
        return FailureClass.CARD_EXPIRED  # makes sense for instrument expiry
    else:
        return FailureClass.NETWORK_TIMEOUT  # default
