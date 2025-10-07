"""
UAT Test Configuration and Fixtures

Provides UAT-specific fixtures and configuration for user acceptance testing.
"""

import pytest


@pytest.fixture(scope="function")
def clean_database():
    """
    Ensure clean database state for each UAT test.

    UAT tests create rich test data and should start with a clean slate.
    """
    import database_service

    database_service.reset_database()
    yield
    # Cleanup after test
    database_service.reset_database()


@pytest.fixture(scope="session")
def uat_test_client():
    """
    Provide Flask test client configured for UAT testing.
    """
    from app import app

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "uat-test-secret-key"

    with app.test_client() as client:
        yield client
