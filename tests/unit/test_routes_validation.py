"""Unit tests for validation API routes (migrated from test_api_routes.py)."""

import os
from io import BytesIO
from unittest.mock import patch

import pytest

from src.app import app
from src.utils.constants import USER_NOT_FOUND_MSG

TEST_PASSWORD = os.environ.get(
    "TEST_PASSWORD", "SecurePass123!"
)  # Test password for unit tests only


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_method_not_allowed(self):
        """Test method not allowed responses."""
        with app.test_client() as client:
            # Try DELETE on an endpoint that doesn't support it
            response = client.delete("/api/health")
            assert response.status_code == 405

    def test_api_endpoints_return_json(self):
        """Test that API endpoints return JSON responses."""
        with app.test_client() as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.content_type.startswith("application/json")


class TestRequestValidation:
    """Test request data validation."""

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

    @patch("src.services.auth_service.has_permission")
    def test_course_creation_validation(self, mock_has_permission):
        """Test course creation with various validation scenarios."""
        self._login_site_admin()

        mock_has_permission.return_value = True

        # Test missing required field
        invalid_course = {
            "course_title": "Test Course"
            # Missing course_number
        }

        response = self.client.post(
            "/api/courses", json=invalid_course, content_type="application/json"
        )
        assert response.status_code == 400

    @patch("src.services.auth_service.has_permission")
    def test_term_creation_validation(self, mock_has_permission):
        """Test term creation with date validation."""
        self._login_site_admin()

        mock_has_permission.return_value = True

        # Test invalid date format
        invalid_term = {
            "term_name": "InvalidTerm",
            "start_date": "invalid-date",
            "end_date": "2024-12-15",
        }

        response = self.client.post(
            "/api/terms", json=invalid_term, content_type="application/json"
        )
        assert response.status_code == 400


class TestAPIRoutesErrorHandling:
    """Test API routes error handling and edge cases."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.api.routes.users.get_all_users", return_value=[])
    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_list_users_no_role_filter_coverage(
        self,
        mock_has_permission,
        mock_get_current_user,
        mock_get_mocku_id,
        mock_get_all_users,
    ):
        """Test list_users endpoint without role filter."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "test-user",
            "role": "site_admin",
        }
        mock_get_mocku_id.return_value = "riverside-tech-institute"

        response = self.client.get("/api/users")

        assert response.status_code == 200
        data = response.get_json()
        assert data["users"] == []
        mock_get_all_users.assert_called_once_with("riverside-tech-institute")

    @patch("src.api.routes.users.get_user_by_id", return_value=None)
    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_get_user_not_found_coverage(
        self,
        mock_has_permission,
        mock_get_current_user,
        mock_get_mocku_id,
        mock_get_user,
    ):
        """Test get_user endpoint when user not found."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_get_current_user.return_value = {
            "user_id": "admin-user",
            "role": "site_admin",
        }
        mock_has_permission.return_value = True
        mock_get_mocku_id.return_value = "riverside-tech-institute"

        response = self.client.get("/api/users/nonexistent-user")

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == USER_NOT_FOUND_MSG
        mock_get_user.assert_called_once_with("nonexistent-user")

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_create_user_stub_success_coverage(
        self, mock_has_permission, mock_get_current_user, mock_get_mocku_id
    ):
        """Test create_user endpoint with real implementation."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "admin-user",
            "role": "site_admin",
        }
        mock_get_mocku_id.return_value = "riverside-tech-institute"

        user_data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": "instructor",
            "institution_id": "riverside-tech-institute",  # Required for non-site_admin roles
            "password": "TestPass123!",
        }

        response = self.client.post("/api/users", json=user_data)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "user_id" in data  # Real API returns actual user_id

    def test_import_excel_empty_filename_coverage(self):
        """Test import_excel endpoint with empty filename."""
        self._login_site_admin()

        with patch("src.services.auth_service.has_permission", return_value=True):
            from io import BytesIO

            data = {"excel_file": (BytesIO(b"test"), "")}

            response = self.client.post("/api/import/excel", data=data)

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No file selected"

    # REMOVED: test_import_excel_invalid_file_type_coverage
    # Legacy test for hardcoded file type validation that was removed in greenfield refactor.
    # File type validation is now handled by adapters via supported_formats declaration.

    @patch("src.api.routes.imports._check_excel_import_permissions")
    @patch("src.services.auth_service.has_permission")
    def test_import_excel_permission_error(self, mock_has_permission, mock_check_perms):
        """Test import_excel endpoint with PermissionError."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_check_perms.side_effect = PermissionError(
            "User has no associated institution"
        )

        from io import BytesIO

        data = {"excel_file": (BytesIO(b"test"), "test.xlsx")}

        response = self.client.post("/api/import/excel", data=data)

        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False
        assert "User has no associated institution" in data["error"]

    @patch("src.api.routes.users._resolve_users_scope")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_list_users_value_error(
        self,
        mock_has_permission,
        mock_get_current_user,
        mock_resolve_scope,
    ):
        """Test list_users with ValueError from scope resolution."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = self.site_admin_user
        mock_resolve_scope.side_effect = ValueError("Invalid scope")

        response = self.client.get("/api/users")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid scope" in data["error"]


