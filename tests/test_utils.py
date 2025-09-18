"""
Centralized test utilities to eliminate code duplication across test files.
Replaces the create_test_session function duplicated across 33+ test files.
"""

import json
from flask import session
from contextlib import contextmanager


# Standard test user data
ADMIN_USER_DATA = {
    "user_id": "admin-456",
    "email": "admin@test.com",
    "role": "institution_admin",
    "institution_id": "inst-123",
    "program_ids": ["prog-1", "prog-2"],
    "display_name": "Admin User",
    "first_name": "Admin",
    "last_name": "User",
    "created_at": "2024-01-01T00:00:00Z",
    "last_activity": "2024-01-01T00:00:00Z",
    "remember_me": False,
}

INSTRUCTOR_USER_DATA = {
    "user_id": "instructor-789",
    "email": "instructor@test.com",
    "role": "instructor",
    "institution_id": "inst-123",
    "program_ids": ["prog-1"],
    "display_name": "Instructor User",
    "first_name": "Instructor",
    "last_name": "User",
    "created_at": "2024-01-01T00:00:00Z",
    "last_activity": "2024-01-01T00:00:00Z",
    "remember_me": False,
}


def create_test_session(client, user_data):
    """
    Helper function to create a test session with user data.
    This replaces the duplicated function across 33+ test files.
    
    Args:
        client: Flask test client
        user_data: Dictionary containing user session data
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


def get_authenticated_client(app_instance, user_data):
    """
    Creates a new Flask test client and authenticates it with the given user data.
    
    Args:
        app_instance: Flask app instance
        user_data: Dictionary containing user session data
        
    Returns:
        Authenticated Flask test client
    """
    client = app_instance.test_client()
    create_test_session(client, user_data)
    return client


def make_authenticated_request(client, method, url, user_data=None, **kwargs):
    """
    Make an authenticated request using the test client.
    
    Args:
        client: Flask test client
        method: HTTP method (GET, POST, PUT, DELETE)
        url: Request URL
        user_data: Optional user data for authentication (uses ADMIN_USER_DATA if None)
        **kwargs: Additional arguments passed to the request method
        
    Returns:
        Response object
    """
    if user_data:
        create_test_session(client, user_data)
    elif user_data is None:
        create_test_session(client, ADMIN_USER_DATA)
    
    method_func = getattr(client, method.lower())
    return method_func(url, **kwargs)


@contextmanager
def authenticated_test_client(app_instance, user_data):
    """
    Context manager for creating an authenticated test client.
    
    Args:
        app_instance: Flask app instance
        user_data: Dictionary containing user session data
        
    Yields:
        Authenticated Flask test client
    """
    client = get_authenticated_client(app_instance, user_data)
    try:
        yield client
    finally:
        # Cleanup if needed
        pass


class AuthenticatedTestMixin:
    """
    Mixin class providing authenticated request helpers for test classes.
    """
    
    def setup_method(self):
        """Set up test fixtures - should be called by test classes."""
        # This will be overridden by test classes to set self.app and self.client
        pass
    
    def make_authenticated_get(self, url, user_data=None, **kwargs):
        """Make authenticated GET request."""
        return make_authenticated_request(self.client, "GET", url, user_data, **kwargs)
    
    def make_authenticated_post(self, url, user_data=None, **kwargs):
        """Make authenticated POST request."""
        return make_authenticated_request(self.client, "POST", url, user_data, **kwargs)
    
    def make_authenticated_put(self, url, user_data=None, **kwargs):
        """Make authenticated PUT request."""
        return make_authenticated_request(self.client, "PUT", url, user_data, **kwargs)
    
    def make_authenticated_delete(self, url, user_data=None, **kwargs):
        """Make authenticated DELETE request."""
        return make_authenticated_request(self.client, "DELETE", url, user_data, **kwargs)