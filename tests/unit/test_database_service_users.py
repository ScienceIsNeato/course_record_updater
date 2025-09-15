"""Unit tests for database_service.py - User management functionality."""

from unittest.mock import Mock, patch

from database_service import USERS_COLLECTION, create_user, get_user_by_email


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

    @patch("database_service.db")
    def test_create_user_with_direct_document_reference(self, mock_db):
        """Test user creation when Firestore returns direct document reference."""
        # Setup mock - simulate direct document reference return
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "direct_ref_user"
        mock_collection.add.return_value = mock_doc_ref  # Direct reference, not tuple
        mock_db.collection.return_value = mock_collection

        user_data = {"email": "direct@example.com", "role": "instructor"}

        result = create_user(user_data)

        assert result == "direct_ref_user"
        mock_collection.add.assert_called_once_with(user_data)


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
