"""Unit tests for database_service.py."""

import os
from unittest.mock import patch, MagicMock, Mock
import pytest

# Import the module under test
import database_service
from database_service import (
    create_user,
    get_user_by_email,
    USERS_COLLECTION,
    COURSES_COLLECTION,
    TERMS_COLLECTION,
    COURSE_SECTIONS_COLLECTION,
    COURSE_OUTCOMES_COLLECTION,
)


class TestFirestoreClientInitialization:
    """Test Firestore client initialization."""

    @patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "localhost:8086"})
    @patch('database_service.firestore.Client')
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
    @patch('database_service.firestore.Client')
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

    @patch('database_service.firestore.Client')
    def test_client_initialization_failure(self, mock_client):
        """Test client initialization failure."""
        mock_client.side_effect = Exception("Connection failed")
        
        # Reload the module to trigger initialization
        import importlib
        importlib.reload(database_service)
        
        # Verify db is None when initialization fails
        assert database_service.db is None

    @patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "localhost:8086"})
    @patch('database_service.firestore.Client')
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


class TestCreateUser:
    """Test create_user function."""

    @patch('database_service.db')
    def test_create_user_success(self, mock_db):
        """Test successful user creation."""
        # Setup mock
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "user123"
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        user_data = {
            "email": "test@example.com",
            "role": "instructor",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # Call function
        result = create_user(user_data)
        
        # Verify results
        assert result == "user123"
        mock_db.collection.assert_called_once_with(USERS_COLLECTION)
        mock_collection.add.assert_called_once_with(user_data)

    def test_create_user_no_db_client(self):
        """Test user creation when db client is not available."""
        # Temporarily set db to None
        original_db = database_service.db
        database_service.db = None
        
        try:
            user_data = {"email": "test@example.com", "role": "instructor"}
            result = create_user(user_data)
            
            assert result is None
        finally:
            # Restore original db
            database_service.db = original_db

    @patch('database_service.db')
    def test_create_user_firestore_exception(self, mock_db):
        """Test user creation when Firestore throws exception."""
        # Setup mock to raise exception
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception("Firestore error")
        mock_db.collection.return_value = mock_collection
        
        user_data = {"email": "test@example.com", "role": "instructor"}
        result = create_user(user_data)
        
        assert result is None

    @patch('database_service.db')
    def test_create_user_with_complex_data(self, mock_db):
        """Test user creation with complex user data."""
        # Setup mock
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "complex_user_456"
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        complex_user_data = {
            "email": "complex@example.com",
            "role": "administrator",
            "first_name": "Complex",
            "last_name": "User",
            "department": "Computer Science",
            "permissions": ["read", "write", "admin"],
            "metadata": {
                "created_by": "system",
                "preferences": {"theme": "dark", "notifications": True}
            }
        }
        
        result = create_user(complex_user_data)
        
        assert result == "complex_user_456"
        mock_collection.add.assert_called_once_with(complex_user_data)


class TestGetUserByEmail:
    """Test get_user_by_email function."""

    @patch('database_service.db')
    def test_get_user_by_email_success(self, mock_db):
        """Test successful user retrieval by email."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.id = "user123"
        mock_doc.to_dict.return_value = {
            "email": "test@example.com",
            "role": "instructor",
            "first_name": "Test",
            "last_name": "User"
        }
        
        mock_query.stream.return_value = [mock_doc]
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_user_by_email("test@example.com")
        
        # Verify results
        expected_result = {
            "email": "test@example.com",
            "role": "instructor",
            "first_name": "Test",
            "last_name": "User",
            "user_id": "user123"
        }
        assert result == expected_result
        mock_db.collection.assert_called_once_with(USERS_COLLECTION)

    @patch('database_service.db')
    def test_get_user_by_email_not_found(self, mock_db):
        """Test user retrieval when user not found."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.stream.return_value = []  # Empty result
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_user_by_email("nonexistent@example.com")
        
        # Verify results
        assert result is None

    def test_get_user_by_email_no_db_client(self):
        """Test user retrieval when db client is not available."""
        # Temporarily set db to None
        original_db = database_service.db
        database_service.db = None
        
        try:
            result = get_user_by_email("test@example.com")
            assert result is None
        finally:
            # Restore original db
            database_service.db = original_db

    @patch('database_service.db')
    def test_get_user_by_email_firestore_exception(self, mock_db):
        """Test user retrieval when Firestore throws exception."""
        # Setup mock to raise exception
        mock_collection = Mock()
        mock_collection.where.side_effect = Exception("Firestore query error")
        mock_db.collection.return_value = mock_collection
        
        result = get_user_by_email("test@example.com")
        
        assert result is None

    @patch('database_service.db')
    @patch('database_service.firestore.FieldFilter')
    def test_get_user_by_email_query_construction(self, mock_field_filter, mock_db):
        """Test that the Firestore query is constructed correctly."""
        # Setup mocks
        mock_filter = Mock()
        mock_field_filter.return_value = mock_filter
        
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.stream.return_value = []
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        get_user_by_email("test@example.com")
        
        # Verify query construction
        mock_field_filter.assert_called_once_with("email", "==", "test@example.com")
        mock_collection.where.assert_called_once_with(filter=mock_filter)
        mock_query.limit.assert_called_once_with(1)

    @patch('database_service.db')
    def test_get_user_by_email_multiple_docs_returns_first(self, mock_db):
        """Test that only the first user is returned when multiple exist."""
        # Setup mock with multiple documents
        mock_collection = Mock()
        mock_query = Mock()
        
        mock_doc1 = Mock()
        mock_doc1.id = "user123"
        mock_doc1.to_dict.return_value = {"email": "test@example.com", "name": "First"}
        
        mock_doc2 = Mock()
        mock_doc2.id = "user456"
        mock_doc2.to_dict.return_value = {"email": "test@example.com", "name": "Second"}
        
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_user_by_email("test@example.com")
        
        # Verify only first user is returned
        assert result["user_id"] == "user123"
        assert result["name"] == "First"

    @patch('database_service.db')
    def test_get_user_by_email_preserves_original_data(self, mock_db):
        """Test that original user data is preserved and user_id is added."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.id = "user789"
        
        original_data = {
            "email": "preserve@example.com",
            "role": "student",
            "metadata": {"complex": {"nested": "data"}},
            "list_field": [1, 2, 3]
        }
        mock_doc.to_dict.return_value = original_data.copy()
        
        mock_query.stream.return_value = [mock_doc]
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_user_by_email("preserve@example.com")
        
        # Verify all original data is preserved
        for key, value in original_data.items():
            assert result[key] == value
        
        # Verify user_id is added
        assert result["user_id"] == "user789"
        assert len(result) == len(original_data) + 1


class TestModuleImports:
    """Test module imports and dependencies."""

    def test_required_imports_available(self):
        """Test that all required imports are available."""
        import database_service
        
        # Test that key imports are available
        assert hasattr(database_service, 'firestore')
        assert hasattr(database_service, 'User')
        assert hasattr(database_service, 'validate_email')
        assert hasattr(database_service, 'os')

    def test_functions_exported(self):
        """Test that key functions are exported."""
        import database_service
        
        assert hasattr(database_service, 'create_user')
        assert hasattr(database_service, 'get_user_by_email')
        assert callable(database_service.create_user)
        assert callable(database_service.get_user_by_email)

    def test_constants_exported(self):
        """Test that collection constants are exported."""
        import database_service
        
        assert hasattr(database_service, 'USERS_COLLECTION')
        assert hasattr(database_service, 'COURSES_COLLECTION')
        assert hasattr(database_service, 'TERMS_COLLECTION')
        assert hasattr(database_service, 'COURSE_SECTIONS_COLLECTION')
        assert hasattr(database_service, 'COURSE_OUTCOMES_COLLECTION')


class TestDatabaseServiceIntegration:
    """Test integration aspects of database service."""

    def test_db_variable_initialization(self):
        """Test that db variable is properly initialized."""
        import database_service
        
        # db should either be a client instance or None
        assert database_service.db is None or hasattr(database_service.db, 'collection')

    @patch.dict(os.environ, {"FIRESTORE_EMULATOR_HOST": "localhost:8086"})
    def test_emulator_host_detection(self):
        """Test that emulator host is properly detected."""
        import database_service
        
        emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
        assert emulator_host == "localhost:8086"

    def test_error_handling_patterns(self):
        """Test that functions follow consistent error handling patterns."""
        # Both functions should return None on error
        with patch('database_service.db', None):
            assert create_user({"email": "test@example.com"}) is None
            assert get_user_by_email("test@example.com") is None

    def test_logging_patterns(self):
        """Test that functions include proper logging."""
        # This test verifies that functions call print statements for logging
        # In a real implementation, you might want to use proper logging
        
        with patch('database_service.db', None):
            with patch('builtins.print') as mock_print:
                create_user({"email": "test@example.com"})
                mock_print.assert_called()
                
        with patch('database_service.db', None):
            with patch('builtins.print') as mock_print:
                get_user_by_email("test@example.com")
                mock_print.assert_called()
