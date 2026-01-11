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
import re

import pytest
import requests

# Default configuration (can be overridden by environment)

DEFAULT_PORT = os.getenv("TEST_PORT", "3003")  # Smoke tests run on port 3003
DEFAULT_BASE_URL = f"http://localhost:{DEFAULT_PORT}"
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

        # 1) Fetch login page to obtain CSRF token (and session cookie)
        login_page = session.get(f"{smoke_target_url}/login", timeout=10)
        csrf_token = None
        csrf_match = re.search(
            r'name="csrf_token" value="([^"]+)"', login_page.text, re.IGNORECASE
        )
        if csrf_match:
            csrf_token = csrf_match.group(1)
        else:
            meta_match = re.search(
                r'name="csrf-token" content="([^"]+)"', login_page.text, re.IGNORECASE
            )
            if meta_match:
                csrf_token = meta_match.group(1)

        if not csrf_token:
            print("Login page did not contain a CSRF token")
            pytest.fail("Could not obtain CSRF token for login")

        # 2) POST to JSON login API with CSRF token header
        login_url = f"{smoke_target_url}/api/auth/login"
        payload = {
            "email": os.getenv("SMOKE_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL),
            "password": os.getenv("SMOKE_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
            "remember_me": False,
        }
        headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token,
            "Referer": f"{smoke_target_url}/login",
        }

        response = session.post(
            login_url, json=payload, headers=headers, allow_redirects=True, timeout=10
        )

        if response.status_code == 400 and "CSRF" in response.text:
            # CSRF validation - try without token for smoke tests
            response = session.post(
                login_url, json=payload, allow_redirects=True, timeout=10
            )

        if response.status_code != 200:
            print(f"Login failed with status {response.status_code}")
            print(f"Response text: {response.text[:500]}...")
            pytest.fail("Login failed - check credentials and server logs")

        # Verify success response
        try:
            data = response.json()
            if not data.get("success"):
                print(f"Login API response: {data}")
                pytest.fail("Login failed - API did not return success")
        except Exception:
            print(f"Non-JSON login response: {response.text[:500]}...")
            pytest.fail("Login failed - unexpected response format")

        # Verify we're actually logged in by checking the dashboard
        dash_resp = session.get(f"{smoke_target_url}/dashboard", timeout=10)
        if dash_resp.status_code != 200 or "login" in dash_resp.url:
            print(f"Dashboard access failed with status {dash_resp.status_code}")
            print(f"Dashboard URL: {dash_resp.url}")
            pytest.fail("Failed to access dashboard after login")

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
