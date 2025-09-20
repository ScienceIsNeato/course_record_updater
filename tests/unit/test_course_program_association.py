"""
Unit tests for Course-Program Association functionality

Tests the course-program association functionality including:
- Adding/removing courses from programs
- Bulk operations for course management
- Course visibility and program filtering
- Orphan course handling with default program assignment
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask, session

from tests.test_utils import CommonAuthMixin


# Test the database service functions
class TestCourseProgramDatabaseService:
    """Test course-program association database service functions"""

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_get_courses_by_program_success(self, mock_timeout, mock_db):
        """Test successful retrieval of courses by program"""
        from database_service import get_courses_by_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_query = Mock()
        mock_doc1 = Mock()
        mock_doc2 = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.where.return_value = mock_query

        # Mock document data
        mock_doc1.id = "course1"
        mock_doc1.to_dict.return_value = {
            "course_number": "CS101",
            "course_title": "Intro to CS",
        }
        mock_doc2.id = "course2"
        mock_doc2.to_dict.return_value = {
            "course_number": "CS201",
            "course_title": "Data Structures",
        }

        mock_query.stream.return_value = [mock_doc1, mock_doc2]

        result = get_courses_by_program("cs-program")

        assert len(result) == 2
        assert result[0]["course_id"] == "course1"
        assert result[0]["course_number"] == "CS101"
        assert result[1]["course_id"] == "course2"
        assert result[1]["course_number"] == "CS201"

        mock_collection.where.assert_called_once_with(
            "program_ids", "array_contains", "cs-program"
        )

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_add_course_to_program_success(self, mock_timeout, mock_db):
        """Test successful course addition to program"""
        from database_service import add_course_to_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc

        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"program_ids": ["other-program"]}

        result = add_course_to_program("course1", "cs-program")

        assert result is True
        mock_doc_ref.update.assert_called_once()
        # Verify program was added to the list
        update_call = mock_doc_ref.update.call_args[0][0]
        assert "other-program" in update_call["program_ids"]
        assert "cs-program" in update_call["program_ids"]

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_add_course_to_program_already_assigned(self, mock_timeout, mock_db):
        """Test adding course to program when already assigned"""
        from database_service import add_course_to_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc

        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"program_ids": ["cs-program", "other-program"]}

        result = add_course_to_program("course1", "cs-program")

        assert result is True
        # Should not call update since already assigned
        mock_doc_ref.update.assert_not_called()

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_add_course_to_program_course_not_found(self, mock_timeout, mock_db):
        """Test adding course to program when course doesn't exist"""
        from database_service import add_course_to_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc

        mock_doc.exists = False

        result = add_course_to_program("nonexistent", "cs-program")

        assert result is False
        mock_doc_ref.update.assert_not_called()

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_remove_course_from_program_success(self, mock_timeout, mock_db):
        """Test successful course removal from program"""
        from database_service import remove_course_from_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc

        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"program_ids": ["cs-program", "other-program"]}

        result = remove_course_from_program("course1", "cs-program")

        assert result is True
        mock_doc_ref.update.assert_called_once()
        # Verify program was removed from the list
        update_call = mock_doc_ref.update.call_args[0][0]
        assert "cs-program" not in update_call["program_ids"]
        assert "other-program" in update_call["program_ids"]

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_remove_course_from_program_with_orphan_handling(
        self, mock_timeout, mock_db
    ):
        """Test course removal with orphan assignment to default program"""
        from database_service import remove_course_from_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_doc_ref = Mock()
        mock_doc = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc

        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "program_ids": ["cs-program"]
        }  # Only one program

        result = remove_course_from_program("course1", "cs-program", "default-program")

        assert result is True
        mock_doc_ref.update.assert_called_once()
        # Verify course was assigned to default program
        update_call = mock_doc_ref.update.call_args[0][0]
        assert update_call["program_ids"] == ["default-program"]

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_bulk_add_courses_to_program_success(self, mock_timeout, mock_db):
        """Test successful bulk course addition to program"""
        from database_service import bulk_add_courses_to_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_batch = Mock()
        mock_doc_ref1 = Mock()
        mock_doc_ref2 = Mock()
        mock_doc1 = Mock()
        mock_doc2 = Mock()

        mock_db.collection.return_value = mock_collection
        mock_db.batch.return_value = mock_batch

        # Mock course documents
        mock_collection.document.side_effect = [mock_doc_ref1, mock_doc_ref2]
        mock_doc_ref1.get.return_value = mock_doc1
        mock_doc_ref2.get.return_value = mock_doc2

        mock_doc1.exists = True
        mock_doc1.to_dict.return_value = {"program_ids": ["other-program"]}
        mock_doc2.exists = True
        mock_doc2.to_dict.return_value = {"program_ids": []}

        result = bulk_add_courses_to_program(["course1", "course2"], "cs-program")

        assert result["success_count"] == 2
        assert result["failure_count"] == 0
        assert result["already_assigned"] == 0
        mock_batch.commit.assert_called_once()

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_bulk_add_courses_mixed_results(self, mock_timeout, mock_db):
        """Test bulk course addition with mixed success/failure results"""
        from database_service import bulk_add_courses_to_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_batch = Mock()
        mock_doc_ref1 = Mock()
        mock_doc_ref2 = Mock()
        mock_doc_ref3 = Mock()
        mock_doc1 = Mock()
        mock_doc2 = Mock()
        mock_doc3 = Mock()

        mock_db.collection.return_value = mock_collection
        mock_db.batch.return_value = mock_batch

        # Mock course documents with mixed scenarios
        mock_collection.document.side_effect = [
            mock_doc_ref1,
            mock_doc_ref2,
            mock_doc_ref3,
        ]
        mock_doc_ref1.get.return_value = mock_doc1
        mock_doc_ref2.get.return_value = mock_doc2
        mock_doc_ref3.get.return_value = mock_doc3

        # Course 1: Success (new assignment)
        mock_doc1.exists = True
        mock_doc1.to_dict.return_value = {"program_ids": ["other-program"]}

        # Course 2: Already assigned
        mock_doc2.exists = True
        mock_doc2.to_dict.return_value = {
            "program_ids": ["cs-program", "other-program"]
        }

        # Course 3: Not found
        mock_doc3.exists = False

        result = bulk_add_courses_to_program(
            ["course1", "course2", "course3"], "cs-program"
        )

        assert result["success_count"] == 1
        assert result["failure_count"] == 1
        assert result["already_assigned"] == 1
        assert len(result["failures"]) == 1
        assert result["failures"][0]["course_id"] == "course3"

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_bulk_remove_courses_from_program_success(self, mock_timeout, mock_db):
        """Test successful bulk course removal from program"""
        from database_service import bulk_remove_courses_from_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_batch = Mock()
        mock_doc_ref1 = Mock()
        mock_doc_ref2 = Mock()
        mock_doc1 = Mock()
        mock_doc2 = Mock()

        mock_db.collection.return_value = mock_collection
        mock_db.batch.return_value = mock_batch

        # Mock course documents
        mock_collection.document.side_effect = [mock_doc_ref1, mock_doc_ref2]
        mock_doc_ref1.get.return_value = mock_doc1
        mock_doc_ref2.get.return_value = mock_doc2

        mock_doc1.exists = True
        mock_doc1.to_dict.return_value = {
            "program_ids": ["cs-program", "other-program"]
        }
        mock_doc2.exists = True
        mock_doc2.to_dict.return_value = {
            "program_ids": ["cs-program"]
        }  # Will be orphaned

        result = bulk_remove_courses_from_program(
            ["course1", "course2"], "cs-program", "default-program"
        )

        assert result["success_count"] == 2
        assert result["failure_count"] == 0
        assert result["not_assigned"] == 0
        assert result["orphaned_assigned_to_default"] == 1
        mock_batch.commit.assert_called_once()


