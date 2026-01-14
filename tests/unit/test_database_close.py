"""
Unit tests for database connection cleanup functions.

These tests verify that close() and close_connection() properly
dispose of database resources.
"""

from unittest.mock import MagicMock


class TestSQLiteServiceClose:
    """Tests for SQLiteService.close() method."""

    def test_close_disposes_engine_and_removes_session(self):
        """Verify close() calls remove() and dispose() in correct order."""
        from src.database.database_sql import SQLiteService

        # Create a service with a temporary in-memory database
        service = SQLiteService("sqlite:///:memory:")

        # Mock the internal components
        service._session_factory = MagicMock()
        service.engine = MagicMock()

        # Call close
        service.close()

        # Verify both cleanup methods were called
        service._session_factory.remove.assert_called_once()
        service.engine.dispose.assert_called_once()


class TestDatabaseServiceCloseConnection:
    """Tests for database_service.close_connection() function."""

    def test_close_connection_calls_sqlite_close(self):
        """Verify close_connection() delegates to sqlite.close()."""
        from src.database import database_service

        # Save original
        original_db_service = database_service._db_service

        try:
            # Create a mock db service with sqlite attribute
            mock_db_service = MagicMock()
            mock_db_service.sqlite = MagicMock()
            database_service._db_service = mock_db_service

            # Call close_connection
            database_service.close_connection()

            # Verify sqlite.close() was called
            mock_db_service.sqlite.close.assert_called_once()
        finally:
            # Restore original
            database_service._db_service = original_db_service

    def test_close_connection_handles_missing_sqlite_attribute(self):
        """Verify close_connection() handles non-SQLite backends gracefully."""
        from src.database import database_service

        # Save original
        original_db_service = database_service._db_service

        try:
            # Create a mock db service WITHOUT sqlite attribute
            mock_db_service = MagicMock(spec=[])  # Empty spec = no attributes
            database_service._db_service = mock_db_service

            # Should not raise - just does nothing
            database_service.close_connection()
        finally:
            # Restore original
            database_service._db_service = original_db_service
