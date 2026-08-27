"""
app/core/policy/engine.py — Deterministic policy kernel.

Evaluates policy rules to produce a verdict (APPROVE, MODIFY, BLOCK, ESCALATE) for a given case and proposed action.
"""

from __future__ import annotations

from app.models.cases import Case
from app.models.enums import ActionType, PolicyVerdict

from .rules import PolicyEngine


class PolicyKernel:
    """Deterministic policy kernel."""

    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self.policy_engine = policy_engine or PolicyEngine()

    def evaluate(self, case: Case, action_type: ActionType) -> PolicyVerdict:
        """
        Evaluate the policy for the given case and action type.

        Returns a PolicyVerdict.
        """
        return self.policy_engine.evaluate(case, action_type)
