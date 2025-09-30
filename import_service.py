"""
Import Service Module

This module provides a comprehensive import system for course data with conflict
resolution, dry-run capabilities, and support for multiple data sources.
Built using the new adapter registry system for extensible, institution-agnostic imports.
"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from adapters.adapter_registry import AdapterRegistryError, get_adapter_registry

# Constants for datetime formatting
UTC_OFFSET = "+00:00"
from database_service import (
    create_course,
    create_course_offering,
    create_course_section,
    create_default_cei_institution,
    create_term,
    create_user,
    get_course_by_number,
    get_course_offering_by_course_and_term,
    get_institution_by_short_name,
    get_term_by_name,
    get_user_by_email,
    update_user,
)

# Import our models and services
from models import (
    format_term_name,
    validate_course_number,
)


class ConflictStrategy(Enum):
    """Conflict resolution strategies"""

    USE_MINE = "use_mine"  # Keep existing data, log conflicts
    USE_THEIRS = "use_theirs"  # Overwrite with import data
    MERGE = "merge"  # Intelligent merge (future enhancement)
    MANUAL_REVIEW = "manual_review"  # Flag for human review


class ImportMode(Enum):
    """Import execution modes"""

    DRY_RUN = "dry_run"  # Simulate import, don't make changes
    EXECUTE = "execute"  # Actually perform the import


@dataclass
class ConflictRecord:
    """Record of a data conflict during import"""

    entity_type: str
    entity_id: str
    field_name: str
    existing_value: Any
    import_value: Any
    resolution: str
    timestamp: datetime


@dataclass
class ImportResult:
    """Result of an import operation"""

    success: bool
    records_processed: int
    records_created: int
    records_updated: int
    records_skipped: int
    conflicts_detected: int
    conflicts_resolved: int
    errors: List[str]
    warnings: List[str]
    conflicts: List[ConflictRecord]
    execution_time: float
    dry_run: bool


def _convert_datetime_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert string datetime fields to datetime objects for SQLite compatibility.

    Args:
        data: Dictionary that may contain datetime fields as strings

    Returns:
        Dictionary with datetime strings converted to datetime objects
    """
    datetime_fields = [
        "created_at",
        "updated_at",
        "invited_at",
        "expires_at",
        "accepted_at",
    ]
    converted_data = data.copy()

    for field in datetime_fields:
        if field in converted_data and isinstance(converted_data[field], str):
            try:
                # Parse ISO format datetime strings to datetime objects
                # Handle both with and without microseconds
                datetime_str = converted_data[field]
                if "." in datetime_str and datetime_str.endswith("Z"):
                    # Handle format like "2025-09-28T17:41:27.935901Z"
                    datetime_str = datetime_str[:-1] + UTC_OFFSET
                elif not datetime_str.endswith(
                    UTC_OFFSET
                ) and not datetime_str.endswith("Z"):
                    # Handle format like "2025-09-28T17:41:27.935901" (assume UTC)
                    if "." in datetime_str:
                        datetime_str = datetime_str + UTC_OFFSET
                    else:
                        datetime_str = datetime_str + ".000000" + UTC_OFFSET

                converted_data[field] = datetime.fromisoformat(datetime_str)
            except (ValueError, TypeError):
                # If parsing fails, leave as is (might be None or already datetime)
                pass

    return converted_data


