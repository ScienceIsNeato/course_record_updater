"""Unit tests for user API routes (migrated from test_api_routes.py)."""

import json
import os
from unittest.mock import patch

import pytest

from src.app import app
from tests.test_utils import CommonAuthMixin

TEST_PASSWORD = os.environ.get(
    "TEST_PASSWORD", "SecurePass123!"
)  # Test password for unit tests only


class TestUserEndpoints(CommonAuthMixin):
    """Test user management endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("src.api.routes.users.get_all_users", return_value=[])
    def test_get_users_endpoint_exists(self, mock_get_all_users):
        """Test that GET /api/users endpoint exists and returns valid JSON."""
        self._login_user()

        response = self.client.get("/api/users")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "users" in data
        assert isinstance(data["users"], list)
        mock_get_all_users.assert_called_once_with("inst-123")

    @patch("src.api.routes.users.get_users_by_role")
    def test_get_users_with_department_filter(self, mock_get_users):
        """Test GET /api/users with department filter"""
        self._login_site_admin(
            {"user_id": "test-user", "institution_id": "test-institution"}
        )
        mock_get_users.return_value = [
            {
                "user_id": "1",
                "email": "math1@example.com",
                "department": "MATH",
                "role": "instructor",
                "institution_id": "test-institution",
            },
            {
                "user_id": "2",
                "email": "cs1@example.com",
                "department": "CS",
                "role": "instructor",
                "institution_id": "test-institution",
            },
            {
                "user_id": "3",
                "email": "math2@example.com",
                "department": "MATH",
                "role": "instructor",
                "institution_id": "test-institution",
            },
        ]

        response = self.client.get("/api/users?role=instructor&department=MATH")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["users"]) == 2  # Should filter to only MATH department
        for user in data["users"]:
            assert user["department"] == "MATH"

    @patch("src.api.routes.users.get_users_by_role")
    def test_get_users_exception_handling(self, mock_get_users):
        """Test GET /api/users exception handling"""
        self._login_user()
        mock_get_users.side_effect = Exception("Database connection failed")

        response = self.client.get("/api/users?role=instructor")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert data["success"] is False
        assert "error" in data

    def test_create_user_no_json_data(self):
        """Test POST /api/users with no JSON data"""
        # Don't create session - test unauthenticated request
        response = self.client.post("/api/users", content_type="application/json")

        # Real auth returns 401 for unauthenticated requests
        assert response.status_code == 401

    def test_create_user_database_failure(self):
        """Test POST /api/users when database creation fails"""
        self._login_site_admin()

        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "instructor",
            "institution_id": "inst-123",  # Required for non-site_admin roles
            "password": "TestPass123!",
        }

        # Mock database failure
        with patch("src.api.routes.users.create_user_db", return_value=None):
            response = self.client.post(
                "/api/users", json=user_data, content_type="application/json"
            )
            # Real API returns 500 on database failure
            assert response.status_code == 500

            data = json.loads(response.data)
            assert data["success"] is False
            assert "error" in data

    def test_create_user_exception_handling(self):
        """Test POST /api/users with exception"""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data_session = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data_session)

        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "instructor",
            "institution_id": "inst-123",  # Required for non-site_admin roles
            "password": "TestPass123!",
        }

        # Mock database exception
        with patch(
            "src.api.routes.users.create_user_db", side_effect=Exception("DB Error")
        ):
            response = self.client.post(
                "/api/users", json=user_data, content_type="application/json"
            )
            # Real API returns 500 on exception
            assert response.status_code == 500

            data = json.loads(response.data)
            assert data["success"] is False

    @patch("src.api.routes.users.get_all_users", return_value=[])
    def test_get_users_without_permission_stub_mode(self, mock_get_all_users):
        """Test GET /api/users in stub mode (auth always passes)."""
        self._login_site_admin()

        response = self.client.get("/api/users")
        # Should succeed in stub mode, but return empty list
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "users" in data
        mock_get_all_users.assert_called_once_with("inst-123")

    @patch("src.api.routes.users.get_users_by_role")
    def test_get_users_with_role_filter(self, mock_get_users):
        """Test GET /api/users with role filter."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data)
        mock_get_users.return_value = [
            {"user_id": "1", "email": "instructor@example.com", "role": "instructor"}
        ]

        response = self.client.get("/api/users?role=instructor")
        assert response.status_code == 200

        # Verify the role filter was applied
        mock_get_users.assert_called_with("instructor")

    def test_create_user_success(self):
        """Test POST /api/users with valid data."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data_session = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data_session)

        user_data = {
            "email": "newuser@example.com",
            "role": "instructor",
            "first_name": "New",
            "last_name": "User",
            "institution_id": "inst-123",  # Required for non-site_admin roles
            "password": "TestPass123!",  # Provide password for immediate activation
        }

        response = self.client.post(
            "/api/users", json=user_data, content_type="application/json"
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "message" in data
        assert "created" in data["message"].lower()
        assert "user_id" in data  # Real API returns actual user_id

    def test_create_user_missing_required_fields(self):
        """Test POST /api/users with missing required fields."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data_session = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data_session)

        incomplete_data = {
            "email": "incomplete@example.com"
            # Missing role
        }

        response = self.client.post(
            "/api/users", json=incomplete_data, content_type="application/json"
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "required" in data["error"].lower()


class TestUserManagementAPI:
    """Test user management API endpoints comprehensively."""

    def setup_method(self):
        """Set up test client and mock data."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "test-user",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }

    def _login_site_admin(self, overrides=None):
        """Authenticate requests as a site admin user."""
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.get_users_by_role")
    @patch("src.api.routes.users.has_permission")
    def test_list_users_with_role_filter(
        self,
        mock_has_permission,
        mock_get_users,
        mock_get_current_user,
        mock_get_institution_id,
    ):
        """Test listing users with role filter."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "test-user",
            "role": "site_admin",
        }
        mock_get_institution_id.return_value = "test-institution"
        mock_get_users.return_value = [
            {
                "user_id": "1",
                "email": "instructor1@mocku.test",
                "role": "instructor",
                "institution_id": "test-institution",
            },
            {
                "user_id": "2",
                "email": "instructor2@mocku.test",
                "role": "instructor",
                "institution_id": "test-institution",
            },
        ]

        response = self.client.get("/api/users?role=instructor")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["users"]) == 2
        mock_get_users.assert_called_once_with("instructor")

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.get_users_by_role")
    @patch("src.api.routes.users.has_permission")
    def test_list_users_with_department_filter(
        self,
        mock_has_permission,
        mock_get_users,
        mock_get_current_user,
        mock_get_institution_id,
    ):
        """Test listing users with department filter."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "test-user",
            "role": "site_admin",
        }
        mock_get_institution_id.return_value = "test-institution"
        mock_get_users.return_value = [
            {
                "user_id": "1",
                "email": "math1@mocku.test",
                "role": "instructor",
                "department": "MATH",
                "institution_id": "test-institution",
            },
            {
                "user_id": "2",
                "email": "eng1@mocku.test",
                "role": "instructor",
                "department": "ENG",
                "institution_id": "test-institution",
            },
        ]

        response = self.client.get("/api/users?role=instructor&department=MATH")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 1
        assert data["users"][0]["department"] == "MATH"

    @patch("src.api.routes.users.has_permission")
    def test_create_user_validation(self, mock_has_permission):
        """Test create user with validation."""
        self._login_site_admin()
        mock_has_permission.return_value = True

        # Test with no JSON data
        response = self.client.post("/api/users")
        # May return 500 if permission decorator fails, 400 if it gets to validation
        assert response.status_code in [400, 500]

        # Test missing required fields
        response = self.client.post("/api/users", json={"email": "test@mocku.test"})
        assert response.status_code == 400
        data = response.get_json()
        assert "First Name is required" in data["error"]

    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_get_user_permission_denied(
        self, mock_has_permission, mock_get_current_user
    ):
        """Test user trying to access other user's details without permission."""
        self._login_site_admin({"user_id": "user123", "role": "instructor"})
        mock_get_current_user.return_value = {"user_id": "user123"}
        mock_has_permission.return_value = False

        response = self.client.get("/api/users/other_user")

        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == "Permission denied"


