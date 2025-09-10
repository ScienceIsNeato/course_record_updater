"""Unit tests for database_service_extended.py."""

from unittest.mock import patch, MagicMock, Mock
import pytest

# Import the module under test
import database_service_extended
from database_service_extended import (
    get_users_by_role,
    update_user_extended,
    create_course,
    get_course_by_number,
    get_courses_by_department,
    create_term,
    get_term_by_name,
    get_active_terms,
    create_course_section,
    get_sections_by_instructor,
    get_sections_by_term,
)


class TestGetUsersByRole:
    """Test get_users_by_role function."""

    @patch('database_service_extended.db')
    def test_get_users_by_role_success(self, mock_db):
        """Test successful user retrieval by role."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "email": "instructor@example.com",
            "role": "instructor",
            "active": True
        }
        mock_doc.id = "user123"
        
        mock_query.stream.return_value = iter([mock_doc])  # Make it iterable
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_users_by_role("instructor")
        
        # Verify results
        assert len(result) == 1
        assert result[0]["role"] == "instructor"
        assert result[0]["user_id"] == "user123"

    def test_get_users_by_role_no_db_client(self):
        """Test user retrieval when db client is not available."""
        # Temporarily set db to None
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = get_users_by_role("instructor")
            assert result == []
        finally:
            # Restore original db
            database_service_extended.db = original_db

    @patch('database_service_extended.db')
    def test_get_users_by_role_firestore_exception(self, mock_db):
        """Test user retrieval when Firestore throws exception."""
        mock_collection = Mock()
        mock_collection.where.side_effect = Exception("Firestore error")
        mock_db.collection.return_value = mock_collection
        
        result = get_users_by_role("instructor")
        assert result == []


class TestUpdateUserExtended:
    """Test update_user_extended function."""

    @patch('database_service_extended.db')
    def test_update_user_extended_success(self, mock_db):
        """Test successful user update."""
        # Setup mock
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db.collection.return_value = mock_collection
        
        update_data = {"first_name": "Updated", "last_name": "User"}
        
        # Call function
        result = update_user_extended("user123", update_data)
        
        # Verify results
        assert result is True
        # The function adds last_modified timestamp, so check that update was called
        mock_doc_ref.update.assert_called_once()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args["first_name"] == "Updated"
        assert call_args["last_name"] == "User"
        assert "last_modified" in call_args

    def test_update_user_extended_no_db_client(self):
        """Test user update when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = update_user_extended("user123", {"name": "test"})
            assert result is False
        finally:
            database_service_extended.db = original_db

    @patch('database_service_extended.db')
    def test_update_user_extended_firestore_exception(self, mock_db):
        """Test user update when Firestore throws exception."""
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.update.side_effect = Exception("Update failed")
        mock_collection.document.return_value = mock_doc_ref
        mock_db.collection.return_value = mock_collection
        
        result = update_user_extended("user123", {"name": "test"})
        assert result is False


class TestCreateCourse:
    """Test create_course function."""

    @patch('database_service_extended.db')
    def test_create_course_success(self, mock_db):
        """Test successful course creation."""
        # Setup mock
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "course123"
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        course_data = {
            "course_number": "MATH-101",
            "course_title": "Algebra",
            "department": "MATH",
            "credit_hours": 3
        }
        
        # Call function
        result = create_course(course_data)
        
        # Verify results
        assert result == "course123"
        mock_collection.add.assert_called_once()

    def test_create_course_no_db_client(self):
        """Test course creation when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = create_course({"course_number": "TEST-101"})
            assert result is None
        finally:
            database_service_extended.db = original_db

    @patch('database_service_extended.db')
    def test_create_course_firestore_exception(self, mock_db):
        """Test course creation when Firestore throws exception."""
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception("Creation failed")
        mock_db.collection.return_value = mock_collection
        
        result = create_course({"course_number": "TEST-101"})
        assert result is None


class TestGetCourseByNumber:
    """Test get_course_by_number function."""

    @patch('database_service_extended.db')
    def test_get_course_by_number_success(self, mock_db):
        """Test successful course retrieval by number."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "course_number": "MATH-101",
            "course_title": "Algebra",
            "department": "MATH"
        }
        mock_doc.id = "course123"
        
        mock_query.stream.return_value = iter([mock_doc])
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_course_by_number("MATH-101")
        
        # Verify results
        assert result["course_number"] == "MATH-101"
        assert result["course_id"] == "course123"

    @patch('database_service_extended.db')
    def test_get_course_by_number_not_found(self, mock_db):
        """Test course retrieval when course not found."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.stream.return_value = []
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        result = get_course_by_number("NONEXISTENT-999")
        assert result is None

    def test_get_course_by_number_no_db_client(self):
        """Test course retrieval when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = get_course_by_number("MATH-101")
            assert result is None
        finally:
            database_service_extended.db = original_db


