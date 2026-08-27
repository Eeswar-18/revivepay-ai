"""
app/core/candidates.py — Feasible candidate action generation.

Given a failure type and policy rules, enumerate valid actions.
"""

from __future__ import annotations

from app.models.enums import ActionType, FailureClass


class CandidateGenerator:
    """Generates feasible candidate actions for a given failure type."""

    def __init__(self) -> None:
        # Define which actions are feasible for each failure class
        # This is a simplified model; in reality, this would be more complex
        # and possibly driven by policy rules.
        self.feasible_actions: dict[FailureClass, list[ActionType]] = {
            FailureClass.INSUFFICIENT_FUNDS: [
                ActionType.RETRY_SAME_RAIL,
                ActionType.RETRY_ALTERNATE_RAIL,
                ActionType.EMAIL_NUDGE,
                ActionType.SMS_NUDGE,
                ActionType.WHATSAPP_NUDGE,
                ActionType.REQUEST_NEW_INSTRUMENT,
                ActionType.AGENT_CALL,
                ActionType.STOP,
            ],
            FailureClass.BANK_DOWNTIME: [
                ActionType.RETRY_SAME_RAIL,
                ActionType.RETRY_ALTERNATE_RAIL,
                ActionType.EMAIL_NUDGE,
                ActionType.SMS_NUDGE,
                ActionType.WHATSAPP_NUDGE,
                ActionType.STOP,
            ],
            FailureClass.NETWORK_TIMEOUT: [
                ActionType.RETRY_SAME_RAIL,
                ActionType.RETRY_ALTERNATE_RAIL,
                ActionType.EMAIL_NUDGE,
                ActionType.SMS_NUDGE,
                ActionType.WHATSAPP_NUDGE,
                ActionType.STOP,
            ],
            FailureClass.AUTH_FAILURE: [
                ActionType.REQUEST_NEW_INSTRUMENT,
                ActionType.AGENT_CALL,
                ActionType.STOP,
            ],
            FailureClass.LIMIT_EXCEEDED: [
                ActionType.EMAIL_NUDGE,
                ActionType.SMS_NUDGE,
                ActionType.WHATSAPP_NUDGE,
                ActionType.REQUEST_NEW_INSTRUMENT,
                ActionType.AGENT_CALL,
                ActionType.STOP,
            ],
            FailureClass.RISK_DECLINE: [
                ActionType.EMAIL_NUDGE,
                ActionType.SMS_NUDGE,
                ActionType.WHATSAPP_NUDGE,
                ActionType.REQUEST_NEW_INSTRUMENT,
                ActionType.AGENT_CALL,
                ActionType.STOP,
            ],
            FailureClass.CARD_EXPIRED: [
                ActionType.REQUEST_NEW_INSTRUMENT,
                ActionType.AGENT_CALL,
                ActionType.STOP,
            ],
            FailureClass.HARD_DECLINE: [
                ActionType.STOP,
            ],
        }

    def generate(self, failure_class: FailureClass) -> list[ActionType]:
        """
        Generate feasible candidate actions for the given failure class.

        Returns a list of action types that are considered feasible.
        """
        return self.feasible_actions.get(failure_class, [])