class TestUserCreationPermissionValidation:
    """Test _validate_user_creation_permissions function."""

    def test_program_admin_cannot_create_site_admin(self):
        """Test that program admin cannot create site admin accounts."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "site_admin", "institution_id": "mock_university"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Program admins can only create instructor accounts"
                in json_data["error"]
            )

    def test_program_admin_cannot_create_institution_admin(self):
        """Test that program admin cannot create institution admin accounts."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "institution_admin", "institution_id": "mock_university"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Program admins can only create instructor accounts"
                in json_data["error"]
            )

    def test_program_admin_cannot_create_program_admin(self):
        """Test that program admin cannot create other program admin accounts."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "program_admin", "institution_id": "mock_university"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Program admins can only create instructor accounts"
                in json_data["error"]
            )

    def test_program_admin_requires_institution_id(self):
        """Test that program admin must provide institution_id when creating instructors."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {
            "role": "instructor"
            # Missing institution_id
        }

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 400
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert "institution_id is required" in json_data["error"]

    def test_program_admin_cannot_create_at_different_institution(self):
        """Test that program admin can only create users at their own institution."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "instructor", "institution_id": "different_institution"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Program admins can only create users at their own institution"
                in json_data["error"]
            )

    def test_program_admin_can_create_instructor_at_own_institution(self):
        """Test that program admin can create instructors at their own institution."""
        from src.api.routes.users import _validate_user_creation_permissions

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "instructor", "institution_id": "mock_university"}

        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )

        assert is_valid is True
        assert error_response is None

    def test_institution_admin_cannot_create_site_admin(self):
        """Test that institution admin cannot create site admin accounts."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {
            "role": "institution_admin",
            "institution_id": "mock_university",
        }
        data = {"role": "site_admin", "institution_id": "mock_university"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Institution admins cannot create site admin accounts"
                in json_data["error"]
            )

    def test_institution_admin_can_create_institution_admin(self):
        """Test that institution admin can create other institution admins."""
        from src.api.routes.users import _validate_user_creation_permissions

        current_user = {
            "role": "institution_admin",
            "institution_id": "mock_university",
        }
        data = {"role": "institution_admin", "institution_id": "mock_university"}

        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )

        assert is_valid is True
        assert error_response is None

    def test_site_admin_can_create_any_role(self):
        """Test that site admin can create users of any role."""
        from src.api.routes.users import _validate_user_creation_permissions

        current_user = {"role": "site_admin", "institution_id": None}

        # Test creating site_admin
        data = {"role": "site_admin", "institution_id": "mock_university"}
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        assert is_valid is True
        assert error_response is None

        # Test creating institution_admin
        data = {"role": "institution_admin", "institution_id": "mock_university"}
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        assert is_valid is True
        assert error_response is None

        # Test creating program_admin
        data = {"role": "program_admin", "institution_id": "mock_university"}
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        assert is_valid is True
        assert error_response is None

        # Test creating instructor
        data = {"role": "instructor", "institution_id": "mock_university"}
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        assert is_valid is True
        assert error_response is None


