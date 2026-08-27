"""
app/api/cases.py — Case management API endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session as SQLASession

from app.db import Session
from app.models.enums import CaseState, CaseType
from app.repositories.cases import CaseRepository

router = APIRouter(
    prefix="/api/cases",
    tags=["cases"],
    responses={404: {"description": "Case not found"}},
)


def get_case_repository(session: SQLASession = Depends(Session)) -> CaseRepository:
    """Dependency to get case repository."""
    return CaseRepository(session)


@router.get("", response_model=list[dict[str, Any]])
def list_cases(
    skip: int = Query(0, ge=0, description="Number of cases to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of cases to return"),
    merchant_id: str | None = Query(None, description="Filter by merchant ID"),
    customer_id: str | None = Query(None, description="Filter by customer ID"),
    case_type: CaseType | None = Query(None, description="Filter by case type"),
    state: CaseState | None = Query(None, description="Filter by case state"),
    case_repo: CaseRepository = Depends(get_case_repository),
) -> list[dict[str, Any]]:
    """
    List cases with optional filtering and pagination.

    Returns a list of case dictionaries with basic information.
    """
    # Build query filters
    filters = {}
    if merchant_id:
        filters["merchant_id"] = merchant_id
    if customer_id:
        filters["customer_id"] = customer_id
    if case_type:
        filters["case_type"] = case_type.value
    if state:
        filters["state"] = state.value

    # Get cases from repository
    if filters:
        # For now, we'll get all and filter in-memory since we don't have
        # complex query methods in the repository yet
        # In a real implementation, we'd add query methods to the repository
        cases = case_repo.list(limit=limit * 2)  # Get extra to account for filtering
        # Apply filters
        filtered_cases = []
        for case in cases:
            match = True
            if merchant_id and str(case.merchant_id) != merchant_id:
                match = False
            if customer_id and str(case.customer_id) != customer_id:
                match = False
            if case_type and case.case_type != case_type.value:
                match = False
            if state and case.state != state.value:
                match = False
            if match:
                filtered_cases.append(case)
        cases = filtered_cases[:limit]
    else:
        cases = case_repo.list(offset=skip, limit=limit)

    # Convert to dictionaries for response
    return [
        {
            "id": str(case.id),
            "merchant_id": str(case.merchant_id),
            "customer_id": str(case.customer_id),
            "case_type": case.case_type,
            "amount_at_risk_minor": case.amount_at_risk_minor,
            "state": case.state,
            "detected_at": case.detected_at.isoformat() if case.detected_at else None,
            "occurred_at": case.occurred_at.isoformat() if case.occurred_at else None,
        }
        for case in cases
    ]


@router.get("/{case_id}", response_model=dict[str, Any])
def get_case(
    case_id: str = Path(..., description="The UUID of the case to retrieve"),
    case_repo: CaseRepository = Depends(get_case_repository),
) -> dict[str, Any]:
    """
    Get a specific case by its ID.

    Returns detailed information about the case.
    """
    try:
        case_uuid = UUID(case_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid case ID format: {case_id}",
        ) from err

    case = case_repo.get(case_uuid)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found",
        )

    return {
        "id": str(case.id),
        "transaction_id": str(case.transaction_id) if case.transaction_id else None,
        "merchant_id": str(case.merchant_id),
        "customer_id": str(case.customer_id),
        "case_type": case.case_type,
        "amount_at_risk_minor": case.amount_at_risk_minor,
        "state": case.state,
        "detected_at": case.detected_at.isoformat() if case.detected_at else None,
        "occurred_at": case.occurred_at.isoformat() if case.occurred_at else None,
        "recovery_deadline_at": case.recovery_deadline_at.isoformat()
        if case.recovery_deadline_at
        else None,
        "recovered_amount_minor": case.recovered_amount_minor,
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
        "close_reason": case.close_reason,
        "priority_score": case.priority_score,
        "expected_net_value_minor": case.expected_net_value_minor,
        "attempts_used": case.attempts_used,
        "simulation_run_id": str(case.simulation_run_id) if case.simulation_run_id else None,
    }


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_case(
    case_data: dict[str, Any],
    case_repo: CaseRepository = Depends(get_case_repository),
) -> dict[str, Any]:
    """
    Create a new case.

    Note: This endpoint is primarily for testing and simulation.
    In production, cases are created via the detection module.
    """
    # Validate required fields
    required_fields = ["merchant_id", "customer_id", "case_type", "amount_at_risk_minor"]
    for field in required_fields:
        if field not in case_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}",
            )

    # Validate case_type
    try:
        case_type = CaseType(case_data["case_type"])
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid case_type: {case_data['case_type']}. Must be one of: {[e.value for e in CaseType]}",
        ) from err

    # Create case instance (in a real implementation, we'd use a factory or service)
    from uuid import UUID

    from app.models.cases import Case

    case = Case(
        merchant_id=UUID(case_data["merchant_id"]),
        customer_id=UUID(case_data["customer_id"]),
        case_type=case_type.value,
        amount_at_risk_minor=case_data["amount_at_risk_minor"],
        state=case_data.get("state", CaseState.DETECTED.value),
        detected_at=case_data.get("detected_at"),
        occurred_at=case_data.get("occurred_at"),
        recovery_deadline_at=case_data.get("recovery_deadline_at"),
        recovered_amount_minor=case_data.get("recovered_amount_minor", 0),
    )

    # Save via repository
    created_case = case_repo.add(case)

    return {
        "id": str(created_case.id),
        "merchant_id": str(created_case.merchant_id),
        "customer_id": str(created_case.customer_id),
        "case_type": created_case.case_type,
        "amount_at_risk_minor": created_case.amount_at_risk_minor,
        "state": created_case.state,
        "detected_at": created_case.detected_at.isoformat() if created_case.detected_at else None,
        "occurred_at": created_case.occurred_at.isoformat() if created_case.occurred_at else None,
        "message": "Case created successfully",
    }
