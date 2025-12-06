"""
Tests for force login parameter and logout error handling.

Ensures users can recover from broken session states.
"""

import pytest
from flask import session


class TestForceLogin:
    """Test force login parameter functionality"""

    def test_force_login_clears_session(self, client):
        """Force login should clear existing session"""
        # First, log in normally
        response = client.post(
            "/api/auth/login",
            json={"email": "demo2025.admin@example.com", "password": "Demo2025!"},
        )
        assert response.status_code == 200

        # Verify we're authenticated
        with client.session_transaction() as sess:
            assert sess.get("user_id") is not None

        # Now access /login?force=true
        response = client.get("/login?force=true", follow_redirects=False)
        assert response.status_code == 200

        # Verify session was cleared
        with client.session_transaction() as sess:
            assert sess.get("user_id") is None

    def test_force_login_shows_login_page(self, client):
        """Force login should show login page even when authenticated"""
        # Log in
        client.post(
            "/api/auth/login",
            json={"email": "demo2025.admin@example.com", "password": "Demo2025!"},
        )

        # Access /login?force=true
        response = client.get("/login?force=true")
        assert response.status_code == 200
        assert b"login" in response.data.lower()

    def test_normal_login_redirects_when_authenticated(self, client):
        """Normal /login should redirect to dashboard when authenticated"""
        # Log in
        client.post(
            "/api/auth/login",
            json={"email": "demo2025.admin@example.com", "password": "Demo2025!"},
        )

        # Access /login (without force)
        response = client.get("/login", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.location

    def test_force_login_with_next_parameter(self, client):
        """Force login should preserve next parameter"""
        # Log in
        client.post(
            "/api/auth/login",
            json={"email": "demo2025.admin@example.com", "password": "Demo2025!"},
        )

        # Access /login?force=true&next=/assessments
        response = client.get("/login?force=true&next=/assessments")
        assert response.status_code == 200

        # Verify next parameter is stored in session
        with client.session_transaction() as sess:
            assert sess.get("next_after_login") == "/assessments"

    def test_force_login_when_not_authenticated(self, client):
        """Force login should work normally when not authenticated"""
        response = client.get("/login?force=true")
        assert response.status_code == 200
        assert b"login" in response.data.lower()


class TestLogoutErrorHandling:
    """Test logout error handling redirects to force login"""

    def test_logout_success_redirects_to_home(self, client):
        """Successful logout should redirect to home"""
        # Log in first
        client.post(
            "/api/auth/login",
            json={"email": "demo2025.admin@example.com", "password": "Demo2025!"},
        )

        # Logout
        response = client.post("/api/auth/logout")
        assert response.status_code == 200

        # Verify session cleared
        with client.session_transaction() as sess:
            assert sess.get("user_id") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
