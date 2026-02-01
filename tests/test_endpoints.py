"""Tests for receiver endpoints."""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Mock settings before importing app
@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for testing."""
    with patch("src.config.settings") as mock:
        mock.allowed_public_keys = ["test_key"]
        mock.auth_required = True
        mock.project_ids = [1, 2, 3]
        mock.max_request_size = 5 * 1024 * 1024
        mock.use_celery = False
        mock.batch_size = 100
        mock.batch_timeout_seconds = 5
        mock.opensearch_hosts = ["http://localhost:9200"]
        mock.opensearch_index_prefix = "sentry-events"
        mock.debug = True
        mock.allowed_cors_origins = []
        mock.rate_limit_enabled = False
        yield mock


@pytest.fixture
def client(mock_settings):
    """Create test client."""
    from src.main import app
    return TestClient(app)


class TestProjectHealthEndpoint:
    """Tests for the project health check endpoint."""

    def test_project_health_valid_project(self, client):
        """Test health check for valid project."""
        response = client.get("/api/1/")
        assert response.status_code == 200
        assert response.json() == {"project_id": 1, "status": "ok"}

    def test_project_health_invalid_project(self, client):
        """Test health check for invalid project."""
        response = client.get("/api/999/")
        assert response.status_code == 404


class TestEnvelopeEndpoint:
    """Tests for the envelope endpoint."""

    def test_envelope_missing_auth(self, client):
        """Test envelope endpoint without authentication."""
        response = client.post(
            "/api/1/envelope/",
            content=b"{}",
            headers={"Content-Type": "application/x-sentry-envelope"},
        )
        assert response.status_code == 401

    def test_envelope_invalid_auth(self, client):
        """Test envelope endpoint with invalid authentication."""
        response = client.post(
            "/api/1/envelope/",
            content=b"{}",
            headers={
                "Content-Type": "application/x-sentry-envelope",
                "X-Sentry-Auth": "Sentry sentry_key=invalid_key",
            },
        )
        assert response.status_code == 401

    def test_envelope_valid_auth_empty_body(self, client):
        """Test envelope endpoint with valid auth and empty body."""
        response = client.post(
            "/api/1/envelope/",
            content=b"",
            headers={
                "Content-Type": "application/x-sentry-envelope",
                "X-Sentry-Auth": "Sentry sentry_key=test_key",
            },
        )
        assert response.status_code == 200
        assert response.json() == {"id": None}

    def test_envelope_invalid_project(self, client):
        """Test envelope endpoint with invalid project."""
        response = client.post(
            "/api/999/envelope/",
            content=b"{}",
            headers={
                "Content-Type": "application/x-sentry-envelope",
                "X-Sentry-Auth": "Sentry sentry_key=test_key",
            },
        )
        assert response.status_code == 404


class TestStoreEndpoint:
    """Tests for the legacy store endpoint."""

    def test_store_missing_auth(self, client):
        """Test store endpoint without authentication."""
        response = client.post(
            "/api/1/store/",
            json={},
        )
        assert response.status_code == 401

    def test_store_valid_auth_empty_body(self, client):
        """Test store endpoint with valid auth and empty body."""
        response = client.post(
            "/api/1/store/",
            content=b"",
            headers={
                "X-Sentry-Auth": "Sentry sentry_key=test_key",
            },
        )
        assert response.status_code == 200
        assert response.json() == {"id": None}


class TestMinidumpEndpoint:
    """Tests for the minidump endpoint."""

    def test_minidump_missing_auth(self, client):
        """Test minidump endpoint without authentication."""
        response = client.post("/api/1/minidump/", content=b"")
        assert response.status_code == 401

    def test_minidump_valid_auth(self, client):
        """Test minidump endpoint with valid auth."""
        response = client.post(
            "/api/1/minidump/",
            content=b"",
            headers={"X-Sentry-Auth": "Sentry sentry_key=test_key"},
        )
        assert response.status_code == 200


class TestSecurityEndpoint:
    """Tests for the security endpoint."""

    def test_security_missing_auth(self, client):
        """Test security endpoint without authentication."""
        response = client.post("/api/1/security/", content=b"")
        assert response.status_code == 401

    def test_security_valid_auth(self, client):
        """Test security endpoint with valid auth."""
        response = client.post(
            "/api/1/security/",
            content=b"",
            headers={"X-Sentry-Auth": "Sentry sentry_key=test_key"},
        )
        assert response.status_code == 200


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint(self, client):
        """Test basic health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
