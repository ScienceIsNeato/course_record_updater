"""
Global pytest configuration for course record updater.

This file provides pytest fixtures and configuration that are available
to all test modules.

All tests use CSRF-enabled clients to properly exercise security code paths.
"""

import re

import pytest


def _get_csrf_token_from_session_or_generate(client):
    """Get CSRF token from session or generate a new one."""
    import secrets

    from flask_wtf.csrf import generate_csrf

    from src.app import app

    # Strategy: Always ensure session has a raw token, then generate signed token from it
    raw_token = None

    # Try to get existing raw token from session
    with client.session_transaction() as sess:
        if "csrf_token" in sess:
            raw_token = sess["csrf_token"]

    # If no token exists, create one and store it
    if not raw_token:
        raw_token = secrets.token_hex(16)
        with client.session_transaction() as sess:
            sess["csrf_token"] = raw_token

    # Generate the signed token from the raw token
    try:
        with app.test_request_context():
            from flask import session as flask_session

            flask_session["csrf_token"] = raw_token
            return generate_csrf()
    except Exception:
        return None


def _make_csrf_wrapper(client, original_method):
    """Create a wrapper that injects CSRF tokens from session on-demand."""

    def wrapper(*args, **kwargs):
        # Get token (checks session first, then generates if needed)
        token = _get_csrf_token_from_session_or_generate(client)
        if not token:
            return original_method(*args, **kwargs)

        # Inject token in headers (for JSON requests)
        # Make copy if headers exist to avoid mutating immutable objects
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        elif not isinstance(kwargs["headers"], dict):
            # If headers is not a dict (e.g., tuple of tuples), convert to dict
            kwargs["headers"] = dict(kwargs["headers"])
        else:
            # Make a copy to avoid mutating caller's dict
            kwargs["headers"] = dict(kwargs["headers"])

        if "X-CSRFToken" not in kwargs["headers"]:
            kwargs["headers"]["X-CSRFToken"] = token

        # Also inject in form data (for multipart/form-data requests)
        # Make copy if data exists to avoid mutating immutable objects
        if "data" in kwargs and isinstance(kwargs["data"], dict):
            if "csrf_token" not in kwargs["data"]:
                # Make a copy to avoid mutating caller's dict
                kwargs["data"] = dict(kwargs["data"])
                kwargs["data"]["csrf_token"] = token

        return original_method(*args, **kwargs)

    return wrapper


@pytest.fixture(scope="function", autouse=True)
def _configure_csrf_for_testing():
    """
    Auto-applied fixture that ensures CSRF is enabled for all tests.

    This runs before every test to ensure production-like security validation.
    It also monkeypatches app.test_client() to return CSRF-aware clients.
    """
    from src.app import app

    # Store original config and methods
    original_csrf = app.config.get("WTF_CSRF_ENABLED")
    original_test_client = app.test_client

    # Enable CSRF for all tests
    app.config["TESTING"] = True  # nosemgrep
    app.config["WTF_CSRF_ENABLED"] = True

    # Monkeypatch app.test_client() to return CSRF-aware clients
    def csrf_aware_test_client(*args, **kwargs):
        """Create a test client with automatic CSRF injection."""
        client = original_test_client(*args, **kwargs)

        # Wrap POST/PUT/PATCH/DELETE methods with CSRF injection
        # Wrap all mutation methods with CSRF injection
        client.post = _make_csrf_wrapper(client, client.post)
        client.put = _make_csrf_wrapper(client, client.put)
        client.patch = _make_csrf_wrapper(client, client.patch)
        client.delete = _make_csrf_wrapper(client, client.delete)

        return client

    app.test_client = csrf_aware_test_client

    yield

    # Restore original (cleanup)
    app.test_client = original_test_client
    if original_csrf is not None:
        app.config["WTF_CSRF_ENABLED"] = original_csrf


@pytest.fixture
def client():
    """
    Create a Flask test client with CSRF ENABLED.

    Use this fixture explicitly when you need the client object.
    """
    from src.app import app

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
        raise ValueError("Failed to extract CSRF token from login page")

    return match.group(1)


@pytest.fixture
def authenticated_client(client, csrf_token):
    """
    Create an authenticated test client with proper CSRF handling.

    This fixture:
    1. Gets a real CSRF token from the login page
    2. Sets up an authenticated session
    3. Stores the CSRF token in the session
    4. Automatically injects CSRF tokens into POST/PUT/DELETE requests

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

    # Wrap the client's request methods to automatically inject CSRF tokens
    original_post = client.post
    original_put = client.put
    original_delete = client.delete

    def post_with_csrf(*args, **kwargs):
        """POST with automatic CSRF token injection"""
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "X-CSRFToken" not in kwargs["headers"]:
            kwargs["headers"]["X-CSRFToken"] = csrf_token
        return original_post(*args, **kwargs)

    def put_with_csrf(*args, **kwargs):
        """PUT with automatic CSRF token injection"""
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "X-CSRFToken" not in kwargs["headers"]:
            kwargs["headers"]["X-CSRFToken"] = csrf_token
        return original_put(*args, **kwargs)

    def delete_with_csrf(*args, **kwargs):
        """DELETE with automatic CSRF token injection"""
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "X-CSRFToken" not in kwargs["headers"]:
            kwargs["headers"]["X-CSRFToken"] = csrf_token
        return original_delete(*args, **kwargs)

    # Monkey-patch the client
    client.post = post_with_csrf
    client.put = put_with_csrf
    client.delete = delete_with_csrf

    yield client

    # Restore original methods
    client.post = original_post
    client.put = original_put
    client.delete = original_delete
