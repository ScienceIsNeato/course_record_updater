"""
Simple API health test - no auth required

This test verifies the basic server functionality without authentication.
"""

import pytest
import requests


class TestAPIHealth:
    """Test basic API functionality"""

    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for the test server"""
        import os

        port = os.getenv("DEFAULT_PORT", "3001")
        return f"http://localhost:{port}"

    def test_health_endpoint(self, base_url: str):
        """Test that the health endpoint returns 200 OK"""
        response = requests.get(f"{base_url}/api/health", timeout=5)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "healthy"

    def test_root_page_loads(self, base_url: str):
        """Test that the root page loads"""
        response = requests.get(base_url, timeout=5)
        assert response.status_code == 200
        assert "html" in response.headers.get("content-type", "").lower()
