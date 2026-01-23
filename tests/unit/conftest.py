"""
Pytest configuration for unit tests.

Provides database fixtures with proper isolation for pytest-xdist parallel execution.
Each worker gets its own database to prevent conflicts.

Performance optimization: Uses DELETE-based table cleanup instead of DROP ALL + CREATE ALL
per test. Schema is created once per session and only data is cleared between tests.
Table list is derived from SQLAlchemy metadata (never hardcoded) so it stays in sync
with the schema automatically.

Invocation: Use `python scripts/ship_it.py --checks python-unit-tests` as the primary
interface. The ship_it.py wrapper handles venv activation, env vars, and parallel
execution via maintAInability-gate.sh. Direct pytest is acceptable for single-file
verification during development only.
"""

import os

import pytest
from sqlalchemy import text


@pytest.fixture(scope="session", autouse=True)
def setup_unit_test_database(tmp_path_factory, worker_id):
    """
    Set up isolated database for each pytest-xdist worker.

    Creates schema once per session. Individual tests use fast DELETE-based
    cleanup instead of expensive DROP/CREATE DDL operations.
    """
    # Create worker-specific database path
    if worker_id == "master":
        db_path = tmp_path_factory.mktemp("data") / "test.db"
    else:
        db_path = tmp_path_factory.mktemp("data", numbered=True) / f"{worker_id}.db"

    db_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = db_url
    os.environ["DATABASE_TYPE"] = "sqlite"
    os.environ["_UNIT_TEST_CLEANUP_ACTIVE"] = "1"

    import src.database.database_service as database_service

    database_service.refresh_connection()
    database_service.reset_database()  # Create schema once per session

    yield db_path

    # Clean up coordination flag so integration tests aren't affected
    # if run in the same process (e.g., pytest tests/unit tests/integration)
    os.environ.pop("_UNIT_TEST_CLEANUP_ACTIVE", None)


@pytest.fixture(scope="function", autouse=True)
def reset_db_between_tests():
    """
    Fast database cleanup between tests using DELETE instead of DROP/CREATE.

    This is ~10-50x faster than reset_database() which does DROP ALL + CREATE ALL.
    Deletes data from all tables in reverse dependency order to respect foreign keys.
    """
    yield
    _fast_clear_all_tables()


def _fast_clear_all_tables():
    """Clear all table data using DELETE statements (much faster than DDL reset).

    Table list is derived from SQLAlchemy Base.metadata.sorted_tables so it
    automatically stays in sync with the schema. Reversed topological sort
    ensures children are deleted before parents (correct FK order).
    """
    import src.database.database_service as database_service
    from src.models.models_sql import Base

    if not hasattr(database_service._db_service, "sql"):
        return

    engine = database_service._db_service.sql.engine
    # sorted_tables returns parent-first; reversed gives children-first (correct for DELETE)
    tables = list(reversed(Base.metadata.sorted_tables))

    try:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            for table in tables:
                conn.execute(table.delete())
            conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.commit()
    finally:
        # Always clear cached sessions, even if commit fails
        database_service._db_service.sql.remove_session()
