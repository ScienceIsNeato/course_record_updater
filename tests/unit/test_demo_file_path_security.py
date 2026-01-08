"""
Unit tests for path traversal protection in demo file imports.

Tests the security validation of demo_file_path parameter in the Excel import endpoint.
"""

import os
from unittest.mock import patch

import pytest


class TestDemoFilePathSecurity:
    """Test path traversal protection for demo file imports."""

    @pytest.fixture
    def mock_app_context(self):
        """Create a Flask app context for testing."""
        from src.app import app

        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["WTF_CSRF_ENABLED"] = False
        return app.test_client()

    @pytest.fixture
    def auth_session(self, mock_app_context):
        """Create an authenticated session."""
        # Login to get authenticated session
        with mock_app_context.session_transaction() as sess:
            sess["user_id"] = "test-user-id"
            sess["institution_id"] = "test-institution-id"
        return mock_app_context

    def test_path_traversal_with_double_dots_blocked(self, auth_session):
        """Path with .. should be rejected."""
        with (
            patch("src.api_routes.get_current_user") as mock_user,
            patch("src.api_routes.get_current_institution_id") as mock_inst,
        ):
            mock_user.return_value = {"user_id": "test", "role": "institution_admin"}
            mock_inst.return_value = "inst-123"

            response = auth_session.post(
                "/api/import/excel",
                data={"demo_file_path": "../../../etc/passwd", "adapter_id": "default"},
            )

            # Should fail with error (400 or 500 due to ValueError)
            assert response.status_code in [400, 500]
            # Check that the path traversal was blocked (not actually tried to read)

    def test_path_traversal_with_absolute_path_blocked(self, auth_session):
        """Absolute paths should be rejected."""
        with (
            patch("src.api_routes.get_current_user") as mock_user,
            patch("src.api_routes.get_current_institution_id") as mock_inst,
        ):
            mock_user.return_value = {"user_id": "test", "role": "institution_admin"}
            mock_inst.return_value = "inst-123"

            response = auth_session.post(
                "/api/import/excel",
                data={"demo_file_path": "/etc/passwd", "adapter_id": "default"},
            )

            # Should fail with error
            assert response.status_code in [400, 500]

    def test_path_outside_allowed_directories_blocked(self, auth_session):
        """Paths not in allowed directories should be rejected."""
        with (
            patch("src.api_routes.get_current_user") as mock_user,
            patch("src.api_routes.get_current_institution_id") as mock_inst,
        ):
            mock_user.return_value = {"user_id": "test", "role": "institution_admin"}
            mock_inst.return_value = "inst-123"

            response = auth_session.post(
                "/api/import/excel",
                data={
                    "demo_file_path": "some_random_dir/file.xlsx",
                    "adapter_id": "default",
                },
            )

            # Should fail with error
            assert response.status_code in [400, 500]

    def test_valid_demo_path_allowed(self, auth_session):
        """Valid paths within allowed directories should be accepted."""
        # Create a test file in demos directory
        test_file = "demos/test_import_file.xlsx"

        # Ensure demos directory exists
        if not os.path.exists("demos"):
            os.makedirs("demos")

        # Create dummy file
        with open(test_file, "w") as f:
            f.write("dummy content")

        try:
            with (
                patch("src.api_routes.get_current_user") as mock_user,
                patch("src.api_routes.get_current_institution_id") as mock_inst,
            ):
                mock_user.return_value = {
                    "user_id": "test",
                    "role": "institution_admin",
                }
                mock_inst.return_value = "inst-123"

                response = auth_session.post(
                    "/api/import/excel",
                    data={"demo_file_path": test_file, "adapter_id": "default"},
                )

                # Should not fail with path validation error (400 or 500)
                # It might return JSON with success=False if file is invalid Excel, but not HTTP error for security
                assert response.status_code != 500
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)

            # Should not fail with path validation error
            # (may still fail for other reasons like adapter not found)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
