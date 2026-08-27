"""
app/core/econ.py — Expected-net-value scoring.

Calculates the expected net value (ENRV) for a candidate action given:
- Probability of recovery
- Amount at risk
- Intervention cost
- Expected churn cost
"""

from __future__ import annotations

from app.config import Settings
from app.core.risk_model import RiskModel
from app.models.cases import Case
from app.models.enums import ActionType


class ExpectedNetValueScorer:
    """Scores actions by expected net value."""

    def __init__(self, settings: Settings, risk_model: RiskModel) -> None:
        self.settings = settings
        self.risk_model = risk_model

    def score(self, case: Case, action_type: ActionType) -> float:
        """
        Calculate expected net value for the given case and action type.

        ENRV = P(recovery) * amount_at_risk_minor - intervention_cost - expected_churn_cost
        """
        # Get recovery probability
        p_recovery = self.risk_model.predict_proba(case, action_type)

        # Amount at risk (in paise)
        amount = case.amount_at_risk_minor

        # Intervention cost (in paise) - simplified model
        intervention_cost = self._intervention_cost(action_type)

        # Expected churn cost (in paise)
        expected_churn_cost = self._expected_churn_cost(case, action_type)

        # Calculate ENRV
        enrv = (p_recovery * amount) - intervention_cost - expected_churn_cost

        return enrv

    def _intervention_cost(self, action_type: ActionType) -> int:
        """
        Calculate intervention cost in paise.

        This is a simplified model based on configuration.
        """
        # Base costs (in paise) for each action type
        base_costs = {
            ActionType.STOP: 0,
            ActionType.RETRY_SAME_RAIL: 100,  # Rs 1
            ActionType.RETRY_ALTERNATE_RAIL: 150,  # Rs 1.50
            ActionType.EMAIL_NUDGE: 50,  # Rs 0.50
            ActionType.SMS_NUDGE: 30,  # Rs 0.30
            ActionType.WHATSAPP_NUDGE: 40,  # Rs 0.40
            ActionType.REQUEST_NEW_INSTRUMENT: 200,  # Rs 2
            ActionType.AGENT_CALL: 1000,  # Rs 10
        }

        return base_costs.get(action_type, 0)

    def _expected_churn_cost(self, case: Case, action_type: ActionType) -> int:
        """
        Calculate expected churn cost in paise.

        Simplified model: higher recovery probability -> lower churn risk.
        """
        # Churn probability increases if recovery fails
        p_recovery = self.risk_model.predict_proba(case, action_type)
        p_churn = 1.0 - p_recovery  # Simplified: if not recovered, customer churns

        # Lifetime value (simplified: use amount as proxy for LTV in paise)
        # In a real system, we would use actual LTV from customer data
        ltv = case.amount_at_risk_minor * 10  # Assume 10x transaction amount as LTV

        return int(p_churn * ltv * self.settings.EXPECTED_CHURN_COST_MULTIPLIER)
