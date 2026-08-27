"""
app/api/customers.py — Customer management API endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.db import Session
from app.models.customers import Customer
from app.models.enums import CustomerSegment
from app.repositories.base import BaseRepository

router = APIRouter(
    prefix="/api/customers",
    tags=["customers"],
    responses={404: {"description": "Customer not found"}},
)


def get_customer_repository(session: Session = Depends(Session)) -> BaseRepository[Customer]:
    """Dependency to get customer repository."""
    return BaseRepository[Customer](session, Customer)


@router.get("", response_model=list[dict[str, Any]])
def list_customers(
    skip: int = Query(0, ge=0, description="Number of customers to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of customers to return"),
    merchant_id: str | None = Query(None, description="Filter by merchant ID"),
    segment: CustomerSegment | None = Query(None, description="Filter by customer segment"),
    customer_repo: BaseRepository[Customer] = Depends(get_customer_repository),
) -> list[dict[str, Any]]:
    """
    List customers with optional filtering and pagination.

    Returns a list of customer dictionaries with basic information.
    """
    # Build query filters
    filters = {}
    if merchant_id:
        filters["merchant_id"] = merchant_id
    if segment:
        filters["segment"] = segment.value

    # Get customers from repository
    if filters:
        # For now, we'll get all and filter in-memory since we don't have
        # complex query methods in the repository yet
        # In a real implementation, we'd add query methods to the repository
        customers = customer_repo.list(limit=limit * 2)  # Get extra to account for filtering
        # Apply filters
        filtered_customers = []
        for customer in customers:
            match = True
            if merchant_id and str(customer.merchant_id) != merchant_id:
                match = False
            if segment and customer.segment != segment.value:
                match = False
            if match:
                filtered_customers.append(customer)
        customers = filtered_customers[:limit]
    else:
        customers = customer_repo.list(offset=skip, limit=limit)

    # Convert to dictionaries for response
    return [
        {
            "id": str(customer.id),
            "merchant_id": str(customer.merchant_id),
            "email_hash": customer.email_hash,
            "phone_hash": customer.phone_hash,
            "region": customer.region,
            "segment": customer.segment,
            "lifetime_txn_count": customer.lifetime_txn_count,
            "lifetime_success_rate": customer.lifetime_success_rate,
            "prior_recovery_successes": customer.prior_recovery_successes,
            "prior_declines": customer.prior_declines,
            "do_not_contact": customer.do_not_contact,
            "mandate_active": customer.mandate_active,
            "preferred_method": customer.preferred_method,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
        }
        for customer in customers
    ]


@router.get("/{customer_id}", response_model=dict[str, Any])
def get_customer(
    customer_id: str = Path(..., description="The UUID of the customer to retrieve"),
    customer_repo: BaseRepository[Customer] = Depends(get_customer_repository),
) -> dict[str, Any]:
    """
    Get a specific customer by its ID.

    Returns detailed information about the customer.
    """
    try:
        customer_uuid = UUID(customer_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid customer ID format: {customer_id}",
        ) from err

    customer = customer_repo.get(customer_uuid)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found",
        )

    return {
        "id": str(customer.id),
        "merchant_id": str(customer.merchant_id),
        "email_hash": customer.email_hash,
        "phone_hash": customer.phone_hash,
        "region": customer.region,
        "segment": customer.segment,
        "lifetime_txn_count": customer.lifetime_txn_count,
        "lifetime_success_rate": customer.lifetime_success_rate,
        "prior_recovery_successes": customer.prior_recovery_successes,
        "prior_declines": customer.prior_declines,
        "do_not_contact": customer.do_not_contact,
        "unsubscribed_at": customer.unsubscribed_at.isoformat()
        if customer.unsubscribed_at
        else None,
        "mandate_active": customer.mandate_active,
        "mandate_expires_at": customer.mandate_expires_at.isoformat()
        if customer.mandate_expires_at
        else None,
        "preferred_method": customer.preferred_method,
        "consented_instruments_json": customer.consented_instruments_json,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_data: dict[str, Any],
    customer_repo: BaseRepository[Customer] = Depends(get_customer_repository),
) -> dict[str, Any]:
    """
    Create a new customer.

    Note: This endpoint is primarily for testing and simulation.
    """
    # Validate required fields
    required_fields = ["merchant_id", "email_hash", "phone_hash", "region", "segment"]
    for field in required_fields:
        if field not in customer_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}",
            )

    # Validate segment
    try:
        segment = CustomerSegment(customer_data["segment"])
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid segment: {customer_data['segment']}. Must be one of: {[e.value for e in CustomerSegment]}",
        ) from err

    # Create customer instance
    from uuid import UUID

    from app.models.customers import Customer

    customer = Customer(
        merchant_id=UUID(customer_data["merchant_id"]),
        email_hash=customer_data["email_hash"],
        phone_hash=customer_data["phone_hash"],
        region=customer_data["region"],
        segment=segment.value,
        lifetime_txn_count=customer_data.get("lifetime_txn_count", 0),
        lifetime_success_rate=customer_data.get("lifetime_success_rate", 0.0),
        prior_recovery_successes=customer_data.get("prior_recovery_successes", 0),
        prior_declines=customer_data.get("prior_declines", 0),
        do_not_contact=customer_data.get("do_not_contact", False),
        mandate_active=customer_data.get("mandate_active", False),
        mandate_expires_at=customer_data.get("mandate_expires_at"),
        preferred_method=customer_data.get("preferred_method", "upi"),
        consented_instruments_json=customer_data.get("consented_instruments_json", {}),
    )

    # Save via repository
    created_customer = customer_repo.add(customer)

    return {
        "id": str(created_customer.id),
        "merchant_id": str(created_customer.merchant_id),
        "email_hash": created_customer.email_hash,
        "phone_hash": created_customer.phone_hash,
        "region": created_customer.region,
        "segment": created_customer.segment,
        "lifetime_txn_count": created_customer.lifetime_txn_count,
        "lifetime_success_rate": created_customer.lifetime_success_rate,
        "prior_recovery_successes": created_customer.prior_recovery_successes,
        "prior_declines": created_customer.prior_declines,
        "do_not_contact": created_customer.do_not_contact,
        "mandate_active": created_customer.mandate_active,
        "preferred_method": created_customer.preferred_method,
        "message": "Customer created successfully",
    }
