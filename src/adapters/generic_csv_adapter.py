"""
Generic CSV Adapter - Institution-Agnostic Import/Export

This adapter provides a generic, normalized CSV format for importing and exporting
course management data. Unlike institution-specific adapters (Gemini, etc.), this adapter
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
from typing import Any, Dict, List, Tuple

from .file_base_adapter import FileBaseAdapter

logger = logging.getLogger(__name__)

# Format version for compatibility checking
FORMAT_VERSION = "1.0"

# Manifest filename constant
MANIFEST_FILENAME = "manifest.json"

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
        "program_id",
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
        "account_status",
        "email_verified",
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
            "public": True,  # Available to ALL users regardless of institution
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

                    # Check for manifest
                    if MANIFEST_FILENAME not in file_list:
                        return False, f"Missing {MANIFEST_FILENAME} in ZIP archive"

                    # Read and validate manifest
                    manifest_data = zf.read(MANIFEST_FILENAME)
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
                manifest_data = zf.read(MANIFEST_FILENAME)
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
        try:
            # Validate ZIP format
            try:
                with zipfile.ZipFile(file_path, "r") as zf:
                    file_list = zf.namelist()

                    # Check for manifest
                    if MANIFEST_FILENAME not in file_list:
                        raise ValueError(f"Missing {MANIFEST_FILENAME} in ZIP archive")

                    # Read and validate manifest
                    manifest_data = zf.read(MANIFEST_FILENAME)
                    manifest = json.loads(manifest_data)

                    # Validate format version
                    if manifest.get("format_version") != FORMAT_VERSION:
                        raise ValueError(
                            f"Incompatible format version: {manifest.get('format_version')}. Expected {FORMAT_VERSION}"
                        )

                    # Get import order from manifest
                    import_order = manifest.get("import_order", EXPORT_ORDER)

                    # Extract and parse each entity type
                    result: Dict[str, List[Dict[str, Any]]] = {}

                    for entity_type in import_order:
                        csv_filename = f"{entity_type}.csv"

                        if csv_filename not in file_list:
                            # Entity type not in export - skip
                            result[entity_type] = []
                            continue

                        # Read CSV
                        csv_content = zf.read(csv_filename).decode("utf-8")

                        # Parse CSV
                        records = self._parse_entity_csv(csv_content, entity_type)

                        result[entity_type] = records

                    logger.info(
                        f"Import parsed: {sum(len(r) for r in result.values())} total records across {len(result)} entity types"
                    )

                    return result

            except zipfile.BadZipFile as e:
                raise ValueError(f"File is not a valid ZIP archive: {e}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid manifest.json format: {e}")

        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            raise

    def _parse_entity_csv(
        self, csv_content: str, entity_type: str
    ) -> List[Dict[str, Any]]:
        """
        Parse CSV content for a single entity type.

        Args:
            csv_content: Raw CSV string
            entity_type: Type of entity (institutions, users, etc.)

        Returns:
            List of parsed record dictionaries
        """
        records = []

        try:
            # Parse CSV
            csv_reader = csv.DictReader(csv_content.splitlines())

            for row in csv_reader:
                # Deserialize and clean record
                record = self._deserialize_record(row)
                records.append(record)

        except Exception as e:
            logger.error(f"Error parsing {entity_type} CSV: {e}")
            raise

        return records

    def _try_parse_json(self, value: str) -> Any:
        """Try to parse value as JSON, return original on failure."""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value

    def _try_parse_datetime(self, value: str) -> Any:
        """Try to parse value as ISO 8601 datetime, return original on failure."""
        try:
            from datetime import datetime

            # Handle 'Z' timezone indicator
            val_to_parse = value[:-1] + "+00:00" if value.endswith("Z") else value
            return datetime.fromisoformat(val_to_parse)
        except (ValueError, AttributeError, TypeError):
            return value

    def _deserialize_value(self, key: str, value: Any) -> Any:
        """
        Deserialize a single CSV value to appropriate Python type.

        Args:
            key: Field name
            value: String value from CSV

        Returns:
            Properly typed value
        """
        # Handle empty/None
        if value == "" or value is None:
            return None

        # Non-string values pass through
        if not isinstance(value, str):
            return value

        # JSON fields
        if key in {"grade_distribution", "assessment_data", "extras"}:
            return self._try_parse_json(value)

        # Boolean fields
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # DateTime fields (ISO 8601)
        return self._try_parse_datetime(value)

    def _deserialize_record(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Deserialize CSV row values to appropriate Python types.

        Args:
            row: CSV row as dictionary (all values are strings)

        Returns:
            Record with properly typed values
        """
        return {key: self._deserialize_value(key, value) for key, value in row.items()}

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
        try:
            # Create temporary directory for CSV files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                total_records = 0
                entity_counts = {}

                # Export each entity type to separate CSV
                for entity_type in EXPORT_ORDER:
                    records = data.get(entity_type, [])
                    csv_file = temp_path / f"{entity_type}.csv"

                    # Write CSV (even if empty)
                    record_count = self._write_entity_csv(
                        entity_type, records, str(csv_file)
                    )

                    entity_counts[entity_type] = record_count
                    total_records += record_count

                # Create manifest
                manifest = self._create_manifest(entity_counts)
                manifest_file = temp_path / MANIFEST_FILENAME
                manifest_file.write_text(json.dumps(manifest, indent=2))

                # Create ZIP archive
                self._create_zip_archive(temp_path, output_path)

                logger.info(
                    f"Export successful: {total_records} records across {len(entity_counts)} entity types"
                )

                return (
                    True,
                    f"Successfully exported {total_records} records",
                    total_records,
                )

        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            return False, f"Export failed: {str(e)}", 0

    def _write_entity_csv(
        self, entity_type: str, records: List[Dict[str, Any]], output_file: str
    ) -> int:
        """
        Write records for a single entity type to CSV file.

        Args:
            entity_type: Type of entity (institutions, users, etc.)
            records: List of record dictionaries
            output_file: Path to output CSV file

        Returns:
            Number of records written
        """
        columns = CSV_COLUMNS.get(entity_type, [])
        if not columns:
            logger.warning(f"No column definition for entity type: {entity_type}")
            return 0

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for record in records:
                # Filter and serialize record
                filtered_record = self._filter_and_serialize_record(record, columns)
                writer.writerow(filtered_record)

        return len(records)

    def _filter_and_serialize_record(
        self, record: Dict[str, Any], columns: List[str]
    ) -> Dict[str, Any]:
        """
        Filter record to only include specified columns and serialize complex types.

        Args:
            record: Original record dictionary
            columns: List of allowed column names

        Returns:
            Filtered and serialized record
        """
        filtered = {}

        for col in columns:
            value = record.get(col)

            # Serialize value based on type
            if value is None:
                filtered[col] = ""  # NULL as empty string
            elif isinstance(value, datetime):
                filtered[col] = value.isoformat()  # ISO 8601 format
            elif isinstance(value, bool):
                filtered[col] = "true" if value else "false"  # Lowercase boolean
            elif isinstance(value, dict):
                filtered[col] = json.dumps(value)  # JSON fields
            elif isinstance(value, (list, tuple)):
                filtered[col] = json.dumps(value)  # JSON arrays
            else:
                filtered[col] = str(value)

        return filtered

    def _create_manifest(self, entity_counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Create manifest.json metadata.

        Args:
            entity_counts: Dictionary of entity types to record counts

        Returns:
            Manifest dictionary
        """
        return {
            "format_version": FORMAT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "entity_counts": entity_counts,
            "import_order": EXPORT_ORDER,
            "security_note": "Passwords and active tokens excluded. Imported users must complete registration.",
        }

    def _create_zip_archive(self, source_dir: Path, output_path: str) -> None:
        """
        Create ZIP archive from directory contents.

        Args:
            source_dir: Directory containing files to ZIP
            output_path: Path to output ZIP file
        """
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add only CSV and JSON files (excludes system files like .DS_Store)
            # Use glob (not rglob) since all export files are at root level
            for file_path in sorted(source_dir.glob("*")):
                if file_path.is_file() and file_path.suffix.lower() in {
                    ".csv",
                    ".json",
                }:
                    # Use filename as archive name (all files at root level)
                    zf.write(file_path, file_path.name)
