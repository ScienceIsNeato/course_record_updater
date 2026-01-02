"""Unit tests for CLO workflow API endpoints."""

from unittest.mock import patch

import pytest
from flask import Flask

# Import the blueprint
from src.api.routes.clo_workflow import clo_workflow_bp


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


@pytest.fixture
def mock_institution():
    """Mock institution ID."""
    with patch("api.routes.clo_workflow.get_current_institution_id") as mock:
        mock.return_value = "inst-123"
        yield mock


@pytest.fixture
def mock_session():
    """Mock Flask session."""
    with patch("api.routes.clo_workflow.session", {"user_id": "user-123"}):
        yield


def assert_json_response(response, status_code, success_expected):
    """Helper to verify common JSON response patterns."""
    assert response.status_code == status_code
    data = response.get_json()
    assert data["success"] is success_expected
    return data


class TestCLOAuditEndpoints:
    """Test CLO audit workflow endpoints."""

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_submit_clo_for_approval_success(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test successfully submitting CLO for approval."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "in_progress",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.submit_clo_for_approval.return_value = True

        response = client.post("/api/outcomes/outcome-1/submit")

        data = assert_json_response(response, 200, True)
        assert "submitted for approval" in data["message"]

    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_submit_clo_for_approval_not_found(
        self, mock_get_outcome, client, mock_institution, mock_session
    ):
        """Test submitting non-existent CLO returns 404."""
        mock_get_outcome.return_value = None
        response = client.post("/api/outcomes/nonexistent/submit")
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_submit_clo_for_approval_exception(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test submitting CLO handles unexpected exceptions."""
        mock_get_outcome.return_value = {"id": "outcome-1", "course_id": "course-1"}
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.submit_clo_for_approval.side_effect = Exception(
            "Unexpected error"
        )

        response = client.post("/api/outcomes/outcome-1/submit")
        assert_json_response(response, 500, False)

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
    def test_approve_clo_success(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test successfully approving a CLO."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.approve_clo.return_value = True

        response = client.post("/api/outcomes/outcome-1/approve")

        data = assert_json_response(response, 200, True)
        assert "approved successfully" in data["message"]

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_request_clo_rework_success(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test successfully requesting CLO rework with feedback."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.request_rework.return_value = True

        response = client.post(
            "/api/outcomes/outcome-1/request-rework",
            json={"comments": "Please clarify the assessment method"},
        )

        data = assert_json_response(response, 200, True)
        mock_workflow.request_rework.assert_called_once()

    @pytest.mark.parametrize(
        "comments,expected_error",
        [
            ({}, "required"),
            ({"comments": "   "}, "empty"),
        ],
    )
    def test_request_clo_rework_invalid_comments(
        self, comments, expected_error, client, mock_institution, mock_session
    ):
        """Test requesting rework with missing or empty comments returns 400."""
        response = client.post("/api/outcomes/outcome-1/request-rework", json=comments)
        data = assert_json_response(response, 400, False)
        assert expected_error in data["error"]

    @pytest.mark.parametrize(
        "endpoint,method_name",
        [
            ("/api/outcomes/outcome-1/submit", "submit_clo_for_approval"),
            ("/api/outcomes/outcome-1/approve", "approve_clo"),
        ],
    )
    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_workflow_service_failure(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        endpoint,
        method_name,
        client,
        mock_institution,
        mock_session,
    ):
        """Test CLO workflow endpoints when service returns False."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        getattr(mock_workflow, method_name).return_value = False

        response = client.post(
            endpoint if "rework" not in endpoint else endpoint,
            json={"comments": "Fix"} if "rework" in endpoint else None,
        )
        assert_json_response(response, 500, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_request_clo_rework_service_failure(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test request rework when service returns False."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.request_rework.return_value = False

        response = client.post(
            "/api/outcomes/outcome-1/request-rework",
            json={"comments": "Please fix this"},
        )
        assert_json_response(response, 500, False)

    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_submit_clo_institution_mismatch(
        self,
        mock_get_outcome,
        mock_get_course,
        client,
        mock_institution,
        mock_session,
    ):
        """Test submitting CLO from different institution returns 404."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "in_progress",
        }
        mock_get_course.return_value = {
            "id": "course-1",
            "institution_id": "different-inst",
        }

        response = client.post("/api/outcomes/outcome-1/submit")
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_current_institution_id")
    def test_get_clos_for_audit_exception_handling(
        self, mock_get_inst_id, mock_get_user, mock_workflow, client
    ):
        """Test get_clos_for_audit handles exceptions gracefully."""
        mock_get_inst_id.return_value = "inst-123"
        mock_get_user.return_value = {
            "id": "user-123",
            "role": "institution_admin",
        }
        mock_workflow.get_clos_by_status.side_effect = Exception("Database error")

        response = client.get("/api/outcomes/audit")
        data = assert_json_response(response, 500, False)
        assert "error" in data

    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_approve_clo_not_found(
        self, mock_get_outcome, client, mock_institution, mock_session
    ):
        """Test approving non-existent CLO returns 404."""
        mock_get_outcome.return_value = None
        response = client.post("/api/outcomes/nonexistent/approve")
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_approve_clo_institution_mismatch(
        self,
        mock_get_outcome,
        mock_get_course,
        client,
        mock_institution,
        mock_session,
    ):
        """Test approving CLO from different institution returns 404."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {
            "id": "course-1",
            "institution_id": "different-inst",
        }

        response = client.post("/api/outcomes/outcome-1/approve")
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_approve_clo_exception(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test approving CLO handles unexpected exceptions."""
        mock_get_outcome.return_value = {"id": "outcome-1", "course_id": "course-1"}
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.approve_clo.side_effect = Exception("Unexpected error")

        response = client.post("/api/outcomes/outcome-1/approve")
        assert_json_response(response, 500, False)

    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_request_rework_not_found(
        self, mock_get_outcome, client, mock_institution, mock_session
    ):
        """Test requesting rework on non-existent CLO returns 404."""
        mock_get_outcome.return_value = None
        response = client.post(
            "/api/outcomes/nonexistent/request-rework",
            json={"comments": "Please fix"},
        )
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_request_rework_institution_mismatch(
        self,
        mock_get_outcome,
        mock_get_course,
        client,
        mock_institution,
        mock_session,
    ):
        """Test requesting rework on CLO from different institution returns 404."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {
            "id": "course-1",
            "institution_id": "different-inst",
        }

        response = client.post(
            "/api/outcomes/outcome-1/request-rework",
            json={"comments": "Please fix"},
        )
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_request_rework_exception(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test requesting rework handles unexpected exceptions."""
        mock_get_outcome.return_value = {"id": "outcome-1", "course_id": "course-1"}
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.request_rework.side_effect = Exception("Unexpected error")

        response = client.post(
            "/api/outcomes/outcome-1/request-rework",
            json={"comments": "Please fix"},
        )
        assert_json_response(response, 500, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_mark_nci_success(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_get_user,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test marking CLO as Never Coming In (CEI demo follow-up)."""
        mock_get_user.return_value = {"user_id": "user-123"}
        mock_get_outcome.return_value = {
            "outcome_id": "outcome-1",
            "course_id": "course-1",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.mark_as_nci.return_value = True

        response = client.post(
            "/api/outcomes/outcome-1/mark-nci",
            json={"reason": "Instructor left institution"},
        )
        assert_json_response(response, 200, True)
        assert response.json["message"] == "CLO marked as Never Coming In (NCI)"

    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_mark_nci_not_found(
        self,
        mock_get_outcome,
        mock_get_user,
        client,
        mock_institution,
        mock_session,
    ):
        """Test marking NCI when outcome doesn't exist."""
        mock_get_user.return_value = {"user_id": "user-123"}
        mock_get_outcome.return_value = None

        response = client.post(
            "/api/outcomes/fake-id/mark-nci",
            json={"reason": "Test"},
        )
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_mark_nci_service_fails(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_get_user,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test marking NCI when service method returns False."""
        mock_get_user.return_value = {"user_id": "user-123"}
        mock_get_outcome.return_value = {
            "outcome_id": "outcome-1",
            "course_id": "course-1",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.mark_as_nci.return_value = False

        response = client.post(
            "/api/outcomes/outcome-1/mark-nci",
            json={},
        )
        assert_json_response(response, 500, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_current_user")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_mark_nci_exception(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_get_user,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test marking NCI handles unexpected exceptions."""
        mock_get_user.return_value = {"user_id": "user-123"}
        mock_get_outcome.return_value = {
            "outcome_id": "outcome-1",
            "course_id": "course-1",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.mark_as_nci.side_effect = Exception("Unexpected error")

        response = client.post(
            "/api/outcomes/outcome-1/mark-nci",
            json={"reason": "Test"},
        )
        assert_json_response(response, 500, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_get_clo_audit_details_success(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test successfully getting CLO audit details."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.get_outcome_with_details.return_value = {
            "id": "outcome-1",
            "course_number": "CS101",
            "instructor_name": "Dr. Smith",
            "submission_history": [],
        }

        response = client.get("/api/outcomes/outcome-1/audit-details")

        data = assert_json_response(response, 200, True)
        assert "outcome" in data
        assert data["outcome"]["id"] == "outcome-1"

    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_get_clo_audit_details_not_found(
        self, mock_get_outcome, client, mock_institution, mock_session
    ):
        """Test getting audit details for non-existent CLO returns 404."""
        mock_get_outcome.return_value = None
        response = client.get("/api/outcomes/nonexistent/audit-details")
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_get_clo_audit_details_institution_mismatch(
        self,
        mock_get_outcome,
        mock_get_course,
        client,
        mock_institution,
        mock_session,
    ):
        """Test getting audit details for CLO from different institution returns 404."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {
            "id": "course-1",
            "institution_id": "different-inst",
        }

        response = client.get("/api/outcomes/outcome-1/audit-details")
        assert_json_response(response, 404, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_get_clo_audit_details_service_returns_none(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test getting audit details when service returns None."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.get_outcome_with_details.return_value = None

        response = client.get("/api/outcomes/outcome-1/audit-details")
        assert_json_response(response, 500, False)

    @patch("api.routes.clo_workflow.CLOWorkflowService")
    @patch("api.routes.clo_workflow.get_course_by_id")
    @patch("api.routes.clo_workflow.get_course_outcome")
    def test_get_clo_audit_details_exception_handling(
        self,
        mock_get_outcome,
        mock_get_course,
        mock_workflow,
        client,
        mock_institution,
        mock_session,
    ):
        """Test get_clo_audit_details handles exceptions gracefully."""
        mock_get_outcome.return_value = {
            "id": "outcome-1",
            "course_id": "course-1",
            "status": "awaiting_approval",
        }
        mock_get_course.return_value = {"id": "course-1", "institution_id": "inst-123"}
        mock_workflow.get_outcome_with_details.side_effect = Exception("Database error")

        response = client.get("/api/outcomes/outcome-1/audit-details")
        data = assert_json_response(response, 500, False)
        assert "error" in data
