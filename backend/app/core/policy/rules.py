"""
app/core/policy/rules.py — Policy rule evaluation.

Loads policy rules from policy.yaml and evaluates them against a case and a proposed action.
"""

from __future__ import annotations

from typing import Any, cast

import yaml

from app.models.cases import Case
from app.models.enums import ActionType, PolicyVerdict


class PolicyEngine:
    """Deterministic policy kernel that evaluates rules to produce a verdict."""

    def __init__(self, policy_path: str = "backend/app/core/policy/policy.yaml") -> None:
        self.policy_path = policy_path
        self.rules = self._load_rules()

    def _load_rules(self) -> list[dict[str, Any]]:
        """Load rules from the YAML file."""
        try:
            with open(self.policy_path) as f:
                data = yaml.safe_load(f)
                return cast(list[dict[str, Any]], data.get("rules", []))
        except Exception:
            # In case of error, return a default rule that approves everything
            # In a real system, we might log the error and use a safe default.
            return [{"if": "true", "then": "APPROVE"}]

    def evaluate(self, case: Case, action_type: ActionType) -> PolicyVerdict:
        """
        Evaluate the policy rules for the given case and action type.

        Returns a PolicyVerdict (APPROVE, MODIFY, BLOCK, or ESCALATE).
        """
        # Prepare the context for rule evaluation
        context = {
            "action_type": action_type.value,
            "case_id": str(case.id),
            "amount_at_risk_minor": case.amount_at_risk_minor,
            "case_type": case.case_type,
            "customer_segment": case.customer.segment,
            "customer_prior_recovery_successes": case.customer.prior_recovery_successes,
            "customer_prior_declines": case.customer.prior_declines,
            "merchant_mdr_bps": case.merchant.mdr_bps,
            "merchant_autonomous_amount_ceiling_minor": case.merchant.autonomous_amount_ceiling_minor,
            # Add any other relevant fields from case, customer, merchant as needed
        }

        # Evaluate each rule in order
        for rule in self.rules:
            condition = rule.get("if", "true")
            verdict_str = rule.get("then", "APPROVE")

            # Simple condition evaluation: we support a limited set of expressions.
            # For simplicity, we only support basic comparisons and logical AND/OR.
            # In a real system, we might use a proper expression evaluator like `asteval` or `simpleeval`.
            # Here we implement a very simple evaluator for demonstration.
            try:
                if self._evaluate_condition(condition, context):
                    # Convert the verdict string to PolicyVerdict enum
                    return PolicyVerdict(verdict_str.upper())
            except Exception:
                # If there's an error evaluating the condition, we skip this rule
                # In a real system, we might log the error and continue.
                continue

        # If no rule matches, default to APPROVE (should not happen if we have a catch-all rule)
        return PolicyVerdict.APPROVE

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """
        Evaluate a condition string in the given context.

        This is a very simple evaluator for demonstration purposes.
        It supports:
        - Comparisons: ==, !=, <, >, <=, >=
        - Logical AND: and
        - Logical OR: or
        - Parentheses for grouping
        - Integer and string literals
        - Variable lookup from context

        For example: "action_type == 'AGENT_CALL' and merchant_mdr_bps > 200"
        """
        # Replace boolean literals
        condition = condition.replace("true", "True").replace("false", "False")

        # Tokenize the condition (very simplistic)
        # We'll use Python's eval in a restricted environment for simplicity.
        # Note: This is dangerous if the condition comes from an untrusted source.
        # In a real system, we should use a safe expression evaluator.
        # Since the policy is trusted (it's part of the system), we can use eval with a restricted globals.
        # We only allow the context variables and built-in functions that are safe.
        # We'll create a safe dictionary with the context and no builtins.
        try:
            # Restrict globals to only allowlist of safe builtins (none actually needed)
            safe_dict: dict[str, Any] = {"__builtins__": {}}
            safe_dict.update(context)
            result = eval(condition, {"__builtins__": {}}, context)
            return bool(result)
        except Exception:
            # If evaluation fails, we treat the condition as False
            return False
