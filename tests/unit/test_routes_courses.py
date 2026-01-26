"""Unit tests for course API routes (migrated from test_api_routes.py)."""

import json
from unittest.mock import patch

import pytest

from src.app import app
from src.utils.constants import GENERIC_PASSWORD

TEST_PASSWORD = GENERIC_PASSWORD  # Test password for unit tests


class TestCourseEndpoints:
    """Test course management endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def _login_user(self, overrides=None):
        return self._login_site_admin(overrides)

    @patch("src.api.routes.courses.get_all_courses")
    def test_get_courses_endpoint_exists(self, mock_get_all_courses):
        """Test that GET /api/courses endpoint exists and returns valid JSON."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_get_all_courses.return_value = []

        response = self.client.get("/api/courses")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "courses" in data
        assert isinstance(data["courses"], list)

    @patch("src.api.routes.courses.get_courses_by_department")
    def test_get_courses_with_department_filter(self, mock_get_courses):
        """Test GET /api/courses with department filter."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_get_courses.return_value = [
            {
                "course_number": "MATH-101",
                "course_title": "Algebra",
                "department": "MATH",
            }
        ]

        response = self.client.get("/api/courses?department=MATH")
        assert response.status_code == 200

        mock_get_courses.assert_called_with("riverside-tech-institute", "MATH")

    @patch("src.api.routes.courses.create_course")
    def test_create_course_success(self, mock_create_course):
        """Test POST /api/courses with valid data."""
        self._login_site_admin()
        mock_create_course.return_value = "course-123"

        course_data = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "TEST",
            "credit_hours": 3,
        }

        response = self.client.post(
            "/api/courses", json=course_data, content_type="application/json"
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "message" in data
        assert "course_id" in data

    @patch("src.api.utils.get_current_institution_id")
    def test_create_course_requires_institution_context(self, mock_get_institution_id):
        """Test POST /api/courses fails when no institution context is available."""
        self._login_site_admin()
        mock_get_institution_id.return_value = None  # No institution context

        course_data = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "TEST",
        }

        response = self.client.post(
            "/api/courses", json=course_data, content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Institution context required" in data["error"]

    @patch("src.api.routes.courses.create_course")
    @patch("src.api.utils.get_current_institution_id")
    def test_create_course_adds_institution_context(
        self, mock_get_institution_id, mock_create_course
    ):
        """Test POST /api/courses automatically adds institution_id from context."""
        self._login_site_admin()
        mock_get_institution_id.return_value = "test-institution-123"
        mock_create_course.return_value = "course-456"

        course_data = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "TEST",
        }

        response = self.client.post(
            "/api/courses", json=course_data, content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["course_id"] == "course-456"

        # Verify that institution_id was added to the course data
        mock_create_course.assert_called_once()
        call_args = mock_create_course.call_args[0][0]
        assert call_args["institution_id"] == "test-institution-123"
        assert call_args["course_number"] == "TEST-101"
        assert call_args["course_title"] == "Test Course"
        assert call_args["department"] == "TEST"

    @patch("src.api.routes.courses.get_course_by_number", return_value=None)
    def test_get_course_by_number_endpoint_exists(self, mock_get_course):
        """Test that GET /api/courses/<course_number> endpoint exists."""
        self._login_site_admin()

        response = self.client.get("/api/courses/MATH-101")
        # Endpoint exists and correctly returns 404 for non-existent course
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        mock_get_course.assert_called_once_with("MATH-101")

    @patch("src.api.routes.courses.get_course_by_number")
    def test_get_course_by_number_not_found(self, mock_get_course):
        """Test GET /api/courses/<course_number> when course doesn't exist."""
        self._login_site_admin()
        mock_get_course.return_value = None

        response = self.client.get("/api/courses/NONEXISTENT-999")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"].lower()

    @patch("src.api.routes.courses.duplicate_course_record")
    @patch("src.api.routes.courses.get_course_by_id")
    def test_duplicate_course_success(
        self, mock_get_course_by_id, mock_duplicate_course
    ):
        """Test POST /api/courses/<course_id>/duplicate succeeds."""
        self._login_site_admin()
        source_course = {
            "course_id": "course-123",
            "course_number": "BIOL-201",
            "institution_id": "inst-123",
            "program_ids": ["prog-1"],
        }
        duplicated_course = {
            "course_id": "course-999",
            "course_number": "BIOL-201-V2",
            "institution_id": "inst-123",
            "program_ids": ["prog-1"],
        }

        mock_get_course_by_id.side_effect = [source_course, duplicated_course]
        mock_duplicate_course.return_value = "course-999"

        response = self.client.post(
            "/api/courses/course-123/duplicate",
            json={"credit_hours": 4},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["course"]["course_id"] == "course-999"
        mock_duplicate_course.assert_called_once()

    @patch("src.api.routes.courses.get_course_by_id")
    def test_duplicate_course_forbidden_for_other_institution(
        self, mock_get_course_by_id
    ):
        """Test duplication blocked when user lacks institution access."""
        self._login_site_admin(
            {"role": "institution_admin", "institution_id": "inst-999"}
        )
        mock_get_course_by_id.return_value = {
            "course_id": "course-123",
            "course_number": "BIOL-201",
            "institution_id": "inst-123",
        }

        response = self.client.post("/api/courses/course-123/duplicate", json={})
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["success"] is False

    @patch("src.api.routes.courses.get_course_by_id")
    def test_duplicate_course_not_found(self, mock_get_course_by_id):
        """Test duplication returns 404 when course missing."""
        self._login_site_admin()
        mock_get_course_by_id.return_value = None

        response = self.client.post("/api/courses/missing-course/duplicate", json={})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False


class TestCourseManagementOperations:
    """Test advanced course management functionality."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("src.api.routes.courses.create_course")
    @patch("src.services.auth_service.has_permission")
    def test_create_course_comprehensive_validation(
        self, mock_has_permission, mock_create_course
    ):
        """Test comprehensive course creation validation."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_create_course.return_value = "course123"

        # Test successful course creation
        course_data = {
            "course_number": "MATH-101",
            "course_title": "Algebra I",
            "department": "MATH",
            "credit_hours": 3,
        }

        response = self.client.post("/api/courses", json=course_data)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["course_id"] == "course123"
        mock_create_course.assert_called_once()

    @patch("src.services.auth_service.has_permission")
    def test_create_course_missing_fields(self, mock_has_permission):
        """Test course creation with missing required fields."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True

        # Test missing course_number
        response = self.client.post(
            "/api/courses", json={"course_title": "Test Course", "department": "TEST"}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "Missing required fields" in data["error"]

    @patch("src.api.routes.terms.create_term")
    @patch("src.services.auth_service.has_permission")
    def test_create_term_comprehensive(self, mock_has_permission, mock_create_term):
        """Test comprehensive term creation."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_create_term.return_value = "term123"

        term_data = {
            "name": "2024 Fall",
            "start_date": "2024-08-15",
            "end_date": "2024-12-15",
            "assessment_due_date": "2024-12-20",
        }

        response = self.client.post("/api/terms", json=term_data)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["term_id"] == "term123"

    @patch("src.api.routes.sections.get_sections_by_instructor")
    def test_get_sections_by_instructor_comprehensive(self, mock_get_sections):
        """Test getting sections by instructor comprehensively."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_get_sections.return_value = [
            {
                "section_id": "1",
                "course_number": "MATH-101",
                "instructor_id": "instructor1",
            },
            {
                "section_id": "2",
                "course_number": "ENG-102",
                "instructor_id": "instructor1",
            },
        ]

        response = self.client.get("/api/sections?instructor_id=instructor1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["sections"]) == 2
        mock_get_sections.assert_called_once_with("instructor1")

    @patch("src.api.routes.sections.get_sections_by_term")
    def test_get_sections_by_term_comprehensive(self, mock_get_sections):
        """Test getting sections by term comprehensively."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_get_sections.return_value = [
            {"section_id": "1", "course_number": "MATH-101", "term_id": "term1"},
            {"section_id": "2", "course_number": "ENG-102", "term_id": "term1"},
        ]

        response = self.client.get("/api/sections?term_id=term1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["sections"]) == 2
        mock_get_sections.assert_called_once_with("term1")

    def test_get_import_progress_comprehensive(self):
        """Test import progress endpoint comprehensively."""
        # Test with valid progress ID
        response = self.client.get("/api/import/progress/progress123")

        # Should handle progress endpoint (currently returns stubbed data)
        assert response.status_code in [200, 404]  # May not be implemented yet

    @patch("src.services.auth_service.has_permission")
    def test_import_excel_file_validation(self, mock_has_permission):
        """Test Excel import file validation."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True

        # Test no file uploaded
        response = self.client.post("/api/import/excel")
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "No Excel file provided"

    @patch("src.api.routes.programs.get_program_by_id")
    @patch("src.api.routes.programs.remove_course_from_program")
    @patch("src.services.auth_service.has_permission")
    def test_remove_course_from_program_success(
        self, mock_has_permission, mock_remove, mock_get_program
    ):
        """Test successful course removal from program."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_get_program.return_value = {
            "program_id": "prog1",
            "name": "Computer Science",
            "institution_id": "test-institution",
        }
        mock_remove.return_value = True

        response = self.client.delete("/api/programs/prog1/courses/course1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "course1" in data["message"]
        mock_remove.assert_called_once()

    @patch("src.api.routes.programs.get_program_by_id")
    @patch("src.services.auth_service.has_permission")
    def test_remove_course_from_program_not_found(
        self, mock_has_permission, mock_get_program
    ):
        """Test course removal when program not found."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_get_program.return_value = None  # Program not found

        response = self.client.delete("/api/programs/invalid-prog/courses/course1")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "Program not found" in data["error"]

    @patch("src.api.routes.programs.get_program_by_id")
    @patch("src.api.routes.programs.bulk_add_courses_to_program")
    @patch("src.services.auth_service.has_permission")
    def test_bulk_manage_courses_add_action(
        self, mock_has_permission, mock_bulk_add, mock_get_program
    ):
        """Test bulk add courses to program."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_get_program.return_value = {"program_id": "prog1", "name": "CS"}
        mock_bulk_add.return_value = {"success_count": 2, "error_count": 0}

        response = self.client.post(
            "/api/programs/prog1/courses/bulk",
            json={"action": "add", "course_ids": ["c1", "c2"]},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "2 added" in data["message"]
        mock_bulk_add.assert_called_once_with(["c1", "c2"], "prog1")

    @patch("src.api.routes.programs.get_program_by_id")
    @patch("src.api.routes.programs.bulk_remove_courses_from_program")
    @patch("src.services.auth_service.has_permission")
    def test_bulk_manage_courses_remove_action(
        self, mock_has_permission, mock_bulk_remove, mock_get_program
    ):
        """Test bulk remove courses from program."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_get_program.return_value = {"program_id": "prog1", "name": "CS"}
        mock_bulk_remove.return_value = {"removed": 2, "failed": 0}

        response = self.client.post(
            "/api/programs/prog1/courses/bulk",
            json={"action": "remove", "course_ids": ["c1", "c2"]},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "2 removed" in data["message"]
        mock_bulk_remove.assert_called_once_with(["c1", "c2"], "prog1")

    @patch("src.services.auth_service.has_permission")
    def test_bulk_manage_courses_invalid_action(self, mock_has_permission):
        """Test bulk manage with invalid action."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)
        mock_has_permission.return_value = True

        response = self.client.post(
            "/api/programs/prog1/courses/bulk",
            json={"action": "invalid", "course_ids": ["c1"]},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid or missing action" in data["error"]

    @patch("src.services.auth_service.has_permission")
    def test_bulk_manage_courses_missing_course_ids(self, mock_has_permission):
        """Test bulk manage with missing course_ids."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)
        mock_has_permission.return_value = True

        response = self.client.post(
            "/api/programs/prog1/courses/bulk",
            json={"action": "add"},  # Missing course_ids
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Missing or invalid course_ids" in data["error"]


class TestDuplicateCourseEndpoint:
    """Test /api/courses/<course_id>/duplicate endpoint."""

    def get_csrf_token(self, client):
        """Get CSRF token using Flask-WTF's generate_csrf."""
        from flask import session as flask_session
        from flask_wtf.csrf import generate_csrf

        with client.session_transaction() as sess:
            raw_token = sess.get("csrf_token")

        with client.application.test_request_context():
            if raw_token:
                flask_session["csrf_token"] = raw_token
            return generate_csrf()

    @pytest.fixture
    def institution_admin_client(self, client):
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-1",
            "email": "admin@example.com",
            "role": "institution_admin",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        create_test_session(client, user_data)
        return client

    @patch("src.api.routes.courses.get_course_by_id")
    def test_source_course_missing_returns_404(
        self, mock_get_course, institution_admin_client
    ):
        mock_get_course.return_value = None
        response = institution_admin_client.post(
            "/api/courses/c1/duplicate",
            json={},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 404
        assert response.get_json()["success"] is False

    @patch("src.api.routes.courses.get_course_by_id")
    @patch("src.api.utils.get_current_user")
    def test_permission_denied_returns_403(
        self, mock_get_user, mock_get_course, institution_admin_client
    ):
        mock_get_course.return_value = {"course_id": "c1", "institution_id": "inst-999"}
        mock_get_user.return_value = {
            "role": "institution_admin",
            "institution_id": "inst-123",
        }
        response = institution_admin_client.post(
            "/api/courses/c1/duplicate",
            json={},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 403
        assert response.get_json()["error"] == "Permission denied"

    @patch("src.api.routes.courses.duplicate_course_record")
    @patch("src.api.routes.courses.get_course_by_id")
    @patch("src.api.utils.get_current_user")
    def test_duplicate_failure_returns_500(
        self, mock_get_user, mock_get_course, mock_duplicate, institution_admin_client
    ):
        mock_get_course.return_value = {"course_id": "c1", "institution_id": "inst-123"}
        mock_get_user.return_value = {
            "role": "institution_admin",
            "institution_id": "inst-123",
        }
        mock_duplicate.return_value = None
        response = institution_admin_client.post(
            "/api/courses/c1/duplicate",
            json={"program_ids": ["p1"], "duplicate_programs": False},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Failed to duplicate course"

    @patch("src.api.routes.courses.duplicate_course_record")
    @patch("src.api.routes.courses.get_course_by_id")
    @patch("src.api.utils.get_current_user")
    def test_duplicate_success_returns_201(
        self, mock_get_user, mock_get_course, mock_duplicate, institution_admin_client
    ):
        mock_get_user.return_value = {
            "role": "institution_admin",
            "institution_id": "inst-123",
        }
        mock_get_course.side_effect = [
            {"course_id": "c1", "institution_id": "inst-123"},
            {
                "course_id": "new-1",
                "institution_id": "inst-123",
                "course_number": "CS101-V2",
            },
        ]
        mock_duplicate.return_value = "new-1"

        response = institution_admin_client.post(
            "/api/courses/c1/duplicate",
            json={"program_ids": ["p1"], "duplicate_programs": False},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["course"]["course_id"] == "new-1"
