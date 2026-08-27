"""
app/core/llm/planner.py — LLM planner.

Selects an action, timing, and justification based on features, scored candidates, and policy prose.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.llm.prompts import DEFAULT_PLANNER_PROMPT, PromptTemplate
from app.core.llm.provider import LLMProvider, get_llm_provider
from app.models.cases import Case
from app.models.enums import ActionType


class Planner:
    """LLM planner for selecting actions and providing justifications."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        prompt_template: PromptTemplate = DEFAULT_PLANNER_PROMPT,
    ) -> None:
        self.provider = provider or get_llm_provider()
        self.prompt_template = prompt_template

    def plan(
        self,
        case: Case,
        scored_candidates: list[dict[str, Any]],
        policy_prose: str,
    ) -> dict[str, Any]:
        """
        Generate a proposal for the given case and scored candidates.

        Args:
            case: The case for which to generate a proposal.
            scored_candidates: List of dictionaries, each containing:
                - action_type: ActionType
                - p_recovery: float
                - enrv: float
                - intervention_cost: int
                - etc. (as output by the scorer)
            policy_prose: A string representation of the policy rules for context.

        Returns:
            A dictionary representing the planner's proposal with keys:
                action_type, schedule_offset_hours, justification, feature_citations
        """
        # Format the prompt
        prompt = self.prompt_template.format(
            case_id=str(case.id),
            amount_at_risk_minor=case.amount_at_risk_minor,
            case_type=case.case_type,
            customer_segment=case.customer.segment,
            merchant_mdr_bps=case.merchant.mdr_bps,
            features=case.__dict__,  # We pass the whole case for simplicity; in practice, we might pass only the feature vector
            scored_candidates=json.dumps(scored_candidates, indent=2),
            policy_prose=policy_prose,
        )

        # Get response from LLM
        raw_output = self.provider.generate(prompt)

        # Parse the JSON response
        try:
            proposal = json.loads(raw_output)
        except json.JSONDecodeError:
            # In case of invalid JSON, we return a safe default
            # In a real system, we might log the error and retry
            proposal = {
                "action_type": ActionType.STOP.value,
                "schedule_offset_hours": 0,
                "justification": "Invalid LLM response; defaulting to STOP.",
                "feature_citations": {},
            }

        # Validate the proposal has the required fields
        required_fields = [
            "action_type",
            "schedule_offset_hours",
            "justification",
            "feature_citations",
        ]
        for field in required_fields:
            if field not in proposal:
                proposal[field] = (
                    ActionType.STOP.value
                    if field == "action_type"
                    else 0
                    if field == "schedule_offset_hours"
                    else "Missing field: " + field
                    if field == "justification"
                    else {}
                )

        # Ensure action_type is a valid ActionType
        try:
            ActionType(proposal["action_type"])
        except ValueError:
            proposal["action_type"] = ActionType.STOP.value

        # Ensure schedule_offset_hours is an integer
        try:
            proposal["schedule_offset_hours"] = int(proposal["schedule_offset_hours"])
        except (ValueError, TypeError):
            proposal["schedule_offset_hours"] = 0

        # Ensure justification is a string
        if not isinstance(proposal["justification"], str):
            proposal["justification"] = str(proposal["justification"])

        # Ensure feature_citations is a dict
        if not isinstance(proposal["feature_citations"], dict):
            proposal["feature_citations"] = {}

        return proposal
