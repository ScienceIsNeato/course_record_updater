"""
Integration test configuration and fixtures.

This module provides common fixtures for integration tests,
including database setup and institution creation.
"""

import pytest


@pytest.fixture
def client():
    """Create a Flask test client for integration tests."""
    import app

    # Configure the app for testing
    app.app.config["TESTING"] = True
    app.app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    with app.app.test_client() as client:
        with app.app.app_context():
            yield client


@pytest.fixture(scope="session", autouse=True)
def setup_integration_test_data():
    """
    Set up integration test data including default CEI institution.

    This fixture runs once per test session and ensures that:
    1. A baseline CEI institution exists for historical test data
    2. Basic test data is available for integration tests
    """
    try:
        # Import and run the database seeder to create full test dataset
        import sys
        from pathlib import Path

        # Add scripts directory to path
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        from seed_db import DatabaseSeeder

        # Create full seeded dataset for integration tests
        seeder = DatabaseSeeder(verbose=False)  # Reduce noise in test output
        seeder.seed_full_dataset()
        print("✅ Seeded full database for integration tests")

    except Exception as e:
        print(f"⚠️  Warning: Could not seed database for integration tests: {e}")
        # Don't fail the tests if this setup fails - let individual tests handle it
