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


def test_readiness_endpoint_exists(client):
    """Test that the readiness endpoint exists and returns 200."""
    response = client.get("/readiness")
    assert response.status_code == 200
