"""
app/api/features.py — Feature computation API endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.features import build_features
from app.db import get_db
from app.repositories.cases import CaseRepository

router = APIRouter(
    prefix="/api/features",
    tags=["features"],
    responses={404: {"description": "Case not found"}},
)


def get_case_repository(session: Session = Depends(get_db)) -> CaseRepository:
    """Dependency to get case repository."""
    return CaseRepository(session)


@router.get("/{case_id}", response_model=dict[str, Any])
def get_case_features(
    case_id: UUID = Path(..., description="The UUID of the case to compute features for"),
    session: Session = Depends(get_db),
    case_repo: CaseRepository = Depends(get_case_repository),
) -> dict[str, Any]:
    """
    Compute and return the feature vector for a specific case.

    Returns a dictionary of feature names to values for the case.
    All values are numbers (int or float) or booleans.
    """
    # Check if case exists first
    case = case_repo.get(case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID {case_id} not found",
        )

    # Compute features using the feature builder
    try:
        features = build_features(session, case_id)
        return features
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing features: {str(err)}",
        ) from err
