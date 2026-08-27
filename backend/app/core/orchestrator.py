"""
app/core/orchestrator.py — Decision pipeline orchestrator.

Orchestrates the flow from case to final decision through the pipeline:
detection -> features -> failure classification -> candidate generation ->
risk modeling -> expected net value scoring -> LLM planning -> validation ->
policy kernel -> blast-radius/kill-switch -> final decision.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db import Session
from app.models.cases import Case
from app.models.customers import Customer
from app.models.enums import ActionType, PolicyVerdict
from app.models.merchants import Merchant
from app.repositories.base import BaseRepository
from app.repositories.cases import CaseRepository

from .candidates import CandidateGenerator
from .econ import ExpectedNetValueScorer
from .features import build_features, classify_failure
from .llm.planner import Planner
from .llm.validate import validate_proposal
from .policy.engine import PolicyKernel
from .risk_model import RiskModel


class Orchestrator:
    """Orchestrates the decision pipeline for a given case."""

    def __init__(
        self,
        session: Session,
        risk_model: RiskModel | None = None,
        scorer: ExpectedNetValueScorer | None = None,
        planner: Planner | None = None,
        policy_kernel: PolicyKernel | None = None,
    ) -> None:
        self.session = session
        self.case_repo = CaseRepository(session)
        self.customer_repo = BaseRepository(session, Customer)
        self.merchant_repo = BaseRepository(session, Merchant)

        self.risk_model = risk_model or RiskModel()
        # For the scorer, we need settings; we'll get them from the config
        from app.config import get_settings

        settings = get_settings()
        self.scorer = scorer or ExpectedNetValueScorer(settings, self.risk_model)
        self.planner = planner or Planner()
        self.policy_kernel = policy_kernel or PolicyKernel()

    def orchestrate(self, case_id: UUID) -> dict[str, Any]:
        """
        Run the full decision pipeline for the given case.

        Returns a dictionary with the final decision and relevant metadata.
        """
        # Step 0: Retrieve the case with related customer and merchant
        case = self._get_case_with_relations(case_id)
        if case is None:
            raise ValueError(f"Case with ID {case_id} not found")

        # Step 1: Build features (we don't need to store them, just use for downstream steps)
        features = build_features(self.session, case.id)

        # Step 2: Classify failure
        failure_class = classify_failure(case)

        # Step 3: Generate feasible candidate actions
        candidate_gen = CandidateGenerator()
        candidate_actions = candidate_gen.generate(failure_class)

        # If no candidates, we default to STOP
        if not candidate_actions:
            candidate_actions = [ActionType.STOP]

        # Step 4: Score each candidate with risk model and expected net value
        scored_candidates = []
        for action_type in candidate_actions:
            p_recovery = self.risk_model.predict_proba(case, action_type)
            enrv = self.scorer.score(case, action_type)
            intervention_cost = self.scorer._intervention_cost(action_type)
            scored_candidates.append(
                {
                    "action_type": action_type,
                    "p_recovery": p_recovery,
                    "enrv": enrv,
                    "intervention_cost": intervention_cost,
                }
            )

        # Step 5: Run LLM planner to get a proposal
        # We need to create a policy prose string for the planner.
        # For simplicity, we'll use a placeholder.
        policy_prose = "Policy rules: approve low-cost actions, escalate high-cost agent calls for high MDR merchants."
        planner = (
            Planner()
        )  # We could reuse the one from __init__ but we want to use the same session? Not needed.
        raw_proposal = planner.plan(case, scored_candidates, policy_prose)

        # Step 6: Validate the proposal
        try:
            validated_proposal = validate_proposal(raw_proposal)
        except Exception as e:
            # If validation fails, we default to a safe proposal
            validated_proposal = {
                "action_type": ActionType.STOP.value,
                "schedule_offset_hours": 0,
                "justification": f"LLM proposal validation failed: {str(e)}",
                "feature_citations": {},
            }

        # Step 7: Apply policy kernel to get a verdict
        action_type_enum = ActionType(validated_proposal["action_type"])
        verdict = self.policy_kernel.evaluate(case, action_type_enum)
        validated_proposal["policy_verdict"] = verdict.value

        # Step 8: Apply blast-radius and kill-switch checks (simplified)
        # We'll implement a very simple check: if the action is AGENT_CALL and the merchant's MDR is high, we escalate.
        # But note: the policy kernel already has a rule for that. We'll just do a simple check here for demonstration.
        # In a real system, we would check budget, rate limits, and kill-switch.
        final_verdict = verdict
        final_action = action_type_enum
        if action_type_enum == ActionType.AGENT_CALL:
            merchant = self.merchant_repo.get(case.merchant_id)
            if merchant and merchant.mdr_bps > 200:
                # Escalate if MDR is high (as per our policy rule)
                final_verdict = PolicyVerdict.ESCALATE
                # We keep the action as AGENT_CALL but the verdict is ESCALATE

        # Step 9: Return the final decision
        return {
            "case_id": str(case.id),
            "failure_class": failure_class.value,
            "features": features,
            "scored_candidates": scored_candidates,
            "raw_proposal": raw_proposal,
            "validated_proposal": validated_proposal,
            "policy_verdict": final_verdict.value,
            "recommended_action": final_action.value,
            "schedule_offset_hours": validated_proposal.get("schedule_offset_hours", 0),
            "justification": validated_proposal.get("justification", ""),
            "feature_citations": validated_proposal.get("feature_citations", {}),
        }

    def _get_case_with_relations(self, case_id: UUID) -> Case | None:
        """
        Retrieve a case by ID, ensuring that the related customer and merchant are loaded.
        This avoids lazy loading issues.
        """
        case = self.case_repo.get(case_id)
        if case is None:
            return None

        # Explicitly load the customer and merchant to avoid lazy loading issues
        # (though in our current setup, the relationships are not set up for lazy loading anyway)
        customer = self.customer_repo.get(case.customer_id)
        merchant = self.merchant_repo.get(case.merchant_id)
        # We don't strictly need to do anything with them; just accessing them ensures they are loaded.
        _ = customer
        _ = merchant

        return case
