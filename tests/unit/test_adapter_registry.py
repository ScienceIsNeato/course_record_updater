"""
Unit tests for AdapterRegistry system
"""

from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

from adapters.adapter_registry import (
    AdapterRegistry,
    AdapterRegistryError,
    get_adapter_registry,
)
from adapters.file_base_adapter import FileBaseAdapter


class MockAdapterA(FileBaseAdapter):
    """Mock adapter for testing - Institution A"""

    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        return True, "Mock A compatible"

    def detect_data_types(self, file_path: str) -> List[str]:
        return ["courses", "faculty"]

    def get_adapter_info(self) -> Dict[str, Any]:
        return {
            "id": "mock_adapter_a",
            "name": "Mock Adapter A",
            "description": "Test adapter for institution A",
            "supported_formats": [".xlsx"],
            "institution_id": "institution_a",
            "data_types": ["courses", "faculty"],
            "version": "1.0.0",
        }

    def parse_file(
        self, file_path: str, options: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        return {"courses": [{"id": "1", "name": "Test Course"}]}

    def export_data(
        self, data: Dict[str, List[Dict]], output_path: str, options: Dict[str, Any]
    ) -> Tuple[bool, str, int]:
        return True, "Mock export successful", 1


class MockAdapterB(FileBaseAdapter):
    """Mock adapter for testing - Institution B"""

    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        return True, "Mock B compatible"

    def detect_data_types(self, file_path: str) -> List[str]:
        return ["students", "enrollments"]

    def get_adapter_info(self) -> Dict[str, Any]:
        return {
            "id": "mock_adapter_b",
            "name": "Mock Adapter B",
            "description": "Test adapter for institution B",
            "supported_formats": [".csv"],
            "institution_id": "institution_b",
            "data_types": ["students", "enrollments"],
            "version": "2.0.0",
        }

    def parse_file(
        self, file_path: str, options: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        return {"students": [{"id": "1", "name": "Test Student"}]}

    def export_data(
        self, data: Dict[str, List[Dict]], output_path: str, options: Dict[str, Any]
    ) -> Tuple[bool, str, int]:
        return True, "Mock export successful", 1


class MockInvalidAdapter(FileBaseAdapter):
    """Mock adapter with invalid metadata for testing"""

    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        return True, "Invalid adapter"

    def detect_data_types(self, file_path: str) -> List[str]:
        return ["data"]

    def get_adapter_info(self) -> Dict[str, Any]:
        # Missing required fields
        return {
            "name": "Invalid Adapter"
            # Missing: id, institution_id, supported_formats, data_types
        }

    def parse_file(
        self, file_path: str, options: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        return {}

    def export_data(
        self, data: Dict[str, List[Dict]], output_path: str, options: Dict[str, Any]
    ) -> Tuple[bool, str, int]:
        return False, "Invalid adapter export", 0


class TestAdapterRegistry:
    """Test suite for AdapterRegistry"""

    def setup_method(self):
        """Set up test environment"""
        self.registry = AdapterRegistry()
        # Clear any cached state
        self.registry._adapters.clear()
        self.registry._adapter_instances.clear()
        self.registry._discovery_complete = False

    @patch("adapters.adapter_registry.importlib.import_module")
    @patch("adapters.adapter_registry.inspect.getmembers")
    @patch("adapters.adapter_registry.Path.glob")
    def test_discover_adapters_success(self, mock_glob, mock_getmembers, mock_import):
        """Test successful adapter discovery"""
        # Mock file discovery
        mock_file = Mock()
        mock_file.name = "mock_adapter.py"
        mock_file.stem = "mock_adapter"
        mock_glob.return_value = [mock_file]

        # Mock module import and inspection
        mock_module = Mock()
        mock_import.return_value = mock_module
        mock_getmembers.return_value = [
            ("MockAdapterA", MockAdapterA),
            ("SomeOtherClass", str),  # Should be ignored
        ]

        self.registry.discover_adapters()

        assert len(self.registry._adapters) == 1
        assert "mock_adapter_a" in self.registry._adapters
        assert self.registry._discovery_complete is True

    @patch("adapters.adapter_registry.importlib.import_module")
    @patch("adapters.adapter_registry.Path.glob")
    def test_discover_adapters_import_error(self, mock_glob, mock_import):
        """Test adapter discovery with import error"""
        # Mock file discovery
        mock_file = Mock()
        mock_file.name = "bad_adapter.py"
        mock_file.stem = "bad_adapter"
        mock_glob.return_value = [mock_file]

        # Mock import error
        mock_import.side_effect = ImportError("Module not found")

        # Should not raise error, just log and continue
        self.registry.discover_adapters()

        assert len(self.registry._adapters) == 0
        assert self.registry._discovery_complete is True

    def test_register_adapter_class_valid(self):
        """Test registering a valid adapter class"""
        self.registry._register_adapter_class(MockAdapterA, "mock_module")

        assert "mock_adapter_a" in self.registry._adapters
        registration = self.registry._adapters["mock_adapter_a"]
        assert registration["class"] == MockAdapterA
        assert registration["active"] is True
        assert registration["info"]["name"] == "Mock Adapter A"

    def test_register_adapter_class_invalid(self):
        """Test registering an adapter with invalid metadata"""
        # Should not raise error, just log warning and skip
        self.registry._register_adapter_class(MockInvalidAdapter, "invalid_module")

        # Should not be registered due to missing required fields
        assert len(self.registry._adapters) == 0

    def test_get_all_adapters(self):
        """Test getting all registered adapters"""
        # Manually register adapters for testing
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            },
            "mock_adapter_b": {
                "class": MockAdapterB,
                "info": MockAdapterB().get_adapter_info(),
                "active": True,
            },
        }
        self.registry._discovery_complete = True

        adapters = self.registry.get_all_adapters()

        assert len(adapters) == 2
        adapter_ids = [adapter["id"] for adapter in adapters]
        assert "mock_adapter_a" in adapter_ids
        assert "mock_adapter_b" in adapter_ids

    def test_get_adapters_for_institution(self):
        """Test getting adapters for specific institution"""
        # Manually register adapters
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            },
            "mock_adapter_b": {
                "class": MockAdapterB,
                "info": MockAdapterB().get_adapter_info(),
                "active": True,
            },
        }
        self.registry._discovery_complete = True

        # Test filtering by institution A
        adapters_a = self.registry.get_adapters_for_institution("institution_a")
        assert len(adapters_a) == 1
        assert adapters_a[0]["id"] == "mock_adapter_a"

        # Test filtering by institution B
        adapters_b = self.registry.get_adapters_for_institution("institution_b")
        assert len(adapters_b) == 1
        assert adapters_b[0]["id"] == "mock_adapter_b"

        # Test non-existent institution
        adapters_none = self.registry.get_adapters_for_institution("nonexistent")
        assert len(adapters_none) == 0

    def test_get_adapters_for_user_site_admin(self):
        """Test adapter access for site admin"""
        # Manually register adapters
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            },
            "mock_adapter_b": {
                "class": MockAdapterB,
                "info": MockAdapterB().get_adapter_info(),
                "active": True,
            },
        }
        self.registry._discovery_complete = True

        # Site admin should see all adapters
        adapters = self.registry.get_adapters_for_user("site_admin", "any_institution")
        assert len(adapters) == 2

    def test_get_adapters_for_user_institution_admin(self):
        """Test adapter access for institution admin"""
        # Manually register adapters
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            },
            "mock_adapter_b": {
                "class": MockAdapterB,
                "info": MockAdapterB().get_adapter_info(),
                "active": True,
            },
        }
        self.registry._discovery_complete = True

        # Institution admin should see only their institution's adapters
        adapters = self.registry.get_adapters_for_user(
            "institution_admin", "institution_a"
        )
        assert len(adapters) == 1
        assert adapters[0]["id"] == "mock_adapter_a"

    def test_get_adapters_for_user_instructor(self):
        """Test adapter access for instructor (should be empty)"""
        # Manually register adapters
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            }
        }
        self.registry._discovery_complete = True

        # Instructors should have no import access
        adapters = self.registry.get_adapters_for_user("instructor", "institution_a")
        assert len(adapters) == 0

    def test_get_adapter_by_id_success(self):
        """Test getting adapter instance by ID"""
        # Manually register adapter
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            }
        }
        self.registry._discovery_complete = True

        adapter = self.registry.get_adapter_by_id("mock_adapter_a")

        assert adapter is not None
        assert isinstance(adapter, MockAdapterA)

        # Should cache the instance
        assert "mock_adapter_a" in self.registry._adapter_instances

        # Second call should return cached instance
        adapter2 = self.registry.get_adapter_by_id("mock_adapter_a")
        assert adapter is adapter2

    def test_get_adapter_by_id_not_found(self):
        """Test getting non-existent adapter"""
        self.registry._discovery_complete = True

        adapter = self.registry.get_adapter_by_id("nonexistent")
        assert adapter is None

    def test_get_adapter_by_id_inactive(self):
        """Test getting inactive adapter"""
        # Register inactive adapter
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": False,
            }
        }
        self.registry._discovery_complete = True

        adapter = self.registry.get_adapter_by_id("mock_adapter_a")
        assert adapter is None

    def test_validate_adapter_access_allowed(self):
        """Test adapter access validation - allowed"""
        # Manually register adapter
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            }
        }
        self.registry._discovery_complete = True

        # Institution admin should have access to their institution's adapter
        has_access = self.registry.validate_adapter_access(
            "mock_adapter_a", "institution_admin", "institution_a"
        )
        assert has_access is True

    def test_validate_adapter_access_denied(self):
        """Test adapter access validation - denied"""
        # Manually register adapter
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            }
        }
        self.registry._discovery_complete = True

        # Institution admin should not have access to other institution's adapter
        has_access = self.registry.validate_adapter_access(
            "mock_adapter_a", "institution_admin", "institution_b"
        )
        assert has_access is False

    def test_get_adapter_info(self):
        """Test getting adapter metadata"""
        # Manually register adapter
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            }
        }
        self.registry._discovery_complete = True

        info = self.registry.get_adapter_info("mock_adapter_a")

        assert info is not None
        assert info["id"] == "mock_adapter_a"
        assert info["name"] == "Mock Adapter A"
        assert info["active"] is True

    def test_deactivate_reactivate_adapter(self):
        """Test deactivating and reactivating adapters"""
        # Manually register adapter
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            }
        }
        self.registry._discovery_complete = True

        # Deactivate adapter
        result = self.registry.deactivate_adapter("mock_adapter_a")
        assert result is True
        assert self.registry._adapters["mock_adapter_a"]["active"] is False

        # Reactivate adapter
        result = self.registry.reactivate_adapter("mock_adapter_a")
        assert result is True
        assert self.registry._adapters["mock_adapter_a"]["active"] is True

        # Test with non-existent adapter
        result = self.registry.deactivate_adapter("nonexistent")
        assert result is False

    def test_get_supported_formats(self):
        """Test getting supported file formats"""
        # Manually register adapters
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            },
            "mock_adapter_b": {
                "class": MockAdapterB,
                "info": MockAdapterB().get_adapter_info(),
                "active": True,
            },
        }
        self.registry._discovery_complete = True

        formats = self.registry.get_supported_formats()

        assert "mock_adapter_a" in formats
        assert "mock_adapter_b" in formats
        assert ".xlsx" in formats["mock_adapter_a"]
        assert ".csv" in formats["mock_adapter_b"]

    def test_find_adapters_for_format(self):
        """Test finding adapters by file format"""
        # Manually register adapters
        self.registry._adapters = {
            "mock_adapter_a": {
                "class": MockAdapterA,
                "info": MockAdapterA().get_adapter_info(),
                "active": True,
            },
            "mock_adapter_b": {
                "class": MockAdapterB,
                "info": MockAdapterB().get_adapter_info(),
                "active": True,
            },
        }
        self.registry._discovery_complete = True

        # Find adapters for .xlsx files
        xlsx_adapters = self.registry.find_adapters_for_format(".xlsx")
        assert len(xlsx_adapters) == 1
        assert xlsx_adapters[0]["id"] == "mock_adapter_a"

        # Find adapters for .csv files
        csv_adapters = self.registry.find_adapters_for_format(".csv")
        assert len(csv_adapters) == 1
        assert csv_adapters[0]["id"] == "mock_adapter_b"

        # Find adapters for unsupported format
        pdf_adapters = self.registry.find_adapters_for_format(".pdf")
        assert len(pdf_adapters) == 0

    def test_clear_cache(self):
        """Test clearing registry cache"""
        # Set up some cached state
        self.registry._adapters = {"test": {}}
        self.registry._adapter_instances = {"test": Mock()}
        self.registry._discovery_complete = True

        self.registry.clear_cache()

        assert len(self.registry._adapters) == 0
        assert len(self.registry._adapter_instances) == 0
        assert self.registry._discovery_complete is False


