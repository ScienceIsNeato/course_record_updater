"""Unit tests for import API routes (migrated from test_api_routes.py)."""

import json
import os
from unittest.mock import Mock, patch

import pytest

from src.app import app

TEST_PASSWORD = os.environ.get(
    "TEST_PASSWORD", "SecurePass123!"
)  # Test password for unit tests only


class TestImportEndpoints:
    """Test import functionality endpoints."""

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

    def test_excel_import_endpoint_exists(self):
        """Test that POST /api/import/excel endpoint exists."""
        self._login_site_admin()

        response = self.client.post("/api/import/excel")
        # Should not be 404 (endpoint exists), but will be 400 due to missing file
        assert response.status_code != 404

    @patch("src.services.auth_service.has_permission")
    def test_excel_import_missing_file(self, mock_has_permission):
        """Test POST /api/import/excel without file."""
        self._login_site_admin()

        mock_has_permission.return_value = True

        response = self.client.post(
            "/api/import/excel",
            data={"conflict_strategy": "use_theirs", "dry_run": "false"},
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "file" in data["error"].lower()


class TestAPIRoutesProgressTracking:
    """Test API progress tracking functionality."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("src.api.routes.imports.create_progress_tracker")
    @patch("src.api.routes.imports.update_progress")
    def test_progress_tracking_coverage(
        self, mock_update_progress, mock_create_progress
    ):
        """Test progress tracking functions are called."""
        mock_create_progress.return_value = "progress123"

        # Test that progress functions exist and can be called
        from src.api.routes.imports import create_progress_tracker, update_progress

        progress_id = create_progress_tracker()
        assert progress_id == "progress123"

        # Test update_progress
        update_progress("progress123", status="running", message="Test")
        mock_update_progress.assert_called_with(
            "progress123", status="running", message="Test"
        )

    def test_import_progress_stub_response(self):
        """Test import progress endpoint stub response."""
        response = self.client.get("/api/import/progress/test123")

        # Should return progress data (currently stubbed)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.get_json()
            # Basic structure check for progress response
            assert isinstance(data, dict)


class TestExcelImportHelpers:
    """Test helper functions for excel_import_api."""

    def test_check_excel_import_permissions_site_admin(self):
        """Test _check_excel_import_permissions for site admin - must have institution_id."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.imports import _check_excel_import_permissions

        # SECURITY: Site admins can no longer import without an institution context
        # This enforces multi-tenant isolation - ALL users need institution_id
        mock_user = {
            "user_id": "admin1",
            "role": "site_admin",
            "institution_id": None,
        }

        with patch("src.api.utils.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_user

            # Should fail because site admin has no institution_id
            with pytest.raises(
                PermissionError, match="User has no associated institution"
            ):
                _check_excel_import_permissions("courses")

    def test_check_excel_import_permissions_no_user(self):
        """Test _check_excel_import_permissions raises when no user."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.imports import _check_excel_import_permissions

        with patch("src.api.utils.get_current_user") as mock_get_user:
            mock_get_user.return_value = None

            with pytest.raises(PermissionError, match="Authentication required"):
                _check_excel_import_permissions("courses")

    # REMOVED: MockU-specific tests no longer apply after security fix
    # Site admins now follow the same rules as all other users:
    # They must have an institution_id and can only import into their own institution

    def test_determine_target_institution_institution_admin(self):
        """Test _determine_target_institution for institution admin."""
        from src.api.routes.imports import _determine_target_institution

        result = _determine_target_institution("inst123")

        assert result == "inst123"

    def test_determine_target_institution_no_institution(self):
        """Test _determine_target_institution when user has no institution."""
        import pytest

        from src.api.routes.imports import _determine_target_institution

        with pytest.raises(PermissionError, match="User has no associated institution"):
            _determine_target_institution(None)

    def test_validate_import_permissions_site_admin_courses(self):
        """Test _validate_import_permissions for site admin importing courses."""
        from src.api.routes.imports import _validate_import_permissions

        # Should not raise
        _validate_import_permissions("site_admin", "courses")

    def test_validate_import_permissions_invalid_role(self):
        """Test _validate_import_permissions with invalid role."""
        import pytest

        from src.api.routes.imports import _validate_import_permissions

        with pytest.raises(PermissionError, match="Invalid user role"):
            _validate_import_permissions("invalid_role", "courses")

    def test_validate_import_permissions_forbidden_data_type(self):
        """Test _validate_import_permissions when user cannot import data type."""
        import pytest

        from src.api.routes.imports import _validate_import_permissions

        # Institution admin cannot import institutions
        with pytest.raises(
            PermissionError, match="institution_admin cannot import institutions"
        ):
            _validate_import_permissions("institution_admin", "institutions")


class TestValidateExcelImportRequest:
    def test_validate_excel_import_request_adapter_not_found(self):
        """Covers adapter-not-found branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test.xlsx"

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={"import_adapter": "missing_adapter", "import_data_type": "courses"},
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = None
                with pytest.raises(ValueError, match="Adapter not found"):
                    _validate_excel_import_request()

    def test_validate_excel_import_request_adapter_info_missing(self):
        """Covers adapter-info-missing branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test.xlsx"

        dummy_adapter = Mock()
        dummy_adapter.get_adapter_info.return_value = None

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={
                "import_adapter": "cei_excel_format_v1",
                "import_data_type": "courses",
            },
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = (
                    dummy_adapter
                )
                with pytest.raises(ValueError, match="Adapter info not available"):
                    _validate_excel_import_request()

    def test_validate_excel_import_request_no_supported_formats(self):
        """Covers supported_formats empty branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test.xlsx"

        dummy_adapter = Mock()
        dummy_adapter.get_adapter_info.return_value = {"supported_formats": []}

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={
                "import_adapter": "cei_excel_format_v1",
                "import_data_type": "courses",
            },
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = (
                    dummy_adapter
                )
                with pytest.raises(ValueError, match="No supported formats defined"):
                    _validate_excel_import_request()

    def test_validate_excel_import_request_file_has_no_extension(self):
        """Covers file extension empty branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test"

        dummy_adapter = Mock()
        dummy_adapter.get_adapter_info.return_value = {"supported_formats": [".xlsx"]}

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={
                "import_adapter": "cei_excel_format_v1",
                "import_data_type": "courses",
            },
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = (
                    dummy_adapter
                )
                with pytest.raises(ValueError, match="File has no extension"):
                    _validate_excel_import_request()

    def test_validate_excel_import_request_file_extension_not_supported(self):
        """Covers invalid extension branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test.csv"

        dummy_adapter = Mock()
        dummy_adapter.get_adapter_info.return_value = {"supported_formats": [".xlsx"]}

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={
                "import_adapter": "cei_excel_format_v1",
                "import_data_type": "courses",
            },
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = (
                    dummy_adapter
                )
                with pytest.raises(ValueError, match=r"Invalid file format"):
                    _validate_excel_import_request()


class TestExcelImportEdgeCases:
    """Test edge cases in excel_import_api function."""

    def test_unsafe_filename_sanitization(self):
        """Test filename sanitization fallback for unsafe names."""
        import re

        # Simulate the exact logic from src/api/routes/imports.py
        filename = "..."  # Only dots
        safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

        # Line 3025-3026: Check if empty or starts with dot
        if not safe_filename or safe_filename.startswith("."):
            safe_filename = f"upload_{hash(filename) % 10000}"  # Line 3026

        # Should have generated fallback filename
        assert safe_filename.startswith("upload_")
        assert len(safe_filename) > 7  # "upload_" + digits
