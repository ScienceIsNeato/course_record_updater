"""Unit tests for CLO workflow API endpoints."""

from unittest.mock import patch

import pytest
from flask import Flask

# Import the blueprint
from api.routes.clo_workflow import clo_workflow_bp


#  Module-level fixture to bypass permission checks for ALL tests in this file
@pytest.fixture(scope="module", autouse=True)
def bypass_permissions():
    """Bypass permission checks for all CLO workflow route tests."""
    with patch(
        "auth_service.permission_required",
        lambda perm, context_keys=None: lambda f: f,
    ):
        yield


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"
    app.config["TESTING"] = True
    app.register_blueprint(clo_workflow_bp)
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


class TestCLOAuditEndpoints:
    """Test CLO audit workflow endpoints."""

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_submit_clo_for_approval_success(
        self,
        mock_get_inst_id,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
    ):
        """Test successfully submitting CLO for approval."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "in_progress",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.submit_clo_for_approval.return_value = True

        # Execute
        response = client.post("/api/outcomes/outcome-1/submit")

        # Verify
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "submitted for approval" in data["message"]

    @patch("api.routes.clo_workflow.get_course_outcome")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_submit_clo_for_approval_not_found(
        self, mock_get_inst_id, mock_get_outcome, client
    ):
        """Test submitting non-existent CLO returns 404."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_outcome.return_value = None

        # Execute
        response = client.post("/api/outcomes/nonexistent/submit")

        # Verify
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    def test_get_clos_for_audit_as_institution_admin(
        self, mock_get_inst_id, mock_get_user, mock_workflow, client
    ):
        """Test getting CLOs for audit as institution admin."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_user.return_value = {
            "id": "user-123",
            "role": "institution_admin",
        }
        mock_workflow.get_clos_by_status.return_value = [
            {"id": "outcome-1", "status": "awaiting_approval"},
            {"id": "outcome-2", "status": "awaiting_approval"},
        ]

        # Execute
        response = client.get("/api/outcomes/audit")

        # Verify
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    def test_get_clos_for_audit_as_program_admin(
        self, mock_get_inst_id, mock_get_user, mock_workflow, client
    ):
        """Test getting CLOs for audit as program admin."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_user.return_value = {
            "id": "user-123",
            "role": "program_admin",
            "program_ids": ["prog-1", "prog-2"],
        }
        mock_workflow.get_clos_by_status.return_value = [
            {"id": "outcome-1", "status": "awaiting_approval"}
        ]

        # Execute
        response = client.get("/api/outcomes/audit?program_id=prog-1")

        # Verify
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_workflow.get_clos_by_status.assert_called_once()

    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    def test_get_clos_for_audit_program_admin_no_programs(
        self, mock_get_inst_id, mock_get_user, client
    ):
        """Test program admin with no programs gets empty list."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_user.return_value = {
            "id": "user-123",
            "role": "program_admin",
            "program_ids": [],
        }

        # Execute
        response = client.get("/api/outcomes/audit")

        # Verify
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 0

    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    def test_get_clos_for_audit_program_admin_wrong_program(
        self, mock_get_inst_id, mock_get_user, client
    ):
        """Test program admin accessing unauthorized program."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_user.return_value = {
            "id": "user-123",
            "role": "program_admin",
            "program_ids": ["prog-1"],
        }

        # Execute
        response = client.get("/api/outcomes/audit?program_id=prog-999")

        # Verify
        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_approve_clo_success(
        self,
        mock_get_inst_id,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
    ):
        """Test successfully approving a CLO."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.approve_clo.return_value = True

        # Execute
        response = client.post("/api/outcomes/outcome-1/approve")

        # Verify
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "approved successfully" in data["message"]

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_request_clo_rework_success(
        self,
        mock_get_inst_id,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
    ):
        """Test successfully requesting CLO rework with feedback."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.request_rework.return_value = True

        # Execute
        response = client.post(
            "/api/outcomes/outcome-1/request-rework",
            json={"comments": "Please clarify the assessment method"},
        )

        # Verify
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_workflow.request_rework.assert_called_once()

    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_request_clo_rework_missing_comments(self, mock_get_inst_id, client):
        """Test requesting rework without comments returns 400."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"

        # Execute
        response = client.post(
            "/api/outcomes/outcome-1/request-rework",
            json={},
        )

        # Verify
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "required" in data["error"]

    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_request_clo_rework_empty_comments(self, mock_get_inst_id, client):
        """Test requesting rework with empty comments returns 400."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"

        # Execute
        response = client.post(
            "/api/outcomes/outcome-1/request-rework",
            json={"comments": "   "},
        )

        # Verify
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "empty" in data["error"]

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_submit_clo_for_approval_service_failure(
        self,
        mock_get_inst_id,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
    ):
        """Test submit CLO when service returns False."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "in_progress",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.submit_clo_for_approval.return_value = False

        # Execute
        response = client.post("/api/outcomes/outcome-1/submit")

        # Verify
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_approve_clo_service_failure(
        self,
        mock_get_inst_id,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
    ):
        """Test approve CLO when service returns False."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.approve_clo.return_value = False

        # Execute
        response = client.post("/api/outcomes/outcome-1/approve")

        # Verify
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    @patch("api.routes.clo_workflow.session", {"user_id": "user-123"})
    def test_request_clo_rework_service_failure(
        self,
        mock_get_inst_id,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
    ):
        """Test request rework when service returns False."""
        # Setup
        mock_get_inst_id.return_value = "inst-123"
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.request_rework.return_value = False

        # Execute
        response = client.post(
            "/api/outcomes/outcome-1/request-rework",
            json={"comments": "Please fix this"},
        )

        # Verify
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
