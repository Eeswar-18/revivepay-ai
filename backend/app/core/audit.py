"""
app/core/audit.py — Audit logging service for the decision pipeline.

This module provides a service layer for recording audit entries in the
hash-chained audit log. It is used by the policy kernel, orchestrator,
and other components to log significant decisions and events.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.executor.clock import clock
from app.repositories.audit import AuditEntryPayload, AuditRepository


class AuditService:
    """Service for recording audit entries in the hash-chained audit log."""

    def __init__(self, session: Session) -> None:
        self._repo = AuditRepository(session)

    def log_policy_decision(
        self,
        *,
        case_id: UUID,
        action_type: str,
        policy_verdict: str,
        proposal: dict[str, Any],
        rules_evaluated: list[str] | None = None,
    ) -> None:
        """
        Log a policy kernel decision.

        Args:
            case_id: The ID of the case being evaluated
            action_type: The action type that was evaluated
            policy_verdict: The verdict from the policy kernel (APPROVE, MODIFY, BLOCK, ESCALATE)
            proposal: The LLM proposal that was evaluated
            rules_evaluated: Optional list of rule names that were evaluated
        """
        payload: dict[str, Any] = {
            "case_id": str(case_id),
            "action_type": action_type,
            "policy_verdict": policy_verdict,
            "proposal": proposal,
            "rules_evaluated": rules_evaluated or [],
            "virtual_clock": clock.now().isoformat(),
        }

        entry_payload: AuditEntryPayload = {
            "actor": "policy",
            "event_type": "policy_decision",
            "case_id": case_id,
            "payload_json": payload,
        }

        self._repo.append(entry_payload)

    def log_orchestrator_event(
        self,
        *,
        case_id: UUID,
        event_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an orchestrator lifecycle event.

        Args:
            case_id: The ID of the case being processed
            event_type: Type of event (e.g., "detection_complete", "features_built")
            details: Optional additional details about the event
        """
        payload: dict[str, Any] = {
            "case_id": str(case_id),
            "event_type": event_type,
            "details": details or {},
            "virtual_clock": clock.now().isoformat(),
        }

        entry_payload: AuditEntryPayload = {
            "actor": "orchestrator",
            "event_type": f"orchestrator_{event_type}",
            "case_id": case_id,
            "payload_json": payload,
        }

        self._repo.append(entry_payload)

    def log_execution_event(
        self,
        *,
        case_id: UUID,
        action_id: UUID | None,
        event_type: str,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """
        Log an executor action event.

        Args:
            case_id: The ID of the case associated with the action
            action_id: The ID of the action being executed (can be None)
            event_type: Type of event (e.g., "execution_started", "execution_completed")
            success: Whether the action execution was successful
            error_message: Optional error message if execution failed
        """
        payload: dict[str, Any] = {
            "case_id": str(case_id),
            "action_id": str(action_id) if action_id is not None else None,
            "event_type": event_type,
            "success": success,
            "error_message": error_message,
            "virtual_clock": clock.now().isoformat(),
        }

        entry_payload: AuditEntryPayload = {
            "actor": "executor",
            "event_type": f"execution_{event_type}",
            "case_id": case_id,
            "action_id": action_id,
            "payload_json": payload,
        }

        self._repo.append(entry_payload)

    def log_system_event(
        self,
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Log a system-level event not tied to a specific case.

        Args:
            event_type: Type of system event
            payload: Optional additional data for the event
        """
        entry_payload: AuditEntryPayload = {
            "actor": "system",
            "event_type": f"system_{event_type}",
            "payload_json": payload or {},
        }

        self._repo.append(entry_payload)