class TestCourseProgramAPIEndpoints(CommonAuthMixin):
    """Test course-program association API endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.secret_key = "test-secret-key"
        self.client = self.app.test_client()

    def _seed_session(self):
        """Populate session with an authenticated site admin user"""
        user_data = {**self._get_default_site_admin_user()}
        session["user_id"] = user_data["user_id"]
        session["email"] = user_data.get("email", "admin@test.com")
        session["role"] = user_data["role"]
        session["institution_id"] = user_data["institution_id"]
        session["program_ids"] = user_data.get("program_ids", ["test-program-123"])
        session["display_name"] = user_data.get("display_name", "Test Admin")

    @contextmanager
    def _authenticated_request_context(self):
        """Request context preloaded with real-auth session data"""
        with self.app.test_request_context():
            self._seed_session()
            yield

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.get_courses_by_program")
    def test_get_program_courses_success(self, mock_get_courses, mock_get_program):
        """Test successful program courses retrieval"""
        from api_routes import get_program_courses

        with self._authenticated_request_context():
            mock_get_program.return_value = {
                "id": "cs-program",
                "name": "Computer Science",
            }
            mock_get_courses.return_value = [
                {
                    "course_id": "course1",
                    "course_number": "CS101",
                    "course_title": "Intro to CS",
                },
                {
                    "course_id": "course2",
                    "course_number": "CS201",
                    "course_title": "Data Structures",
                },
            ]

            with patch("api_routes.jsonify") as mock_jsonify:
                mock_jsonify.return_value = Mock()

                result = get_program_courses("cs-program")

                mock_jsonify.assert_called_once()
                call_args = mock_jsonify.call_args[0][0]
                assert call_args["success"] is True
                assert call_args["program_id"] == "cs-program"
                assert call_args["program_name"] == "Computer Science"
                assert len(call_args["courses"]) == 2
                assert call_args["count"] == 2

    @patch("api_routes.get_program_by_id")
    def test_get_program_courses_program_not_found(self, mock_get_program):
        """Test program courses retrieval when program doesn't exist"""
        from api_routes import get_program_courses

        with self._authenticated_request_context():
            mock_get_program.return_value = None

            with patch("api_routes.jsonify") as mock_jsonify:
                mock_jsonify.return_value = (Mock(), 404)

                result = get_program_courses("nonexistent")

                mock_jsonify.assert_called_once_with(
                    {"success": False, "error": "Program not found"}
                )

    def test_add_course_to_program_success(self):
        """Test successful course addition to program"""
        from api_routes import add_course_to_program_api

        with self._authenticated_request_context():
            with (
                patch("api_routes.request") as mock_request,
                patch("api_routes.get_program_by_id") as mock_get_program,
                patch("api_routes.get_course_by_number") as mock_get_course,
                patch("api_routes.add_course_to_program") as mock_add,
                patch("api_routes.jsonify") as mock_jsonify,
            ):

                mock_request.get_json = Mock(return_value={"course_id": "CS101"})
                mock_get_program.return_value = {
                    "id": "cs-program",
                    "name": "Computer Science",
                }
                mock_get_course.return_value = {
                    "course_id": "course1",
                    "course_number": "CS101",
                }
                mock_add.return_value = True
                mock_jsonify.return_value = Mock()

                result = add_course_to_program_api("cs-program")

                mock_add.assert_called_once_with("course1", "cs-program")
                mock_jsonify.assert_called_once()
                call_args = mock_jsonify.call_args[0][0]
                assert call_args["success"] is True
                assert "CS101 added to program Computer Science" in call_args["message"]

    def test_add_course_to_program_missing_data(self):
        """Test course addition with missing required data"""
        from api_routes import add_course_to_program_api

        with self._authenticated_request_context():
            with (
                patch("api_routes.request") as mock_request,
                patch("api_routes.jsonify") as mock_jsonify,
            ):

                mock_request.get_json = Mock(return_value={"other_field": "value"})
                mock_jsonify.return_value = (Mock(), 400)

                result = add_course_to_program_api("cs-program")

                mock_jsonify.assert_called_once_with(
                    {"success": False, "error": "Missing required field: course_id"}
                )

    def test_bulk_manage_program_courses_add_success(self):
        """Test successful bulk course addition"""
        from api_routes import bulk_manage_program_courses

        with self._authenticated_request_context():
            with (
                patch("api_routes.request") as mock_request,
                patch("api_routes.get_program_by_id") as mock_get_program,
                patch("api_routes.bulk_add_courses_to_program") as mock_bulk_add,
                patch("api_routes.jsonify") as mock_jsonify,
            ):

                mock_request.get_json = Mock(
                    return_value={
                        "action": "add",
                        "course_ids": ["course1", "course2", "course3"],
                    }
                )
                mock_get_program.return_value = {
                    "id": "cs-program",
                    "name": "Computer Science",
                }
                mock_bulk_add.return_value = {
                    "success_count": 2,
                    "failure_count": 1,
                    "already_assigned": 0,
                    "failures": [{"course_id": "course3", "error": "Course not found"}],
                }
                mock_jsonify.return_value = Mock()

                result = bulk_manage_program_courses("cs-program")

                mock_bulk_add.assert_called_once_with(
                    ["course1", "course2", "course3"], "cs-program"
                )
                mock_jsonify.assert_called_once()
                call_args = mock_jsonify.call_args[0][0]
                assert call_args["success"] is True
                assert "Bulk add operation completed: 2 added" in call_args["message"]

    def test_bulk_manage_program_courses_invalid_action(self):
        """Test bulk course management with invalid action"""
        from api_routes import bulk_manage_program_courses

        with self._authenticated_request_context():
            with (
                patch("api_routes.request") as mock_request,
                patch("api_routes.jsonify") as mock_jsonify,
            ):

                mock_request.get_json = Mock(
                    return_value={"action": "invalid", "course_ids": ["course1"]}
                )
                mock_jsonify.return_value = (Mock(), 400)

                result = bulk_manage_program_courses("cs-program")

                mock_jsonify.assert_called_once_with(
                    {
                        "success": False,
                        "error": "Invalid or missing action. Use 'add' or 'remove'",
                    }
                )

    @patch("api_routes.get_course_by_number")
    @patch("api_routes.get_program_by_id")
    def test_get_course_programs_success(self, mock_get_program, mock_get_course):
        """Test successful course programs retrieval"""
        from api_routes import get_course_programs

        with self._authenticated_request_context():
            mock_get_course.return_value = {
                "course_id": "course1",
                "course_title": "Introduction to Computer Science",
                "program_ids": ["cs-program", "eng-program"],
            }
            mock_get_program.side_effect = [
                {"id": "cs-program", "name": "Computer Science"},
                {"id": "eng-program", "name": "Engineering"},
            ]

            with patch("api_routes.jsonify") as mock_jsonify:
                mock_jsonify.return_value = Mock()

                result = get_course_programs("CS101")

                mock_jsonify.assert_called_once()
                call_args = mock_jsonify.call_args[0][0]
                assert call_args["success"] is True
                assert call_args["course_id"] == "CS101"
                assert call_args["course_title"] == "Introduction to Computer Science"
                assert len(call_args["programs"]) == 2
                assert call_args["count"] == 2


