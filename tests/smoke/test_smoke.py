"""
Critical Path Smoke Tests - PRODUCTION SAFE

These tests verify the core system functionality against a running environment.
They are designed to be safe to run against production (read-only operations where possible).

Scope:
1. System Health (API status)
2. Authentication (Login flow)
3. Data Availability (Seeded data check)
"""

import os

import pytest
import requests

from src.utils.constants import SITE_ADMIN_EMAIL

# Default configuration (can be overridden by environment)

DEFAULT_PORT = os.getenv("TEST_PORT", "3003")  # Smoke tests run on port 3003
DEFAULT_BASE_URL = f"http://localhost:{DEFAULT_PORT}"
DEFAULT_ADMIN_EMAIL = SITE_ADMIN_EMAIL


@pytest.mark.smoke
class TestSystemSmoke:
    """Critical path system verification"""

    @pytest.fixture(scope="class")
    def smoke_target_url(self):
        """Get the target base URL"""
        return os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    def test_api_health(self, smoke_target_url):
        """Verify API health endpoint is accessible and healthy"""
        try:
            resp = requests.get(f"{smoke_target_url}/api/health", timeout=5)
            assert (
                resp.status_code == 200
            ), f"Health endpoint returned {resp.status_code}"
            data = resp.json()
            assert (
                data.get("status") == "healthy"
            ), f"System reported unhealthy status: {data}"
        except requests.exceptions.ConnectionError:
            pytest.fail(f"Could not connect to server at {smoke_target_url}")

    def test_basic_authentication_flow(self, smoke_target_url):
        """Verify strict authentication boundaries"""
        # 1. Verify protected endpoint rejects unauthenticated access
        resp = requests.get(f"{smoke_target_url}/dashboard", allow_redirects=False)
        assert resp.status_code == 302, "Protected route should redirect"
        assert "/login" in resp.headers.get("Location", ""), "Should redirect to login"
