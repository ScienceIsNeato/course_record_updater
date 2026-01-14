"""
Unit tests for Adapter API endpoints.
Tests /api/adapters and /api/export/data.
"""

from unittest.mock import Mock, patch

from src.app import app
from tests.test_utils import create_test_session


class TestAdapterEndpoints:

    def setup_method(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("src.adapters.adapter_registry.get_adapter_registry")
    def test_get_available_adapters_success(self, mock_get_registry):
        """Test fetching available adapters."""
        # Setup mock registry
        mock_registry = Mock()
        mock_get_registry.return_value = mock_registry

        mock_registry.get_adapters_for_user.return_value = [
            {
                "id": "csv_v1",
                "name": "CSV Adapter",
                "description": "Exports CSV",
                "supported_formats": [".csv"],
                "data_types": ["courses"],
            }
        ]

        # Authenticate
        create_test_session(
            self.client,
            {"user_id": "u1", "role": "institution_admin", "institution_id": "i1"},
        )

        response = self.client.get("/api/adapters")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["adapters"]) == 1
        assert data["adapters"][0]["id"] == "csv_v1"
        assert data["adapters"][0]["supported_formats"] == [".csv"]

    def test_get_available_adapters_unauthorized(self):
        """Test fetching adapters without login."""
        response = self.client.get("/api/adapters")
        assert response.status_code == 401  # API returns 401, not 302

    @patch("src.api_routes._export_all_institutions")
    def test_export_data_site_admin(self, mock_export_all):
        """Test site admin export delegates to _export_all_institutions."""
        create_test_session(
            self.client,
            {"user_id": "admin", "role": "site_admin", "email": "admin@test.com"},
        )

        # Mock what _export_all_institutions returns (Response object or tuple)
        mock_export_all.return_value = "ZIP RESPONSE"

        response = self.client.get("/api/export/data")

        # Verify call
        mock_export_all.assert_called_once()

    @patch("src.api_routes.create_export_service")
    def test_export_data_institution_admin_success(self, mock_create_service):
        """Test export data for institution admin."""
        create_test_session(
            self.client,
            {
                "user_id": "u1",
                "role": "institution_admin",
                "institution_id": "i1",
                "email": "user@test.com",
            },
        )

        # Mock service and registry
        mock_service = Mock()
        mock_create_service.return_value = mock_service

        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {"supported_formats": [".xlsx"]}
        mock_service.registry.get_adapter_by_id.return_value = mock_adapter

        # Mock export_data result
        mock_result = Mock()
        mock_result.success = True
        mock_result.records_exported = 10
        mock_service.export_data.return_value = mock_result

        with patch("src.api_routes.send_file") as mock_send_file:
            # Need to mock Path.exists/unlink or just ensure execution flow
            mock_send_file.return_value = "FILE RESPONSE"

            # Note: The code creates a temp file. Mocking send_file prevents reading it.
            # But the logic uses 'os' and 'datetime' which we might need to be careful with.
            # However, for this test, simply calling it triggers the logic paths.
            response = self.client.get(
                "/api/export/data?export_adapter=excel&export_data_type=courses"
            )

            assert response.status_code == 200

            # Verify adapter lookup
            mock_service.registry.get_adapter_by_id.assert_called_with("excel")

            # Verify export call
            mock_service.export_data.assert_called_once()

    def test_export_data_missing_institution_context(self):
        """Test export fails if user has no institution ID."""
        create_test_session(
            self.client,
            {
                "user_id": "u1",
                "role": "instructor",
                # No institution_id
                "email": "user@test.com",
            },
        )

        response = self.client.get("/api/export/data")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        # Update assertion to match actual error message
        assert "Institution context required" in data["error"]

    @patch("src.api_routes.create_export_service")
    def test_export_data_adapter_not_found(self, mock_create_service):
        """Test export fails if adapter is invalid."""
        create_test_session(
            self.client,
            {"user_id": "u1", "role": "institution_admin", "institution_id": "i1"},
        )

        mock_service = Mock()
        mock_create_service.return_value = mock_service
        mock_service.registry.get_adapter_by_id.return_value = None

        response = self.client.get("/api/export/data?export_adapter=bad_adapter")

        assert response.status_code == 400
        data = response.get_json()
        assert "Adapter not found" in data["error"]


class TestExportHelpers:
    """Test hidden export helper functions for coverage."""

    def test_create_system_manifest(self):
        """Test manifest creation."""
        from src.api_routes import _create_system_manifest

        manifest = _create_system_manifest(
            current_user={"email": "admin@test.com"},
            timestamp="20250101",
            adapter_id="csv",
            data_type="courses",
            institutions=[{"institution_id": "i1"}],
            institution_results=[{"success": True}, {"success": False}],
        )

        assert manifest["exported_by"] == "admin@test.com"
        assert manifest["successful_exports"] == 1
        assert manifest["failed_exports"] == 1
        assert manifest["total_institutions"] == 1

    @patch("src.api_routes._DEFAULT_EXPORT_EXTENSION", ".csv")
    def test_get_adapter_file_extension(self):
        """Test extension resolution."""
        from src.api_routes import _get_adapter_file_extension

        mock_service = Mock()
        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {"supported_formats": [".json"]}

        # Case 1: Adapter found
        mock_service.registry.get_adapter_by_id.return_value = mock_adapter
        ext = _get_adapter_file_extension(mock_service, "json_adapter")
        assert ext == ".json"

        # Case 2: Adapter not found
        mock_service.registry.get_adapter_by_id.return_value = None
        ext = _get_adapter_file_extension(mock_service, "unknown")
        assert ext == ".csv"

    @patch("src.api_routes.get_all_institutions")
    @patch("src.api_routes._create_system_export_zip")
    @patch("src.api_routes.send_file")
    @patch("src.api_routes.create_export_service")
    def test_export_all_institutions_flow(
        self, mock_create_service, mock_send_file, mock_create_zip, mock_get_insts
    ):
        """Test the logic within _export_all_institutions."""
        from src.api_routes import _export_all_institutions

        # Setup mocks
        mock_get_insts.return_value = [{"institution_id": "i1", "short_name": "inst1"}]
        mock_create_zip.return_value = "/tmp/test.zip"

        # Export service mock
        mock_service = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.errors = []  # JSON serializable list, not Mock
        mock_result.records_exported = 10
        mock_service.export_data.return_value = mock_result
        mock_create_service.return_value = mock_service

        # Mock shutil to prevent actual file ops if needed, but the code uses Path
        # We rely on mocks avoiding real FS writes deep down
        with patch("shutil.rmtree") as mock_rmtree:
            with app.test_request_context("/?export_adapter=csv"):
                response = _export_all_institutions({"email": "admin@test.com"})

                # Verify steps
                mock_get_insts.assert_called_once()
                mock_create_zip.assert_called_once()
                mock_send_file.assert_called_once()
                # Verify cleanup happened (rmtree called on temp dir)
                # Note: valid flow calls rmtree in 'finally' or after zip?
                # Actually _export_all_institutions uses a try/finally or similar?
                # Let's check code. It cleans up system_export_dir.
                mock_rmtree.assert_called()
