"""
Integration tests to fill coverage gaps identified in E2E API audit.

These tests cover API-level scenarios that were previously only tested via
E2E tests with direct API calls. By moving them to integration tests, we:
1. Remove browser overhead (faster tests)
2. Keep E2E tests focused on UI workflows
3. Maintain comprehensive API coverage

See E2E_API_AUDIT.md for rationale and mapping to original E2E tests.
"""

from unittest.mock import patch

import pytest

from app import app
from tests.test_utils import CommonAuthMixin, create_test_session


def get_csrf_token(client):
    """Get CSRF token using Flask-WTF's generate_csrf."""
    from flask import session as flask_session
    from flask_wtf.csrf import generate_csrf

    # Get the raw token from the session (created by create_test_session)
    with client.session_transaction() as sess:
        raw_token = sess.get("csrf_token")

    # Generate the signed token from the raw token
    with client.application.test_request_context():
        if raw_token:
            flask_session["csrf_token"] = raw_token
        return generate_csrf()


class TestProgramDeletionScenarios(CommonAuthMixin):
    """Test program deletion scenarios: empty programs vs programs with courses"""

    def setup_method(self):
        """Set up test fixtures"""
        import database_service as db

        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Create test institution for this test
        self.institution_id = db.create_institution(
            {
                "name": "Test Institution",
                "short_name": "TEST",
                "admin_email": "admin@test.edu",
                "website_url": "https://test.edu",
                "created_by": "test-user",
            }
        )

        # Login with test institution ID
        self._login_institution_admin({"institution_id": self.institution_id})

        # Note: Default program is automatically created with institution

        # Create an empty program for deletion test
        self.empty_program_id = db.create_program(
            {
                "name": "Empty Test Program",
                "institution_id": self.institution_id,
            }
        )

        # Create a program with courses
        self.program_with_courses_id = db.create_program(
            {
                "name": "Program With Courses",
                "institution_id": self.institution_id,
            }
        )

        # Create a course linked to the second program
        course_id = db.create_course(
            {
                "course_number": "TEST-101",
                "course_title": "Test Course",
                "credits": 3,
                "institution_id": self.institution_id,
                "program_ids": [self.program_with_courses_id],
            }
        )
        self.test_course_id = course_id

    def test_delete_empty_program_success_200(self):
        """
        Test that deleting an empty program (no courses) succeeds with 200.

        Covers: test_tc_crud_ia_003_delete_empty_program (E2E)
        """
        response = self.client.delete(
            f"/api/programs/{self.empty_program_id}",
            headers={"X-CSRFToken": get_csrf_token(self.client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_delete_program_with_courses_fails_referential_integrity(self):
        """
        Test that deleting a program with courses fails with 400/409.

        Validates referential integrity constraint.
        Covers: test_tc_crud_ia_004_cannot_delete_program_with_courses (E2E)
        """
        response = self.client.delete(
            f"/api/programs/{self.program_with_courses_id}",
            headers={"X-CSRFToken": get_csrf_token(self.client)},
        )

        # Should return 400 or 409 (conflict/constraint violation)
        assert response.status_code in [400, 409]
        data = response.get_json()
        assert data["success"] is False
        # Error message should mention courses/constraint
        error_text = data.get("message", "") + data.get("error", "")
        assert "course" in error_text.lower() or "cannot" in error_text.lower()


class TestRoleHierarchyUserDeletion(CommonAuthMixin):
    """Test that users cannot delete users with higher or equal privilege levels"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def _login_program_admin(self, overrides=None):
        """Helper to login as program admin"""
        defaults = {
            "user_id": "prog-admin-123",
            "email": "prog-admin@test.com",
            "role": "program_admin",
            "institution_id": "inst-123",
            "program_ids": ["prog-1", "prog-2"],
        }
        user_data = {**defaults}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("database_service.delete_user")
    @patch("database_service.get_user_by_id")
    @patch("auth_service.auth_service.has_permission")
    @patch("auth_service.auth_service.get_current_user")
    def test_program_admin_cannot_delete_higher_role_user_403(
        self, mock_current_user, mock_has_perm, mock_get_user, mock_delete
    ):
        """
        Test that program admin cannot delete institution admin (higher role).

        Validates role hierarchy in user deletion.
        Covers: test_tc_crud_pa_003_cannot_delete_institution_user (E2E)
        """
        # Login as program admin
        self._login_program_admin()

        # Mock current user (program admin)
        mock_current_user.return_value = {
            "user_id": "prog-admin-1",
            "role": "program_admin",
            "institution_id": "inst-1",
            "program_ids": ["prog-1"],
        }

        # Mock target user (institution admin - higher role)
        mock_get_user.return_value = {
            "user_id": "inst-admin-1",
            "email": "admin@inst.test",
            "role": "institution_admin",
            "institution_id": "inst-1",
        }

        # Mock permission check - should deny
        mock_has_perm.return_value = False

        response = self.client.delete(
            "/api/users/inst-admin-1",
            headers={"X-CSRFToken": get_csrf_token(self.client)},
        )

        # Should return 403 Forbidden
        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False

        # Verify deletion was never attempted
        mock_delete.assert_not_called()

    @patch("database_service.delete_user")
    @patch("database_service.get_user_by_id")
    @patch("auth_service.auth_service.has_permission")
    @patch("auth_service.auth_service.get_current_user")
    def test_program_admin_cannot_delete_equal_role_user_403(
        self, mock_current_user, mock_has_perm, mock_get_user, mock_delete
    ):
        """
        Test that program admin cannot delete another program admin (equal role).

        Validates that users cannot delete peers at same privilege level.
        """
        # Login as program admin
        self._login_program_admin()

        # Mock current user (program admin)
        mock_current_user.return_value = {
            "user_id": "prog-admin-1",
            "role": "program_admin",
            "institution_id": "inst-1",
            "program_ids": ["prog-1"],
        }

        # Mock target user (another program admin - equal role)
        mock_get_user.return_value = {
            "user_id": "prog-admin-2",
            "email": "other@inst.test",
            "role": "program_admin",
            "institution_id": "inst-1",
            "program_ids": ["prog-2"],
        }

        # Mock permission check - should deny
        mock_has_perm.return_value = False

        response = self.client.delete(
            "/api/users/prog-admin-2",
            headers={"X-CSRFToken": get_csrf_token(self.client)},
        )

        # Should return 403 Forbidden
        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False

        # Verify deletion was never attempted
        mock_delete.assert_not_called()


class TestInvitationAPI(CommonAuthMixin):
    """Test invitation creation API"""

    def setup_method(self):
        """Set up test fixtures"""
        import database_service as db

        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Create test institution for this test
        self.institution_id = db.create_institution(
            {
                "name": "Test Institution",
                "short_name": "TEST",
                "admin_email": "admin@test.edu",
                "website_url": "https://test.edu",
                "created_by": "test-user",
            }
        )

        # Login with test institution ID
        self._login_institution_admin({"institution_id": self.institution_id})

    def test_create_invitation_success_201(self):
        """
        Test that institution admin can create invitation successfully.

        Covers: test_tc_crud_ia_005_invite_instructor (E2E)
        """
        # Use timestamp for unique email to avoid conflicts
        import time

        timestamp = int(time.time() * 1000)
        invitation_data = {
            "email": f"newinstructor{timestamp}@inst.test",
            "first_name": "New",
            "last_name": "Instructor",
            "role": "instructor",
        }

        response = self.client.post(
            "/api/invitations",
            json=invitation_data,
            headers={"X-CSRFToken": get_csrf_token(self.client)},
        )

        assert response.status_code in [200, 201]
        data = response.get_json()
        assert data["success"] is True

    def test_create_invitation_duplicate_email_fails_400(self):
        """
        Test that creating invitation with duplicate email fails.

        Validates email uniqueness constraint.
        """
        # Create first invitation
        invitation_data = {
            "email": "duplicate@inst.test",
            "first_name": "First",
            "last_name": "User",
            "role": "instructor",
        }

        response1 = self.client.post(
            "/api/invitations",
            json=invitation_data,
            headers={"X-CSRFToken": get_csrf_token(self.client)},
        )
        assert response1.status_code in [200, 201]  # First one should succeed

        # Try to create duplicate
        response2 = self.client.post(
            "/api/invitations",
            json=invitation_data,
            headers={"X-CSRFToken": get_csrf_token(self.client)},
        )

        assert response2.status_code == 400
        data = response2.get_json()
        assert data["success"] is False
        # Check for email-related error in either message or error field
        error_text = data.get("message", "") + data.get("error", "")
        assert (
            "email" in error_text.lower()
            or "duplicate" in error_text.lower()
            or "already" in error_text.lower()
        )


class TestHealthEndpoint:
    """Smoke test for health endpoint"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_health_endpoint_returns_200(self):
        """
        Test that health endpoint returns 200 OK.

        This is infrastructure validation, not a user workflow.
        Covers: test_health_endpoint (E2E) - moved to smoke tests
        """
        response = self.client.get("/api/health")

        assert response.status_code == 200
        data = response.get_json()
        # Health endpoint should return some status indicator
        assert data is not None
        # Common health check patterns
        assert (
            data.get("status") == "healthy"
            or data.get("status") == "ok"
            or "health" in str(data).lower()
        )

    def test_health_endpoint_no_authentication_required(self):
        """
        Test that health endpoint doesn't require authentication.

        Health checks need to work for monitoring systems.
        """
        # Don't login - test unauthenticated access
        response = self.client.get("/api/health")

        # Should still return 200 (health checks are public)
        assert response.status_code == 200
