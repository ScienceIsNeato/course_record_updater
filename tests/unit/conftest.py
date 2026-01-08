"""
Pytest configuration for unit tests.

Provides database fixtures with proper isolation for pytest-xdist parallel execution.
Each worker gets its own database to prevent conflicts.
"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_unit_test_database(tmp_path_factory, worker_id):
    """
    Set up isolated database for each pytest-xdist worker.

    This fixture runs once per worker session and ensures:
    1. Each worker has its own database file (prevents conflicts)
    2. Database tables are created before tests run
    3. Environment variables point to the correct database

    Args:
        tmp_path_factory: pytest fixture for creating temp directories
        worker_id: pytest-xdist worker ID (e.g., 'gw0', 'gw1', or 'master')
    """
    # Create worker-specific database path
    if worker_id == "master":
        # Running without xdist (single process)
        db_path = tmp_path_factory.mktemp("data") / "test.db"
    else:
        # Running with xdist (parallel workers)
        # Each worker gets its own isolated database
        db_path = tmp_path_factory.mktemp("data", numbered=True) / f"{worker_id}.db"

    # Set DATABASE_URL environment variable for this worker
    db_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = db_url
    os.environ["DATABASE_TYPE"] = "sqlite"

    # Initialize database tables
    # Import here to ensure environment variables are set first
    import src.database.database_service as database_service

    # Refresh connection to pick up new DATABASE_URL (updates module-level singleton)
    database_service.refresh_connection()

    # Create all tables
    database_service.reset_database()

    # Return the database path for tests that need it
    yield db_path

    # Cleanup is handled automatically by tmp_path_factory


@pytest.fixture(scope="function", autouse=True)
def reset_db_between_tests():
    """
    Reset database between tests to ensure isolation.

    This prevents test pollution where one test's data affects another.
    Runs automatically before each test function.
    """
    import src.database.database_service as database_service

    # Reset database to clean state
    database_service.reset_database()

    yield
