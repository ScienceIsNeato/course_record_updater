"""Unit tests for database_service.py."""

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
    create_course,
    create_course_offering,
    create_course_section,
    create_default_cei_institution,
    create_institution,
    create_new_institution,
    create_term,
    create_user,
    get_active_terms,
    get_all_course_offerings,
    get_all_courses,
    get_all_institutions,
    get_all_instructors,
    get_all_sections,
    get_course_by_number,
    get_course_offering,
    get_courses_by_department,
    get_institution_by_id,
    get_institution_by_short_name,
    get_institution_instructor_count,
    get_course_offering_by_course_and_term,
    get_sections_by_instructor,
    get_sections_by_term,
    get_term_by_name,
    get_user_by_email,
    get_users_by_role,
    sanitize_for_logging,
    update_user_extended,
)

# pytest import removed


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


class TestCreateUser:
    """Test create_user function."""

    @patch("database_service.db")
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
            "last_name": "User",
        }

        # Call function
        result = create_user(user_data)

        # Verify results
        assert result == "user123"
        mock_db.collection.assert_called_once_with(USERS_COLLECTION)
        mock_collection.add.assert_called_once_with(user_data)

    @patch("database_service.db", None)
    def test_create_user_no_db_client(self):
        """Test user creation when db client is not available."""
        user_data = {"email": "test@example.com", "role": "instructor"}
        result = create_user(user_data)

        assert result is None

    @patch("database_service.db")
    def test_create_user_firestore_exception(self, mock_db):
        """Test user creation when Firestore throws exception."""
        # Setup mock to raise exception
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception("Firestore error")
        mock_db.collection.return_value = mock_collection

        user_data = {"email": "test@example.com", "role": "instructor"}
        result = create_user(user_data)

        assert result is None

    @patch("database_service.db")
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
                "preferences": {"theme": "dark", "notifications": True},
            },
        }

        result = create_user(complex_user_data)

        assert result == "complex_user_456"
        mock_collection.add.assert_called_once_with(complex_user_data)


class TestGetUserByEmail:
    """Test get_user_by_email function."""

    @patch("database_service.db")
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
            "last_name": "User",
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
            "user_id": "user123",
        }
        assert result == expected_result
        mock_db.collection.assert_called_once_with(USERS_COLLECTION)

    @patch("database_service.db")
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

    @patch("database_service.db", None)
    def test_get_user_by_email_no_db_client(self):
        """Test user retrieval when db client is not available."""
        result = get_user_by_email("test@example.com")
        assert result is None

    @patch("database_service.db")
    def test_get_user_by_email_firestore_exception(self, mock_db):
        """Test user retrieval when Firestore throws exception."""
        # Setup mock to raise exception
        mock_collection = Mock()
        mock_collection.where.side_effect = Exception("Firestore query error")
        mock_db.collection.return_value = mock_collection

        result = get_user_by_email("test@example.com")

        assert result is None

    @patch("database_service.db")
    @patch("database_service.firestore.FieldFilter")
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

    @patch("database_service.db")
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

    @patch("database_service.db")
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
            "list_field": [1, 2, 3],
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
        # Both functions should return None on error
        with patch("database_service.db", None):
            assert create_user({"email": "test@example.com"}) is None
            assert get_user_by_email("test@example.com") is None

    def test_logging_patterns(self):
        """Test that functions include proper logging."""
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


