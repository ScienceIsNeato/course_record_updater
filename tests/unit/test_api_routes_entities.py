import json
from unittest.mock import patch

from src.app import app
from tests.test_utils import create_test_session


class TestTermRoutes:
    """Test Term management API routes."""

    def setup_method(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret"
        self.client = self.app.test_client()
        self.headers = {"Content-Type": "application/json"}
        self.admin_user = {
            "user_id": "u1",
            "email": "admin@test.edu",
            "role": "institution_admin",
            "institution_id": "inst-1",
            "first_name": "Test",
            "last_name": "Admin",
        }

    @patch("src.api_routes.get_active_terms")
    def test_list_terms_success(self, mock_get_terms):
        """Test listing terms for an institution."""
        create_test_session(self.client, self.admin_user)
        mock_get_terms.return_value = [{"term_id": "t1", "name": "Fall 2024"}]

        response = self.client.get("/api/terms")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["terms"]) == 1
        assert data["terms"][0]["name"] == "Fall 2024"

    @patch("src.api_routes.create_term")
    def test_create_term_success(self, mock_create):
        """Test creating a new term."""
        create_test_session(self.client, self.admin_user)
        mock_create.return_value = "term-123"

        payload = {
            "name": "Spring 2025",
            "start_date": "2025-01-01",
            "end_date": "2025-05-01",
            "assessment_due_date": "2025-05-15",
        }

        response = self.client.post("/api/terms", json=payload, headers=self.headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["term_id"] == "term-123"

    @patch("src.api_routes.get_term_by_id")
    def test_get_term_success(self, mock_get_term):
        """Test getting a term by ID."""
        create_test_session(self.client, self.admin_user)
        mock_get_term.return_value = {
            "term_id": "t1",
            "name": "Fall 2024",
            "institution_id": "inst-1",
        }

        response = self.client.get("/api/terms/t1")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["term"]["name"] == "Fall 2024"

    @patch("src.api_routes.get_term_by_id")
    def test_get_term_not_found_or_access_denied(self, mock_get_term):
        """Test getting term that doesn't exist or wrong institution."""
        create_test_session(self.client, self.admin_user)

        # Case 1: Term not found
        mock_get_term.return_value = None
        response = self.client.get("/api/terms/t999")
        assert response.status_code == 404

        # Case 2: Wrong institution
        mock_get_term.return_value = {"term_id": "t1", "institution_id": "other-inst"}
        response = self.client.get("/api/terms/t1")
        assert response.status_code == 404

    @patch("src.api_routes.get_term_by_id")
    @patch("src.api_routes.update_term")
    def test_update_term_success(self, mock_update, mock_get_term):
        """Test updating a term."""
        create_test_session(self.client, self.admin_user)
        mock_get_term.return_value = {"term_id": "t1", "institution_id": "inst-1"}
        mock_update.return_value = True

        response = self.client.put(
            "/api/terms/t1", json={"name": "Updated Name"}, headers=self.headers
        )

        assert response.status_code == 200
        assert json.loads(response.data)["success"] is True

    @patch("src.api_routes.get_term_by_id")
    @patch("src.api_routes.delete_term")
    def test_delete_term_success(self, mock_delete, mock_get_term):
        """Test deleting a term."""
        create_test_session(self.client, self.admin_user)
        mock_get_term.return_value = {
            "term_id": "t1",
            "institution_id": "inst-1",
            "name": "Fall 2024",
        }
        mock_delete.return_value = True

        response = self.client.delete("/api/terms/t1")

        assert response.status_code == 200
        assert json.loads(response.data)["success"] is True


class TestProgramRoutes:
    """Test Program management API routes."""

    def setup_method(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret"
        self.client = self.app.test_client()
        self.headers = {"Content-Type": "application/json"}
        self.admin_user = {
            "user_id": "u1",
            "email": "admin@test.edu",
            "role": "institution_admin",
            "institution_id": "inst-1",
            "first_name": "Test",
            "last_name": "Admin",
        }

    @patch("src.api_routes.get_programs_by_institution")
    def test_list_programs_success(self, mock_get_programs):
        """Test listing programs."""
        create_test_session(self.client, self.admin_user)
        mock_get_programs.return_value = [
            {"program_id": "p1", "name": "Computer Science"}
        ]

        response = self.client.get("/api/programs")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["programs"]) == 1

    @patch("src.api_routes.create_program")
    def test_create_program_success(self, mock_create):
        """Test creating a program."""
        create_test_session(self.client, self.admin_user)
        mock_create.return_value = "prog-123"

        payload = {"name": "Physics", "short_name": "PHYS"}
        response = self.client.post("/api/programs", json=payload, headers=self.headers)

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["program_id"] == "prog-123"

    @patch("src.api_routes.get_program_by_id")
    def test_get_program_success(self, mock_get_program):
        """Test getting a program."""
        user = self.admin_user.copy()
        user["program_ids"] = ["p1"]
        create_test_session(self.client, user)
        mock_get_program.return_value = {"program_id": "p1", "name": "Physics"}

        response = self.client.get("/api/programs/p1")

        assert response.status_code == 200
        assert json.loads(response.data)["program"]["name"] == "Physics"

    @patch("src.api_routes.get_program_by_id")
    @patch("src.api_routes.update_program")
    def test_update_program_success(self, mock_update, mock_get_program):
        """Test updating a program."""
        create_test_session(self.client, self.admin_user)
        mock_get_program.return_value = {"program_id": "p1"}
        mock_update.return_value = True

        response = self.client.put(
            "/api/programs/p1", json={"name": "New Name"}, headers=self.headers
        )

        assert response.status_code == 200
        assert json.loads(response.data)["success"] is True

    @patch("src.api_routes.get_program_by_id")
    @patch("src.api_routes.delete_program")
    @patch("src.api_routes.get_programs_by_institution")
    def test_delete_program_success(
        self, mock_get_programs, mock_delete, mock_get_prog
    ):
        """Test deleting a program."""
        create_test_session(self.client, self.admin_user)

        # Setup program to delete
        mock_get_prog.return_value = {
            "program_id": "p1",
            "institution_id": "inst-1",
            "is_default": False,
        }

        # Setup default program for reassignment
        mock_get_programs.return_value = [
            {"program_id": "p1", "is_default": False},
            {"program_id": "default-p", "is_default": True},
        ]

        mock_delete.return_value = True

        response = self.client.delete("/api/programs/p1")

        assert response.status_code == 200
        assert json.loads(response.data)["success"] is True
