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

# Default configuration (can be overridden by environment)
DEFAULT_BASE_URL = "http://localhost:3002"
DEFAULT_ADMIN_EMAIL = "siteadmin@system.local"
DEFAULT_ADMIN_PASSWORD = "SiteAdmin123!"


@pytest.mark.smoke
class TestSystemSmoke:
    """Critical path system verification"""

    @pytest.fixture(scope="class")
    def smoke_target_url(self):
        """Get the target base URL"""
        return os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    @pytest.fixture(scope="class")
    def api_session(self, smoke_target_url):
        """Create an authenticated session for API checking"""
        session = requests.Session()

        # 1. Login via API (auth.js uses /api/auth/login)
        # First, get CSRF token from login page
        import re

        login_page_url = f"{smoke_target_url}/login"
        page_resp = session.get(login_page_url)

        csrf_token = None
        # Try to find in meta tag (standard in this app base template)
        meta_match = re.search(r'name="csrf-token" content="([^"]+)"', page_resp.text)
        if meta_match:
            csrf_token = meta_match.group(1)
        # Try to find in input field as fallback
        if not csrf_token:
            input_match = re.search(
                r'name="csrf_token" value="([^"]+)"', page_resp.text
            )
            if input_match:
                csrf_token = input_match.group(1)

        login_url = f"{smoke_target_url}/api/auth/login"
        headers = {"Content-Type": "application/json", "X-CSRFToken": csrf_token or ""}

        payload = {
            "email": os.getenv("SMOKE_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL),
            "password": os.getenv("SMOKE_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
            "remember_me": False,
        }

        # The API expects JSON, not form data
        response = session.post(
            login_url, json=payload, headers=headers, allow_redirects=True, timeout=10
        )

        if response.status_code != 200:
            print(f"Login failed status: {response.status_code}")
            print(f"Response: {response.text}")

        # Verify success (API returns JSON with success: true)
        try:
            data = response.json()
            if data.get("success"):
                return session
        except Exception:
            pass

        # Fallback verification: Check if we can access dashboard
        dash_resp = session.get(f"{smoke_target_url}/dashboard")
        if dash_resp.status_code == 200 and "login" not in dash_resp.url:
            return session

        # If we are here, login failed
        pytest.fail(f"Smoke test authentication failed against {smoke_target_url}")
        return session

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

    def test_seeded_data_availability(self, smoke_target_url, api_session):
        """Verify minimal seeded data availability (Site Admin context)"""
        # 1. Verify we can access the dashboard page (HTML)
        resp = api_session.get(f"{smoke_target_url}/dashboard")
        assert resp.status_code == 200
        # Check for dashboard title/header to confirm we are logged in and on the right page
        assert (
            "Dashboard" in resp.text or "Site Administrator" in resp.text
        ), "Dashboard content not found"

        # 2. Verify we can access API data (since dashboard loads it dynamically)
        # Check for institutions list which should contain the seeded MockU
        api_resp = api_session.get(f"{smoke_target_url}/api/institutions")
        assert (
            api_resp.status_code == 200
        ), f"API Institutions endpoint returned {api_resp.status_code}"

        data = api_resp.json()
        assert data.get("success") is True, "API reported failure"

        # Check for MockU in the returned institutions list
        institutions = data.get("institutions", [])
        mocku_found = any(
            "MockU" in inst.get("name", "") or "Mock University" in inst.get("name", "")
            for inst in institutions
        )

        assert (
            mocku_found
        ), f"Seeded institution 'MockU' not found in API response. Found: {[i.get('name') for i in institutions]}"
