"""
Pytest configuration for unit tests.

Provides database fixtures with proper isolation for pytest-xdist parallel execution.
Each worker gets its own database to prevent conflicts.

OPTIMIZATION NOTE (2024):
The previous implementation used `reset_database()` (DROP ALL + CREATE ALL) for every
test, which was extremely slow (~70ms per test = ~112 seconds total overhead for 1600 tests).
Now we use efficient DELETE statements which are ~50x faster (~1.5ms per test).
"""

import os

import pytest

# Cache the table names to avoid repeated metadata lookups
_TABLE_DELETE_ORDER = None


def _get_table_delete_order():
    """
    Get tables in reverse dependency order for safe deletion.

    Cached at module level to avoid repeated metadata inspection.
    Tables are ordered to respect foreign key constraints.
    """
    global _TABLE_DELETE_ORDER
    if _TABLE_DELETE_ORDER is None:
        from src.models.models_sql import Base

        # sorted_tables returns tables in dependency order (parents first)
        # We need reverse order to delete children before parents
        _TABLE_DELETE_ORDER = list(reversed(Base.metadata.sorted_tables))
    return _TABLE_DELETE_ORDER


def _fast_clear_all_tables(engine):
    """
    Efficiently clear all table data using DELETE statements.

    This is ~50x faster than DROP ALL + CREATE ALL because:
    1. No DDL operations (schema stays intact)
    2. No constraint recreation
    3. SQLite can reuse existing pages

    Args:
        engine: SQLAlchemy engine instance
    """
    from sqlalchemy import text

    tables = _get_table_delete_order()

    with engine.begin() as conn:
        # Disable foreign key checks for faster deletion (SQLite-specific)
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        for table in tables:
            conn.execute(text(f"DELETE FROM {table.name}"))
        conn.execute(text("PRAGMA foreign_keys = ON"))


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

    # Create all tables (only once per session, not per test)
    database_service.reset_database()

    # Return the database path for tests that need it
    yield db_path

    # Cleanup is handled automatically by tmp_path_factory


@pytest.fixture(scope="function", autouse=True)
def reset_db_between_tests():
    """
    Clear database data between tests to ensure isolation.

    Uses efficient DELETE statements instead of DROP/CREATE for ~50x speedup.
    This prevents test pollution where one test's data affects another.
    Runs automatically before each test function.
    """
    from src.database.database_factory import get_database_service

    db_service = get_database_service()

    # Use fast table clearing instead of expensive schema recreation
    if hasattr(db_service, "sql") and hasattr(db_service.sql, "engine"):
        _fast_clear_all_tables(db_service.sql.engine)

    yield
