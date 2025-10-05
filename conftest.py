"""
Global pytest configuration for course record updater.

This file provides pytest fixtures and configuration that are available
to all test modules.

All tests use CSRF-enabled clients to properly exercise security code paths.
"""

import pytest


@pytest.fixture(scope="function", autouse=True)
def _configure_csrf_for_testing():
    """
    Auto-applied fixture that ensures CSRF is enabled for all tests.

    This runs before every test to ensure production-like security validation.
    Tests that create their own clients will inherit this configuration.
    """
    from app import app

    # Store original config
    original_csrf = app.config.get("WTF_CSRF_ENABLED")

    # Enable CSRF for all tests
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = True

    yield

    # Restore original (cleanup)
    if original_csrf is not None:
        app.config["WTF_CSRF_ENABLED"] = original_csrf


@pytest.fixture
def client():
    """
    Create a Flask test client with CSRF ENABLED.

    Use this fixture explicitly when you need the client object.
    """
    from app import app

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