class TestGetCoursesByDepartment:
    """Test get_courses_by_department function."""

    @patch('database_service_extended.db')
    def test_get_courses_by_department_success(self, mock_db):
        """Test successful course retrieval by department."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {"course_number": "MATH-101", "department": "MATH"}
        mock_doc1.id = "course1"
        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {"course_number": "MATH-102", "department": "MATH"}
        mock_doc2.id = "course2"
        
        mock_query.stream.return_value = iter([mock_doc1, mock_doc2])
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_courses_by_department("MATH")
        
        # Verify results
        assert len(result) == 2
        assert all(course["department"] == "MATH" for course in result)

    def test_get_courses_by_department_no_db_client(self):
        """Test course retrieval when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = get_courses_by_department("MATH")
            assert result == []
        finally:
            database_service_extended.db = original_db


class TestCreateTerm:
    """Test create_term function."""

    @patch('database_service_extended.db')
    def test_create_term_success(self, mock_db):
        """Test successful term creation."""
        # Setup mock
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "term123"
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        term_data = {
            "name": "Fall2024",
            "start_date": "2024-08-15",
            "end_date": "2024-12-15",
            "assessment_due_date": "2024-12-01"
        }
        
        # Call function
        result = create_term(term_data)
        
        # Verify results
        assert result == "term123"
        mock_collection.add.assert_called_once()

    def test_create_term_no_db_client(self):
        """Test term creation when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = create_term({"term_name": "Fall2024"})
            assert result is None
        finally:
            database_service_extended.db = original_db


class TestGetTermByName:
    """Test get_term_by_name function."""

    @patch('database_service_extended.db')
    def test_get_term_by_name_success(self, mock_db):
        """Test successful term retrieval by name."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "term_name": "Fall2024",
            "start_date": "2024-08-15",
            "end_date": "2024-12-15"
        }
        mock_doc.id = "term123"
        
        mock_query.stream.return_value = iter([mock_doc])
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_term_by_name("Fall2024")
        
        # Verify results
        assert result["term_name"] == "Fall2024"
        assert result["term_id"] == "term123"

    @patch('database_service_extended.db')
    def test_get_term_by_name_not_found(self, mock_db):
        """Test term retrieval when term not found."""
        mock_collection = Mock()
        mock_query = Mock()
        mock_query.stream.return_value = []
        mock_query.limit.return_value = mock_query
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        result = get_term_by_name("NonexistentTerm")
        assert result is None


class TestGetActiveTerms:
    """Test get_active_terms function."""

    @patch('database_service_extended.db')
    def test_get_active_terms_success(self, mock_db):
        """Test successful active terms retrieval."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "term_name": "Fall2024",
            "active": True,
            "start_date": "2024-08-15"
        }
        mock_doc.id = "term123"
        
        mock_query.stream.return_value = iter([mock_doc])
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_active_terms()
        
        # Verify results
        assert len(result) == 1
        assert result[0]["active"] is True
        assert result[0]["term_id"] == "term123"

    def test_get_active_terms_no_db_client(self):
        """Test active terms retrieval when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = get_active_terms()
            assert result == []
        finally:
            database_service_extended.db = original_db


class TestCreateCourseSection:
    """Test create_course_section function."""

    @patch('database_service_extended.db')
    def test_create_course_section_success(self, mock_db):
        """Test successful course section creation."""
        # Setup mock
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc_ref.id = "section123"
        mock_collection.add.return_value = (None, mock_doc_ref)
        mock_db.collection.return_value = mock_collection
        
        section_data = {
            "course_id": "course123",
            "term_id": "term123",
            "instructor_email": "instructor@example.com",
            "max_enrollment": 30
        }
        
        # Call function
        result = create_course_section(section_data)
        
        # Verify results
        assert result == "section123"
        mock_collection.add.assert_called_once()

    def test_create_course_section_no_db_client(self):
        """Test section creation when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = create_course_section({"course_number": "MATH-101"})
            assert result is None
        finally:
            database_service_extended.db = original_db


class TestGetSectionsByInstructor:
    """Test get_sections_by_instructor function."""

    @patch('database_service_extended.db')
    def test_get_sections_by_instructor_success(self, mock_db):
        """Test successful section retrieval by instructor."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "course_number": "MATH-101",
            "instructor_id": "instructor123",
            "term": "Fall2024"
        }
        mock_doc.id = "section123"
        
        mock_query.stream.return_value = iter([mock_doc])
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_sections_by_instructor("instructor123")
        
        # Verify results
        assert len(result) == 1
        assert result[0]["instructor_id"] == "instructor123"
        assert result[0]["section_id"] == "section123"

    def test_get_sections_by_instructor_no_db_client(self):
        """Test section retrieval when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = get_sections_by_instructor("instructor123")
            assert result == []
        finally:
            database_service_extended.db = original_db


class TestGetSectionsByTerm:
    """Test get_sections_by_term function."""

    @patch('database_service_extended.db')
    def test_get_sections_by_term_success(self, mock_db):
        """Test successful section retrieval by term."""
        # Setup mock
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc = Mock()
        mock_doc.to_dict.return_value = {
            "course_number": "MATH-101",
            "term_id": "fall2024",
            "instructor_email": "instructor@example.com"
        }
        mock_doc.id = "section123"
        
        mock_query.stream.return_value = iter([mock_doc])
        mock_collection.where.return_value = mock_query
        mock_db.collection.return_value = mock_collection
        
        # Call function
        result = get_sections_by_term("fall2024")
        
        # Verify results
        assert len(result) == 1
        assert result[0]["term_id"] == "fall2024"
        assert result[0]["section_id"] == "section123"

    def test_get_sections_by_term_no_db_client(self):
        """Test section retrieval when db client is not available."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            result = get_sections_by_term("fall2024")
            assert result == []
        finally:
            database_service_extended.db = original_db


