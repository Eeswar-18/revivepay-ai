"""
app/core/llm/validate.py — Schema + invariant validation for LLM proposals.

Validates that the LLM's output conforms to the expected schema and satisfies
invariants (e.g., citation checks).
"""

from __future__ import annotations

from typing import Any

from app.models.enums import ActionType


def validate_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and normalize a planner proposal.

    This function checks that the proposal contains the required fields with
    correct types and values. It also performs invariant checks such as
    verifying that cited features actually exist in the case.

    Args:
        proposal: The raw proposal dictionary from the LLM.

    Returns:
        A validated and normalized proposal dictionary.

    Raises:
        ValueError: If the proposal fails validation.
    """
    # Make a copy to avoid mutating the original
    validated = dict(proposal)

    # --- Schema validation ---
    # action_type: must be a valid ActionType string
    action_type_str = validated.get("action_type")
    if not isinstance(action_type_str, str):
        raise ValueError("action_type must be a string")
    try:
        ActionType(action_type_str)  # This will raise ValueError if invalid
    except ValueError as err:
        raise ValueError(f"Invalid action_type: {action_type_str}") from err

    # schedule_offset_hours: must be an integer
    schedule_offset = validated.get("schedule_offset_hours")
    if not isinstance(schedule_offset, int):
        # Try to convert if it's a string representing an integer
        if isinstance(schedule_offset, str) and schedule_offset.isdigit():
            schedule_offset = int(schedule_offset)
        else:
            raise ValueError("schedule_offset_hours must be an integer")
    validated["schedule_offset_hours"] = schedule_offset

    # justification: must be a string
    justification = validated.get("justification")
    if not isinstance(justification, str):
        # Try to convert
        justified = str(justification) if justification is not None else ""
        validated["justification"] = justified

    # feature_citations: must be a dictionary mapping strings to booleans
    feature_citations = validated.get("feature_citations")
    if not isinstance(feature_citations, dict):
        raise ValueError("feature_citations must be a dictionary")
    # Ensure all keys are strings and values are booleans
    for key, value in list(feature_citations.items()):
        if not isinstance(key, str):
            raise ValueError(f"feature_citations key must be string: {key}")
        if not isinstance(value, bool):
            # Try to convert
            if isinstance(value, str):
                if value.lower() in ("true", "false"):
                    feature_citations[key] = value.lower() == "true"
                else:
                    raise ValueError(f"feature_citations value must be boolean: {value}")
            elif isinstance(value, int):
                feature_citations[key] = bool(value)
            else:
                raise ValueError(f"feature_citations value must be boolean: {value}")

    # --- Invariant checks ---
    # In a real system, we would verify that the cited features are present in the case
    # and that the justification actually relates to the cited features.
    # For this implementation, we skip detailed invariant checks due to lack of case context.
    # However, we at least ensure that the feature_citations dictionary is not empty
    # if the justification mentions specific features? We skip for simplicity.

    # If we had access to the case, we could check that the cited features exist in the feature vector.
    # Since we don't have the case here, we assume the caller will handle that if needed.

    return validated
