"""Global test configuration and fixtures for SQLite backend."""

import os
import tempfile

import pytest

import database_service

# Shared test credentials (seeded by seed_db.py)
SITE_ADMIN_EMAIL = "siteadmin@system.local"
SITE_ADMIN_PASSWORD = "SiteAdmin123!"
INSTITUTION_ADMIN_EMAIL = "sarah.admin@cei.edu"
INSTITUTION_ADMIN_PASSWORD = "InstitutionAdmin123!"


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database(tmp_path_factory):
    """Provide isolated test database.

    KISS approach with pytest-xdist support:
    - If DATABASE_URL already set (e.g., by run_uat.sh): use it
    - Otherwise: create a temporary database for this test session/worker
    - Each pytest-xdist worker gets its own database (via tmp_path_factory)

    Args:
        tmp_path_factory: pytest fixture that creates unique temp dirs per worker
    """
    # If already set (E2E tests), use it
    if os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_TYPE"] = "sqlite"
        database_service.refresh_connection()
        yield
        return

    # Create temporary database for unit tests
    # tmp_path_factory is xdist-aware and creates unique dirs per worker
    temp_dir = tmp_path_factory.mktemp("test_db")
    temp_db_path = temp_dir / "test.db"

    os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"
    os.environ["DATABASE_TYPE"] = "sqlite"

    database_service.refresh_connection()

    yield

    # Cleanup happens automatically via tmp_path_factory


@pytest.fixture(autouse=True)
def clean_database_between_tests():
    """Reset database after each test to guarantee isolation.

    Skip for E2E/UAT tests which manage their own database state.
    """
    yield
    # Skip cleanup for E2E/UAT tests - they handle their own state
    env = os.environ.get("ENV", "development")
    if env != "test":
        database_service.reset_database()
