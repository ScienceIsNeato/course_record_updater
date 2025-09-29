"""
Unit tests for FileBaseAdapter abstract base class
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from adapters.file_base_adapter import (
    AdapterValidationResult,
    FileBaseAdapter,
    FileCompatibilityError,
)


class MockAdapter(FileBaseAdapter):
    """Mock adapter implementation for testing"""

    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        # Simple mock: accept .txt files, reject others
        if file_path.endswith(".txt"):
            return True, "Mock adapter accepts .txt files"
        return False, "Mock adapter only accepts .txt files"

    def detect_data_types(self, file_path: str) -> List[str]:
        return ["mock_data", "test_records"]

    def get_adapter_info(self) -> Dict[str, Any]:
        return {
            "id": "mock_adapter_v1",
            "name": "Mock Adapter v1.0",
            "description": "Test adapter for unit testing",
            "supported_formats": [".txt"],
            "institution_id": "test_institution",
            "data_types": ["mock_data", "test_records"],
            "version": "1.0.0",
            "created_by": "Test Suite",
            "last_updated": "2024-09-25",
        }

    def parse_file(
        self, file_path: str, options: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        return {
            "mock_data": [
                {
                    "id": "1",
                    "name": "Test Record",
                    "institution_id": options.get("institution_id", "test"),
                }
            ]
        }

    def export_data(
        self, data: Dict[str, List[Dict]], output_path: str, options: Dict[str, Any]
    ) -> Tuple[bool, str, int]:
        # Mock export - just count records
        total_records = sum(len(records) for records in data.values())
        return True, f"Mock export to {output_path}", total_records


class TestFileBaseAdapter:
    """Test suite for FileBaseAdapter abstract base class"""

    def test_cannot_instantiate_abstract_class(self):
        """Test that FileBaseAdapter cannot be instantiated directly"""
        with pytest.raises(TypeError):
            FileBaseAdapter()

    def test_mock_adapter_implementation(self):
        """Test that mock adapter properly implements abstract methods"""
        adapter = MockAdapter()

        # Test adapter info
        info = adapter.get_adapter_info()
        assert info["id"] == "mock_adapter_v1"
        assert info["name"] == "Mock Adapter v1.0"
        assert ".txt" in info["supported_formats"]

        # Test data type detection
        data_types = adapter.detect_data_types("/fake/path.txt")
        assert "mock_data" in data_types
        assert "test_records" in data_types

    def test_file_size_validation(self):
        """Test file size validation functionality"""
        adapter = MockAdapter()

        # Create a small test file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Small test file")
            temp_path = f.name

        try:
            is_valid, message = adapter.validate_file_size(temp_path)
            assert is_valid is True
            assert "File size OK" in message
        finally:
            Path(temp_path).unlink()

    def test_file_exists_validation(self):
        """Test file existence validation"""
        adapter = MockAdapter()

        # Test with existing file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test content")
            temp_path = f.name

        try:
            is_valid, message = adapter.validate_file_exists(temp_path)
            assert is_valid is True
            assert "exists and is readable" in message
        finally:
            Path(temp_path).unlink()

        # Test with non-existent file
        is_valid, message = adapter.validate_file_exists("/nonexistent/file.txt")
        assert is_valid is False
        assert "File not found" in message

    def test_file_extension_validation(self):
        """Test file extension validation"""
        adapter = MockAdapter()

        # Test supported extension
        is_valid, message = adapter.validate_file_extension("/path/file.txt")
        assert is_valid is True
        assert "is supported" in message

        # Test unsupported extension
        is_valid, message = adapter.validate_file_extension("/path/file.pdf")
        assert is_valid is False
        assert "Unsupported file extension" in message
        assert ".txt" in message

    def test_get_supported_extensions(self):
        """Test getting supported extensions from adapter info"""
        adapter = MockAdapter()
        extensions = adapter.get_supported_extensions()
        assert ".txt" in extensions

    def test_default_limits(self):
        """Test default file size and record limits"""
        adapter = MockAdapter()

        # Test default file size limit (50MB)
        assert adapter.get_file_size_limit() == 50 * 1024 * 1024

        # Test default max records (10000)
        assert adapter.get_max_records() == 10000

    def test_compatibility_validation(self):
        """Test file compatibility validation"""
        adapter = MockAdapter()

        # Test compatible file
        is_compatible, message = adapter.validate_file_compatibility("/path/file.txt")
        assert is_compatible is True
        assert "accepts .txt files" in message

        # Test incompatible file
        is_compatible, message = adapter.validate_file_compatibility("/path/file.xlsx")
        assert is_compatible is False
        assert "only accepts .txt files" in message

    def test_parse_file_with_options(self):
        """Test file parsing with options"""
        adapter = MockAdapter()

        options = {
            "institution_id": "test_institution_123",
            "conflict_strategy": "use_theirs",
        }

        result = adapter.parse_file("/path/file.txt", options)

        assert "mock_data" in result
        assert len(result["mock_data"]) == 1
        assert result["mock_data"][0]["institution_id"] == "test_institution_123"


class TestAdapterValidationResult:
    """Test suite for AdapterValidationResult helper class"""

    def test_validation_result_creation(self):
        """Test creating validation result object"""
        result = AdapterValidationResult("test_adapter", "/path/file.txt")

        assert result.adapter_id == "test_adapter"
        assert result.file_path == "/path/file.txt"
        assert result.is_compatible is False  # Default
        assert result.detected_data_types == []
        assert result.validation_errors == []

    def test_add_error_and_warning(self):
        """Test adding errors and warnings"""
        result = AdapterValidationResult("test_adapter", "/path/file.txt")

        result.add_error("Test error message")
        result.add_warning("Test warning message")

        assert "Test error message" in result.validation_errors
        assert "Test warning message" in result.validation_warnings

    def test_set_compatible(self):
        """Test marking result as compatible"""
        result = AdapterValidationResult("test_adapter", "/path/file.txt")

        result.set_compatible("File is compatible", ["courses", "faculty"])

        assert result.is_compatible is True
        assert result.compatibility_message == "File is compatible"
        assert result.detected_data_types == ["courses", "faculty"]

    def test_set_incompatible(self):
        """Test marking result as incompatible"""
        result = AdapterValidationResult("test_adapter", "/path/file.txt")

        result.set_incompatible("File format not supported")

        assert result.is_compatible is False
        assert result.compatibility_message == "File format not supported"

    def test_to_dict(self):
        """Test converting result to dictionary"""
        result = AdapterValidationResult("test_adapter", "/full/path/file.txt")
        result.set_compatible("Compatible", ["data"])
        result.add_error("Test error")
        result.add_warning("Test warning")

        result_dict = result.to_dict()

        assert result_dict["adapter_id"] == "test_adapter"
        assert result_dict["file_path"] == "file.txt"  # Just filename
        assert result_dict["is_compatible"] is True
        assert result_dict["compatibility_message"] == "Compatible"
        assert result_dict["detected_data_types"] == ["data"]
        assert "Test error" in result_dict["validation_errors"]
        assert "Test warning" in result_dict["validation_warnings"]


class TestFileCompatibilityError:
    """Test suite for FileCompatibilityError exception"""

    def test_file_compatibility_error(self):
        """Test FileCompatibilityError exception"""
        with pytest.raises(FileCompatibilityError) as exc_info:
            raise FileCompatibilityError("Test compatibility error")

        assert "Test compatibility error" in str(exc_info.value)
