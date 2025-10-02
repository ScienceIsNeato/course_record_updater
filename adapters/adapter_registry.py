"""
Adapter Registry System

This module provides centralized management of file processing adapters,
including discovery, institution-scoped filtering, and access control.
The registry enables the adaptive import system to dynamically load
and validate adapters based on user permissions and institution context.
"""

import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from logging_config import get_logger

from .file_base_adapter import FileBaseAdapter

logger = get_logger("AdapterRegistry")


class AdapterRegistryError(Exception):
    """Raised when adapter registry operations fail"""


class AdapterRegistry:
    """
    Central registry for managing file processing adapters.

    Responsibilities:
    1. Discover available adapters in the adapters directory
    2. Filter adapters based on institution and user permissions
    3. Provide adapter instances for file processing
    4. Validate adapter access based on user roles
    5. Cache adapter metadata for performance
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, Dict[str, Any]] = {}
        self._adapter_instances: Dict[str, FileBaseAdapter] = {}
        self._discovery_complete = False

        # Adapter discovery configuration
        self.adapter_module_path = "adapters"
        self.exclude_modules = [
            "__init__.py",
            "base_adapter.py",  # Old form-based adapter
            "file_base_adapter.py",  # Abstract base class
            "adapter_registry.py",  # This file
            "file_adapter_dispatcher.py",  # Old dispatcher
        ]

    def discover_adapters(self) -> None:
        """
        Discover and register all available adapters.

        Scans the adapters directory for modules containing FileBaseAdapter
        implementations and registers them with their metadata.
        """
        if self._discovery_complete:
            return

        logger.info("Starting adapter discovery...")

        try:
            adapters_dir = Path(__file__).parent

            for module_file in adapters_dir.glob("*.py"):
                if module_file.name in self.exclude_modules:
                    continue

                module_name = module_file.stem
                self._try_register_adapter_from_module(module_name)

            self._discovery_complete = True
            logger.info(
                f"Adapter discovery complete. Found {len(self._adapters)} adapters."
            )

        except Exception as e:
            logger.error(f"Error during adapter discovery: {e}")
            raise AdapterRegistryError(f"Failed to discover adapters: {e}") from e

    def _try_register_adapter_from_module(self, module_name: str) -> None:
        """
        Attempt to register an adapter from a specific module.

        Args:
            module_name: Name of the module to inspect for adapters
        """
        try:
            # Import the module
            full_module_path = f"{self.adapter_module_path}.{module_name}"
            module = importlib.import_module(full_module_path)

            # Look for classes that inherit from FileBaseAdapter
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    obj != FileBaseAdapter
                    and issubclass(obj, FileBaseAdapter)
                    and not inspect.isabstract(obj)
                ):

                    self._register_adapter_class(obj, module_name)

        except ImportError as e:
            logger.debug(f"Could not import module {module_name}: {e}")
        except (AttributeError, TypeError) as e:
            logger.warning(f"Error inspecting module {module_name}: {e}")

    def _register_adapter_class(
        self, adapter_class: Type[FileBaseAdapter], module_name: str
    ) -> None:
        """
        Register a discovered adapter class.

        Args:
            adapter_class: The adapter class to register
            module_name: Name of the module containing the adapter
        """
        try:
            # Create an instance to get metadata
            instance = adapter_class()
            adapter_info = instance.get_adapter_info()

            # Validate required metadata fields
            required_fields = [
                "id",
                "name",
                "supported_formats",
                "data_types",
            ]
            missing_fields = [
                field for field in required_fields if field not in adapter_info
            ]

            # Must have either institution_id OR institution_short_name for institution binding
            has_institution_id = "institution_id" in adapter_info
            has_institution_short_name = "institution_short_name" in adapter_info

            if not has_institution_id and not has_institution_short_name:
                missing_fields.append("institution_id or institution_short_name")

            if missing_fields:
                logger.warning(
                    f"Adapter {adapter_class.__name__} missing required fields: {missing_fields}"
                )
                return

            adapter_id = adapter_info["id"]

            # Register the adapter
            self._adapters[adapter_id] = {
                "class": adapter_class,
                "module_name": module_name,
                "info": adapter_info,
                "active": True,
            }

            logger.info("Registered adapter successfully")

        except (TypeError, ValueError, AttributeError) as e:
            logger.error(f"Failed to register adapter {adapter_class.__name__}: {e}")

    def get_all_adapters(self) -> List[Dict[str, Any]]:
        """
        Get metadata for all registered adapters.

        Returns:
            List of adapter metadata dictionaries
        """
        self.discover_adapters()

        all_adapters = []
        for registration in self._adapters.values():
            if not registration["active"]:
                continue

            adapter_info = registration["info"].copy()

            # Resolve institution_id for adapters using institution_short_name
            if (
                "institution_short_name" in adapter_info
                and "institution_id" not in adapter_info
            ):
                try:
                    import database_service as db

                    institution = db.get_institution_by_short_name(
                        adapter_info["institution_short_name"]
                    )
                    if institution:
                        adapter_info["institution_id"] = institution.get(
                            "institution_id"
                        )
                except Exception:
                    pass  # If resolution fails, leave institution_id as None

            adapter_info["active"] = registration["active"]
            all_adapters.append(adapter_info)

        return all_adapters

    def get_adapters_for_institution(self, institution_id: str) -> List[Dict[str, Any]]:
        """
        Get all adapters available for a specific institution.

        Args:
            institution_id: ID of the institution to filter by

        Returns:
            List of adapter metadata for the institution
        """
        self.discover_adapters()

        institution_adapters = []

        for registration in self._adapters.values():
            if not registration["active"]:
                continue

            adapter_info = registration["info"]

            # Check if adapter serves this institution
            adapter_institution_id = adapter_info.get("institution_id")
            adapter_institution_short_name = adapter_info.get("institution_short_name")

            # Match by institution_id (legacy) or by short_name (stable identifier)
            if adapter_institution_id == institution_id:
                institution_adapters.append(
                    {**adapter_info, "active": registration["active"]}
                )
            elif adapter_institution_short_name:
                # Look up institution by short_name to get current ID
                try:
                    import database_service as db

                    institution = db.get_institution_by_short_name(
                        adapter_institution_short_name
                    )
                    if (
                        institution
                        and institution.get("institution_id") == institution_id
                    ):
                        # Add the resolved institution_id to the adapter info
                        adapter_info_with_id = {
                            **adapter_info,
                            "institution_id": institution_id,
                        }
                        institution_adapters.append(
                            {**adapter_info_with_id, "active": registration["active"]}
                        )
                except Exception:
                    # If database lookup fails, skip this adapter
                    pass

        logger.debug(
            f"Found {len(institution_adapters)} adapters for institution {institution_id}"
        )
        return institution_adapters

    def get_adapters_for_user(
        self, user_role: str, institution_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get adapters available to a specific user based on role and institution.

        Args:
            user_role: User's role (site_admin, institution_admin, program_admin, instructor)
            institution_id: User's institution ID

        Returns:
            List of adapter metadata filtered by permissions
        """
        self.discover_adapters()

        if user_role == "site_admin":
            # Site admins can see all adapters
            return self.get_all_adapters()

        elif user_role in ["institution_admin", "program_admin"]:
            # Institution and program admins see adapters for their institution
            return self.get_adapters_for_institution(institution_id)

        elif user_role == "instructor":
            # Instructors have no import access, return empty list
            return []

        else:
            logger.warning(f"Unknown user role: {user_role}")
            return []

    def get_adapter_by_id(self, adapter_id: str) -> Optional[FileBaseAdapter]:
        """
        Get an adapter instance by its ID.

        Args:
            adapter_id: Unique identifier for the adapter

        Returns:
            Adapter instance or None if not found

        Raises:
            AdapterRegistryError: If adapter cannot be instantiated
        """
        self.discover_adapters()

        # Check if we have a cached instance
        if adapter_id in self._adapter_instances:
            return self._adapter_instances[adapter_id]

        # Check if adapter is registered
        if adapter_id not in self._adapters:
            # Don't log user-controlled adapter_id to prevent log injection
            logger.warning("Adapter not found in registry")
            return None

        registration = self._adapters[adapter_id]

        if not registration["active"]:
            # Don't log user-controlled adapter_id to prevent log injection
            logger.warning("Requested adapter is not active")
            return None

        try:
            # Create new instance
            adapter_class = registration["class"]
            instance = adapter_class()

            # Cache the instance
            self._adapter_instances[adapter_id] = instance

            logger.debug("Created adapter instance successfully")
            return instance

        except Exception as e:
            logger.error("Failed to create adapter instance: %s", e)
            raise AdapterRegistryError(
                f"Cannot instantiate adapter {adapter_id}: {e}"
            ) from e

    def validate_adapter_access(
        self, adapter_id: str, user_role: str, institution_id: str
    ) -> bool:
        """
        Validate that a user has access to a specific adapter.

        Args:
            adapter_id: ID of the adapter to check
            user_role: User's role
            institution_id: User's institution ID

        Returns:
            True if user has access, False otherwise
        """
        self.discover_adapters()

        # Get adapters available to this user
        available_adapters = self.get_adapters_for_user(user_role, institution_id)

        # Check if the requested adapter is in the available list
        for adapter_info in available_adapters:
            if adapter_info["id"] == adapter_id:
                return True

        logger.warning(
            f"Access denied: User {user_role}@{institution_id} cannot access adapter {adapter_id}"
        )
        return False

    def get_adapter_info(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific adapter.

        Args:
            adapter_id: ID of the adapter

        Returns:
            Adapter metadata or None if not found
        """
        self.discover_adapters()

        if adapter_id not in self._adapters:
            return None

        registration = self._adapters[adapter_id]
        return {**registration["info"], "active": registration["active"]}

    def deactivate_adapter(self, adapter_id: str) -> bool:
        """
        Deactivate an adapter (for maintenance or deprecation).

        Args:
            adapter_id: ID of the adapter to deactivate

        Returns:
            True if deactivated, False if not found
        """
        if adapter_id not in self._adapters:
            return False

        self._adapters[adapter_id]["active"] = False

        # Remove from instance cache if present
        if adapter_id in self._adapter_instances:
            del self._adapter_instances[adapter_id]

        logger.info("Deactivated adapter successfully")
        return True

    def reactivate_adapter(self, adapter_id: str) -> bool:
        """
        Reactivate a previously deactivated adapter.

        Args:
            adapter_id: ID of the adapter to reactivate

        Returns:
            True if reactivated, False if not found
        """
        if adapter_id not in self._adapters:
            return False

        self._adapters[adapter_id]["active"] = True
        logger.info("Reactivated adapter successfully")
        return True

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        Get all supported file formats across all adapters.

        Returns:
            Dict mapping adapter IDs to their supported formats
        """
        self.discover_adapters()

        formats = {}
        for adapter_id, registration in self._adapters.items():
            if registration["active"]:
                adapter_info = registration["info"]
                formats[adapter_id] = adapter_info.get("supported_formats", [])

        return formats

    def find_adapters_for_format(self, file_extension: str) -> List[Dict[str, Any]]:
        """
        Find all adapters that support a specific file format.

        Args:
            file_extension: File extension to search for (e.g., '.xlsx')

        Returns:
            List of adapter metadata that support the format
        """
        self.discover_adapters()

        matching_adapters = []

        for registration in self._adapters.values():
            if not registration["active"]:
                continue

            adapter_info = registration["info"]
            supported_formats = adapter_info.get("supported_formats", [])

            if file_extension.lower() in [fmt.lower() for fmt in supported_formats]:
                matching_adapters.append(
                    {**adapter_info, "active": registration["active"]}
                )

        return matching_adapters

    def clear_cache(self) -> None:
        """Clear the adapter instance cache and force re-discovery."""
        self._adapter_instances.clear()
        self._adapters.clear()
        self._discovery_complete = False
        logger.info("Adapter registry cache cleared")


# Global registry instance
_registry_instance: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """
    Get the global adapter registry instance (singleton pattern).

    Returns:
        Global AdapterRegistry instance
    """
    # pylint: disable=global-statement
    global _registry_instance

    if _registry_instance is None:
        _registry_instance = AdapterRegistry()

    return _registry_instance
