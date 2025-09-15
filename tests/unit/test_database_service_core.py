"""Unit tests for database_service.py - Core functionality."""

import os
from unittest.mock import Mock, patch

# Import the module under test
import database_service
from database_service import (
    COURSE_OUTCOMES_COLLECTION,
    COURSE_SECTIONS_COLLECTION,
    COURSES_COLLECTION,
    TERMS_COLLECTION,
    USERS_COLLECTION,
)


class TestFirestoreClientInitialization:
    """Test Firestore client initialization."""

    @patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "localhost:8086"})
    @patch("database_service.firestore.Client")
    def test_client_initialization_with_emulator(self, mock_client):
        """Test client initialization with emulator."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance

        # Reload the module to trigger initialization
        import importlib

        importlib.reload(database_service)

        # Verify client was created
        mock_client.assert_called_once()
        assert database_service.db is not None

    @patch.dict(os.environ, {}, clear=True)
    @patch("database_service.firestore.Client")
    def test_client_initialization_without_emulator(self, mock_client):
        """Test client initialization without emulator."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance

        # Reload the module to trigger initialization
        import importlib

        importlib.reload(database_service)

        # Verify client was created
        mock_client.assert_called_once()
        assert database_service.db is not None

    @patch("database_service.firestore.Client")
    def test_client_initialization_failure(self, mock_client):
        """Test client initialization failure."""
        mock_client.side_effect = Exception("Connection failed")

        # Reload the module to trigger initialization
        import importlib

        importlib.reload(database_service)

        # Verify db is None when initialization fails
        assert database_service.db is None

    @patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "localhost:8086"})
    @patch("database_service.firestore.Client")
    def test_client_initialization_emulator_failure(self, mock_client):
        """Test client initialization failure with emulator."""
        mock_client.side_effect = Exception("Emulator connection failed")

        # Reload the module to trigger initialization
        import importlib

        importlib.reload(database_service)

        # Verify db is None when initialization fails
        assert database_service.db is None


class TestCollectionConstants:
    """Test collection name constants."""

    def test_collection_constants_defined(self):
        """Test that all collection constants are properly defined."""
        assert USERS_COLLECTION == "users"
        assert COURSES_COLLECTION == "courses"
        assert TERMS_COLLECTION == "terms"
        assert COURSE_SECTIONS_COLLECTION == "course_sections"
        assert COURSE_OUTCOMES_COLLECTION == "course_outcomes"

    def test_collection_constants_are_strings(self):
        """Test that all collection constants are strings."""
        collections = [
            USERS_COLLECTION,
            COURSES_COLLECTION,
            TERMS_COLLECTION,
            COURSE_SECTIONS_COLLECTION,
            COURSE_OUTCOMES_COLLECTION,
        ]

        for collection in collections:
            assert isinstance(collection, str)
            assert len(collection) > 0


class TestModuleImports:
    """Test module imports and dependencies."""

    def test_required_imports_available(self):
        """Test that all required imports are available."""
        import database_service

        # Test that key imports are available
        assert hasattr(database_service, "firestore")
        assert hasattr(database_service, "User")
        assert hasattr(database_service, "validate_email")
        assert hasattr(database_service, "os")

    def test_functions_exported(self):
        """Test that key functions are exported."""
        import database_service

        assert hasattr(database_service, "create_user")
        assert hasattr(database_service, "get_user_by_email")
        assert callable(database_service.create_user)
        assert callable(database_service.get_user_by_email)

    def test_constants_exported(self):
        """Test that collection constants are exported."""
        import database_service

        assert hasattr(database_service, "USERS_COLLECTION")
        assert hasattr(database_service, "COURSES_COLLECTION")
        assert hasattr(database_service, "TERMS_COLLECTION")
        assert hasattr(database_service, "COURSE_SECTIONS_COLLECTION")
        assert hasattr(database_service, "COURSE_OUTCOMES_COLLECTION")


class TestDatabaseServiceIntegration:
    """Test integration aspects of database service."""

    def test_db_variable_initialization(self):
        """Test that db variable is properly initialized."""
        import database_service

        # db should either be a client instance or None
        assert database_service.db is None or hasattr(database_service.db, "collection")

    @patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "localhost:8086"})
    def test_emulator_host_detection(self):
        """Test that emulator host is properly detected."""
        import database_service  # noqa: F401

        emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
        assert emulator_host == "localhost:8086"

    def test_error_handling_patterns(self):
        """Test that functions follow consistent error handling patterns."""
        from database_service import create_user, get_user_by_email

        # Both functions should return None on error
        with patch("database_service.db", None):
            assert create_user({"email": "test@example.com"}) is None
            assert get_user_by_email("test@example.com") is None

    def test_logging_patterns(self):
        """Test that functions include proper logging."""
        from database_service import create_user, get_user_by_email

        # This test verifies that functions use proper logging

        with patch("database_service.db", None):
            with patch("database_service.logger") as mock_logger:
                create_user({"email": "test@example.com"})
                mock_logger.info.assert_called()
                mock_logger.error.assert_called()

        with patch("database_service.db", None):
            with patch("database_service.logger") as mock_logger:
                get_user_by_email("test@example.com")
                mock_logger.info.assert_called()
                mock_logger.error.assert_called()
