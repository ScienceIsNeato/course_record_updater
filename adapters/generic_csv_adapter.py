"""
Generic CSV Adapter - Institution-Agnostic Import/Export

This adapter provides a generic, normalized CSV format for importing and exporting
course management data. Unlike institution-specific adapters (CEI, etc.), this adapter
uses a standard database export format that works for any institution.

Format: ZIP file containing multiple normalized CSV files (one per entity type)
Security: Excludes passwords and active tokens (users imported as "pending")
Documentation: See CSV_FORMAT_SPEC.md for complete specification

Key Features:
- Normalized structure (no data duplication)
- Complete bidirectional support (import + export)
- Security-first approach (no sensitive data exported)
- Standard ZIP + CSV format (no custom parsing needed)
"""

import csv
import json
import logging
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .file_base_adapter import FileBaseAdapter, FileCompatibilityError

logger = logging.getLogger(__name__)

# Format version for compatibility checking
FORMAT_VERSION = "1.0"

# Entity export order (respects foreign key dependencies)
EXPORT_ORDER = [
    "institutions",
    "programs",
    "users",
    "user_programs",
    "courses",
    "course_programs",
    "terms",
    "course_offerings",
    "course_sections",
    "course_outcomes",
    "user_invitations",
]

# CSV column definitions for each entity type
# Format: entity_name -> list of column names
CSV_COLUMNS = {
    "institutions": [
        "id",
        "name",
        "short_name",
        "website_url",
        "created_by",
        "admin_email",
        "allow_self_registration",
        "require_email_verification",
        "is_active",
        "created_at",
        "updated_at",
    ],
    "programs": [
        "id",
        "name",
        "short_name",
        "description",
        "institution_id",
        "created_by",
        "is_default",
        "is_active",
        "created_at",
        "updated_at",
    ],
    "users": [
        "id",
        "email",
        "first_name",
        "last_name",
        "display_name",
        "role",
        "institution_id",
        "invited_by",
        "invited_at",
        "registration_completed_at",
        "oauth_provider",
        "created_at",
        "updated_at",
    ],
    "user_programs": [
        "user_id",
        "program_id",
    ],
    "courses": [
        "id",
        "course_number",
        "course_title",
        "department",
        "credit_hours",
        "institution_id",
        "active",
        "created_at",
        "updated_at",
    ],
    "course_programs": [
        "course_id",
        "program_id",
    ],
    "terms": [
        "id",
        "term_name",
        "name",
        "start_date",
        "end_date",
        "assessment_due_date",
        "active",
        "institution_id",
        "created_at",
        "updated_at",
    ],
    "course_offerings": [
        "id",
        "course_id",
        "term_id",
        "institution_id",
        "status",
        "capacity",
        "total_enrollment",
        "section_count",
        "created_at",
        "updated_at",
    ],
    "course_sections": [
        "id",
        "offering_id",
        "instructor_id",
        "section_number",
        "enrollment",
        "status",
        "grade_distribution",
        "assigned_date",
        "completed_date",
        "created_at",
        "updated_at",
    ],
    "course_outcomes": [
        "id",
        "course_id",
        "clo_number",
        "description",
        "assessment_method",
        "active",
        "assessment_data",
        "narrative",
        "created_at",
        "updated_at",
    ],
    "user_invitations": [
        "id",
        "email",
        "role",
        "institution_id",
        "invited_by",
        "invited_at",
        "status",
        "accepted_at",
        "personal_message",
        "created_at",
        "updated_at",
    ],
}


