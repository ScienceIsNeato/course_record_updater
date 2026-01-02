"""Global test configuration and fixtures for SQLite backend."""

import os
import tempfile

import pytest

import src.database.database_service as database_service


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection order to run bulk_email tests FIRST.

    This is necessary because bulk_email tests need to mock permission_required
    before any other test imports the main Flask app (which auto-imports bulk_email).

    Running bulk_email tests first ensures the mock is applied before the decorators
    are evaluated.
    """
    bulk_email_tests = []
    other_tests = []

    for item in items:
        if "test_bulk_email" in str(item.fspath):
            bulk_email_tests.append(item)
        else:
            other_tests.append(item)

    # Run bulk_email tests FIRST
    items[:] = bulk_email_tests + other_tests


# Shared test credentials (seeded by seed_db.py)
# Import from E2E test data contract if available for consistency
try:
    from tests.e2e.e2e_test_data_contract import BASE_ACCOUNTS

    SITE_ADMIN_EMAIL = BASE_ACCOUNTS["site_admin"]["email"]
    SITE_ADMIN_PASSWORD = BASE_ACCOUNTS["site_admin"]["password"]
    INSTITUTION_ADMIN_EMAIL = BASE_ACCOUNTS["institution_admin"]["email"]
    INSTITUTION_ADMIN_PASSWORD = BASE_ACCOUNTS["institution_admin"]["password"]
except (ImportError, KeyError):
    # Fallback if contract not available
    SITE_ADMIN_EMAIL = "siteadmin@system.local"
    SITE_ADMIN_PASSWORD = "SiteAdmin123!"
    INSTITUTION_ADMIN_EMAIL = "sarah.admin@mocku.test"
    INSTITUTION_ADMIN_PASSWORD = "InstitutionAdmin123!"


def get_worker_id():
    """Get pytest-xdist worker ID (e.g., 'gw0' -> 0, 'gw1' -> 1, None -> use base account)"""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", None)
    if worker_id and worker_id.startswith("gw"):
        try:
            return int(worker_id[2:])  # Extract number from 'gw0', 'gw1', etc.
        except (ValueError, IndexError):
            return None
    return None


def get_worker_email(base_email: str) -> str:
    """Get worker-specific email address for parallel test execution.

    Args:
        base_email: Base email (e.g., 'siteadmin@system.local')

    Returns:
        Worker-specific email (e.g., 'siteadmin_worker0@system.local') or base email if not in parallel mode
    """
    worker_id = get_worker_id()
    if worker_id is None:
        return base_email

    # Insert worker suffix before @domain
    email_parts = base_email.rsplit("@", 1)
    return f"{email_parts[0]}_worker{worker_id}@{email_parts[1]}"


# Worker-aware credential getters (use these in E2E tests for parallel execution)
def get_site_admin_credentials() -> tuple[str, str]:
    """Get site admin credentials for current worker"""
    return (get_worker_email(SITE_ADMIN_EMAIL), SITE_ADMIN_PASSWORD)


def get_institution_admin_credentials() -> tuple[str, str]:
    """Get institution admin credentials for current worker"""
    return (get_worker_email(INSTITUTION_ADMIN_EMAIL), INSTITUTION_ADMIN_PASSWORD)


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