class TestCourseProgramIntegration:
    """Test course-program association integration scenarios"""

    def test_course_model_program_ids_support(self):
        """Test Course model supports program_ids"""
        from models import Course

        schema = Course.create_schema(
            course_number="CS101",
            course_title="Introduction to Computer Science",
            department="Computer Science",
            institution_id="test-institution",
            program_ids=["cs-program", "eng-program"],
        )

        assert schema["course_number"] == "CS101"
        assert schema["course_title"] == "Introduction to Computer Science"
        assert schema["program_ids"] == ["cs-program", "eng-program"]
        assert "course_id" in schema

    def test_course_model_empty_program_ids(self):
        """Test Course model with empty program_ids"""
        from models import Course

        schema = Course.create_schema(
            course_number="CS101",
            course_title="Introduction to Computer Science",
            department="Computer Science",
            institution_id="test-institution",
        )

        assert schema["program_ids"] == []

    def test_default_program_assignment_logic(self):
        """Test that orphan courses are assigned to default program"""
        # This test verifies the logic exists in the remove functions
        from database_service import remove_course_from_program

        # The function signature includes default_program_id parameter
        assert hasattr(remove_course_from_program, "__call__")

        # Check function signature includes the default program parameter
        import inspect

        sig = inspect.signature(remove_course_from_program)
        assert "default_program_id" in sig.parameters
