"""
Export Service for Course Record Updater

Provides bidirectional export functionality using pluggable adapters to convert
database records back to institution-specific Excel formats. Enables roundtrip
validation and data interchange with external systems.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from openpyxl import Workbook

from adapters.adapter_registry import AdapterRegistryError, get_adapter_registry
from database_service import (
    get_active_terms,  # Use active_terms instead of get_all_terms
)
from database_service import (
    get_all_course_offerings,
    get_all_courses,
    get_all_sections,
    get_all_users,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """Configuration for export operations."""

    institution_id: str
    adapter_id: str = "cei_excel_format_v1"
    export_view: str = "standard"  # standard, academic_summary, administrative
    include_metadata: bool = True
    output_format: str = "xlsx"  # xlsx, csv, json


@dataclass
class ExportResult:
    """Result of export operation with metadata."""

    success: bool
    file_path: Optional[str] = None
    records_exported: int = 0
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    export_timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.export_timestamp is None:
            self.export_timestamp = datetime.now(timezone.utc)


class ExportService:
    """Service for exporting database records to institution-specific formats using adapter registry."""

    def __init__(self):
        self.registry = get_adapter_registry()

    def validate_export_access(
        self, user: Dict[str, Any], adapter_id: str
    ) -> Tuple[bool, str]:
        """
        Validate that a user has access to export with a specific adapter.

        Args:
            user: User object with role and institution_id
            adapter_id: ID of the adapter to validate

        Returns:
            Tuple[bool, str]: (has_access, message)
        """
        try:
            # Check if user has access to this adapter
            user_role = user.get("role")
            user_institution_id = user.get("institution_id")

            if not self.registry.validate_adapter_access(
                adapter_id, user_role, user_institution_id
            ):
                return False, f"Access denied to adapter: {adapter_id}"

            # Check if adapter exists
            adapter = self.registry.get_adapter_by_id(adapter_id)
            if not adapter:
                return False, f"Adapter not found: {adapter_id}"

            return True, "Access granted"

        except Exception as e:
            return False, f"Failed to validate adapter access: {str(e)}"

    def export_data(
        self,
        config: ExportConfig,
        output_path: str | Path,
        filters: Optional[Dict[str, Any]] = None,
    ) -> ExportResult:
        """
        Export database records using specified adapter configuration.

        Args:
            config: Export configuration including adapter and view settings
            output_path: Path where export file should be saved
            filters: Optional filters to limit export scope (e.g., term, program)

        Returns:
            ExportResult with success status and metadata
        """
        try:
            LOGGER.info(f"Starting export with adapter: {config.adapter_id}")

            # Get adapter from registry
            try:
                adapter = self.registry.get_adapter_by_id(config.adapter_id)
                if not adapter:
                    return ExportResult(
                        success=False,
                        errors=[f"Adapter not found: {config.adapter_id}"],
                    )
            except AdapterRegistryError as e:
                return ExportResult(
                    success=False,
                    errors=[f"Failed to get adapter {config.adapter_id}: {str(e)}"],
                )

            # Fetch data from database
            export_data = self._fetch_export_data(config.institution_id, filters)
            if not export_data:
                return ExportResult(
                    success=False, errors=["No data found for export criteria"]
                )

            # Check if adapter supports export
            if not adapter.supports_export():
                return ExportResult(
                    success=False,
                    errors=[
                        f"Adapter {config.adapter_id} does not support export functionality"
                    ],
                )

            # Use the adapter's export method
            export_options = {
                "institution_id": config.institution_id,
                "export_view": config.export_view,
                "include_metadata": config.include_metadata,
                "output_format": config.output_format,
            }

            success, message, records_exported = adapter.export_data(
                export_data, str(output_path), export_options
            )

            if success:
                result = ExportResult(
                    success=True,
                    file_path=str(output_path),
                    records_exported=records_exported,
                    export_timestamp=datetime.now(timezone.utc),
                )
            else:
                result = ExportResult(
                    success=False,
                    errors=[message],
                )

            LOGGER.info(f"Export completed: {result.records_exported} records")
            return result

        except Exception as e:
            LOGGER.error(f"Export failed: {str(e)}")
            return ExportResult(success=False, errors=[f"Export failed: {str(e)}"])

    def _fetch_export_data(
        self, institution_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all relevant data from database for export.

        Args:
            institution_id: Institution to export data for
            filters: Optional filters to limit scope

        Returns:
            Dictionary with organized export data
        """
        try:
            LOGGER.info(f"Fetching export data for institution: {institution_id}")

            # Fetch all data types
            courses = get_all_courses(institution_id)
            users = get_all_users(institution_id)
            terms = get_active_terms(institution_id)
            sections = get_all_sections(institution_id)
            offerings = get_all_course_offerings(institution_id)

            # Convert to list of dicts if needed
            courses_list = [dict(course) for course in courses] if courses else []
            users_list = [dict(user) for user in users] if users else []
            terms_list = [dict(term) for term in terms] if terms else []
            sections_list = [dict(section) for section in sections] if sections else []
            offerings_list = (
                [dict(offering) for offering in offerings] if offerings else []
            )

            # Organize data for export
            export_data = {
                "courses": courses_list,
                "users": users_list,
                "terms": terms_list,
                "offerings": offerings_list,
                "sections": sections_list,
            }

            LOGGER.info(
                f"Fetched {len(courses_list)} courses, {len(users_list)} users, {len(terms_list)} terms"
            )
            return export_data

        except Exception as e:
            LOGGER.error(f"Failed to fetch export data: {str(e)}")
            return {}


def create_export_service() -> ExportService:
    """Factory function to create configured ExportService instance."""
    return ExportService()
