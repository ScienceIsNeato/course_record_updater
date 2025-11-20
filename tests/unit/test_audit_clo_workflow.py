"""Unit tests for CLO audit workflow filtering and export."""

import json
from unittest.mock import MagicMock, patch

import pytest

from api.routes.clo_workflow import get_clos_for_audit
from app import app
from clo_workflow_service import CLOWorkflowService


@pytest.fixture
def mock_get_current_institution_id():
    with patch("api.routes.clo_workflow.get_current_institution_id") as mock:
        mock.return_value = "inst-1"
        yield mock


@pytest.fixture
def mock_get_current_user():
    with patch("api.routes.clo_workflow.get_current_user") as mock:
        mock.return_value = {"role": "institution_admin", "user_id": "user-1"}
        yield mock


@pytest.fixture
def mock_clo_service():
    with patch("api.routes.clo_workflow.CLOWorkflowService") as mock:
        yield mock


@pytest.fixture
def mock_get_term_by_name():
    with patch("api.routes.clo_workflow.get_term_by_name") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_permission_required():
    """Mock permission_required to bypass auth checks."""
    with patch("auth_service.permission_required") as mock:
        # Create a pass-through decorator
        def side_effect(permission):
            def decorator(f):
                return f

            return decorator

        mock.side_effect = side_effect
        yield mock


def test_get_clos_for_audit_with_term_id(
    mock_get_current_institution_id, mock_get_current_user, mock_clo_service
):
    """Test filtering CLOs by term_id."""
    with app.test_request_context("/api/outcomes/audit?term_id=term-1"):
        mock_clo_service.get_clos_by_status.return_value = []

        response, status_code = get_clos_for_audit()

        assert status_code == 200
        mock_clo_service.get_clos_by_status.assert_called_once_with(
            status="awaiting_approval",
            institution_id="inst-1",
            program_id=None,
            term_id="term-1",
        )


def test_get_clos_for_audit_with_term_name(
    mock_get_current_institution_id,
    mock_get_current_user,
    mock_clo_service,
    mock_get_term_by_name,
):
    """Test filtering CLOs by term_name (resolves to term_id)."""
    mock_get_term_by_name.return_value = {"term_id": "term-resolved"}

    with app.test_request_context("/api/outcomes/audit?term_name=Fall 2024"):
        mock_clo_service.get_clos_by_status.return_value = []

        response, status_code = get_clos_for_audit()

        assert status_code == 200

        mock_get_term_by_name.assert_called_once_with("Fall 2024", "inst-1")

        mock_clo_service.get_clos_by_status.assert_called_once_with(
            status="awaiting_approval",
            institution_id="inst-1",
            program_id=None,
            term_id="term-resolved",
        )


def test_get_clos_for_audit_with_program_filter(
    mock_get_current_institution_id, mock_get_current_user, mock_clo_service
):
    """Test filtering CLOs by program_id."""
    with app.test_request_context("/api/outcomes/audit?program_id=prog-1"):
        mock_clo_service.get_clos_by_status.return_value = []

        response, status_code = get_clos_for_audit()

        assert status_code == 200
        mock_clo_service.get_clos_by_status.assert_called_once_with(
            status="awaiting_approval",
            institution_id="inst-1",
            program_id="prog-1",
            term_id=None,
        )
