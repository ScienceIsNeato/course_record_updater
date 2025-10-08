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
def sqlite_test_database():
    """Provide isolated SQLite database for the test session."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_TYPE"] = "sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    database_service.refresh_connection()
    database_service.reset_database()
    yield
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def clean_database_between_tests():
    """Reset database after each test to guarantee isolation."""
    yield
    database_service.reset_database()