class TestAdapterRegistrySingleton:
    """Test suite for adapter registry singleton"""

    def test_get_adapter_registry_singleton(self):
        """Test that get_adapter_registry returns the same instance"""
        registry1 = get_adapter_registry()
        registry2 = get_adapter_registry()

        assert registry1 is registry2
        assert isinstance(registry1, AdapterRegistry)


class TestAdapterRegistryError:
    """Test suite for AdapterRegistryError"""

    def test_adapter_registry_error(self):
        """Test AdapterRegistryError exception"""
        with pytest.raises(AdapterRegistryError) as exc_info:
            raise AdapterRegistryError("Test registry error")

        assert "Test registry error" in str(exc_info.value)

    def test_get_adapter_instance_creation_failure(self):
        """Test get_adapter raises AdapterRegistryError when adapter instantiation fails."""
        from unittest.mock import MagicMock

        from adapters.adapter_registry import AdapterRegistry, AdapterRegistryError

        registry = AdapterRegistry()

        # Create a mock adapter class that raises exception on instantiation
        mock_adapter_class = MagicMock(side_effect=RuntimeError("Instantiation failed"))

        # Register the failing adapter
        registry._adapters["failing_adapter"] = {
            "class": mock_adapter_class,
            "name": "Failing Adapter",
            "active": True,
        }

        # Attempt to get instance should raise AdapterRegistryError (line 337-339)
        with pytest.raises(AdapterRegistryError, match="Cannot instantiate adapter"):
            registry.get_adapter_by_id("failing_adapter")