class GenericCSVAdapter(FileBaseAdapter):
    """
    Generic CSV adapter for institution-agnostic data import/export.

    Format: ZIP file containing normalized CSV files (one per entity type)
    Version: 1.0
    """

    def get_adapter_info(self) -> Dict[str, Any]:
        """Return adapter metadata for UI and filtering."""
        return {
            "id": "generic_csv_v1",
            "name": "Generic CSV Format (ZIP)",
            "description": "Institution-agnostic normalized CSV format. ZIP file containing separate CSV files for each entity type. Security-first: excludes passwords and tokens.",
            "supported_formats": [".zip"],
            "institution_id": None,  # Generic - works for all institutions
            "data_types": [
                "institutions",
                "programs",
                "users",
                "courses",
                "terms",
                "course_offerings",
                "course_sections",
                "course_outcomes",
                "user_invitations",
            ],
            "version": FORMAT_VERSION,
            "is_bidirectional": True,
            "security_note": "Passwords and active tokens are excluded. Imported users must complete registration.",
        }

    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        """
        Check if uploaded file is a valid Generic CSV ZIP export.

        Validates:
        - File is a ZIP archive
        - Contains manifest.json
        - Manifest has correct version
        - Required CSV files are present

        Args:
            file_path: Path to uploaded file

        Returns:
            Tuple[bool, str]: (is_compatible, message)
        """
        try:
            path = Path(file_path)

            # Check file extension
            if path.suffix.lower() != ".zip":
                return False, f"Invalid file type: {path.suffix}. Expected .zip"

            # Try to open as ZIP
            try:
                with zipfile.ZipFile(file_path, "r") as zf:
                    file_list = zf.namelist()

                    # Check for manifest.json
                    if "manifest.json" not in file_list:
                        return False, "Missing manifest.json in ZIP archive"

                    # Read and validate manifest
                    manifest_data = zf.read("manifest.json")
                    manifest = json.loads(manifest_data)

                    # Check format version
                    if manifest.get("format_version") != FORMAT_VERSION:
                        return (
                            False,
                            f"Incompatible format version: {manifest.get('format_version')}. Expected {FORMAT_VERSION}",
                        )

                    # Check for required CSV files (at least institutions.csv)
                    if "institutions.csv" not in file_list:
                        return False, "Missing required file: institutions.csv"

                    # Count entities
                    entity_counts = manifest.get("entity_counts", {})
                    total_records = sum(entity_counts.values())

                    return (
                        True,
                        f"Valid Generic CSV export. Contains {total_records} total records across {len(entity_counts)} entity types.",
                    )

            except zipfile.BadZipFile:
                return False, "File is not a valid ZIP archive"
            except json.JSONDecodeError:
                return False, "Invalid manifest.json format"

        except Exception as e:
            logger.error(f"Error validating file compatibility: {e}", exc_info=True)
            return False, f"Validation error: {str(e)}"

    def detect_data_types(self, file_path: str) -> List[str]:
        """
        Detect what entity types are present in the ZIP export.

        Args:
            file_path: Path to ZIP file

        Returns:
            List of entity types found
        """
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Read manifest to get entity counts
                manifest_data = zf.read("manifest.json")
                manifest = json.loads(manifest_data)

                entity_counts = manifest.get("entity_counts", {})

                # Return entities that have at least 1 record
                data_types = [
                    entity for entity, count in entity_counts.items() if count > 0
                ]

                return data_types

        except Exception as e:
            logger.error(f"Error detecting data types: {e}", exc_info=True)
            return []

    def parse_file(
        self, file_path: str, options: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse ZIP file and extract all entity data.

        Args:
            file_path: Path to ZIP file
            options: Import options (conflict_resolution, dry_run, etc.)

        Returns:
            Dictionary mapping entity types to lists of records
        """
        # TODO: Implement in Step 6 (Import Implementation)
        raise NotImplementedError("Import functionality will be implemented in Step 6")

    def export_data(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        output_path: str,
        options: Dict[str, Any],
    ) -> Tuple[bool, str, int]:
        """
        Export data to ZIP file containing normalized CSVs.

        Args:
            data: Dictionary of entity types to records
            output_path: Where to write the ZIP file
            options: Export options

        Returns:
            Tuple[bool, str, int]: (success, message, record_count)
        """
        # TODO: Implement in Step 3 (Export Implementation)
        raise NotImplementedError("Export functionality will be implemented in Step 3")
