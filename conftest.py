"""
Global pytest configuration for course record updater.

This file provides pytest fixtures and configuration that are available
to all test modules.
"""

import os

import pytest

# Configure environment for testing
os.environ["WTF_CSRF_ENABLED"] = "false"  # Disable CSRF for testing


@pytest.fixture
def client():
    """Create a Flask test client"""
    from app import app

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated test client with mocked session"""
    # Mock session for authentication - simpler than creating real users
    with client.session_transaction() as sess:
        sess["user_id"] = "test-user-id"
        sess["email"] = "test@example.com"
        sess["role"] = "institution_admin"
        sess["institution_id"] = "test-institution"

    yield client