class TestAPIRoutesValidation:
    """Test API validation endpoints."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.services.auth_service.has_permission")
    @patch("src.api.routes.imports.import_excel")
    @patch("src.api.utils.get_current_institution_id")
    def test_validate_import_file_coverage(
        self, mock_get_institution_id, mock_import_excel, mock_has_permission
    ):
        """Test import file validation endpoint."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_institution_id.return_value = "test-institution"

        # Mock import result
        from src.services.import_service import ImportResult

        mock_result = ImportResult(
            success=True,
            records_processed=10,
            records_created=8,
            records_updated=2,
            records_skipped=0,
            conflicts_detected=0,
            conflicts_resolved=0,
            errors=[],
            warnings=[],
            conflicts=[],
            dry_run=True,
            execution_time=1.0,
        )
        mock_import_excel.return_value = mock_result

        # Test with valid Excel file
        from io import BytesIO

        data = {"excel_file": (BytesIO(b"test excel data"), "test.xlsx")}

        response = self.client.post("/api/import/validate", data=data)

        # Should validate the file
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "validation" in data

    def test_validate_import_no_file(self):
        """Test validation endpoint with no file."""
        self._login_site_admin()

        with patch("src.services.auth_service.has_permission", return_value=True):
            response = self.client.post("/api/import/validate")

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No Excel file provided"

    def test_validate_import_empty_filename(self):
        """Test validation endpoint with empty filename."""
        self._login_site_admin()

        with patch("src.services.auth_service.has_permission", return_value=True):
            from io import BytesIO

            data = {"excel_file": (BytesIO(b"test"), "")}

            response = self.client.post("/api/import/validate", data=data)

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No file selected"

    # REMOVED: test_validate_import_invalid_file_type
    # Legacy test for hardcoded file type validation that was removed in greenfield refactor.
    # File type validation is now handled by adapters via supported_formats declaration.

    @patch("src.services.auth_service.has_permission")
    @patch("src.api.routes.imports.import_excel")
    @patch("os.unlink")
    @patch("src.api.utils.get_current_institution_id")
    def test_validate_import_cleanup_error(
        self,
        mock_get_institution_id,
        mock_unlink,
        mock_import_excel,
        mock_has_permission,
    ):
        """Test validation endpoint cleanup error handling."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_institution_id.return_value = "test-institution"
        mock_unlink.side_effect = OSError("Permission denied")

        # Mock import result
        from src.services.import_service import ImportResult

        mock_result = ImportResult(
            success=True,
            records_processed=5,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            conflicts_detected=0,
            conflicts_resolved=0,
            errors=[],
            warnings=[],
            conflicts=[],
            dry_run=True,
            execution_time=1.0,
        )
        mock_import_excel.return_value = mock_result

        from io import BytesIO

        data = {"excel_file": (BytesIO(b"excel data"), "test.xlsx")}

        response = self.client.post("/api/import/validate", data=data)

        # Should still succeed despite cleanup error
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
