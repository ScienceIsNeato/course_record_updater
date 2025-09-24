"""
Export Service for Course Record Updater

Provides bidirectional export functionality using pluggable adapters to convert
database records back to institution-specific Excel formats. Enables roundtrip
validation and data interchange with external systems.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from openpyxl import Workbook

from database_service import (
    get_active_terms,  # Use active_terms instead of get_all_terms
)
from database_service import (
    get_all_courses,
    get_all_users,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """Configuration for export operations."""

    institution_id: str
    adapter_name: str = "cei_excel_adapter"
    export_view: str = "standard"  # standard, academic_summary, administrative
    include_metadata: bool = True
    output_format: str = "xlsx"  # xlsx, csv, json


@dataclass
class ExportResult:
    """Result of export operation with metadata."""

    success: bool
    file_path: Optional[str] = None
    records_exported: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    export_timestamp: datetime = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.export_timestamp is None:
            self.export_timestamp = datetime.utcnow()


class ExportService:
    """Service for exporting database records to institution-specific formats."""

    def __init__(self):
        self.supported_adapters = {
            "cei_excel_adapter": self._export_cei_format,
            "default_adapter": self._export_default_format,
        }

    def export_data(
        self,
        config: ExportConfig,
        output_path: Union[str, Path],
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
            LOGGER.info(f"Starting export with adapter: {config.adapter_name}")

            # Validate adapter
            if config.adapter_name not in self.supported_adapters:
                return ExportResult(
                    success=False,
                    errors=[f"Unsupported adapter: {config.adapter_name}"],
                )

            # Fetch data from database
            export_data = self._fetch_export_data(config.institution_id, filters)
            if not export_data:
                return ExportResult(
                    success=False, errors=["No data found for export criteria"]
                )

            # Call appropriate adapter export function
            adapter_func = self.supported_adapters[config.adapter_name]
            result = adapter_func(export_data, config, output_path)

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

        Returns a dictionary with entity types as keys and lists of records as values.
        """
        try:
            data: Dict[str, List[Dict[str, Any]]] = {
                "courses": [],
                "users": [],
                "terms": [],
                "offerings": [],
                "sections": [],
            }

            # Fetch courses
            courses = get_all_courses(institution_id)
            data["courses"] = courses  # Already dict objects

            # Fetch users (instructors)
            users = get_all_users(institution_id)
            data["users"] = users  # Already dict objects

            # Fetch terms
            terms = get_active_terms(institution_id)
            data["terms"] = terms  # Already dict objects

            # TODO: Fetch offerings and sections when those services exist
            # For now, we'll work with the core entities

            LOGGER.info(
                f"Fetched export data: {len(data['courses'])} courses, "
                f"{len(data['users'])} users, {len(data['terms'])} terms"
            )

            return data

        except Exception as e:
            LOGGER.error(f"Failed to fetch export data: {str(e)}")
            return {}

    def _export_cei_format(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        config: ExportConfig,
        output_path: Union[str, Path],
    ) -> ExportResult:
        """
        Export data in CEI's specific Excel format.

        This creates the same structure as the input files to enable roundtrip validation.
        """
        try:
            # Create DataFrame in CEI format
            export_records = []

            # Combine data from multiple entities into CEI row format
            for course in data["courses"]:
                # Find matching instructor
                instructor = self._find_instructor_for_course(course, data["users"])

                # Find matching term
                term = self._find_term_for_course(course, data["terms"])

                # Create CEI-format record
                record = self._build_cei_record(course, instructor, term)
                if record:
                    export_records.append(record)

            if not export_records:
                return ExportResult(
                    success=False, errors=["No valid records to export"]
                )

            # Create DataFrame and Excel file
            df = pd.DataFrame(export_records)

            # Ensure output directory exists
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to Excel with proper formatting
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="2024FA_feed", index=False)

                # Apply column formatting (ensure all columns visible)
                worksheet = writer.sheets["2024FA_feed"]
                for column in worksheet.columns:
                    max_length = max(len(str(cell.value or "")) for cell in column)
                    column_width = min(max(max_length + 2, 10), 50)
                    worksheet.column_dimensions[column[0].column_letter].width = (
                        column_width
                    )
                    worksheet.column_dimensions[column[0].column_letter].hidden = False

            return ExportResult(
                success=True,
                file_path=str(output_path),
                records_exported=len(export_records),
            )

        except Exception as e:
            return ExportResult(success=False, errors=[f"CEI export failed: {str(e)}"])

    def _export_default_format(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        config: ExportConfig,
        output_path: Union[str, Path],
    ) -> ExportResult:
        """
        Export data in default/standard academic format.

        This provides a standardized export format for institutions without
        custom requirements.
        """
        # TODO: Implement default format export
        return ExportResult(
            success=False, errors=["Default adapter export not yet implemented"]
        )

    def _find_instructor_for_course(
        self, course: Dict[str, Any], users: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find the instructor associated with a course."""
        # This is a simplified lookup - in reality we'd need offering/section data
        # For now, return the first instructor we find
        instructors = [u for u in users if u.get("role") == "instructor"]
        return instructors[0] if instructors else None

    def _find_term_for_course(
        self, course: Dict[str, Any], terms: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find the term associated with a course."""
        # This is simplified - in reality we'd need offering data to link course to term
        # For now, return the most recent term
        if terms:
            return sorted(terms, key=lambda t: t.get("year", 0), reverse=True)[0]
        return None

    def _build_cei_record(
        self,
        course: Dict[str, Any],
        instructor: Optional[Dict[str, Any]],
        term: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Build a single record in CEI format from database entities.

        This creates the same column structure as the CEI test data file.
        """
        if not course:
            return None

        # Build record matching CEI test data format
        record = {
            "course": course.get("course_number", ""),
            "combo": "",  # Not available in our data model yet
            "cllo_text": "",  # Course learning outcome text
            "Enrolled Students": 0,  # Would come from sections/enrollments
            "Total W's": 0,  # Withdrawals - would come from sections
            "pass_course": 0,  # Pass count
            "dfic_course": 0,  # Difficulty course metric
            "cannot reconcile (y/n)": "n",
            "email": instructor.get("email", "") if instructor else "",
            "course enddate": "",  # Would come from term/offering data
            "Term": self._format_term_for_cei(term) if term else "",
            "assessment tool": "",
            "passed_c": 0,
            "took_c": 0,
            "celebrations": "",
            "challenges": "",
            "changes": "",
            "I status": "",
            "A status": "",
            "X status": "",
        }

        return record

    def _format_term_for_cei(self, term: Dict[str, Any]) -> str:
        """Format term data for CEI export format."""
        if not term:
            return ""

        year = term.get("year", "")
        season = term.get("season", "")

        if year and season:
            return f"{year} {season}"

        return term.get("name", "")


def create_export_service() -> ExportService:
    """Factory function to create configured ExportService instance."""
    return ExportService()
