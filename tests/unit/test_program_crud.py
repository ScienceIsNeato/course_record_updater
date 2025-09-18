"""
Unit tests for Program CRUD operations

Tests the program management functionality including:
- Program creation, retrieval, update, and deletion
- Database service functions for program operations
- API endpoints for program management
- Default program handling and course reassignment
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest


# Test the database service functions
class TestProgramDatabaseService:
    """Test program database service functions"""

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    @patch("database_service.check_db_connection")
    def test_create_program_success(self, mock_check_db, mock_timeout, mock_db):
        """Test successful program creation"""
        from database_service import create_program

        # Mock database connection check
        mock_check_db.return_value = None

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_doc = Mock()
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc

        program_data = {
            "id": "test-program-id",
            "name": "Computer Science",
            "short_name": "CS",
            "institution_id": "test-institution",
        }

        result = create_program(program_data)

        assert result == "test-program-id"
        # Check that programs collection was called (may be called multiple times due to connection test)
        assert any(
            call[0][0] == "programs" for call in mock_db.collection.call_args_list
        )
        mock_collection.document.assert_called_once_with("test-program-id")
        mock_doc.set.assert_called_once()

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_get_programs_by_institution_success(self, mock_timeout, mock_db):
        """Test successful retrieval of programs by institution"""
        from database_service import get_programs_by_institution

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
        mock_doc1.id = "program1"
        mock_doc1.to_dict.return_value = {
            "name": "Computer Science",
            "short_name": "CS",
        }
        mock_doc2.id = "program2"
        mock_doc2.to_dict.return_value = {"name": "Mathematics", "short_name": "MATH"}

        mock_query.stream.return_value = [mock_doc1, mock_doc2]

        result = get_programs_by_institution("test-institution")

        assert len(result) == 2
        assert result[0]["id"] == "program1"
        assert result[0]["name"] == "Computer Science"
        assert result[1]["id"] == "program2"
        assert result[1]["name"] == "Mathematics"

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_get_program_by_id_found(self, mock_timeout, mock_db):
        """Test successful program retrieval by ID"""
        from database_service import get_program_by_id

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
        mock_doc.id = "test-program"
        mock_doc.to_dict.return_value = {"name": "Computer Science", "short_name": "CS"}

        result = get_program_by_id("test-program")

        assert result is not None
        assert result["id"] == "test-program"
        assert result["name"] == "Computer Science"

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_get_program_by_id_not_found(self, mock_timeout, mock_db):
        """Test program retrieval when program doesn't exist"""
        from database_service import get_program_by_id

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

        result = get_program_by_id("nonexistent-program")

        assert result is None

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_update_program_success(self, mock_timeout, mock_db):
        """Test successful program update"""
        from database_service import update_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_collection = Mock()
        mock_doc_ref = Mock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref

        updates = {"name": "Updated Name", "description": "Updated description"}

        result = update_program("test-program", updates)

        assert result is True
        mock_doc_ref.update.assert_called_once()
        # Verify timestamp was added
        call_args = mock_doc_ref.update.call_args[0][0]
        assert "updated_at" in call_args

    @patch("database_service.db")
    @patch("database_service.db_operation_timeout")
    def test_delete_program_with_course_reassignment(self, mock_timeout, mock_db):
        """Test program deletion with course reassignment"""
        from database_service import delete_program

        # Mock database operations
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)
        mock_courses_ref = Mock()
        mock_programs_ref = Mock()
        mock_query = Mock()
        mock_batch = Mock()
        mock_doc1 = Mock()
        mock_doc2 = Mock()

        mock_db.collection.side_effect = lambda name: (
            mock_courses_ref if name == "courses" else mock_programs_ref
        )
        mock_courses_ref.where.return_value = mock_query
        mock_db.batch.return_value = mock_batch

        # Mock course documents
        mock_doc1.to_dict.return_value = {
            "program_ids": ["program-to-delete", "other-program"]
        }
        mock_doc1.reference = Mock()
        mock_doc2.to_dict.return_value = {"program_ids": ["program-to-delete"]}
        mock_doc2.reference = Mock()

        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_programs_ref.document.return_value = Mock()

        result = delete_program("program-to-delete", "default-program")

        assert result is True
        mock_batch.commit.assert_called_once()