class TestUpdateUserRoleEndpoint:
    """Test /api/users/<user_id>/role endpoint."""

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

    @patch("src.api.utils.get_current_institution_id")
    def test_missing_role_returns_400(self, mock_get_inst, institution_admin_client):
        mock_get_inst.return_value = "inst-123"
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "Role is required"

    @patch("src.api.utils.get_current_institution_id")
    def test_invalid_role_returns_400(self, mock_get_inst, institution_admin_client):
        mock_get_inst.return_value = "inst-123"
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "site_admin"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 400
        assert response.get_json()["success"] is False
        assert "Invalid role" in response.get_json()["error"]

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.get_user_by_id")
    def test_user_not_found_returns_404(
        self, mock_get_user, mock_get_inst, institution_admin_client
    ):
        mock_get_inst.return_value = "inst-123"
        mock_get_user.return_value = None
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "instructor"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "User not found"

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.get_user_by_id")
    def test_institution_mismatch_returns_404(
        self, mock_get_user, mock_get_inst, institution_admin_client
    ):
        mock_get_inst.return_value = "inst-123"
        mock_get_user.return_value = {"user_id": "u1", "institution_id": "inst-999"}
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "instructor"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "User not found"

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.update_user_role")
    @patch("src.api.routes.users.get_user_by_id")
    def test_update_failure_returns_500(
        self, mock_get_user, mock_update_role, mock_get_inst, institution_admin_client
    ):
        mock_get_inst.return_value = "inst-123"
        mock_get_user.return_value = {"user_id": "u1", "institution_id": "inst-123"}
        mock_update_role.return_value = False
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "instructor"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Failed to update role"

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.update_user_role")
    @patch("src.api.routes.users.get_user_by_id")
    def test_success_returns_200(
        self, mock_get_user, mock_update_role, mock_get_inst, institution_admin_client
    ):
        mock_get_inst.return_value = "inst-123"
        mock_get_user.side_effect = [
            {"user_id": "u1", "institution_id": "inst-123"},
            {"user_id": "u1", "institution_id": "inst-123", "role": "instructor"},
        ]
        mock_update_role.return_value = True
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "instructor"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert "User role updated" in payload["message"]