class TestExtendedDatabaseFunctions:
    """Test extended database functions that were consolidated from database_service_extended."""

    @patch("database_service.db")
    def test_get_users_by_role_success(self, mock_db):
        """Test get_users_by_role function."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.id = "user123"
        mock_doc.to_dict.return_value = {
            "email": "test@example.com",
            "role": "instructor",
        }

        mock_query.stream.return_value = [mock_doc]
        mock_query.where.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection

        result = get_users_by_role("instructor")

        assert len(result) == 1
        assert result[0]["user_id"] == "user123"
        assert result[0]["role"] == "instructor"

    @patch("database_service.db")
    def test_create_course_success(self, mock_db):
        """Test create_course function."""
        # Setup mock
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "course123"
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection

        course_data = {"course_number": "MATH-101", "course_title": "Algebra"}
        result = create_course(course_data)

        assert result == "course123"
        mock_collection.add.assert_called_once_with(course_data)

    @patch("database_service.db")
    def test_get_users_by_role_exception(self, mock_db):
        """Test exception handling in get_users_by_role - lines 149-151."""
        mock_db.collection.side_effect = Exception("Database connection failed")

        result = get_users_by_role("instructor")

        assert result == []

    @patch("database_service.db")
    def test_update_user_extended_success(self, mock_db):
        """Test successful user update."""
        mock_doc_ref = Mock()
        mock_collection = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref

        update_data = {"first_name": "Updated", "last_name": "Name"}
        result = update_user_extended("user123", update_data)

        assert result is True
        mock_db.collection.assert_called_once_with(USERS_COLLECTION)
        mock_collection.document.assert_called_once_with("user123")
        mock_doc_ref.update.assert_called_once_with(update_data)

    @patch("database_service.db")
    def test_update_user_extended_exception(self, mock_db):
        """Test exception handling in update_user_extended - lines 176-178."""
        mock_db.collection.side_effect = Exception("Update failed")

        result = update_user_extended("user123", {"first_name": "Test"})

        assert result is False

    @patch("database_service.db")
    def test_get_course_by_number_not_found(self, mock_db):
        """Test get_course_by_number when course not found - lines 253-254."""
        mock_collection = Mock()
        mock_query = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.stream.return_value = []  # No documents found

        result = get_course_by_number("NONEXISTENT-999")

        assert result is None

    @patch("database_service.db")
    def test_get_course_by_number_exception(self, mock_db):
        """Test exception handling in get_course_by_number - lines 256-258."""
        mock_db.collection.side_effect = Exception("Database error")

        result = get_course_by_number("MATH-101")

        assert result is None

    @patch("database_service.db")
    def test_get_courses_by_department_success(self, mock_db):
        """Test get_courses_by_department function - lines 749-795."""
        mock_collection = Mock()
        mock_query1 = Mock()
        mock_query2 = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        # First where() call for institution_id returns mock_query1
        mock_collection.where.return_value = mock_query1
        # Second where() call for department returns mock_query2
        mock_query1.where.return_value = mock_query2
        # Final stream() call returns the documents
        mock_query2.stream.return_value = [mock_doc]

        mock_doc.id = "course123"
        mock_doc.to_dict.return_value = {
            "course_number": "MATH-101",
            "course_title": "Algebra",
            "department": "MATH",
        }

        result = get_courses_by_department("test-institution-id", "MATH")

        assert len(result) == 1
        assert result[0]["course_id"] == "course123"
        assert result[0]["department"] == "MATH"

    @patch("database_service.db")
    def test_create_term_success(self, mock_db):
        """Test create_term function - lines 317-333."""
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "term123"

        mock_db.collection.return_value = mock_collection
        mock_collection.add.return_value = (None, mock_doc_ref)

        term_data = {
            "term_name": "Fall 2024",
            "start_date": "2024-08-01",
            "end_date": "2024-12-15",
        }

        result = create_term(term_data)

        assert result == "term123"
        mock_collection.add.assert_called_once_with(term_data)

    @patch("database_service.db")
    def test_create_term_missing_field(self, mock_db):
        """Test create_term with missing required field - lines 320-323."""
        term_data = {
            "term_name": "Fall 2024",
            "start_date": "2024-08-01",
            # Missing end_date
        }

        result = create_term(term_data)

        assert result is None

    @patch("database_service.db")
    def test_create_term_exception(self, mock_db):
        """Test create_term exception handling - lines 331-333."""
        mock_db.collection.side_effect = Exception("Database error")

        term_data = {
            "term_name": "Fall 2024",
            "start_date": "2024-08-01",
            "end_date": "2024-12-15",
        }

        result = create_term(term_data)

        assert result is None

    @patch("database_service.db")
    def test_get_term_by_name_success(self, mock_db):
        """Test get_term_by_name function - lines 351-371."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_doc.id = "term123"
        mock_doc.to_dict.return_value = {
            "term_name": "Fall 2024",
            "start_date": "2024-08-01",
            "end_date": "2024-12-15",
        }

        result = get_term_by_name("Fall 2024")

        assert result is not None
        assert result["term_id"] == "term123"
        assert result["term_name"] == "Fall 2024"

    @patch("database_service.db")
    def test_get_term_by_name_not_found(self, mock_db):
        """Test get_term_by_name when term not found - lines 365-367."""
        mock_collection = Mock()
        mock_query = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = []  # No documents found

        result = get_term_by_name("Nonexistent Term")

        assert result is None

    @patch("database_service.db")
    def test_get_active_terms_success(self, mock_db):
        """Test get_active_terms function - lines 386-404."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_doc.id = "term123"
        mock_doc.to_dict.return_value = {
            "term_name": "Fall 2024",
            "active": True,
            "start_date": "2024-08-01",
        }

        result = get_active_terms("test-institution-id")

        assert len(result) == 1
        assert result[0]["term_id"] == "term123"
        assert result[0]["active"] is True

    @patch("database_service.db")
    def test_get_active_terms_exception(self, mock_db):
        """Test get_active_terms exception handling - lines 402-404."""
        mock_db.collection.side_effect = Exception("Database error")

        result = get_active_terms("test-institution-id")

        assert result == []

    @patch("database_service.db")
    def test_create_course_section_success(self, mock_db):
        """Test create_course_section function - lines 427-443."""
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "section123"

        mock_db.collection.return_value = mock_collection
        mock_collection.add.return_value = (None, mock_doc_ref)

        section_data = {
            "course_id": "course123",
            "term_id": "term123",
            "section_number": "001",
            "instructor_id": "instructor123",
        }

        result = create_course_section(section_data)

        assert result == "section123"
        mock_collection.add.assert_called_once_with(section_data)

    @patch("database_service.db")
    def test_create_course_section_missing_field(self, mock_db):
        """Test create_course_section with missing field - lines 430-433."""
        section_data = {
            "course_id": "course123",
            "term_id": "term123",
            # Missing section_number
        }

        result = create_course_section(section_data)

        assert result is None

    @patch("database_service.db")
    def test_get_course_by_number_success(self, mock_db):
        """Test get_course_by_number function."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.id = "course123"
        mock_doc.to_dict.return_value = {
            "course_number": "MATH-101",
            "course_title": "Algebra",
        }

        mock_query.stream.return_value = [mock_doc]
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection

        result = get_course_by_number("MATH-101")

        assert result["course_id"] == "course123"
        assert result["course_number"] == "MATH-101"

    def test_extended_functions_no_db_client(self):
        """Test that extended functions handle missing db client gracefully."""
        with patch("database_service.db", None):
            # All these should return empty lists or None
            assert get_users_by_role("instructor") == []
            assert update_user_extended("user123", {}) is False
            assert create_course({"course_number": "TEST-101"}) is None
            assert get_course_by_number("TEST-101") is None
            assert get_courses_by_department("test-institution-id", "MATH") == []
            assert create_term({"term_name": "FA24"}) is None
            assert get_term_by_name("FA24") is None
            assert get_active_terms("test-institution-id") == []
            assert create_course_section({"course_id": "123"}) is None
            assert get_sections_by_instructor("instructor123") == []
            assert get_sections_by_term("term123") == []

    def test_all_extended_functions_exist(self):
        """Test that all extended functions are properly imported."""
        # Verify all functions exist and are callable
        assert callable(get_users_by_role)
        assert callable(update_user_extended)
        assert callable(create_course)
        assert callable(get_course_by_number)
        assert callable(get_courses_by_department)
        assert callable(create_term)
        assert callable(get_term_by_name)
        assert callable(get_active_terms)
        assert callable(create_course_section)
        assert callable(get_sections_by_instructor)
        assert callable(get_sections_by_term)


