"""
Global pytest configuration for course record updater.

This file provides pytest fixtures and configuration that are available
to all test modules.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command-line options to pytest."""
    parser.addoption(
        "--use-real-auth",
        action="store_true",
        default=False,
        help="Use real session-based authentication instead of mock auth in tests",
    )


def pytest_configure(config):
    """Configure pytest with custom settings based on command-line options."""
    # Add custom marker for real auth tests
    config.addinivalue_line(
        "markers", "real_auth: marks tests that use real authentication instead of mock"
    )


@pytest.fixture(autouse=True)
def configure_auth_mode(request):
    """
    Automatically configure auth mode for all tests based on --use-real-auth flag.

    This fixture runs before every test and sets up the Flask app configuration
    to use either real or mock authentication.
    """
    use_real_auth = request.config.getoption("--use-real-auth")

    # Import here to avoid circular imports
    from app import app

    # Set the flag in Flask app config
    with app.app_context():
        app.config["USE_REAL_AUTH"] = use_real_auth

    # Optional: Print debug info for first test
    if not hasattr(configure_auth_mode, "_printed"):
        auth_mode = "REAL" if use_real_auth else "MOCK"
        print(f"\n🔐 Auth Mode: {auth_mode} (--use-real-auth={use_real_auth})")
        configure_auth_mode._printed = True
