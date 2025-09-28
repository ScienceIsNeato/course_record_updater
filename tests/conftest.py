"""Global test configuration and fixtures for SQLite backend."""

import os
import tempfile

import pytest

import database_service


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
