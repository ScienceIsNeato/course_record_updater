"""
Test utilities for course record updater tests.
Provides authentication helpers and test data for consistent testing.
"""

import json
from contextlib import contextmanager

from flask import current_app, session

# Standard test user data
ADMIN_USER_DATA = {
    "user_id": "test-admin-123",
    "email": "admin@test.edu",
    "role": "site_admin",
    "first_name": "Test",
    "last_name": "Admin",
    "institution_id": "test-inst-123",
    "program_ids": ["test-prog-123", "test-prog-456"],
    "display_name": "Test Admin",
}

INSTRUCTOR_USER_DATA = {
    "user_id": "test-instructor-456",
    "email": "instructor@test.edu",
    "role": "instructor",
    "first_name": "Test",
    "last_name": "Instructor",
    "institution_id": "test-inst-123",
    "program_ids": ["test-prog-123"],
    "display_name": "Test Instructor",
}


def require_auth_session(client, user_data):
    """
    Create a test session that's compatible with session authentication.

    It creates a proper Flask session that SessionService can read.

    Args:
        client: Flask test client
        user_data: Dictionary with user session data
    """
    # Always create a proper session (session auth is now default)
    create_test_session(client, user_data)


def create_test_session(client, user_data):
    """
    Helper function to create a test session with user data.
    Works with both mock and real auth modes.
    """
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


def setup_admin_auth(client):
    """Quick setup for admin authentication"""
    create_test_session(client, ADMIN_USER_DATA)


def setup_instructor_auth(client):
    """Quick setup for instructor authentication"""
    create_test_session(client, INSTRUCTOR_USER_DATA)


class RealAuthTestMixin:
    """
    Mixin for test classes that want to use real authentication.

    Usage:
    class TestMyEndpoints(RealAuthTestMixin):
        def setup_method(self):
            super().setup_method()  # Enables real auth
            self.app = app
            self.client = app.test_client()
    """

    # Real auth is now enabled by default - no setup needed


@contextmanager
def authenticated_test_client(app_instance, user_data):
    """
    Context manager for authenticated test client.

    Usage:
    with authenticated_test_client(app, ADMIN_USER_DATA) as client:
        response = client.get('/api/endpoint')
    """
    client = app_instance.test_client()
    create_test_session(client, user_data)
    yield client


def get_authenticated_client(app_instance, user_data):
    """
    Creates a new Flask test client and authenticates it with the given user data.
    """
    client = app_instance.test_client()
    create_test_session(client, user_data)
    return client


class AuthenticatedTestMixin:
    """
    Mixin that provides authenticated request helpers.
    """

    def make_authenticated_request(self, method, url, user_data=None, **kwargs):
        """Make an authenticated request"""
        if user_data is None:
            user_data = ADMIN_USER_DATA

        client = get_authenticated_client(self.app, user_data)
        return getattr(client, method.lower())(url, **kwargs)


class CommonAuthMixin:
    """
    Common authentication mixin for test classes.
    Provides standardized login methods to avoid duplication across test classes.
    """

    def _get_default_site_admin_user(self):
        """Default site admin user data"""
        return {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }

    def _login_site_admin(self, overrides=None):
        """Authenticate requests as a site admin user."""
        user_data = {**self._get_default_site_admin_user()}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def _login_user(self, overrides=None):
        """Alias for _login_site_admin for backward compatibility"""
        return self._login_site_admin(overrides)

    def _login_institution_admin(self, overrides=None):
        """Authenticate as institution admin"""
        defaults = {
            "user_id": "inst-admin-123",
            "email": "inst-admin@test.com",
            "role": "institution_admin",
            "institution_id": "inst-123",
        }
        user_data = {**defaults}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data