class TestInstitutionManagement:
    """Test institution management functions for coverage."""

    @patch("database_service.db")
    def test_create_institution_success(self, mock_db):
        """Test create_institution function."""
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "institution123"

        mock_db.collection.return_value = mock_collection
        mock_collection.add.return_value = (None, mock_doc_ref)

        institution_data = {
            "name": "Test University",
            "short_name": "TU",
            "domain": "test.edu",
        }

        result = create_institution(institution_data)

        assert result == "institution123"
        mock_collection.add.assert_called_once_with(institution_data)

    @patch("database_service.db")
    def test_get_institution_by_id_success(self, mock_db):
        """Test get_institution_by_id function."""
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Test University", "short_name": "TU"}
        mock_doc.id = "institution123"

        result = get_institution_by_id("institution123")

        assert result["name"] == "Test University"
        assert result["institution_id"] == "institution123"

    @patch("database_service.db")
    def test_get_institution_by_short_name_success(self, mock_db):
        """Test get_institution_by_short_name function."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_doc.id = "institution123"
        mock_doc.to_dict.return_value = {"name": "Test University", "short_name": "TU"}

        result = get_institution_by_short_name("TU")

        assert result["short_name"] == "TU"
        assert result["institution_id"] == "institution123"

    @patch("database_service.get_institution_by_short_name")
    @patch("database_service.create_institution")
    def test_create_default_cei_institution_new(
        self, mock_create_institution, mock_get_institution
    ):
        """Test create_default_cei_institution when CEI doesn't exist."""
        mock_get_institution.return_value = None
        mock_create_institution.return_value = "cei-institution-id"

        result = create_default_cei_institution()

        assert result == "cei-institution-id"
        mock_create_institution.assert_called_once()

    @patch("database_service.get_institution_by_short_name")
    def test_create_default_cei_institution_existing(self, mock_get_institution):
        """Test create_default_cei_institution when CEI already exists."""
        mock_get_institution.return_value = {"institution_id": "existing-cei-id"}

        result = create_default_cei_institution()

        assert result == "existing-cei-id"