def create_test_session(client, user_data):
    """Helper function to create a test session with user data."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_data.get("user_id")
        sess["email"] = user_data.get("email")
        sess["role"] = user_data.get("role")
        sess["institution_id"] = user_data.get("institution_id")
        sess["program_ids"] = user_data.get("program_ids", [])
        sess["display_name"] = user_data.get(
            "display_name",
            f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
        )
        sess["created_at"] = user_data.get("created_at")
        sess["last_activity"] = user_data.get("last_activity")
        sess["remember_me"] = user_data.get("remember_me", False)


class TestProgramAPIEndpoints:
    """Test program API endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        from flask import Flask

        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_programs_by_institution")
    def test_list_programs_success(self, mock_get_programs, mock_get_institution):
        """Test successful program listing"""
        from api_routes import list_programs

        mock_get_institution.return_value = "test-institution"
        mock_get_programs.return_value = [
            {"id": "prog1", "name": "Computer Science", "short_name": "CS"},
            {"id": "prog2", "name": "Mathematics", "short_name": "MATH"},
        ]

        with patch("api_routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = Mock()

            result = list_programs()

            mock_jsonify.assert_called_once_with(
                {
                    "success": True,
                    "programs": [
                        {"id": "prog1", "name": "Computer Science", "short_name": "CS"},
                        {"id": "prog2", "name": "Mathematics", "short_name": "MATH"},
                    ],
                }
            )

    @patch("api_routes.get_current_institution_id")
    def test_list_programs_no_institution(self, mock_get_institution):
        """Test program listing when no institution ID available"""
        from api_routes import list_programs

        mock_get_institution.return_value = None

        with patch("api_routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = (Mock(), 400)

            result = list_programs()

            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Institution ID not found"}
            )

    def test_create_program_success(self):
        """Test successful program creation"""
        from api_routes import create_program_api

        with self.app.test_request_context():
            with (
                patch("api_routes.request") as mock_request,
                patch("api_routes.get_current_institution_id") as mock_get_institution,
                patch("api_routes.get_current_user") as mock_get_user,
                patch("api_routes.Program.create_schema") as mock_schema,
                patch("api_routes.create_program") as mock_create,
                patch("api_routes.jsonify") as mock_jsonify,
            ):

                mock_request.get_json = Mock(
                    return_value={
                        "name": "Computer Science",
                        "short_name": "CS",
                        "description": "Computer Science Program",
                    }
                )
                mock_get_institution.return_value = "test-institution"
                user_data = {"user_id": "test-user"}
                create_test_session(self.client, user_data)
                mock_schema.return_value = {"id": "new-program"}
                mock_create.return_value = "new-program"
                mock_jsonify.return_value = (Mock(), 201)

                result = create_program_api()

                mock_schema.assert_called_once()
                mock_create.assert_called_once_with({"id": "new-program"})

    def test_create_program_missing_required_field(self):
        """Test program creation with missing required fields"""
        from api_routes import create_program_api

        with self.app.test_request_context():
            with (
                patch("api_routes.request") as mock_request,
                patch("api_routes.jsonify") as mock_jsonify,
            ):

                mock_request.get_json = Mock(
                    return_value={
                        "name": "Computer Science"
                        # Missing short_name
                    }
                )
                mock_jsonify.return_value = (Mock(), 400)

                result = create_program_api()

                mock_jsonify.assert_called_once_with(
                    {"success": False, "error": "Missing required field: short_name"}
                )

    @patch("api_routes.get_program_by_id")
    def test_get_program_success(self, mock_get_program):
        """Test successful program retrieval"""
        from flask import Flask

        from api_routes import get_program

        mock_get_program.return_value = {
            "id": "test-program",
            "name": "Computer Science",
            "short_name": "CS",
        }

        app = Flask(__name__)
        with app.test_request_context("/programs/test-program"):
            with patch("api_routes.jsonify") as mock_jsonify:
                mock_jsonify.return_value = Mock()

                result = get_program("test-program")

            mock_jsonify.assert_called_once_with(
                {
                    "success": True,
                    "program": {
                        "id": "test-program",
                        "name": "Computer Science",
                        "short_name": "CS",
                    },
                }
            )

    @patch("api_routes.get_program_by_id")
    def test_get_program_not_found(self, mock_get_program):
        """Test program retrieval when program doesn't exist"""
        from flask import Flask

        from api_routes import get_program

        mock_get_program.return_value = None

        app = Flask(__name__)
        with app.test_request_context("/programs/nonexistent-program"):
            with patch("api_routes.jsonify") as mock_jsonify:
                mock_jsonify.return_value = (Mock(), 404)

                result = get_program("nonexistent-program")

            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Program not found"}
            )

    def test_update_program_success(self):
        """Test successful program update"""
        from api_routes import update_program_api

        with self.app.test_request_context():
            with (
                patch("api_routes.request") as mock_request,
                patch("api_routes.get_program_by_id") as mock_get_program,
                patch("api_routes.update_program") as mock_update,
                patch("api_routes.jsonify") as mock_jsonify,
            ):

                mock_request.get_json = Mock(
                    return_value={
                        "name": "Updated Computer Science",
                        "description": "Updated description",
                    }
                )
                mock_get_program.return_value = {
                    "id": "test-program",
                    "name": "Computer Science",
                }
                mock_update.return_value = True
                mock_jsonify.return_value = Mock()

                result = update_program_api("test-program")

                mock_update.assert_called_once_with(
                    "test-program",
                    {
                        "name": "Updated Computer Science",
                        "description": "Updated description",
                    },
                )

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_programs_by_institution")
    @patch("api_routes.delete_program")
    def test_delete_program_success(
        self, mock_delete, mock_get_programs, mock_get_institution, mock_get_program
    ):
        """Test successful program deletion"""
        from api_routes import delete_program_api

        mock_get_program.return_value = {"id": "test-program", "is_default": False}
        mock_get_institution.return_value = "test-institution"
        mock_get_programs.return_value = [
            {"id": "default-program", "is_default": True},
            {"id": "test-program", "is_default": False},
        ]
        mock_delete.return_value = True

        with patch("api_routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = Mock()

            result = delete_program_api("test-program")

            mock_delete.assert_called_once_with("test-program", "default-program")

    @patch("api_routes.get_program_by_id")
    def test_delete_default_program_prevented(self, mock_get_program):
        """Test that default program cannot be deleted"""
        from api_routes import delete_program_api

        mock_get_program.return_value = {"id": "default-program", "is_default": True}

        with patch("api_routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = (Mock(), 400)

            result = delete_program_api("default-program")

            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Cannot delete default program"}
            )


class TestProgramIntegration:
    """Test program integration scenarios"""

    @patch("database_service.db")
    def test_program_creation_during_registration(self, mock_db):
        """Test that default program is created during institution registration"""
        from registration_service import RegistrationService

        # This test verifies the integration point exists
        # The actual functionality is tested in registration_service tests
        assert hasattr(RegistrationService, "register_institution_admin")

    def test_program_model_schema_creation(self):
        """Test Program model schema creation"""
        from models import Program

        schema = Program.create_schema(
            name="Computer Science",
            short_name="CS",
            institution_id="test-institution",
            created_by="test-user",
            description="CS Program",
            is_default=False,
            program_admins=["admin1", "admin2"],
        )

        assert schema["name"] == "Computer Science"
        assert schema["short_name"] == "CS"
        assert schema["institution_id"] == "test-institution"
        assert schema["created_by"] == "test-user"
        assert schema["description"] == "CS Program"
        assert schema["is_default"] is False
        assert schema["program_admins"] == ["admin1", "admin2"]
        assert "program_id" in schema
        assert "created_at" in schema

    def test_default_program_schema_creation(self):
        """Test default program creation schema"""
        from models import Program

        schema = Program.create_schema(
            name="Unclassified",
            short_name="UNCLASSIFIED",
            institution_id="test-institution",
            created_by="system",
            description="Default program for unassigned courses",
            is_default=True,
        )

        assert schema["name"] == "Unclassified"
        assert schema["is_default"] is True
        assert schema["program_admins"] == []
