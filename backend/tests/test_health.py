"""
tests/test_health.py — Tests for GET /api/health.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    """Health endpoint returns HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_database_ok(client: TestClient) -> None:
    """Health endpoint reports database as 'ok' when the DB is reachable."""
    data = client.get("/api/health").json()
    assert data["database"] == "ok"


def test_health_status_ok(client: TestClient) -> None:
    """Health endpoint reports overall status as 'ok'."""
    data = client.get("/api/health").json()
    assert data["status"] == "ok"


def test_health_contains_uptime(client: TestClient) -> None:
    """Health endpoint includes uptime_seconds as a non-negative number."""
    data = client.get("/api/health").json()
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


def test_health_contains_timestamp(client: TestClient) -> None:
    """Health endpoint includes a timestamp string."""
    data = client.get("/api/health").json()
    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)
    assert len(data["timestamp"]) > 0


def test_request_id_propagates_to_response_header(client: TestClient) -> None:
    """A caller-supplied X-Request-Id is echoed back in the response headers."""
    custom_id = "test-request-id-abc123"
    response = client.get("/api/health", headers={"X-Request-Id": custom_id})
    assert response.headers.get("x-request-id") == custom_id


def test_generated_request_id_in_response_header(client: TestClient) -> None:
    """When no X-Request-Id is supplied, a UUID is generated and returned."""
    response = client.get("/api/health")
    request_id = response.headers.get("x-request-id")
    assert request_id is not None
    assert len(request_id) > 0
