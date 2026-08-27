"""
app/core/llm/prompts.py — LLM prompt templates.

Defines versioned prompt templates used by the LLM planner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PromptTemplate:
    """A versioned prompt template for the LLM planner.

    Attributes
    ----------
    version: str
        The version identifier of this template.
    template: str
        The prompt template string with placeholders for variables.
    """

    version: str
    template: str

    def format(self, **kwargs: Any) -> str:
        """Format the template with the given keyword arguments.

        Returns:
            The formatted prompt string.
        """
        return self.template.format(**kwargs)


# Default prompt template for the planner.
# This template instructs the LLM to select an action, timing, and justification.
DEFAULT_PLANNER_PROMPT = PromptTemplate(
    version="v1",
    template="""You are an AI assistant for revenue recovery. Your task is to select the best action to recover revenue at risk.

Case details:
- Case ID: {case_id}
- Amount at risk: {amount_at_risk_minor} paise
- Case type: {case_type}
- Customer segment: {customer_segment}
- Merchant MDR: {merchant_mdr_bps} bps
- Features: {features}

Scored candidate actions:
{scored_candidates}

Policy prose:
{policy_prose}

Select one action from the candidate actions. For the selected action, provide:
1. action_type: one of the candidate action types
2. schedule_offset_hours: integer hours from now to schedule the action (can be 0 for immediate)
3. justification: a brief explanation for why this action was selected, citing specific features
4. feature_citations: a dictionary mapping feature names to boolean indicating if the feature influenced the decision

Respond with a JSON object containing exactly these fields. Do not include any other text.
""",
)
