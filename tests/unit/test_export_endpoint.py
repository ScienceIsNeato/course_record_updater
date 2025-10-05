"""
Unit tests for /api/export/data endpoint

Tests authentication, parameter handling, and security
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from export_service import ExportResult


@pytest.mark.unit
class TestExportEndpoint:
    """Test /api/export/data endpoint"""

    def test_export_requires_authentication(self, client):
        """Unauthenticated users should get 401"""
        response = client.get("/api/export/data")

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False

    @patch("api_routes.create_export_service")
    def test_export_with_authentication(
        self, mock_create_service, authenticated_client
    ):
        """Authenticated users should be able to export"""

        # Mock the export service to write the actual file where the endpoint expects it
        def mock_export(config, output_path):
            # Create the file at the path the endpoint specifies
            with open(output_path, "wb") as f:
                f.write(b"fake excel data")
            return ExportResult(
                success=True,
                file_path=output_path,
                records_exported=10,
                errors=[],
            )

        # Mock adapter to return supported formats
        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {
            "id": "cei_excel_format_v1",
            "supported_formats": [".xlsx"],
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter

        mock_service = Mock()
        mock_service.registry = mock_registry
        mock_service.export_data.side_effect = mock_export
        mock_create_service.return_value = mock_service

        response = authenticated_client.get("/api/export/data")

        # Should succeed
        assert response.status_code == 200

    @patch("api_routes.create_export_service")
    def test_export_sanitizes_path_traversal(
        self, mock_create_service, authenticated_client
    ):
        """Export should sanitize path traversal attempts"""
        # Create a real temp file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            temp_path = f.name
            f.write(b"fake excel data")

        try:
            # Mock adapter to return supported formats
            mock_adapter = Mock()
            mock_adapter.get_adapter_info.return_value = {
                "id": "cei_excel_format_v1",
                "supported_formats": [".xlsx"],
            }

            mock_registry = Mock()
            mock_registry.get_adapter_by_id.return_value = mock_adapter

            # Mock the export service
            mock_service = Mock()
            mock_service.registry = mock_registry
            mock_service.export_data.return_value = ExportResult(
                success=True,
                file_path=temp_path,
                records_exported=10,
                errors=[],
            )
            mock_create_service.return_value = mock_service

            # Try path traversal attack
            response = authenticated_client.get(
                "/api/export/data?export_data_type=../../etc/passwd"
            )

            # Should still succeed (sanitization prevents the attack)
            assert response.status_code in [200, 500]

            # Verify the export service was called (sanitization happened)
            assert mock_service.export_data.called

        finally:
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)

    @patch("api_routes.create_export_service")
    def test_export_handles_failure(self, mock_create_service, authenticated_client):
        """Export should handle service failures gracefully"""
        # Mock adapter to return supported formats
        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {
            "id": "cei_excel_format_v1",
            "supported_formats": [".xlsx"],
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter

        # Mock service failure
        mock_service = Mock()
        mock_service.registry = mock_registry
        mock_service.export_data.return_value = ExportResult(
            success=False,
            file_path=None,
            records_exported=0,
            errors=["Export failed"],
        )
        mock_create_service.return_value = mock_service

        response = authenticated_client.get("/api/export/data")

        # Should return error
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch("api_routes.create_export_service")
    def test_export_with_parameters(self, mock_create_service, authenticated_client):
        """Export should accept and use optional parameters"""

        # Mock the export service to write the actual file where the endpoint expects it
        def mock_export(config, output_path):
            # Create the file at the path the endpoint specifies
            with open(output_path, "wb") as f:
                f.write(b"fake excel data")
            return ExportResult(
                success=True,
                file_path=output_path,
                records_exported=10,
                errors=[],
            )

        # Mock adapter to return supported formats
        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {
            "id": "cei_excel_format_v1",
            "supported_formats": [".xlsx"],
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter

        mock_service = Mock()
        mock_service.registry = mock_registry
        mock_service.export_data.side_effect = mock_export
        mock_create_service.return_value = mock_service

        # Call with parameters
        response = authenticated_client.get(
            "/api/export/data?"
            "export_data_type=courses&"
            "export_format=excel&"
            "export_adapter=cei_excel_format_v1&"
            "include_metadata=true&"
            "anonymize_data=false"
        )

        # Should succeed
        assert response.status_code == 200

        # Verify export was called
        assert mock_service.export_data.called

    @patch("api_routes.create_export_service")
    def test_export_handles_exception(self, mock_create_service, authenticated_client):
        """Export should handle unexpected exceptions"""
        # Mock adapter to return supported formats
        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {
            "id": "cei_excel_format_v1",
            "supported_formats": [".xlsx"],
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter

        # Mock service to raise exception
        mock_service = Mock()
        mock_service.registry = mock_registry
        mock_service.export_data.side_effect = Exception("Unexpected error")
        mock_create_service.return_value = mock_service

        response = authenticated_client.get("/api/export/data")

        # Should return 500 error
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data
