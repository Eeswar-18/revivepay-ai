"""
app/api/merchants.py — Merchant management API endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.merchants import Merchant
from app.repositories.base import BaseRepository

router = APIRouter(
    prefix="/api/merchants",
    tags=["merchants"],
    responses={404: {"description": "Merchant not found"}},
)


def get_merchant_repository(session: Session = Depends(get_db)) -> BaseRepository[Merchant]:
    """Dependency to get merchant repository."""
    return BaseRepository[Merchant](session, Merchant)


@router.get("", response_model=list[dict[str, Any]])
def list_merchants(
    skip: int = Query(0, ge=0, description="Number of merchants to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of merchants to return"),
    risk_appetite: str | None = Query(None, description="Filter by risk appetite"),
    merchant_repo: BaseRepository[Merchant] = Depends(get_merchant_repository),
) -> list[dict[str, Any]]:
    """
    List merchants with optional filtering and pagination.

    Returns a list of merchant dictionaries with basic information.
    """
    # Build query filters
    filters = {}
    if risk_appetite:
        filters["risk_appetite"] = risk_appetite

    # Get merchants from repository
    if filters:
        # For now, we'll get all and filter in-memory since we don't have
        # complex query methods in the repository yet
        merchants = merchant_repo.list(limit=limit * 2)  # Get extra to account for filtering
        # Apply filters
        filtered_merchants = []
        for merchant in merchants:
            match = True
            if risk_appetite and merchant.risk_appetite != risk_appetite:
                match = False
            if match:
                filtered_merchants.append(merchant)
        merchants = filtered_merchants[:limit]
    else:
        merchants = merchant_repo.list(offset=skip, limit=limit)

    # Convert to dictionaries for response
    return [
        {
            "id": str(merchant.id),
            "name": merchant.name,
            "currency": merchant.currency,
            "risk_appetite": merchant.risk_appetite,
            "max_retries_default": merchant.max_retries_default,
            "contact_budget_per_week": merchant.contact_budget_per_week,
            "mdr_bps": merchant.mdr_bps,
            "autonomous_amount_ceiling_minor": merchant.autonomous_amount_ceiling_minor,
            "created_at": merchant.created_at.isoformat() if merchant.created_at else None,
        }
        for merchant in merchants
    ]


@router.get("/{merchant_id}", response_model=dict[str, Any])
def get_merchant(
    merchant_id: str = Path(..., description="The UUID of the merchant to retrieve"),
    merchant_repo: BaseRepository[Merchant] = Depends(get_merchant_repository),
) -> dict[str, Any]:
    """
    Get a specific merchant by its ID.

    Returns detailed information about the merchant.
    """
    try:
        merchant_uuid = UUID(merchant_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid merchant ID format: {merchant_id}",
        ) from err

    merchant = merchant_repo.get(merchant_uuid)
    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant with ID {merchant_id} not found",
        )

    return {
        "id": str(merchant.id),
        "name": merchant.name,
        "currency": merchant.currency,
        "risk_appetite": merchant.risk_appetite,
        "max_retries_default": merchant.max_retries_default,
        "contact_budget_per_week": merchant.contact_budget_per_week,
        "mdr_bps": merchant.mdr_bps,
        "autonomous_amount_ceiling_minor": merchant.autonomous_amount_ceiling_minor,
        "created_at": merchant.created_at.isoformat() if merchant.created_at else None,
    }


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_merchant(
    merchant_data: dict[str, Any],
    merchant_repo: BaseRepository[Merchant] = Depends(get_merchant_repository),
) -> dict[str, Any]:
    """
    Create a new merchant.

    Note: This endpoint is primarily for testing and simulation.
    """
    # Validate required fields
    required_fields = ["name", "currency", "risk_appetite", "mdr_bps"]
    for field in required_fields:
        if field not in merchant_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}",
            )

    # Validate risk_appetite
    valid_appetites = ["conservative", "balanced", "aggressive"]
    if merchant_data["risk_appetite"] not in valid_appetites:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid risk_appetite: {merchant_data['risk_appetite']}. Must be one of: {valid_appetites}",
        )

    # Validate currency (should be INR for this project)
    if merchant_data.get("currency", "INR") != "INR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Currency must be INR for this project",
        )

    # Create merchant instance

    from app.models.merchants import Merchant

    merchant = Merchant(
        name=merchant_data["name"],
        currency=merchant_data.get("currency", "INR"),
        risk_appetite=merchant_data["risk_appetite"],
        max_retries_default=merchant_data.get("max_retries_default", 3),
        contact_budget_per_week=merchant_data.get("contact_budget_per_week", 10_000),
        mdr_bps=merchant_data["mdr_bps"],
        autonomous_amount_ceiling_minor=merchant_data.get(
            "autonomous_amount_ceiling_minor", 1_000_000
        ),
    )

    # Save via repository
    created_merchant = merchant_repo.add(merchant)

    return {
        "id": str(created_merchant.id),
        "name": created_merchant.name,
        "currency": created_merchant.currency,
        "risk_appetite": created_merchant.risk_appetite,
        "max_retries_default": created_merchant.max_retries_default,
        "contact_budget_per_week": created_merchant.contact_budget_per_week,
        "mdr_bps": created_merchant.mdr_bps,
        "autonomous_amount_ceiling_minor": created_merchant.autonomous_amount_ceiling_minor,
        "created_at": created_merchant.created_at.isoformat()
        if created_merchant.created_at
        else None,
        "message": "Merchant created successfully",
    }
