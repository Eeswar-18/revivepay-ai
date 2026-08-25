"""
tests/test_config_endpoint.py — Tests for GET /api/system/config.

Critical assertion: the response body must never contain raw secret values.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_config_returns_200(client: TestClient) -> None:
    """Config endpoint returns HTTP 200."""
    response = client.get("/api/system/config")
    assert response.status_code == 200


def test_config_contains_no_raw_secret_values(client: TestClient) -> None:
    """The config response body must not contain any raw secret value.

    We deliberately set recognisable placeholder values in test_settings
    (e.g., 'test-operator-key') and assert they are absent from the response.
    """
    # These are the values set in conftest.py test_settings.
    # They must never appear in the response body.
    secret_values_that_must_be_absent = [
        "test-operator-key",
        "test-viewer-key",
    ]

    response = client.get("/api/system/config")
    body_text = response.text

    for secret in secret_values_that_must_be_absent:
        assert secret not in body_text, (
            f"Secret value '{secret}' was found in the config endpoint response body. "
            "Raw secret values must never appear in this endpoint."
        )


def test_config_secret_fields_are_redacted(client: TestClient) -> None:
    """Secret fields appear as 'set' or 'unset', never as raw values."""
    data = client.get("/api/system/config").json()
    secret_fields = [
        "API_KEY_OPERATOR",
        "API_KEY_VIEWER",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET",
    ]
    for field in secret_fields:
        assert field in data, f"Expected field '{field}' to be present in config response."
        assert data[field] in {"set", "unset"}, (
            f"Field '{field}' should be 'set' or 'unset', got: {data[field]!r}"
        )


def test_config_operator_key_shows_set(client: TestClient) -> None:
    """API_KEY_OPERATOR shows 'set' because test_settings has a non-empty value."""
    data = client.get("/api/system/config").json()
    assert data["API_KEY_OPERATOR"] == "set"


def test_config_gemini_key_shows_unset(client: TestClient) -> None:
    """GEMINI_API_KEY shows 'unset' because test_settings has an empty value."""
    data = client.get("/api/system/config").json()
    assert data["GEMINI_API_KEY"] == "unset"


def test_config_body_is_valid_json(client: TestClient) -> None:
    """Response body must be valid JSON."""
    response = client.get("/api/system/config")
    try:
        json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Config response is not valid JSON: {exc}") from exc


def test_config_contains_non_secret_fields(client: TestClient) -> None:
    """Non-secret fields are present and have their real values."""
    data = client.get("/api/system/config").json()
    assert data["LLM_PROVIDER"] == "mock"
    assert data["APP_ENV"] == "test"
    assert isinstance(data["SIM_DEFAULT_SEED"], int)
