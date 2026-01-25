"""
Unit tests for Site Admin system-wide export functionality

Tests the _export_all_institutions function with various scenarios
to achieve complete coverage of all code paths.
"""

import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.services.export_service import ExportResult


@pytest.mark.unit
class TestSiteAdminExport:
    """Test Site Admin system-wide export function

    Tests now run safely in parallel thanks to UUID-based temporary directory
    naming that prevents collisions (fixed in api_routes.py).
    """

    @patch("src.api.routes.data_export.get_all_institutions")
    @patch("src.api.routes.data_export.create_export_service")
    def test_site_admin_export_adapter_not_found(
        self, mock_create_service, mock_get_institutions, client
    ):
        """Test Site Admin export when adapter is not found"""
        # Create site admin session
        with client.session_transaction() as sess:
            sess["user_id"] = "test-site-admin"
            sess["email"] = "admin@system.local"
            sess["role"] = "site_admin"
            sess["institution_id"] = None
            sess["program_ids"] = []
            sess["display_name"] = "Site Admin"
            sess["created_at"] = "2024-01-01T00:00:00Z"

        # Mock institutions
        mock_get_institutions.return_value = [
            {"institution_id": "inst1", "name": "Institution 1", "short_name": "I1"},
        ]

        # Mock registry returning None for adapter
        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = None

        mock_service = Mock()
        mock_service.registry = mock_registry
        mock_create_service.return_value = mock_service

        # Call export as site admin
        response = client.get(
            "/api/export/data?export_adapter=nonexistent_adapter&export_data_type=courses"
        )

        # Should return 400
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Adapter not found" in data["error"]

    @patch("src.api.routes.data_export.get_all_institutions")
    @patch("src.api.routes.data_export.create_export_service")
    def test_site_admin_export_adapter_info_exception(
        self, mock_create_service, mock_get_institutions, client
    ):
        """Test Site Admin export when get_adapter_info raises exception"""
        # Create site admin session
        with client.session_transaction() as sess:
            sess["user_id"] = "test-site-admin"
            sess["email"] = "admin@system.local"
            sess["role"] = "site_admin"
            sess["institution_id"] = None
            sess["program_ids"] = []
            sess["display_name"] = "Site Admin"
            sess["created_at"] = "2024-01-01T00:00:00Z"

        # Mock institutions
        mock_get_institutions.return_value = [
            {"institution_id": "inst1", "name": "Institution 1", "short_name": "I1"},
        ]

        # Mock adapter that raises exception on get_adapter_info
        mock_adapter = Mock()
        mock_adapter.get_adapter_info.side_effect = Exception("Adapter info failed")

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter

        def mock_export(config, output_path):
            # Create fake export file
            with open(output_path, "wb") as f:
                f.write(b"fake export data")
            return ExportResult(
                success=True,
                file_path=str(output_path),
                records_exported=5,
                errors=[],
            )

        mock_service = Mock()
        mock_service.registry = mock_registry
        mock_service.export_data.side_effect = mock_export
        mock_create_service.return_value = mock_service

        # Call export as site admin - should fall back to default extension
        response = client.get(
            "/api/export/data?export_adapter=generic_csv_v1&export_data_type=courses"
        )

        # Should succeed with fallback
        assert response.status_code == 200

    @patch("src.api.routes.data_export.get_all_institutions")
    @patch("src.api.routes.data_export.create_export_service")
    def test_site_admin_export_partial_failure(
        self, mock_create_service, mock_get_institutions, client
    ):
        """Test Site Admin export when one institution export fails"""
        # Create site admin session
        with client.session_transaction() as sess:
            sess["user_id"] = "test-site-admin"
            sess["email"] = "admin@system.local"
            sess["role"] = "site_admin"
            sess["institution_id"] = None
            sess["program_ids"] = []
            sess["display_name"] = "Site Admin"
            sess["created_at"] = "2024-01-01T00:00:00Z"

        # Mock institutions
        mock_get_institutions.return_value = [
            {"institution_id": "inst1", "name": "Institution 1", "short_name": "I1"},
            {"institution_id": "inst2", "name": "Institution 2", "short_name": "I2"},
        ]

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {
            "id": "generic_csv_v1",
            "supported_formats": [".zip"],
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter

        # Mock export - first succeeds, second fails
        call_count = [0]

        def mock_export(config, output_path):
            call_count[0] += 1
            # Create fake export file
            with open(output_path, "wb") as f:
                f.write(b"fake export data")

            if call_count[0] == 1:
                return ExportResult(
                    success=True,
                    file_path=str(output_path),
                    records_exported=5,
                    errors=[],
                )
            else:
                return ExportResult(
                    success=False,
                    file_path=str(output_path),
                    records_exported=0,
                    errors=["Export failed for institution 2"],
                )

        mock_service = Mock()
        mock_service.registry = mock_registry
        mock_service.export_data.side_effect = mock_export
        mock_create_service.return_value = mock_service

        # Call export as site admin
        response = client.get(
            "/api/export/data?export_adapter=generic_csv_v1&export_data_type=courses"
        )

        # Should still succeed and create ZIP with partial results
        assert response.status_code == 200
        assert response.content_type == "application/zip"

        # Verify ZIP contains expected files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp.write(response.data)
            tmp_path = Path(tmp.name)

        try:
            with zipfile.ZipFile(tmp_path, "r") as zf:
                # Should have system_manifest.json and at least one institution export
                files = zf.namelist()
                assert "system_manifest.json" in files
        finally:
            tmp_path.unlink()

    @patch("src.api.routes.data_export.get_all_institutions")
    @patch("src.api.routes.data_export.create_export_service")
    def test_site_admin_export_default_adapter(
        self, mock_create_service, mock_get_institutions, client
    ):
        """Test Site Admin export uses default adapter when needed"""
        # Create site admin session
        with client.session_transaction() as sess:
            sess["user_id"] = "test-site-admin"
            sess["email"] = "admin@system.local"
            sess["role"] = "site_admin"
            sess["institution_id"] = None
            sess["program_ids"] = []
            sess["display_name"] = "Site Admin"
            sess["created_at"] = "2024-01-01T00:00:00Z"

        # Mock institutions
        mock_get_institutions.return_value = [
            {"institution_id": "inst1", "name": "Institution 1", "short_name": "I1"},
        ]

        # Mock adapter - any adapter ID will return this
        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {
            "id": "generic_csv_v1",
            "supported_formats": [".zip"],
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter

        def mock_export(config, output_path):
            # Create fake export file
            with open(output_path, "wb") as f:
                f.write(b"fake export data")
            return ExportResult(
                success=True,
                file_path=str(output_path),
                records_exported=5,
                errors=[],
            )

        mock_service = Mock()
        mock_service.registry = mock_registry
        mock_service.export_data.side_effect = mock_export
        mock_create_service.return_value = mock_service

        # Call with default parameters (no explicit adapter)
        response = client.get("/api/export/data?export_data_type=courses")

        # Should succeed with default adapter
        assert response.status_code == 200

    @patch("src.api.routes.data_export.get_all_institutions")
    @patch("src.api.routes.data_export.create_export_service")
    def test_site_admin_export_general_exception(
        self, mock_create_service, mock_get_institutions, client
    ):
        """Test Site Admin export handles general exceptions gracefully"""
        # Create site admin session
        with client.session_transaction() as sess:
            sess["user_id"] = "test-site-admin"
            sess["email"] = "admin@system.local"
            sess["role"] = "site_admin"
            sess["institution_id"] = None
            sess["program_ids"] = []
            sess["display_name"] = "Site Admin"
            sess["created_at"] = "2024-01-01T00:00:00Z"

        # Mock institutions to raise an exception
        mock_get_institutions.side_effect = Exception("Database error")

        # Call export as site admin
        response = client.get(
            "/api/export/data?export_adapter=generic_csv_v1&export_data_type=courses"
        )

        # Should return 500
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data
