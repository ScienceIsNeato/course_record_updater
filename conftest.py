"""
Global pytest configuration for LoopCloser.

This file provides pytest fixtures and configuration that are available
to all test modules.

All tests use CSRF-enabled clients to properly exercise security code paths.
"""

import time
from typing import Any, Callable, Generator, cast

import pytest
from flask.testing import FlaskClient


# =============================================================================
# Fixture Performance Gate
# =============================================================================
# Warns when function-scoped fixtures take too long, which often indicates
# expensive setup that should be moved to session or module scope.
# This caught the ~70ms/fixture * 1600 tests = 112s overhead issue.
# =============================================================================

FIXTURE_SLOW_THRESHOLD_MS = 10.0  # Warn if fixture takes longer than this


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):  # type: ignore[no-untyped-def]
    """Monitor fixture setup time and warn about slow function-scoped fixtures."""
    start = time.perf_counter()
    yield
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Only warn for function-scoped fixtures (the ones that run per-test)
    if fixturedef.scope == "function" and elapsed_ms > FIXTURE_SLOW_THRESHOLD_MS:
        import warnings

        warnings.warn(
            f"Slow fixture: '{fixturedef.argname}' took {elapsed_ms:.1f}ms "
            f"(threshold: {FIXTURE_SLOW_THRESHOLD_MS}ms). "
            f"Consider session/module scope if setup is expensive.",
            stacklevel=1,
        )


def _get_csrf_token_from_session_or_generate(client: FlaskClient) -> str | None:
    """Get CSRF token from session or generate a new one."""
    import secrets

    from flask_wtf.csrf import generate_csrf  # type: ignore[import]

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
    except Exception as e:
        # Log error for debugging instead of silently returning None
        import warnings

        warnings.warn(f"Failed to generate CSRF token in test: {e}")
        return None


def _make_csrf_wrapper(
    client: FlaskClient, original_method: Callable[..., Any]
) -> Callable[..., Any]:
    """Create a wrapper that injects CSRF tokens from session on-demand."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
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
def _configure_csrf_for_testing() -> Generator[None, None, None]:
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
    def csrf_aware_test_client(*args: Any, **kwargs: Any) -> FlaskClient:
        """Create a test client with automatic CSRF injection."""
        client = original_test_client(*args, **kwargs)

        # Wrap POST/PUT/PATCH/DELETE methods with CSRF injection
        # Wrap all mutation methods with CSRF injection
        setattr(
            client,
            "post",
            cast(Callable[..., Any], _make_csrf_wrapper(client, client.post)),
        )
        setattr(
            client,
            "put",
            cast(Callable[..., Any], _make_csrf_wrapper(client, client.put)),
        )
        setattr(
            client,
            "patch",
            cast(Callable[..., Any], _make_csrf_wrapper(client, client.patch)),
        )
        setattr(
            client,
            "delete",
            cast(Callable[..., Any], _make_csrf_wrapper(client, client.delete)),
        )

        return client

    setattr(app, "test_client", csrf_aware_test_client)

    yield

    # Restore original (cleanup)
    setattr(app, "test_client", original_test_client)
    if original_csrf is not None:
        app.config["WTF_CSRF_ENABLED"] = original_csrf


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    """
    Create a Flask test client with CSRF ENABLED.

    Use this fixture explicitly when you need the client object.
    """
    from src.app import app

    with app.test_client() as client:
        yield client


@pytest.fixture
def csrf_token(client: FlaskClient) -> str:
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
def authenticated_client(
    client: FlaskClient,
    csrf_token: str,
) -> Generator[FlaskClient, None, None]:
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

    def post_with_csrf(*args: Any, **kwargs: Any) -> Any:
        """POST with automatic CSRF token injection"""
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "X-CSRFToken" not in kwargs["headers"]:
            kwargs["headers"]["X-CSRFToken"] = csrf_token
        return original_post(*args, **kwargs)

    def put_with_csrf(*args: Any, **kwargs: Any) -> Any:
        """PUT with automatic CSRF token injection"""
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "X-CSRFToken" not in kwargs["headers"]:
            kwargs["headers"]["X-CSRFToken"] = csrf_token
        return original_put(*args, **kwargs)

    def delete_with_csrf(*args: Any, **kwargs: Any) -> Any:
        """DELETE with automatic CSRF token injection"""
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "X-CSRFToken" not in kwargs["headers"]:
            kwargs["headers"]["X-CSRFToken"] = csrf_token
        return original_delete(*args, **kwargs)

    # Monkey-patch the client
    setattr(client, "post", cast(Callable[..., Any], post_with_csrf))
    setattr(client, "put", cast(Callable[..., Any], put_with_csrf))
    setattr(client, "delete", cast(Callable[..., Any], delete_with_csrf))

    yield client

    # Restore original methods
    setattr(client, "post", original_post)
    setattr(client, "put", original_put)
    setattr(client, "delete", original_delete)
