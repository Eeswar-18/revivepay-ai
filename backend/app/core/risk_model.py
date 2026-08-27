"""
app/core/risk_model.py — Calibrated recovery probability model.

This model estimates the probability of recovery given a case and a candidate action.
For determinism and testability, we use a simple rule-based approach instead of
a full ML model. In a production system, this would be replaced with a
CalibratedClassifierCV trained on historical data.
"""

from __future__ import annotations

from app.models.cases import Case
from app.models.enums import ActionType


class RiskModel:
    """Calibrated probability model for recovery."""

    def __init__(self) -> None:
        # Base recovery probability (can be adjusted based on features)
        self.base_probability = 0.5

        # Feature weights (for demonstration, we use simple heuristics)
        # In a real system, these would be learned from data.
        self.amount_weight = -0.000001  # Higher amount -> lower recovery probability
        self.customer_segment_weights = {
            "NEW": 0.1,
            "OCCASIONAL": 0.0,
            "LOYAL": 0.2,
            "HIGH_VALUE": 0.3,
        }
        self.action_weights = {
            ActionType.STOP: -0.5,  # Stopping reduces recovery chance to zero (handled elsewhere)
            ActionType.RETRY_SAME_RAIL: 0.2,
            ActionType.RETRY_ALTERNATE_RAIL: 0.3,
            ActionType.EMAIL_NUDGE: 0.1,
            ActionType.SMS_NUDGE: 0.15,
            ActionType.WHATSAPP_NUDGE: 0.2,
            ActionType.REQUEST_NEW_INSTRUMENT: 0.25,
            ActionType.AGENT_CALL: 0.4,
        }

    def predict_proba(self, case: Case, action_type: ActionType) -> float:
        """
        Estimate the probability of recovery for the given case and action type.

        Returns a probability between 0.0 and 1.0.
        """
        # Start with base probability
        prob = self.base_probability

        # Adjust based on amount at risk (higher amount -> lower probability)
        prob += self.amount_weight * case.amount_at_risk_minor

        # Adjust based on customer segment
        prob += self.customer_segment_weights.get(case.customer.segment, 0.0)

        # Adjust based on action type
        prob += self.action_weights.get(action_type, 0.0)

        # Clamp to [0.0, 1.0]
        prob = max(0.0, min(1.0, prob))

        return prob