class TestModuleImportsAndConstants:
    """Test module imports and constants."""

    def test_required_imports_available(self):
        """Test that all required imports are available."""
        assert hasattr(database_service_extended, 'firestore')
        assert hasattr(database_service_extended, 'db')
        assert hasattr(database_service_extended, 'USERS_COLLECTION')
        assert hasattr(database_service_extended, 'COURSES_COLLECTION')

    def test_all_functions_exported(self):
        """Test that all functions are properly exported."""
        functions = [
            'get_users_by_role',
            'update_user_extended',
            'create_course',
            'get_course_by_number',
            'get_courses_by_department',
            'create_term',
            'get_term_by_name',
            'get_active_terms',
            'create_course_section',
            'get_sections_by_instructor',
            'get_sections_by_term',
        ]
        
        for func_name in functions:
            assert hasattr(database_service_extended, func_name)
            assert callable(getattr(database_service_extended, func_name))


class TestErrorHandlingPatterns:
    """Test consistent error handling patterns across functions."""

    def test_all_functions_handle_no_db_client(self):
        """Test that all functions handle missing db client gracefully."""
        original_db = database_service_extended.db
        database_service_extended.db = None
        
        try:
            # Functions that should return empty lists
            list_functions = [
                (get_users_by_role, ("instructor",), []),
                (get_courses_by_department, ("MATH",), []),
                (get_active_terms, (), []),
                (get_sections_by_instructor, ("instructor123",), []),
                (get_sections_by_term, ("fall2024",), []),
            ]
            
            for func, args, expected in list_functions:
                result = func(*args)
                assert result == expected, f"{func.__name__} should return {expected} when db is None"
            
            # Functions that should return None
            none_functions = [
                (create_course, ({"course_number": "TEST-101"},)),
                (get_course_by_number, ("TEST-101",)),
                (create_term, ({"term_name": "Test"},)),
                (get_term_by_name, ("Test",)),
                (create_course_section, ({"course_number": "TEST-101"},)),
            ]
            
            for func, args in none_functions:
                result = func(*args)
                assert result is None, f"{func.__name__} should return None when db is None"
            
            # Functions that should return False
            assert update_user_extended("user123", {"name": "test"}) is False
            
        finally:
            database_service_extended.db = original_db

    @patch('database_service_extended.db')
    def test_functions_handle_firestore_exceptions(self, mock_db):
        """Test that functions handle Firestore exceptions gracefully."""
        # Setup mock to raise exceptions
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception("Firestore error")
        mock_collection.where.side_effect = Exception("Query error")
        mock_doc_ref = Mock()
        mock_doc_ref.update.side_effect = Exception("Update error")
        mock_collection.document.return_value = mock_doc_ref
        mock_db.collection.return_value = mock_collection
        
        # Test functions that should return empty lists on error
        list_functions = [
            (get_users_by_role, ("instructor",)),
            (get_courses_by_department, ("MATH",)),
            (get_active_terms, ()),
            (get_sections_by_instructor, ("instructor123",)),
            (get_sections_by_term, ("fall2024",)),
        ]
        
        for func, args in list_functions:
            result = func(*args)
            assert result == [], f"{func.__name__} should return [] on Firestore error"
        
        # Test functions that should return None on error
        none_functions = [
            (create_course, ({"course_number": "TEST-101"},)),
            (create_term, ({"term_name": "Test"},)),
            (create_course_section, ({"course_number": "TEST-101"},)),
        ]
        
        for func, args in none_functions:
            result = func(*args)
            assert result is None, f"{func.__name__} should return None on Firestore error"
        
        # Test update function returns False on error
        assert update_user_extended("user123", {"name": "test"}) is False
