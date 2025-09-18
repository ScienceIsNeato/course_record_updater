"""
Shared test utilities to eliminate code duplication across test files.
"""

from flask import session
import json


def create_test_session(client, user_data):
    """
    Helper function to create a test session with user data.
    This replaces the duplicated function across 33+ test files.
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


def create_authenticated_client(app, user_data):
    """
    Create a test client with an authenticated session.
    This solves the auth issue by ensuring the session is on the same client used for requests.
    
    Args:
        app: Flask app instance
        user_data: Dictionary with user session data
        
    Returns:
        Test client with authenticated session
    """
    client = app.test_client()
    create_test_session(client, user_data)
    return client


def make_authenticated_request(client, method, url, user_data=None, **kwargs):
    """
    Make an authenticated request using an existing client or creating a session.
    
    Args:
        client: Test client (can be self.client or app.test_client())
        method: HTTP method ('get', 'post', 'put', 'delete')
        url: Request URL
        user_data: User data for session (if not already authenticated)
        **kwargs: Additional arguments for the request
        
    Returns:
        Response object
    """
    # If user_data provided, ensure session exists
    if user_data:
        create_test_session(client, user_data)
    
    # Make the request
    method_func = getattr(client, method.lower())
    return method_func(url, **kwargs)


def authenticated_test_client(app_instance, user_data):
    """
    Create a Flask test client with authentication session.
    This is the key function that solves the auth issue by ensuring
    the session and request happen on the same client instance.
    
    Usage:
        with authenticated_test_client(app, user_data) as client:
            response = client.post('/api/endpoint', json={...})
    
    Args:
        app_instance: Flask app instance  
        user_data: User data dictionary for session
        
    Returns:
        Context manager that yields authenticated test client
    """
    from contextlib import contextmanager
    
    @contextmanager
    def _client_context():
        client = app_instance.test_client()
        create_test_session(client, user_data)
        yield client
    
    return _client_context()


class AuthenticatedTestMixin:
    """
    Mixin class to provide authenticated request helpers to test classes.
    Usage: class TestMyAPI(AuthenticatedTestMixin, unittest.TestCase):
    """
    
    def make_auth_request(self, method, url, user_data, **kwargs):
        """Make an authenticated request using self.client."""
        return make_authenticated_request(self.client, method, url, user_data, **kwargs)
    
    def post_auth(self, url, user_data, **kwargs):
        """Make authenticated POST request."""
        return self.make_auth_request('post', url, user_data, **kwargs)
    
    def get_auth(self, url, user_data, **kwargs):
        """Make authenticated GET request."""
        return self.make_auth_request('get', url, user_data, **kwargs)
    
    def put_auth(self, url, user_data, **kwargs):
        """Make authenticated PUT request."""
        return self.make_auth_request('put', url, user_data, **kwargs)
    
    def delete_auth(self, url, user_data, **kwargs):
        """Make authenticated DELETE request."""
        return self.make_auth_request('delete', url, user_data, **kwargs)


# Standard test user data templates
ADMIN_USER_DATA = {
    "id": "admin-456",
    "email": "admin@test.com",
    "role": "institution_admin",
    "institution_id": "inst-123",
    "display_name": "Test Admin",
}

INSTRUCTOR_USER_DATA = {
    "id": "instructor-789",
    "email": "instructor@test.com", 
    "role": "instructor",
    "institution_id": "inst-123",
    "display_name": "Test Instructor",
}

PROGRAM_ADMIN_USER_DATA = {
    "id": "program-admin-101",
    "email": "program.admin@test.com",
    "role": "program_admin", 
    "institution_id": "inst-123",
    "program_ids": ["prog-456"],
    "display_name": "Test Program Admin",
}

SITE_ADMIN_USER_DATA = {
    "id": "site-admin-202",
    "email": "site.admin@test.com",
    "role": "site_admin",
    "display_name": "Test Site Admin",
}
