"""
Simple API health test - no auth required

This test verifies the basic server functionality without authentication.
"""

import pytest
import requests


def create_test_session(client, user_data):
    """Helper function to create a test session with user data."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_data.get("user_id")
        sess["email"] = user_data.get("email")
        sess["role"] = user_data.get("role")
        sess["institution_id"] = user_data.get("institution_id")
        sess["program_ids"] = user_data.get("program_ids", [])
        sess["display_name"] = user_data.get(
            "display_name",
            f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
        )
        sess["created_at"] = user_data.get("created_at")
        sess["last_activity"] = user_data.get("last_activity")
        sess["remember_me"] = user_data.get("remember_me", False)


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
