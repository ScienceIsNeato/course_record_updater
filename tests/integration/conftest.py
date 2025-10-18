"""
Integration test configuration and fixtures.

This module provides common fixtures for integration tests,
including database setup and institution creation.
"""

import os

import pytest


@pytest.fixture
def client():
    """Create a Flask test client for integration tests."""
    import app

    # Configure the app for testing
    app.app.config["TESTING"] = True

    with app.app.test_client() as client:
        with app.app.app_context():
            yield client


@pytest.fixture(scope="class", autouse=True)
def setup_integration_test_data():
    """
    Set up integration test data including default MockU institution.

    This fixture runs once per test class and ensures that:
    1. A baseline MockU institution exists for historical test data
    2. Basic test data is available for integration tests
    3. Database connection is properly established
    """
    try:
        # Import and run the database seeder to create full test dataset
        import sys
        from pathlib import Path

        # Add scripts directory to path
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        from seed_db import DatabaseSeeder

        import database_service as db

        # Check if data already exists to avoid duplicate seeding
        institutions = db.get_all_institutions() or []
        mocku_exists = any(
            "California Engineering Institute" in inst.get("name", "")
            for inst in institutions
        )

        if not mocku_exists:
            # Create full seeded dataset for integration tests
            seeder = DatabaseSeeder(verbose=False)  # Reduce noise in test output
            seeder.seed_full_dataset()
            print("✅ Seeded full database for integration tests")
        else:
            print("✅ Integration test data already exists")

    except Exception as e:
        print(f"⚠️  Warning: Could not seed database for integration tests: {e}")
        # Don't fail the tests if this setup fails - let individual tests handle it


@pytest.fixture(scope="session", autouse=True)
def setup_integration_test_database(tmp_path_factory):
    """
    Set up integration test database with email whitelist configuration.

    This runs once per test session and:
    1. Creates a temporary database for integration tests
    2. Configures email whitelist to allow test emails
    3. Sets up environment variables for integration testing
    """
    # Set up email whitelist for integration tests to allow test emails
    # Use wildcard to allow all test emails
    os.environ["EMAIL_WHITELIST"] = (
        "*@inst.test,*@example.com,*@testu.edu,*@eu.edu,*@mocku.test,*@ethereal.email"
    )

    # Create temporary database for integration tests
    db_path = tmp_path_factory.mktemp("data") / "integration_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DATABASE_TYPE"] = "sqlite"

    # Initialize database - must call refresh_connection() to update module-level singleton
    import database_service

    database_service.refresh_connection()
    database_service.reset_database()

    yield db_path

    # Cleanup email whitelist after tests
    if "EMAIL_WHITELIST" in os.environ:
        del os.environ["EMAIL_WHITELIST"]


@pytest.fixture(scope="function", autouse=True)
def clean_database_between_tests():
    """
    Clean database between integration tests to prevent pollution.

    This ensures each test starts with a fresh database state.
    """
    import database_service

    # Reset database to clean state
    database_service.reset_database()

    yield
