"""
Global pytest configuration for course record updater.

This file provides pytest fixtures and configuration that are available
to all test modules.
"""

import os

import pytest

# Configure environment for testing
# For new tests, use the csrf-enabled fixtures (client, authenticated_client)
# For legacy tests, they create their own clients with CSRF disabled
os.environ["WTF_CSRF_ENABLED"] = "false"  # Default for backward compatibility


@pytest.fixture
def client():
    """
    Create a Flask test client with CSRF ENABLED.

    Use this fixture for new tests that properly handle CSRF tokens.
    Legacy tests create their own clients in setup_method().
    """
    from app import app

    app.config["TESTING"] = True
    # Enable CSRF to properly exercise security code paths
    app.config["WTF_CSRF_ENABLED"] = True

    with app.test_client() as client:
        yield client


@pytest.fixture
def csrf_token(client):
    """
    Get a valid CSRF token from the login page.

    Use this with the `client` fixture to make authenticated requests.
    """
    response = client.get("/login")
    html = response.data.decode("utf-8")

    # Extract CSRF token from hidden input field
    # Format: <input ... name="csrf_token" value="TOKEN_HERE">
    import re

    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        raise Exception("Failed to extract CSRF token from login page")

    return match.group(1)


@pytest.fixture
def authenticated_client(client, csrf_token):
    """
    Create an authenticated test client with proper CSRF handling.

    This fixture:
    1. Gets a real CSRF token from the login page
    2. Sets up an authenticated session
    3. Stores the CSRF token in the session

    Use this for new tests that need authentication with CSRF enabled.
    """
    # Set up session with authentication
    with client.session_transaction() as sess:
        sess["user_id"] = "test-user-id"
        sess["email"] = "test@example.com"
        sess["role"] = "institution_admin"
        sess["institution_id"] = "test-institution"
        # Store CSRF token in session
        sess["csrf_token"] = csrf_token

    yield client
