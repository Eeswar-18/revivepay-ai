"""
tests/test_version.py — Tests for GET /api/version.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

EXPECTED_KEYS = {"app_name", "version", "git_sha", "llm_provider", "environment", "demo_mode"}


def test_version_returns_200(client: TestClient) -> None:
    """Version endpoint returns HTTP 200."""
    response = client.get("/api/version")
    assert response.status_code == 200


def test_version_contains_expected_keys(client: TestClient) -> None:
    """Version response contains all required keys."""
    data = client.get("/api/version").json()
    assert EXPECTED_KEYS.issubset(data.keys()), f"Missing keys: {EXPECTED_KEYS - data.keys()}"


def test_version_app_name(client: TestClient) -> None:
    """app_name is a non-empty string."""
    data = client.get("/api/version").json()
    assert isinstance(data["app_name"], str)
    assert len(data["app_name"]) > 0


def test_version_demo_mode_is_true(client: TestClient) -> None:
    """demo_mode is always True — all payment effects are simulated."""
    data = client.get("/api/version").json()
    assert data["demo_mode"] is True


def test_version_llm_provider(client: TestClient) -> None:
    """llm_provider is one of the valid provider literals."""
    data = client.get("/api/version").json()
    assert data["llm_provider"] in {"mock", "gemini", "openai", "anthropic"}


def test_version_environment(client: TestClient) -> None:
    """environment is one of the valid literals."""
    data = client.get("/api/version").json()
    assert data["environment"] in {"development", "test", "production"}


def test_version_git_sha_is_string_or_null(client: TestClient) -> None:
    """git_sha is either a non-empty string or null."""
    data = client.get("/api/version").json()
    sha = data["git_sha"]
    assert sha is None or (isinstance(sha, str) and len(sha) > 0)
