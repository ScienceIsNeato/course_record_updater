"""
Pytest configuration for unit tests.

Provides database fixtures with proper isolation for pytest-xdist parallel execution.
Each worker gets its own database to prevent conflicts.

Performance optimization: Uses DELETE-based table cleanup instead of DROP ALL + CREATE ALL
per test. Schema is created once per session and only data is cleared between tests.

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
    """Clear all table data using DELETE statements (much faster than DDL reset)."""
    import src.database.database_service as database_service

    if not hasattr(database_service._db_service, "sql"):
        return

    engine = database_service._db_service.sql.engine
    # Delete in reverse dependency order to respect foreign keys.
    # Leaf/association tables first, then child tables, then parent tables.
    # Table names must match __tablename__ in models_sql.py exactly.
    tables_in_delete_order = [
        "outcome_history",  # FK → course_section_outcomes
        "course_section_outcomes",  # FK → course_sections, course_outcomes
        "course_programs",  # association: FK → courses, programs
        "user_programs",  # association: FK → users, programs
        "audit_log",  # FK → users
        "instructor_reminders",  # FK → course_sections, users
        "bulk_email_jobs",  # references users (no FK constraint)
        "course_sections",  # FK → course_offerings, users
        "course_outcomes",  # FK → courses
        "course_offerings",  # FK → courses, terms, institutions
        "user_invitations",  # FK → institutions
        "terms",  # FK → institutions
        "courses",  # FK → institutions
        "programs",  # FK → institutions
        "users",  # FK → institutions
        "institutions",
    ]

    try:
        with engine.connect() as conn:
            # Disable FK checks for speed (SQLite-specific)
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            for table in tables_in_delete_order:
                try:
                    conn.execute(text(f"DELETE FROM {table}"))  # noqa: S608
                except Exception:
                    pass  # Table might not exist yet in some edge cases
            conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.commit()
    finally:
        # Always clear cached sessions, even if commit fails
        database_service._db_service.sql.remove_session()
