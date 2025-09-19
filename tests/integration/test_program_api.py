"""
Integration tests for Program Management API endpoints

Tests the complete program management functionality including:
- Program creation via API
- Program listing and retrieval
- Program updates and deletion
- Default program protection
"""

from unittest.mock import Mock, patch

import pytest

from app import app
from tests.test_utils import CommonAuthMixin


class TestProgramAPIIntegration(CommonAuthMixin):
    """Test program API endpoints with full Flask app context"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_programs_by_institution")
    def test_list_programs_integration(self, mock_get_programs, mock_get_institution):
        """Test program listing endpoint integration"""
        mock_get_institution.return_value = "test-institution"
        mock_get_programs.return_value = [
            {
                "id": "cs-program",
                "name": "Computer Science",
                "short_name": "CS",
                "institution_id": "test-institution",
                "is_default": False,
            },
            {
                "id": "default-program",
                "name": "Unclassified",
                "short_name": "UNCLASSIFIED",
                "institution_id": "test-institution",
                "is_default": True,
            },
        ]

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/programs")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["programs"]) == 2
        assert data["programs"][0]["name"] == "Computer Science"

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_current_user")
    @patch("api_routes.create_program")
    def test_create_program_integration(
        self, mock_create, mock_get_user, mock_get_institution
    ):
        """Test program creation endpoint integration"""
        mock_get_institution.return_value = "test-institution"
        mock_get_user.return_value = {"user_id": "test-user"}
        mock_create.return_value = "new-program-id"

        program_data = {
            "name": "Mathematics",
            "short_name": "MATH",
            "description": "Mathematics Program",
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post("/api/programs", json=program_data)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["program_id"] == "new-program-id"
        assert data["message"] == "Program created successfully"

    @patch("api_routes.get_program_by_id")
    def test_get_program_integration(self, mock_get_program):
        """Test program retrieval endpoint integration"""
        mock_get_program.return_value = {
            "id": "cs-program",
            "name": "Computer Science",
            "short_name": "CS",
            "institution_id": "test-institution",
            "description": "Computer Science Program",
        }

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/programs/cs-program")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["program"]["name"] == "Computer Science"
        assert data["program"]["short_name"] == "CS"

    @patch("api_routes.get_program_by_id")
    def test_get_program_not_found_integration(self, mock_get_program):
        """Test program retrieval when program doesn't exist"""
        mock_get_program.return_value = None

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/programs/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Program not found"

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.update_program")
    def test_update_program_integration(self, mock_update, mock_get_program):
        """Test program update endpoint integration"""
        mock_get_program.return_value = {
            "id": "cs-program",
            "name": "Computer Science",
            "is_default": False,
        }
        mock_update.return_value = True

        update_data = {
            "name": "Computer Science & Engineering",
            "description": "Updated description",
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.put("/api/programs/cs-program", json=update_data)

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["message"] == "Program updated successfully"

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_programs_by_institution")
    @patch("api_routes.delete_program")
    def test_delete_program_integration(
        self, mock_delete, mock_get_programs, mock_get_institution, mock_get_program
    ):
        """Test program deletion endpoint integration"""
        mock_get_program.return_value = {
            "id": "cs-program",
            "name": "Computer Science",
            "is_default": False,
        }
        mock_get_institution.return_value = "test-institution"
        mock_get_programs.return_value = [
            {"id": "default-program", "is_default": True},
            {"id": "cs-program", "is_default": False},
        ]
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete("/api/programs/cs-program")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["message"] == "Program deleted successfully and courses reassigned"

    @patch("api_routes.get_program_by_id")
    def test_delete_default_program_prevented_integration(self, mock_get_program):
        """Test that default program deletion is prevented"""
        mock_get_program.return_value = {
            "id": "default-program",
            "name": "Unclassified",
            "is_default": True,
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete("/api/programs/default-program")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Cannot delete default program"

    def test_create_program_missing_data_integration(self):
        """Test program creation with missing required data"""
        incomplete_data = {
            "name": "Mathematics"
            # Missing short_name
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post("/api/programs", json=incomplete_data)

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Missing required field" in data["error"]

    def test_create_program_no_data_integration(self):
        """Test program creation with no JSON data"""
        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post("/api/programs")

        # Flask returns 500 when no Content-Type is provided
        assert response.status_code == 500
        # The error is handled by the exception handler, so we get a generic error response

    @patch("api_routes.get_current_institution_id")
    def test_list_programs_no_institution_integration(self, mock_get_institution):
        """Test program listing when no institution context available"""
        mock_get_institution.return_value = None

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/programs")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Institution ID not found"


class TestProgramWorkflow(CommonAuthMixin):
    """Test complete program management workflow"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_current_user")
    @patch("api_routes.create_program")
    @patch("api_routes.get_program_by_id")
    @patch("api_routes.update_program")
    @patch("api_routes.get_programs_by_institution")
    @patch("api_routes.delete_program")
    def test_complete_program_lifecycle(
        self,
        mock_delete,
        mock_get_programs,
        mock_update,
        mock_get_program,
        mock_create,
        mock_get_user,
        mock_get_institution,
    ):
        """Test complete program lifecycle: create -> read -> update -> delete"""

        # Setup mocks
        mock_get_institution.return_value = "test-institution"
        mock_get_user.return_value = {"user_id": "test-user"}

        # Step 1: Create program
        mock_create.return_value = "new-program-id"

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            create_response = self.client.post(
                "/api/programs",
                json={
                    "name": "Engineering",
                    "short_name": "ENG",
                    "description": "Engineering Program",
                },
            )

        assert create_response.status_code == 201
        create_data = create_response.get_json()
        assert create_data["success"] is True
        program_id = create_data["program_id"]

        # Step 2: Read program
        mock_get_program.return_value = {
            "id": program_id,
            "name": "Engineering",
            "short_name": "ENG",
            "description": "Engineering Program",
        }

        with patch("api_routes.login_required", lambda f: f):
            read_response = self.client.get(f"/api/programs/{program_id}")

        assert read_response.status_code == 200
        read_data = read_response.get_json()
        assert read_data["success"] is True
        assert read_data["program"]["name"] == "Engineering"

        # Step 3: Update program
        mock_update.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            update_response = self.client.put(
                f"/api/programs/{program_id}",
                json={
                    "name": "Engineering & Technology",
                    "description": "Updated Engineering Program",
                },
            )

        assert update_response.status_code == 200
        update_data = update_response.get_json()
        assert update_data["success"] is True

        # Step 4: Delete program
        mock_get_program.return_value = {
            "id": program_id,
            "name": "Engineering & Technology",
            "is_default": False,
        }
        mock_get_programs.return_value = [{"id": "default-program", "is_default": True}]
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            delete_response = self.client.delete(f"/api/programs/{program_id}")

        assert delete_response.status_code == 200
        delete_data = delete_response.get_json()
        assert delete_data["success"] is True
        assert "deleted successfully" in delete_data["message"]
