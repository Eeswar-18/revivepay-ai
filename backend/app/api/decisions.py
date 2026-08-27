"""
app/api/decisions.py — Decision management API endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.decisions import Decision
from app.models.enums import ActionStatus, ActionType, PolicyVerdict
from app.repositories.decisions import DecisionRepository

router = APIRouter(
    prefix="/api/decisions",
    tags=["decisions"],
    responses={404: {"description": "Decision not found"}},
)


def get_decision_repository(session: Session = Depends(get_db)) -> DecisionRepository:
    """Dependency to get decision repository."""
    return DecisionRepository(session)


@router.get("", response_model=list[dict[str, Any]])
def list_decisions(
    skip: int = Query(0, ge=0, description="Number of decisions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of decisions to return"),
    case_id: str | None = Query(None, description="Filter by case ID"),
    action_type: ActionType | None = Query(None, description="Filter by action type"),
    policy_verdict: PolicyVerdict | None = Query(None, description="Filter by policy verdict"),
    status: ActionStatus | None = Query(None, description="Filter by action status"),
    decision_repo: DecisionRepository = Depends(get_decision_repository),
) -> list[dict[str, Any]]:
    """
    List decisions with optional filtering and pagination.

    Returns a list of decision dictionaries with basic information.
    """
    # Build query filters
    filters = {}
    if case_id:
        filters["case_id"] = case_id
    if action_type:
        filters["action_type"] = action_type.value
    if policy_verdict:
        filters["policy_verdict"] = policy_verdict.value
    if status:
        filters["status"] = status.value

    # Get decisions from repository
    if filters:
        # For now, we'll get all and filter in-memory since we don't have
        # complex query methods in the repository yet
        decisions = decision_repo.list(limit=limit * 2)  # Get extra to account for filtering
        # Apply filters
        filtered_decisions = []
        for decision in decisions:
            match = True
            if case_id and str(decision.case_id) != case_id:
                match = False
            if action_type and decision.chosen_action != action_type.value:
                match = False
            if policy_verdict and decision.policy_verdict != policy_verdict.value:
                match = False
            if status and decision.validation_status != status.value:
                match = False
            if match:
                filtered_decisions.append(decision)
        decisions = filtered_decisions[:limit]
    else:
        decisions = decision_repo.list(offset=skip, limit=limit)

    # Convert to dictionaries for response
    return [
        {
            "id": str(decision.id),
            "case_id": str(decision.case_id),
            "seq": decision.seq,
            "action_type": decision.chosen_action,
            "policy_verdict": decision.policy_verdict,
            "status": decision.validation_status,
            "llm_provider": decision.llm_provider,
            "llm_model": decision.llm_model,
            "llm_confidence": decision.llm_confidence,
            "llm_self_probability": decision.llm_self_probability,
            "prompt_version": decision.prompt_version,
            "applied_rules_json": decision.applied_rules_json,
            "created_at": decision.created_at.isoformat() if decision.created_at else None,
        }
        for decision in decisions
    ]


@router.get("/{decision_id}", response_model=dict[str, Any])
def get_decision(
    decision_id: str = Path(..., description="The UUID of the decision to retrieve"),
    decision_repo: DecisionRepository = Depends(get_decision_repository),
) -> dict[str, Any]:
    """
    Get a specific decision by its ID.

    Returns detailed information about the decision.
    """
    try:
        decision_uuid = UUID(decision_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision ID format: {decision_id}",
        ) from err

    decision = decision_repo.get(decision_uuid)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision with ID {decision_id} not found",
        )

    return {
        "id": str(decision.id),
        "case_id": str(decision.case_id),
        "seq": decision.seq,
        "action_type": decision.chosen_action,
        "policy_verdict": decision.policy_verdict,
        "status": decision.validation_status,
        "llm_provider": decision.llm_provider,
        "llm_model": decision.llm_model,
        "llm_confidence": decision.llm_confidence,
        "llm_self_probability": decision.llm_self_probability,
        "prompt_version": decision.prompt_version,
        "prompt_hash": decision.prompt_hash,
        "raw_llm_output": decision.raw_llm_output,
        "proposal_json": decision.proposal_json,
        "validation_status": decision.validation_status,
        "validation_errors_json": decision.validation_errors_json,
        "policy_version": decision.policy_version,
        "applied_rules_json": decision.applied_rules_json,
        "violated_rules_json": decision.violated_rules_json,
        "chosen_action": decision.chosen_action,
        "chosen_params_json": decision.chosen_params_json,
        "expected_net_value_minor": decision.expected_net_value_minor,
        "decision_latency_ms": decision.decision_latency_ms,
        "seed": decision.seed,
        "fallback_used": decision.fallback_used,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
    }


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_decision(
    decision_data: dict[str, Any],
    decision_repo: DecisionRepository = Depends(get_decision_repository),
) -> dict[str, Any]:
    """
    Create a new decision.

    Note: This endpoint is primarily for testing and simulation.
    In production, decisions are created via the decision pipeline.
    """
    # Validate required fields
    required_fields = ["case_id", "action_type"]
    for field in required_fields:
        if field not in decision_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}",
            )

    # Validate case_id exists (optional check)
    # Validate action_type
    try:
        ActionType(decision_data["action_type"])
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type: {decision_data['action_type']}. Must be one of: {[e.value for e in ActionType]}",
        ) from err

    # Validate policy_verdict if provided
    policy_verdict_enum = None
    if "policy_verdict" in decision_data:
        try:
            policy_verdict_enum = PolicyVerdict(decision_data["policy_verdict"])
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid policy_verdict: {decision_data['policy_verdict']}. Must be one of: {[e.value for e in PolicyVerdict]}",
            ) from err

    # Validate status if provided
    if "status" in decision_data:
        try:
            ActionStatus(decision_data["status"])
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {decision_data['status']}. Must be one of: {[e.value for e in ActionStatus]}",
            ) from err

    # Create decision instance
    from uuid import UUID

    decision = Decision(
        case_id=UUID(decision_data["case_id"]),
        seq=decision_data.get("seq", 1),
        chosen_action=decision_data.get("chosen_action"),
        policy_verdict=policy_verdict_enum.value if policy_verdict_enum else None,
        validation_status=decision_data.get("validation_status", "valid"),
        llm_provider=decision_data.get("llm_provider", "mock"),
        llm_model=decision_data.get("llm_model", "mock-v1"),
        llm_confidence=decision_data.get("llm_confidence", 0.0),
        llm_self_probability=decision_data.get("llm_self_probability", 0.0),
        prompt_version=decision_data.get("prompt_version", "p1"),
        prompt_hash=decision_data.get("prompt_hash", "a" * 64),
        raw_llm_output=decision_data.get("raw_llm_output", ""),
        proposal_json=decision_data.get("proposal_json", {}),
        validation_errors_json=decision_data.get("validation_errors_json", {}),
        policy_version=decision_data.get("policy_version", "pol-v1"),
        applied_rules_json=decision_data.get("applied_rules_json", {}),
        violated_rules_json=decision_data.get("violated_rules_json", {}),
        chosen_params_json=decision_data.get("chosen_params_json", {}),
        expected_net_value_minor=decision_data.get("expected_net_value_minor"),
        decision_latency_ms=decision_data.get("decision_latency_ms", 0),
        seed=decision_data.get("seed"),
        fallback_used=decision_data.get("fallback_used", False),
    )

    # Save via repository
    created_decision = decision_repo.add(decision)

    return {
        "id": str(created_decision.id),
        "case_id": str(created_decision.case_id),
        "seq": created_decision.seq,
        "action_type": created_decision.chosen_action,
        "policy_verdict": created_decision.policy_verdict,
        "status": created_decision.validation_status,
        "llm_provider": created_decision.llm_provider,
        "llm_model": created_decision.llm_model,
        "message": "Decision created successfully",
    }