class ImportService:
    """Service for handling data imports with conflict resolution using the adapter registry system"""

    def __init__(self, institution_id, verbose=False, progress_callback=None):
        """
        Initialize the ImportService for a specific institution.

        Args:
            institution_id: Required ID of the institution to import data for
            verbose: Enable verbose logging output
            progress_callback: Optional callback for progress updates
        """
        if not institution_id:
            raise ValueError("institution_id is required")

        self.institution_id = institution_id
        self.verbose = verbose
        self.progress_callback = progress_callback
        self._processed_users = set()  # Track users we've already processed
        self._processed_courses = set()  # Track courses we've already processed

        # Get centralized logger
        from logging_config import get_import_logger

        self.logger = get_import_logger()

        self.reset_stats()

    def reset_stats(self):
        """Reset import statistics"""
        self.stats = {
            "records_processed": 0,
            "records_created": 0,
            "records_updated": 0,
            "records_skipped": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "errors": [],
            "warnings": [],
            "conflicts": [],
        }

    def _log(self, message: str, level: str = "info"):
        """Smart logging that respects verbose mode"""
        if self.verbose or level in ["error", "warning", "summary"]:
            if level == "error":
                self.logger.error(message)
            elif level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)

    def import_excel_file(
        self,
        file_path: str,
        conflict_strategy: ConflictStrategy = ConflictStrategy.USE_THEIRS,
        dry_run: bool = False,
        adapter_id: str = "cei_excel_format_v1",
    ) -> ImportResult:
        """
        Import data from Excel file using the new adapter system

        Args:
            file_path: Path to Excel file
            conflict_strategy: How to resolve conflicts
            dry_run: If True, simulate import without making changes
            adapter_id: ID of the adapter to use for parsing

        Returns:
            ImportResult with detailed statistics
        """
        start_time = datetime.now(timezone.utc)
        self.reset_stats()

        self._log_import_start(file_path, conflict_strategy, dry_run)

        try:
            # Validate and prepare for import
            adapter = self._prepare_import(file_path, adapter_id, start_time, dry_run)
            if not adapter:
                return self._create_import_result(start_time, dry_run)

            # Parse file data
            parsed_data = self._parse_file_data(
                adapter, file_path, adapter_id, start_time, dry_run
            )
            if not parsed_data:
                return self._create_import_result(start_time, dry_run)

            # Process all parsed data
            self._process_parsed_data(parsed_data, conflict_strategy, dry_run)

        except Exception as e:
            error_msg = f"Unexpected error during import: {str(e)}"
            self.stats["errors"].append(error_msg)
            self.logger.error(f"[Import] {error_msg}")

        return self._create_import_result(start_time, dry_run)

    def _log_import_start(
        self, file_path: str, conflict_strategy: ConflictStrategy, dry_run: bool
    ):
        """Log import start information."""
        self.logger.info(f"[Import] Starting import from: {file_path}")
        self.logger.info(f"[Import] Conflict strategy: {conflict_strategy.value}")
        self.logger.info(f"[Import] Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")

    def _prepare_import(
        self, file_path: str, adapter_id: str, start_time, dry_run: bool
    ):
        """Prepare import by validating file and getting adapter."""
        # Validate file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.stats["errors"].append(error_msg)
            return None

        # Get adapter from registry
        try:
            registry = get_adapter_registry()
            adapter = registry.get_adapter_by_id(adapter_id)
            if not adapter:
                error_msg = f"Adapter not found: {adapter_id}"
                self.stats["errors"].append(error_msg)
                return None
        except AdapterRegistryError as e:
            error_msg = f"Failed to get adapter {adapter_id}: {str(e)}"
            self.stats["errors"].append(error_msg)
            return None

        # Validate file compatibility with adapter
        try:
            is_compatible, validation_message = adapter.validate_file_compatibility(
                file_path
            )
            if not is_compatible:
                error_msg = (
                    f"File incompatible with adapter {adapter_id}: {validation_message}"
                )
                self.stats["errors"].append(error_msg)
                return None

            self.logger.info(f"[Import] File validation passed: {validation_message}")
        except Exception as e:
            error_msg = f"File validation failed: {str(e)}"
            self.stats["errors"].append(error_msg)
            return None

        return adapter

    def _parse_file_data(
        self, adapter, file_path: str, adapter_id: str, start_time, dry_run: bool
    ):
        """Parse file data using the adapter."""
        try:
            parse_options = {"institution_id": self.institution_id}
            parsed_data = adapter.parse_file(file_path, parse_options)
            self.logger.info(
                f"[Import] Successfully parsed file with adapter {adapter_id}"
            )

            # Log what data types were found
            data_types = []
            for data_type, records in parsed_data.items():
                if records:
                    data_types.append(f"{data_type}: {len(records)}")
                    self.logger.info(
                        f"[Import] Found {len(records)} {data_type} records"
                    )

            if not data_types:
                error_msg = "No valid data found in file"
                self.stats["errors"].append(error_msg)
                return None

            return parsed_data

        except Exception as e:
            error_msg = f"Failed to parse file with adapter {adapter_id}: {str(e)}"
            self.stats["errors"].append(error_msg)
            return None

    def _process_parsed_data(
        self,
        parsed_data: Dict[str, List],
        conflict_strategy: ConflictStrategy,
        dry_run: bool,
    ):
        """Process all parsed data in dependency order."""
        all_conflicts = []
        total_records = sum(len(records) for records in parsed_data.values())
        processed_records = 0

        self.logger.info(f"[Import] Processing {total_records} total records")

        # Process each data type in dependency order
        processing_order = ["users", "courses", "terms", "offerings", "sections"]

        for data_type in processing_order:
            records = parsed_data.get(data_type, [])
            if not records:
                continue

            self.logger.info(f"[Import] Processing {len(records)} {data_type} records")

            conflicts = self._process_data_type_records(
                data_type,
                records,
                conflict_strategy,
                dry_run,
                processed_records,
                total_records,
            )
            all_conflicts.extend(conflicts)
            processed_records += len(records)

        self.stats["conflicts"].extend(all_conflicts)

    def _process_data_type_records(
        self,
        data_type: str,
        records: List,
        conflict_strategy: ConflictStrategy,
        dry_run: bool,
        processed_records: int,
        total_records: int,
    ) -> List:
        """Process records for a specific data type."""
        all_conflicts = []

        for record in records:
            processed_records += 1
            self.stats["records_processed"] += 1

            # Show progress periodically
            self._update_progress(processed_records, total_records, data_type)

            try:
                conflicts = self._process_single_record(
                    data_type, record, conflict_strategy, dry_run
                )
                all_conflicts.extend(conflicts)

            except Exception as e:
                error_msg = f"Error processing {data_type} record: {str(e)}"
                self.stats["errors"].append(error_msg)
                self.logger.error(f"[Import] {error_msg}")

        return all_conflicts

    def _update_progress(
        self, processed_records: int, total_records: int, data_type: str
    ):
        """Update progress reporting."""
        progress = int(processed_records / total_records * 100)
        if (
            processed_records % max(1, total_records // 20) == 0
            or processed_records == total_records
        ):
            self._log(
                f"Processing record {processed_records}/{total_records} ({progress}%)",
                "summary",
            )

            if self.progress_callback:
                self.progress_callback(
                    percentage=progress,
                    records_processed=processed_records,
                    total_records=total_records,
                    message=f"Processing {data_type} record {processed_records}/{total_records} ({progress}%)",
                )

    def _process_single_record(
        self,
        data_type: str,
        record: Dict,
        conflict_strategy: ConflictStrategy,
        dry_run: bool,
    ) -> List:
        """Process a single record based on its data type."""
        if data_type == "courses":
            _, conflicts = self.process_course_import(
                record, conflict_strategy, dry_run
            )
            return conflicts
        elif data_type == "users":
            _, conflicts = self.process_user_import(record, conflict_strategy, dry_run)
            return conflicts
        elif data_type == "terms":
            self._process_term_import(record, dry_run)
            return []
        elif data_type == "offerings":
            self._process_offering_import(record, conflict_strategy, dry_run)
            return []
        elif data_type == "sections":
            self._process_section_import(record, conflict_strategy, dry_run)
            return []
        else:
            return []

    def process_course_import(
        self,
        course_data: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool = False,
    ) -> Tuple[bool, List[ConflictRecord]]:
        """
        Process course import with conflict resolution

        Args:
            course_data: Course data to import
            strategy: Conflict resolution strategy
            dry_run: If True, simulate without making changes

        Returns:
            Tuple of (success, conflicts)
        """
        conflicts: List[ConflictRecord] = []

        try:
            course_number = course_data.get("course_number")
            if not course_number:
                self.stats["errors"].append("Course missing course_number")
                return False, conflicts

            # Check if course already exists
            existing_course = get_course_by_number(course_number)

            if existing_course:
                return self._handle_existing_course(
                    course_data, existing_course, strategy, dry_run, conflicts
                )
            else:
                return self._handle_new_course(
                    course_data, course_number, dry_run, conflicts
                )

        except Exception as e:
            self.stats["errors"].append(
                f"Error processing course {course_data.get('course_number')}: {str(e)}"
            )
            return False, conflicts

    def _handle_existing_course(
        self,
        course_data: Dict[str, Any],
        existing_course: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool,
        conflicts: List[ConflictRecord],
    ) -> Tuple[bool, List[ConflictRecord]]:
        """Handle import of an existing course with conflict resolution."""
        course_number = course_data.get("course_number")

        # Detect conflicts by comparing fields
        detected_conflicts = self._detect_course_conflicts(
            course_data, existing_course, course_number
        )
        conflicts.extend(detected_conflicts)

        if detected_conflicts:
            self.stats["conflicts_detected"] += len(detected_conflicts)

        # Handle conflict based on strategy
        return self._resolve_course_conflicts(
            strategy, detected_conflicts, course_data, course_number, dry_run, conflicts
        )

    def _detect_course_conflicts(
        self,
        course_data: Dict[str, Any],
        existing_course: Dict[str, Any],
        course_number: str,
    ) -> List[ConflictRecord]:
        """Detect conflicts between import data and existing course."""
        detected_conflicts = []

        for field, new_value in course_data.items():
            if field == "course_number":
                continue  # Skip course_number as it's the key
            existing_value = existing_course.get(field)
            if existing_value != new_value:
                conflict = ConflictRecord(
                    entity_type="course",
                    entity_id=existing_course.get("course_id", course_number),
                    field_name=field,
                    existing_value=existing_value,
                    import_value=new_value,
                    resolution="pending",
                    timestamp=datetime.now(timezone.utc),
                )
                detected_conflicts.append(conflict)

        return detected_conflicts

    def _resolve_course_conflicts(
        self,
        strategy: ConflictStrategy,
        detected_conflicts: List[ConflictRecord],
        course_data: Dict[str, Any],
        course_number: str,
        dry_run: bool,
        conflicts: List[ConflictRecord],
    ) -> Tuple[bool, List[ConflictRecord]]:
        """Resolve course conflicts based on strategy."""
        if strategy == ConflictStrategy.USE_MINE:
            self.stats["records_skipped"] += 1
            self._log(f"Skipping existing course: {course_number}")
            return True, conflicts
        elif strategy == ConflictStrategy.USE_THEIRS:
            if detected_conflicts:
                self.stats["conflicts_resolved"] += len(detected_conflicts)
                # Update conflict resolution status
                for conflict in detected_conflicts:
                    conflict.resolution = strategy.value

            if not dry_run:
                # Update existing course with import data
                converted_course_data = _convert_datetime_fields(course_data)
                # TODO: Implement proper update_course function
                self.stats["records_updated"] += 1
                self._log(
                    f"Updated course: {course_number} (update logic needs implementation)"
                )
            else:
                self._log(f"DRY RUN: Would update course: {course_number}")
            return True, conflicts

        return True, conflicts

    def _handle_new_course(
        self,
        course_data: Dict[str, Any],
        course_number: str,
        dry_run: bool,
        conflicts: List[ConflictRecord],
    ) -> Tuple[bool, List[ConflictRecord]]:
        """Handle import of a new course."""
        if not dry_run:
            create_course(course_data)
            self.stats["records_created"] += 1
            self._log(f"Created course: {course_number}")
        else:
            self.stats["records_skipped"] += 1
            self._log(f"DRY RUN: Would create course: {course_number}")

        return True, conflicts

    def process_user_import(
        self,
        user_data: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool = False,
    ) -> Tuple[bool, List[ConflictRecord]]:
        """
        Process user import with conflict resolution

        Args:
            user_data: User data to import
            strategy: Conflict resolution strategy
            dry_run: If True, simulate without making changes

        Returns:
            Tuple of (success, conflicts)
        """
        conflicts: List[ConflictRecord] = []

        try:
            email = user_data.get("email")
            if not email:
                self.stats["errors"].append("User missing email")
                return False, conflicts

            # Check if user already exists
            existing_user = get_user_by_email(email)

            if existing_user:
                return self._handle_existing_user(
                    user_data, existing_user, strategy, dry_run, conflicts
                )
            else:
                return self._handle_new_user(user_data, email, dry_run, conflicts)

        except Exception as e:
            self.stats["errors"].append(
                f"Error processing user {user_data.get('email')}: {str(e)}"
            )
            return False, conflicts

    def _handle_existing_user(
        self,
        user_data: Dict[str, Any],
        existing_user: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool,
        conflicts: List[ConflictRecord],
    ) -> Tuple[bool, List[ConflictRecord]]:
        """Handle import of an existing user with conflict resolution."""
        email = user_data.get("email")

        # Detect conflicts by comparing fields
        detected_conflicts = self._detect_user_conflicts(
            user_data, existing_user, email
        )
        conflicts.extend(detected_conflicts)

        if detected_conflicts:
            self.stats["conflicts_detected"] += len(detected_conflicts)

        # Handle conflict based on strategy
        return self._resolve_user_conflicts(
            strategy,
            detected_conflicts,
            user_data,
            existing_user,
            email,
            dry_run,
            conflicts,
        )

    def _detect_user_conflicts(
        self, user_data: Dict[str, Any], existing_user: Dict[str, Any], email: str
    ) -> List[ConflictRecord]:
        """Detect conflicts between import data and existing user."""
        detected_conflicts = []

        for field, new_value in user_data.items():
            if field == "email":
                continue  # Skip email as it's the key
            existing_value = existing_user.get(field)
            if existing_value != new_value:
                conflict = ConflictRecord(
                    entity_type="user",
                    entity_id=existing_user.get("user_id", email),
                    field_name=field,
                    existing_value=existing_value,
                    import_value=new_value,
                    resolution="pending",
                    timestamp=datetime.now(timezone.utc),
                )
                detected_conflicts.append(conflict)

        return detected_conflicts

    def _resolve_user_conflicts(
        self,
        strategy: ConflictStrategy,
        detected_conflicts: List[ConflictRecord],
        user_data: Dict[str, Any],
        existing_user: Dict[str, Any],
        email: str,
        dry_run: bool,
        conflicts: List[ConflictRecord],
    ) -> Tuple[bool, List[ConflictRecord]]:
        """Resolve user conflicts based on strategy."""
        if strategy == ConflictStrategy.USE_MINE:
            self.stats["records_skipped"] += 1
            self._log(f"Skipping existing user: {email}")
            return True, conflicts
        elif strategy == ConflictStrategy.USE_THEIRS:
            if detected_conflicts:
                self.stats["conflicts_resolved"] += len(detected_conflicts)
                # Update conflict resolution status
                for conflict in detected_conflicts:
                    conflict.resolution = strategy.value

            if not dry_run:
                # Update existing user - convert datetime fields for SQLite compatibility
                converted_user_data = _convert_datetime_fields(user_data)
                update_user(
                    existing_user.get("user_id", existing_user.get("id", email)),
                    converted_user_data,
                )
                self.stats["records_updated"] += 1
                self._log(f"Updated user: {email}")
            else:
                self._log(f"DRY RUN: Would update user: {email}")
            return True, conflicts

        return True, conflicts

    def _handle_new_user(
        self,
        user_data: Dict[str, Any],
        email: str,
        dry_run: bool,
        conflicts: List[ConflictRecord],
    ) -> Tuple[bool, List[ConflictRecord]]:
        """Handle import of a new user."""
        if not dry_run:
            create_user(user_data)
            self.stats["records_created"] += 1
            self._log(f"Created user: {email}")
        else:
            self._log(f"DRY RUN: Would create user: {email}")

        return True, conflicts

    def _process_term_import(self, term_data: Dict[str, Any], dry_run: bool = False):
        """Process term import (simplified implementation)"""
        try:
            term_name = term_data.get("term_name")
            if not term_name:
                self.stats["errors"].append("Term missing term_name")
                return

            existing_term = get_term_by_name(term_name, self.institution_id)

            if existing_term:
                self.stats["records_skipped"] += 1
                self._log(f"Term already exists: {term_name}")
            else:
                if not dry_run:
                    create_term(term_data)
                    self.stats["records_created"] += 1
                    self._log(f"Created term: {term_name}")
                else:
                    self._log(f"DRY RUN: Would create term: {term_name}")

        except Exception as e:
            self.stats["errors"].append(
                f"Error processing term {term_data.get('term_name')}: {str(e)}"
            )

    def _process_offering_import(
        self,
        offering_data: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool = False,
    ):
        """Process course offering import (placeholder implementation)"""
        try:
            # Simplified offering processing
            # TODO: Implement proper offering creation using offering_data and strategy
            if not dry_run:
                # This would need proper offering creation logic
                self.stats["records_created"] += 1
                self._log(
                    f"Created offering for {offering_data.get('course_id', 'unknown course')}"
                )
            else:
                self._log(
                    f"DRY RUN: Would create offering for {offering_data.get('course_id', 'unknown course')}"
                )

        except Exception as e:
            self.stats["errors"].append(f"Error processing offering: {str(e)}")

    def _process_section_import(
        self,
        section_data: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool = False,
    ):
        """Process course section import (placeholder implementation)"""
        try:
            # Simplified section processing
            # TODO: Implement proper section creation using section_data and strategy
            if not dry_run:
                # This would need proper section creation logic
                self.stats["records_created"] += 1
                self._log(
                    f"Created section {section_data.get('section_number', 'unknown')} for {section_data.get('course_id', 'unknown course')}"
                )
            else:
                self._log(
                    f"DRY RUN: Would create section {section_data.get('section_number', 'unknown')} for {section_data.get('course_id', 'unknown course')}"
                )

        except Exception as e:
            self.stats["errors"].append(f"Error processing section: {str(e)}")

    def _create_import_result(
        self, start_time: datetime, dry_run: bool
    ) -> ImportResult:
        """Create ImportResult with current statistics"""
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()

        return ImportResult(
            success=len(self.stats["errors"]) == 0,
            records_processed=self.stats["records_processed"],
            records_created=self.stats["records_created"],
            records_updated=self.stats["records_updated"],
            records_skipped=self.stats["records_skipped"],
            conflicts_detected=self.stats["conflicts_detected"],
            conflicts_resolved=self.stats["conflicts_resolved"],
            errors=self.stats["errors"],
            warnings=self.stats["warnings"],
            conflicts=self.stats["conflicts"],
            execution_time=execution_time,
            dry_run=dry_run,
        )


# Convenience functions
def import_excel(
    file_path: str,
    institution_id: str,
    conflict_strategy: str = "use_theirs",
    dry_run: bool = False,
    adapter_id: str = "cei_excel_format_v1",
    verbose: bool = False,
    progress_callback: Optional[Callable] = None,
) -> ImportResult:
    """
    Convenience function to import Excel file

    Args:
        file_path: Path to Excel file
        institution_id: Required ID of the institution to import data for
        conflict_strategy: "use_mine", "use_theirs", "merge", or "manual_review"
        dry_run: If True, simulate import without making changes
        adapter_id: ID of the adapter to use
        verbose: Enable verbose logging
        progress_callback: Optional callback for progress updates

    Returns:
        ImportResult with detailed statistics
    """
    strategy_map = {
        "use_mine": ConflictStrategy.USE_MINE,
        "use_theirs": ConflictStrategy.USE_THEIRS,
        "merge": ConflictStrategy.MERGE,
        "manual_review": ConflictStrategy.MANUAL_REVIEW,
    }

    strategy = strategy_map.get(conflict_strategy, ConflictStrategy.USE_THEIRS)

    # Create service instance with institution ID, verbose setting and progress callback
    service = ImportService(
        institution_id=institution_id,
        verbose=verbose,
        progress_callback=progress_callback,
    )

    return service.import_excel_file(
        file_path=file_path,
        conflict_strategy=strategy,
        dry_run=dry_run,
        adapter_id=adapter_id,
    )


def create_import_report(result: ImportResult) -> str:
    """Create a detailed import report"""
    report = []
    report.append("=" * 60)
    report.append("IMPORT REPORT")
    report.append("=" * 60)
    report.append(f"Success: {result.success}")
    report.append(f"Mode: {'DRY RUN' if result.dry_run else 'EXECUTE'}")
    report.append(f"Execution Time: {result.execution_time:.2f}s")
    report.append("")
    report.append("STATISTICS:")
    report.append(f"  Records Processed: {result.records_processed}")
    report.append(f"  Records Created: {result.records_created}")
    report.append(f"  Records Updated: {result.records_updated}")
    report.append(f"  Records Skipped: {result.records_skipped}")
    report.append(f"  Conflicts Detected: {result.conflicts_detected}")
    report.append(f"  Conflicts Resolved: {result.conflicts_resolved}")

    if result.errors:
        report.append("")
        report.append("ERRORS:")
        for error in result.errors:
            report.append(f"  - {error}")

    if result.warnings:
        report.append("")
        report.append("WARNINGS:")
        for warning in result.warnings:
            report.append(f"  - {warning}")

    if result.conflicts:
        report.append("")
        report.append("CONFLICTS:")
        for conflict in result.conflicts:
            report.append(
                f"  - {conflict.entity_type} {conflict.entity_id}: {conflict.field_name}"
            )
            report.append(f"    Existing: {conflict.existing_value}")
            report.append(f"    Import: {conflict.import_value}")
            report.append(f"    Resolution: {conflict.resolution}")

    report.append("=" * 60)
    return "\n".join(report)
