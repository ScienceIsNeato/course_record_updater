"""
Unit tests for API utility functions.
"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from werkzeug.exceptions import BadRequest

from src.api.utils import (
    InstitutionContextMissingError,
    get_mimetype_for_extension,
    handle_api_error,
    resolve_institution_scope,
    validate_request_json,
)
from src.services.auth_service import UserRole


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestGetMimetypeForExtension:
    """Tests for get_mimetype_for_extension utility."""

    def test_xlsx_mimetype(self):
        """Test XLSX mimetype."""
        result = get_mimetype_for_extension(".xlsx")
        assert (
            result
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_xls_mimetype(self):
        """Test XLS mimetype."""
        result = get_mimetype_for_extension(".xls")
        assert result == "application/vnd.ms-excel"

    def test_csv_mimetype(self):
        """Test CSV mimetype."""
        result = get_mimetype_for_extension(".csv")
        assert result == "text/csv"

    def test_json_mimetype(self):
        """Test JSON mimetype."""
        result = get_mimetype_for_extension(".json")
        assert result == "application/json"

    def test_unknown_extension_returns_default(self):
        """Test that unknown extensions return default mimetype."""
        result = get_mimetype_for_extension(".unknown")
        assert result == "application/octet-stream"

    def test_case_insensitive(self):
        """Test that extension matching is case-insensitive."""
        result = get_mimetype_for_extension(".XLSX")
        assert (
            result
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


class TestResolveInstitutionScope:
    """Tests for resolve_institution_scope utility."""

    @patch("src.api.utils.get_current_user")
    @patch("src.api.utils.get_current_institution_id")
    def test_resolve_with_institution_context(self, mock_get_inst_id, mock_get_user):
        """Test resolution when institution context is set."""
        mock_user = {"user_id": "user-123", "role": "program_admin"}
        mock_get_user.return_value = mock_user
        mock_get_inst_id.return_value = "inst-123"

        user, inst_ids, is_global = resolve_institution_scope()

        assert user == mock_user
        assert inst_ids == ["inst-123"]
        assert is_global is False

    @patch("src.api.utils.get_current_user")
    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_all_institutions")
    def test_resolve_as_site_admin_without_context(
        self, mock_get_all_inst, mock_get_inst_id, mock_get_user
    ):
        """Test resolution for site admin without institution context."""
        mock_user = {"user_id": "admin-123", "role": UserRole.SITE_ADMIN.value}
        mock_get_user.return_value = mock_user
        mock_get_inst_id.return_value = None
        mock_get_all_inst.return_value = [
            {"institution_id": "inst-1"},
            {"institution_id": "inst-2"},
            {"institution_id": "inst-3"},
        ]

        user, inst_ids, is_global = resolve_institution_scope()

        assert user == mock_user
        assert inst_ids == ["inst-1", "inst-2", "inst-3"]
        assert is_global is True

    @patch("src.api.utils.get_current_user")
    @patch("src.api.utils.get_current_institution_id")
    def test_resolve_without_context_raises_error_when_required(
        self, mock_get_inst_id, mock_get_user
    ):
        """Test that missing context raises error when required."""
        mock_user = {"user_id": "user-123", "role": "program_admin"}
        mock_get_user.return_value = mock_user
        mock_get_inst_id.return_value = None

        with pytest.raises(InstitutionContextMissingError):
            resolve_institution_scope(require=True)

    @patch("src.api.utils.get_current_user")
    @patch("src.api.utils.get_current_institution_id")
    def test_resolve_without_context_returns_empty_when_not_required(
        self, mock_get_inst_id, mock_get_user
    ):
        """Test that missing context returns empty list when not required."""
        mock_user = {"user_id": "user-123", "role": "program_admin"}
        mock_get_user.return_value = mock_user
        mock_get_inst_id.return_value = None

        user, inst_ids, is_global = resolve_institution_scope(require=False)

        assert user == mock_user
        assert inst_ids == []
        assert is_global is False


class TestHandleApiError:
    """Tests for handle_api_error utility."""

    def test_handle_api_error_returns_json_response(self, app):
        """Test that error handler returns proper JSON response."""
        error = ValueError("Test error")

        with app.app_context():
            response, status_code = handle_api_error(
                error, operation_name="Test operation", user_message="Test failed"
            )

            json_data = response.get_json()
            assert json_data["success"] is False
            assert json_data["error"] == "Test failed"
            assert status_code == 500

    def test_handle_api_error_custom_status_code(self, app):
        """Test that custom status code is used."""
        error = ValueError("Test error")

        with app.app_context():
            response, status_code = handle_api_error(
                error,
                operation_name="Test operation",
                user_message="Bad request",
                status_code=400,
            )

            assert status_code == 400

    def test_handle_api_error_default_message(self, app):
        """Test that default message is used when not provided."""
        error = ValueError("Test error")

        with app.app_context():
            response, status_code = handle_api_error(error)

            json_data = response.get_json()
            assert json_data["error"] == "An error occurred"
            assert status_code == 500


class TestValidateRequestJson:
    """Tests for validate_request_json utility."""

    def test_validate_json_success(self, app):
        """Test successful JSON validation."""
        with app.test_request_context(
            "/test", method="POST", json={"field1": "value1", "field2": "value2"}
        ):
            data = validate_request_json()
            assert data == {"field1": "value1", "field2": "value2"}

    def test_validate_json_with_required_fields_success(self, app):
        """Test successful validation with required fields."""
        with app.test_request_context(
            "/test", method="POST", json={"field1": "value1", "field2": "value2"}
        ):
            data = validate_request_json(required_fields=["field1", "field2"])
            assert data == {"field1": "value1", "field2": "value2"}

    def test_validate_json_missing_data(self, app):
        """Test error when no JSON data is provided."""
        with app.test_request_context("/test", method="POST", json={}):
            with pytest.raises(ValueError, match="No JSON data provided"):
                validate_request_json()

    def test_validate_json_missing_required_field(self, app):
        """Test error when required field is missing."""
        with app.test_request_context(
            "/test", method="POST", json={"field1": "value1"}
        ):
            with pytest.raises(ValueError, match="Missing required fields: field2"):
                validate_request_json(required_fields=["field1", "field2"])

    def test_validate_json_multiple_missing_required_fields(self, app):
        """Test error when multiple required fields are missing."""
        with app.test_request_context(
            "/test", method="POST", json={"field1": "value1"}
        ):
            with pytest.raises(
                ValueError, match="Missing required fields: field2, field3"
            ):
                validate_request_json(required_fields=["field1", "field2", "field3"])

    def test_validate_json_empty_field_value(self, app):
        """Test that empty field values are treated as missing."""
        with app.test_request_context(
            "/test", method="POST", json={"field1": "value1", "field2": ""}
        ):
            with pytest.raises(ValueError, match="Missing required fields: field2"):
                validate_request_json(required_fields=["field1", "field2"])
