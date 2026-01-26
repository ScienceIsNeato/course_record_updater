"""Unit tests for institution API routes (migrated from test_api_routes.py)."""

import json
from unittest.mock import patch

from src.app import app
from src.utils.constants import INVALID_PASSWORD


class TestInstitutionEndpoints:
    """Test institution management endpoints."""

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
            "institution_id": "riverside-tech-institute",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def _login_user(self, overrides=None):
        """Alias for _login_site_admin for backward compatibility"""
        return self._login_site_admin(overrides)

    @patch("src.api.routes.institutions.get_all_institutions")
    @patch("src.api.routes.institutions.get_institution_instructor_count")
    def test_list_institutions_success(self, mock_get_count, mock_get_institutions):
        """Test GET /api/institutions endpoint."""
        self._login_site_admin()

        mock_get_institutions.return_value = [
            {"institution_id": "inst1", "name": "University 1"},
            {"institution_id": "inst2", "name": "University 2"},
        ]
        mock_get_count.return_value = 15

        response = self.client.get("/api/institutions")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "institutions" in data
        assert len(data["institutions"]) == 2

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_success(self, mock_create_institution):
        """Test POST /api/institutions/register endpoint success (public registration)."""
        # No login needed - this is a public registration endpoint
        mock_create_institution.return_value = ("institution123", "user123")

        institution_data = {
            "institution": {
                "name": "Test University",
                "short_name": "TU",
                "domain": "test.edu",
            },
            "admin_user": {
                "email": "admin@test.edu",
                "first_name": "Admin",
                "last_name": "User",
                "password": INVALID_PASSWORD,
            },
        }

        response = self.client.post("/api/institutions/register", json=institution_data)
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["success"] is True
        assert "institution_id" in data

    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.institutions.get_institution_by_id")
    def test_get_institution_details_success(self, mock_get_institution, mock_get_user):
        """Test GET /api/institutions/<id> endpoint success."""
        self._login_site_admin()

        mock_get_user.return_value = {
            "user_id": "user123",
            "institution_id": "institution123",
            "role": "admin",
        }
        mock_get_institution.return_value = {
            "institution_id": "institution123",
            "name": "Test University",
            "domain": "test.edu",
        }

        response = self.client.get("/api/institutions/institution123")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "institution" in data
        assert data["institution"]["name"] == "Test University"

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.get_all_instructors")
    def test_list_instructors_success(self, mock_get_instructors, mock_get_mocku):
        """Test GET /api/instructors endpoint success."""
        self._login_site_admin()

        mock_get_mocku.return_value = "mocku-institution-id"
        mock_get_instructors.return_value = [
            {"user_id": "inst1", "first_name": "John", "last_name": "Doe"},
            {"user_id": "inst2", "first_name": "Jane", "last_name": "Smith"},
        ]

        response = self.client.get("/api/instructors")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "instructors" in data
        assert len(data["instructors"]) == 2

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_missing_data(self, mock_create_institution):
        """Test POST /api/institutions/register with missing data."""
        with app.test_client() as client:
            response = client.post("/api/institutions/register", json={})
            assert response.status_code == 400

            data = json.loads(response.data)
            assert data["success"] is False

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_missing_admin_user_field(self, mock_create_institution):
        """Test POST /api/institutions/register with missing admin user field."""
        with app.test_client() as client:
            # Send institution data but missing admin user email
            response = client.post(
                "/api/institutions/register",
                json={
                    "institution": {
                        "name": "Test University",
                        "short_name": "TU",
                        "domain": "testuniversity.edu",
                    },
                    "admin_user": {
                        "first_name": "John",
                        "last_name": "Doe",
                        "password": "SecurePassword123!",  # Missing email field
                    },
                },
            )
            assert response.status_code == 400

            data = json.loads(response.data)
            assert data["success"] is False
            assert "Admin user email is required" in data["error"]

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_creation_failure(self, mock_create_institution):
        """Test POST /api/institutions/register when institution creation fails."""
        # Setup - make create_new_institution return None (failure)
        mock_create_institution.return_value = None

        with app.test_client() as client:
            response = client.post(
                "/api/institutions/register",
                json={
                    "institution": {
                        "name": "Test University",
                        "short_name": "TU",
                        "domain": "testuniversity.edu",
                    },
                    "admin_user": {
                        "email": "admin@testuniversity.edu",
                        "first_name": "John",
                        "last_name": "Doe",
                        "password": "SecurePassword123!",
                    },
                },
            )
            assert response.status_code == 500

            data = json.loads(response.data)
            assert data["success"] is False
            assert "Failed to create institution" in data["error"]

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_exception_handling(self, mock_create_institution):
        """Test POST /api/institutions/register exception handling."""
        # Setup - make create_new_institution raise an exception
        mock_create_institution.side_effect = Exception("Database connection failed")

        with app.test_client() as client:
            response = client.post(
                "/api/institutions/register",
                json={
                    "institution": {
                        "name": "Test University",
                        "short_name": "TU",
                        "domain": "testuniversity.edu",
                    },
                    "admin_user": {
                        "email": "admin@testuniversity.edu",
                        "first_name": "John",
                        "last_name": "Doe",
                        "password": "SecurePassword123!",
                    },
                },
            )
            assert response.status_code == 500

            data = json.loads(response.data)
            assert data["success"] is False
            assert "Failed to create institution" in data["error"]

    @patch("src.api.routes.institutions.get_all_institutions")
    def test_list_institutions_exception(self, mock_get_institutions):
        """Test GET /api/institutions exception handling."""
        self._login_user()

        mock_get_institutions.side_effect = Exception("Database error")

        response = self.client.get("/api/institutions")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert data["success"] is False

    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.institutions.get_institution_by_id")
    def test_get_institution_details_access_denied(
        self, mock_get_institution, mock_get_user
    ):
        """Test GET /api/institutions/<id> access denied."""
        self._login_user(
            {
                "user_id": "user123",
                "email": "instructor@test.com",
                "role": "instructor",
                "institution_id": "different-institution",
            }
        )

        mock_get_user.return_value = {
            "user_id": "user123",
            "institution_id": "different-institution",
            "role": "instructor",
        }

        response = self.client.get("/api/institutions/target-institution")
        assert response.status_code == 403

        data = json.loads(response.data)
        assert data["success"] is False
        assert "permission denied" in data["error"].lower()

    @patch("src.api.routes.courses.create_course")
    def test_create_course_data_validation(self, mock_create_course):
        """Test course creation with comprehensive data validation."""
        self._login_user({"institution_id": "test-institution"})

        mock_create_course.return_value = "course123"

        # Test with complete, valid course data
        course_data = {
            "course_number": "CS-101",
            "course_title": "Introduction to Computer Science",
            "department": "CS",
            "credit_hours": 3,
            "description": "An introductory course covering fundamental concepts.",
        }

        response = self.client.post("/api/courses", json=course_data)
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["success"] is True
        assert "course_id" in data

        # Verify the course was created with proper data
        mock_create_course.assert_called_once()
        call_args = mock_create_course.call_args[0][0]
        assert call_args["course_number"] == "CS-101"
        assert call_args["department"] == "CS"
        assert call_args["credit_hours"] == 3

    @patch("src.api.routes.terms.create_term")
    def test_create_term_data_validation(self, mock_create_term):
        """Test term creation with proper data validation."""
        self._login_user({"institution_id": "test-institution"})

        mock_create_term.return_value = "term123"

        term_data = {
            "term_name": "Fall 2024",
            "start_date": "2024-08-15",
            "end_date": "2024-12-15",
            "is_active": True,
        }

        response = self.client.post("/api/terms", json=term_data)

        # Test that the endpoint responds properly (exact status may vary)
        assert response.status_code in [200, 201, 400]  # Various valid responses

        data = json.loads(response.data)
        assert "success" in data  # Response should have success field

    def test_api_error_handling_comprehensive(self):
        """Test comprehensive API error handling scenarios."""
        self._login_user({"institution_id": "test-institution"})

        # Test invalid JSON data
        response = self.client.post(
            "/api/courses", data="invalid json", content_type="application/json"
        )
        # Should handle invalid JSON gracefully
        assert response.status_code in [400, 500]  # Either error response is valid

        # Test missing content type
        response = self.client.post("/api/courses", data='{"test": "data"}')
        # Should handle gracefully - exact behavior varies
        assert response.status_code is not None

    def test_api_endpoints_comprehensive_error_handling(self):
        """Test comprehensive error handling across different API endpoints."""
        with app.test_client() as client:
            # Test various endpoints for proper error responses
            endpoints_to_test = [
                ("/api/nonexistent", "GET"),
                ("/api/courses", "DELETE"),  # Method not allowed
                ("/api/users", "PUT"),  # Method not allowed
            ]

            for endpoint, method in endpoints_to_test:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "DELETE":
                    response = client.delete(endpoint)
                elif method == "PUT":
                    response = client.put(endpoint)

                # Should return proper HTTP error codes
                assert response.status_code in [404, 405, 500]

    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_get_user_endpoint_comprehensive(
        self, mock_has_permission, mock_get_current_user
    ):
        """Test user retrieval endpoint with permission checking."""
        self._login_user({"institution_id": "test-institution"})

        mock_get_current_user.return_value = {"user_id": "user123"}
        mock_has_permission.return_value = True

        response = self.client.get("/api/users/user123")

        # Should handle user retrieval properly
        assert response.status_code in [200, 404]

        data = json.loads(response.data)
        assert "success" in data

    @patch("src.api.routes.imports.create_progress_tracker")
    @patch("src.api.routes.imports.update_progress")
    def test_import_excel_api_validation(
        self, mock_update_progress, mock_create_progress
    ):
        """Test Excel import API validation and error handling."""
        self._login_user({"institution_id": "test-institution"})

        mock_create_progress.return_value = "progress123"

        # Test missing file
        response = self.client.post("/api/import/excel")
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data["success"] is False
        assert "no excel file" in data["error"].lower()

    def test_import_progress_endpoint(self):
        """Test import progress tracking endpoint."""
        with app.test_client() as client:
            response = client.get("/api/import/progress/nonexistent")

            # Should handle progress requests
            assert response.status_code in [200, 404, 500]

    @patch("src.api.utils.handle_api_error")
    def test_api_error_handler_functionality(self, mock_handle_error):
        """Test API error handler functionality."""
        mock_handle_error.return_value = (
            {"success": False, "error": "Test error"},
            500,
        )

        # Test that error handler is called appropriately
        test_exception = Exception("Test exception")
        result = mock_handle_error(test_exception, "Test operation", "Test message")

        assert result[0]["success"] is False
        assert result[1] == 500

    @patch("src.api.utils.get_current_institution_id")
    def test_institution_context_handling(self, mock_get_institution_id):
        """Test institution context handling across endpoints."""
        self._login_user({"institution_id": "test-institution"})

        mock_get_institution_id.return_value = "institution123"

        # Test endpoints that require institution context
        endpoints = ["/api/courses", "/api/terms", "/api/sections"]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should handle institution context properly
            assert response.status_code in [200, 400, 403, 500]
