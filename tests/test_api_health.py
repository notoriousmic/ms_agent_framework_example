"""Tests for API health endpoints."""

import pytest
from fastapi.testclient import TestClient

from microsoft_agent_framework.infrastructure.api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_endpoint_exists(client):
    """Test that the health endpoint exists and returns 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_status(client):
    """Test that the health endpoint returns a status field."""
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy", "degraded"]


def test_health_endpoint_returns_timestamp(client):
    """Test that the health endpoint returns a timestamp."""
    response = client.get("/health")
    data = response.json()
    assert "timestamp" in data


def test_health_endpoint_returns_service_info(client):
    """Test that the health endpoint returns service information."""
    response = client.get("/health")
    data = response.json()
    assert "service_initialized" in data
    assert "environment" in data


def test_health_endpoint_returns_agent_count(client):
    """Test that the health endpoint returns agent count information."""
    response = client.get("/health")
    data = response.json()
    assert "agent_count" in data
    assert isinstance(data["agent_count"], int)
    assert data["agent_count"] >= 0


def test_health_endpoint_returns_version(client):
    """Test that the health endpoint returns version information."""
    response = client.get("/health")
    data = response.json()
    assert "version" in data


def test_health_endpoint_returns_system_status(client):
    """Test that the health endpoint returns system status monitoring."""
    response = client.get("/health")
    data = response.json()
    assert "system_status" in data

    system_status = data["system_status"]

    # Check if error occurred or if we have valid system metrics
    if "error" not in system_status:
        # CPU metrics
        assert "cpu" in system_status
        assert "usage_percent" in system_status["cpu"]
        assert "count" in system_status["cpu"]
        assert isinstance(system_status["cpu"]["usage_percent"], (int, float))
        assert isinstance(system_status["cpu"]["count"], int)
        assert 0 <= system_status["cpu"]["usage_percent"] <= 100

        # Memory metrics
        assert "memory" in system_status
        assert "usage_percent" in system_status["memory"]
        assert "available_mb" in system_status["memory"]
        assert "total_mb" in system_status["memory"]
        assert isinstance(system_status["memory"]["usage_percent"], (int, float))
        assert 0 <= system_status["memory"]["usage_percent"] <= 100

        # Disk metrics
        assert "disk" in system_status
        assert "usage_percent" in system_status["disk"]
        assert "available_gb" in system_status["disk"]
        assert "total_gb" in system_status["disk"]
        assert isinstance(system_status["disk"]["usage_percent"], (int, float))
        assert 0 <= system_status["disk"]["usage_percent"] <= 100

        # Platform info
        assert "platform" in system_status
        assert "system" in system_status["platform"]
        assert "python_version" in system_status["platform"]


def test_health_endpoint_returns_response_metrics(client):
    """Test that the health endpoint returns API response time metrics."""
    response = client.get("/health")
    data = response.json()
    assert "response_metrics" in data

    metrics = data["response_metrics"]
    assert "total_requests" in metrics
    assert "average_response_time_ms" in metrics
    assert "last_request_time" in metrics

    assert isinstance(metrics["total_requests"], int)
    assert metrics["total_requests"] >= 0
    assert isinstance(metrics["average_response_time_ms"], (int, float))
    assert metrics["average_response_time_ms"] >= 0


def test_health_endpoint_tracks_response_time(client):
    """Test that the health endpoint tracks response times correctly."""
    # Make a request to a different endpoint first
    client.get("/")

    # Check health to see metrics
    response = client.get("/health")
    data = response.json()

    # After making a request to root, we should have metrics
    metrics = data["response_metrics"]
    assert metrics["total_requests"] >= 1
    if metrics["total_requests"] > 0:
        assert metrics["average_response_time_ms"] > 0


def test_response_time_header_present(client):
    """Test that API responses include X-Process-Time header."""
    response = client.get("/")
    assert "X-Process-Time" in response.headers
    process_time = float(response.headers["X-Process-Time"])
    assert process_time >= 0


def test_readiness_endpoint_exists(client):
    """Test that the readiness endpoint exists and returns 200."""
    response = client.get("/readiness")
    assert response.status_code == 200
