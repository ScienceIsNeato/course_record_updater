"""
Test for logout CSRF token issue

This test reproduces the issue where the dashboard logout function
fails because it doesn't include CSRF tokens in the request headers.
"""

import json
from unittest.mock import patch

import pytest
from flask import session

from src.app import src.app as app


class TestLogoutCSRFIssue:
    """Test logout CSRF token handling"""

    @pytest.fixture
    def client_with_csrf(self):
        """Create test client with CSRF protection enabled"""
        # Store original config
        original_csrf_enabled = app.config.get("WTF_CSRF_ENABLED")

        try:
            # Configure for CSRF testing
            app.config["TESTING"] = True
            app.config["SECRET_KEY"] = "test-secret-key"
            app.config["WTF_CSRF_ENABLED"] = True  # Force enable CSRF for this test

            with app.test_client() as client:
                with app.app_context():
                    yield client
        finally:
            # Restore original config
            if original_csrf_enabled is not None:
                app.config["WTF_CSRF_ENABLED"] = original_csrf_enabled
            else:
                app.config.pop("WTF_CSRF_ENABLED", None)

    def test_logout_without_csrf_token_should_fail(self, client_with_csrf):
        """Test that logout fails without CSRF token (CSRF is now required)"""
        # Create a session with a logged in user
        with client_with_csrf.session_transaction() as sess:
            sess["user_id"] = "test-user-123"
            sess["email"] = "instructor@test.com"
            sess["role"] = "instructor"
            sess["institution_id"] = "test-institution"
            sess["first_name"] = "Test"
            sess["last_name"] = "Instructor"

        # Bypass the automatic CSRF injection by explicitly setting an empty header
        # This simulates what would happen if the JavaScript didn't include the token
        response = client_with_csrf.post(
            "/api/auth/logout",
            headers={"Content-Type": "application/json", "X-CSRFToken": ""},
        )

        # Should fail - CSRF is now required for all POST requests
        assert response.status_code == 400
        # Flask-WTF returns HTML error pages for CSRF failures
        assert b"CSRF" in response.data or b"Bad Request" in response.data

    def test_logout_with_csrf_token_should_succeed(self, client_with_csrf):
        """Test that logout succeeds when CSRF token is included"""
        # Create a session with a logged in user
        with client_with_csrf.session_transaction() as sess:
            sess["user_id"] = "test-user-456"
            sess["email"] = "instructor2@test.com"
            sess["role"] = "instructor"
            sess["institution_id"] = "test-institution"
            sess["first_name"] = "Test"
            sess["last_name"] = "Instructor2"

        # The key insight: Flask-WTF CSRF tokens are tied to the request context
        # We need to make a GET request first to establish a session with a CSRF token
        # Then extract that token and use it in our POST request

        # Step 1: Make a GET request to any endpoint to generate a CSRF token
        get_response = client_with_csrf.get(
            "/dashboard"
        )  # This should generate a CSRF token

        # Step 2: Extract the CSRF token from the response
        # Flask-WTF puts the token in the session and also in the HTML (if using templates)
        # Let's extract it from the session after the GET request
        csrf_token = None
        with client_with_csrf.session_transaction() as sess:
            raw_token = sess.get("csrf_token")
            if raw_token:
                # Generate the signed token from the raw token
                from flask_wtf.csrf import generate_csrf

                with client_with_csrf.application.test_request_context():
                    # Set the raw token in the session for this context
                    from flask import session

                    session["csrf_token"] = raw_token
                    csrf_token = generate_csrf()

        # Step 3: Use the CSRF token in the POST request
        response = client_with_csrf.post(
            "/api/auth/logout",
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": csrf_token,
            },
        )

        # This should succeed
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["logout_success"] is True

    def test_dashboard_logout_function_includes_csrf_token(self):
        """Test that the dashboard logout function now includes CSRF token (after fix)"""
        import os

        # Read the dashboard template using a relative path
        # __file__ is tests/unit/test_logout_csrf_issue.py
        # Go up two levels to get to project root: tests/unit -> tests -> project_root
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        template_path = os.path.join(
            project_root, "templates", "dashboard", "base_dashboard.html"
        )

        with open(template_path, "r") as f:
            template_content = f.read()

        # Check that the logout function exists
        assert "async function logout()" in template_content

        # Check that it makes a POST request to /api/auth/logout
        assert "'/api/auth/logout'" in template_content
        assert "method: 'POST'" in template_content

        # Extract the logout function (find the end of the complete function)
        logout_function_start = template_content.find("async function logout()")
        # Find the closing brace that matches the function (need to count braces)
        brace_count = 0
        pos = logout_function_start
        while pos < len(template_content):
            if template_content[pos] == "{":
                brace_count += 1
            elif template_content[pos] == "}":
                brace_count -= 1
                if brace_count == 0:
                    logout_function_end = pos
                    break
            pos += 1
        logout_function = template_content[
            logout_function_start : logout_function_end + 1
        ]

        # Verify the fix - CSRF token is now included
        assert "X-CSRFToken" in logout_function
        assert "csrf_token()" in logout_function

        # Should still have Content-Type header
        assert "Content-Type" in logout_function