class TestCourseOfferingManagement:
    """Test course offering management functions for coverage."""

    @patch("database_service.db")
    def test_create_course_offering_success(self, mock_db):
        """Test create_course_offering function."""
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "offering123"

        mock_db.collection.return_value = mock_collection
        mock_collection.add.return_value = (None, mock_doc_ref)

        offering_data = {
            "course_id": "course123",
            "term_id": "term123",
            "institution_id": "institution123",
        }

        result = create_course_offering(offering_data)

        assert result is not None
        assert isinstance(result, str)

    @patch("database_service.db")
    def test_get_course_offering_success(self, mock_db):
        """Test get_course_offering function."""
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"course_id": "course123", "term_id": "term123"}
        mock_doc.id = "offering123"

        result = get_course_offering("offering123")

        assert result["course_id"] == "course123"
        assert result["offering_id"] == "offering123"

    @patch("database_service.db")
    def test_get_all_course_offerings_success(self, mock_db):
        """Test get_all_course_offerings function."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_doc.id = "offering123"
        mock_doc.to_dict.return_value = {"course_id": "course123", "term_id": "term123"}

        result = get_all_course_offerings("institution123")

        assert len(result) == 1
        assert result[0]["offering_id"] == "offering123"


class TestSectionManagement:
    """Test section management functions for coverage."""

    @patch("database_service.db")
    def test_get_all_sections_success(self, mock_db):
        """Test get_all_sections function."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_doc.id = "section123"
        mock_doc.to_dict.return_value = {
            "offering_id": "offering123",
            "instructor_id": "instructor123",
        }

        result = get_all_sections("institution123")

        assert len(result) == 1
        assert result[0]["section_id"] == "section123"

    @patch("database_service.db")
    def test_get_all_courses_success(self, mock_db):
        """Test get_all_courses function."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_doc.id = "course123"
        mock_doc.to_dict.return_value = {
            "course_number": "MATH-101",
            "department": "MATH",
        }

        result = get_all_courses("institution123")

        assert len(result) == 1
        assert result[0]["course_id"] == "course123"

    @patch("database_service.db")
    def test_get_all_instructors_success(self, mock_db):
        """Test get_all_instructors function."""
        mock_collection = Mock()
        mock_query1 = Mock()
        mock_query2 = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        # First where() call for role returns mock_query1
        mock_collection.where.return_value = mock_query1
        # Second where() call for institution_id returns mock_query2
        mock_query1.where.return_value = mock_query2
        # Final stream() call returns the documents
        mock_query2.stream.return_value = [mock_doc]

        mock_doc.id = "instructor123"
        mock_doc.to_dict.return_value = {
            "email": "instructor@test.edu",
            "role": "instructor",
        }

        result = get_all_instructors("institution123")

        assert len(result) == 1
        assert result[0]["user_id"] == "instructor123"


class TestAdditionalDatabaseFunctions:
    """Test additional database functions for coverage."""

    @patch("database_service.db")
    def test_get_all_institutions_success(self, mock_db):
        """Test get_all_institutions function."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_doc.id = "institution123"
        mock_doc.to_dict.return_value = {"name": "Test University", "is_active": True}

        result = get_all_institutions()

        assert len(result) == 1
        assert result[0]["institution_id"] == "institution123"

    @patch("database_service.db")
    def test_get_institution_instructor_count_success(self, mock_db):
        """Test get_institution_instructor_count function."""
        mock_collection = Mock()
        mock_query1 = Mock()
        mock_query2 = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query1
        mock_query1.where.return_value = mock_query2
        mock_query2.stream.return_value = ["doc1", "doc2", "doc3"]  # 3 instructors

        result = get_institution_instructor_count("institution123")

        assert result == 3

    @patch("database_service.db")
    def test_create_new_institution_success(self, mock_db):
        """Test create_new_institution function."""
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "institution123"

        mock_db.collection.return_value = mock_collection
        mock_collection.add.return_value = (None, mock_doc_ref)

        with patch("database_service.create_user", return_value="user123"):
            institution_data = {"name": "Test University", "domain": "test.edu"}
            admin_data = {"email": "admin@test.edu", "first_name": "Admin"}

            result = create_new_institution(institution_data, admin_data)

            assert result == ("institution123", "user123")

    def test_sanitize_for_logging_comprehensive(self):
        """Test sanitize_for_logging with comprehensive input types."""
        # Test None input
        assert sanitize_for_logging(None) == "None"
        
        # Test various data types
        assert sanitize_for_logging(42) == "42"
        assert sanitize_for_logging(True) == "True"
        
        # Test dangerous characters
        dangerous = "test\nwith\r\nnewlines\x00nulls\x1bescape"
        result = sanitize_for_logging(dangerous)
        assert "\\n" in result
        assert "\\r" in result
        assert "\\x00" in result
        assert "\\x1b" in result
        
        # Test length limiting
        long_input = "a" * 200
        result = sanitize_for_logging(long_input, max_length=50)
        assert len(result) == 50

    @patch("database_service.db")
    def test_course_offering_error_paths(self, mock_db):
        """Test course offering functions error handling."""
        mock_db.collection.side_effect = Exception("Database error")
        
        assert create_course_offering({"course_id": "test"}) is None
        assert get_course_offering("test") is None
        assert get_course_offering_by_course_and_term("c", "t", "i") is None
        assert get_all_course_offerings("institution123") == []

    @patch("database_service.db", None)
    def test_course_offering_no_db(self):
        """Test course offering functions when db is None."""
        assert create_course_offering({"course_id": "test"}) is None
        assert get_course_offering("test") is None
        assert get_course_offering_by_course_and_term("c", "t", "i") is None
        assert get_all_course_offerings("institution123") == []
