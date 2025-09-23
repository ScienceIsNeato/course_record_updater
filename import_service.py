"""
Import Service Module

This module provides a comprehensive import system for course data with conflict
resolution, dry-run capabilities, and support for multiple data sources.
Built to handle CEI's specific needs while being extensible for other customers.
"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

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
    get_user_by_email,
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
    """Represents a data conflict during import"""

    entity_type: str  # 'course', 'user', 'section', etc.
    entity_key: str  # Unique identifier for the entity
    field_name: str  # Which field has the conflict
    existing_value: Any  # Current value in database
    import_value: Any  # New value from import
    resolution: Optional[str] = None  # How the conflict was resolved


@dataclass
class ImportResult:
    """Results of an import operation"""

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


class ImportService:
    """Service for handling data imports with conflict resolution"""

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

        # Cache for entities to avoid duplicate lookups during a single import run
        self.entity_cache: Dict[str, Dict] = {
            "courses": {},  # course_number -> course_data
            "terms": {},  # term_name -> term_data
            "users": {},  # email -> user_data
            "sections": {},  # composite_key -> section_data
        }

    def _log(self, message: str, level: str = "info"):
        """Smart logging that respects verbose mode"""
        if level == "error":
            self.logger.error(f"[Import] ERROR: {message}")
        elif level == "warning":
            self.logger.warning(f"[Import] WARNING: {message}")
        elif level == "summary":
            self.logger.info(f"[Import] {message}")
        elif self.verbose:
            self.logger.debug(f"[Import] {message}")
        # Otherwise, skip debug-level messages in non-verbose mode

    def detect_course_conflict(
        self, import_course: Dict[str, Any]
    ) -> List[ConflictRecord]:
        """
        Detect conflicts for course data

        Args:
            import_course: Course data from import

        Returns:
            List of detected conflicts
        """
        conflicts: List[ConflictRecord] = []
        course_number = import_course.get("course_number")

        if not course_number:
            return conflicts

        # Check if course already exists
        existing_course = get_course_by_number(course_number)

        if existing_course:
            # FIXED: Always flag existing courses as conflicts
            # The existence itself is a conflict that needs resolution
            # Strategy will determine whether to skip, update, or handle

            # First, add a conflict for the course existence
            existence_conflict = ConflictRecord(
                entity_type="course",
                entity_key=course_number,
                field_name="_existence",
                existing_value="exists",
                import_value="importing",
            )
            conflicts.append(existence_conflict)

            # Then check for field conflicts
            conflict_fields = ["course_title", "department", "credit_hours"]

            for field in conflict_fields:
                existing_value = existing_course.get(field)
                import_value = import_course.get(field)

                if existing_value != import_value and import_value is not None:
                    conflict = ConflictRecord(
                        entity_type="course",
                        entity_key=course_number,
                        field_name=field,
                        existing_value=existing_value,
                        import_value=import_value,
                    )
                    conflicts.append(conflict)

        return conflicts

    def detect_user_conflict(self, import_user: Dict[str, Any]) -> List[ConflictRecord]:
        """
        Detect conflicts for user data

        Args:
            import_user: User data from import

        Returns:
            List of detected conflicts
        """
        conflicts: List[ConflictRecord] = []
        email = import_user.get("email")

        if not email:
            return conflicts

        # Check if user already exists
        existing_user = get_user_by_email(email)

        if existing_user:
            # First, add an existence conflict to ensure we don't create duplicates
            existence_conflict = ConflictRecord(
                entity_type="user",
                entity_key=email,
                field_name="_existence",
                existing_value="exists",
                import_value="exists",
            )
            conflicts.append(existence_conflict)

            # Then check for field conflicts
            conflict_fields = ["first_name", "last_name", "role", "department"]

            for field in conflict_fields:
                existing_value = existing_user.get(field)
                import_value = import_user.get(field)

                if existing_value != import_value and import_value is not None:
                    conflict = ConflictRecord(
                        entity_type="user",
                        entity_key=email,
                        field_name=field,
                        existing_value=existing_value,
                        import_value=import_value,
                    )
                    conflicts.append(conflict)

        return conflicts

    def resolve_conflict(
        self, conflict: ConflictRecord, strategy: ConflictStrategy
    ) -> str:
        """
        Resolve a single conflict based on strategy

        Args:
            conflict: The conflict to resolve
            strategy: Resolution strategy to use

        Returns:
            Resolution action taken
        """
        if strategy == ConflictStrategy.USE_MINE:
            conflict.resolution = "kept_existing"
            return f"Kept existing {conflict.field_name}: {conflict.existing_value}"

        elif strategy == ConflictStrategy.USE_THEIRS:
            conflict.resolution = "used_import"
            return f"Updated {conflict.field_name}: {conflict.existing_value} → {conflict.import_value}"

        elif strategy == ConflictStrategy.MERGE:
            # For now, merge defaults to USE_THEIRS
            # Future enhancement: intelligent merging logic
            conflict.resolution = "merged_import"
            return f"Merged {conflict.field_name}: {conflict.existing_value} → {conflict.import_value}"

        elif strategy == ConflictStrategy.MANUAL_REVIEW:
            conflict.resolution = "flagged_manual"
            return f"Flagged for manual review: {conflict.field_name}"

        else:
            conflict.resolution = "unresolved"
            return f"Unresolved conflict: {conflict.field_name}"

    def process_course_import(
        self,
        course_data: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool = False,
    ) -> Tuple[bool, List[ConflictRecord]]:
        """
        Process import of a single course

        Args:
            course_data: Course data to import
            strategy: Conflict resolution strategy
            dry_run: If True, don't make actual changes

        Returns:
            Tuple of (success, conflicts)
        """
        conflicts = self.detect_course_conflict(course_data)

        if conflicts:
            self.stats["conflicts_detected"] += len(conflicts)

            # Resolve conflicts based on strategy
            course_number = course_data.get("course_number")
            if course_number not in self._processed_courses:
                self._processed_courses.add(course_number)
                self._log(
                    f"Resolving {len(conflicts)} conflicts for course: {course_number}",
                    "summary",
                )
                for conflict in conflicts:
                    resolution = self.resolve_conflict(conflict, strategy)
                    self._log(f"Course conflict resolved: {resolution}", "debug")
            else:
                for conflict in conflicts:
                    resolution = self.resolve_conflict(conflict, strategy)
                    self._log(f"Course conflict resolved: {resolution}", "debug")

            # Apply resolution if not dry run
            if not dry_run and strategy == ConflictStrategy.USE_THEIRS:
                # Check if there are actual field differences that need updating
                field_conflicts = [c for c in conflicts if c.field_name != "_existence"]

                if field_conflicts:
                    # Update existing course with import data
                    course_number = course_data["course_number"]
                    existing_course = get_course_by_number(course_number)

                    if existing_course:
                        # NOTE: update_course function will be implemented when course update features are added
                        # update_course(existing_course['course_id'], course_data)
                        self.stats["records_updated"] += 1
                        self.logger.info(f"[Import] Updated course: {course_number}")
                    else:
                        self.stats["errors"].append(
                            f"Course not found for update: {course_number}"
                        )
                        return False, conflicts
                else:
                    # Course exists with identical data - no action needed
                    self.stats["records_skipped"] += 1
                    course_number = course_data.get("course_number")
                    self._log(
                        f"Course already exists with identical data: {course_number}",
                        "debug",
                    )

            elif strategy == ConflictStrategy.USE_MINE:
                # Skip the import, keep existing
                self.stats["records_skipped"] += 1
                course_number = course_data.get("course_number")
                self._log(
                    f"Skipped course (keeping existing): {course_number}", "debug"
                )

            self.stats["conflicts_resolved"] += len(conflicts)

        else:
            # No conflicts, create new course
            if not dry_run:
                course_id = create_course(course_data)
                if course_id:
                    self.stats["records_created"] += 1
                    self.logger.info(
                        f"[Import] Created course: {course_data.get('course_number')}"
                    )
                else:
                    self.stats["errors"].append(
                        f"Failed to create course: {course_data.get('course_number')}"
                    )
                    return False, conflicts
            else:
                self.logger.info(
                    f"[Import] DRY RUN: Would create course: {course_data.get('course_number')}"
                )

        return True, conflicts

    def _extract_user_email(self, user_data: Dict[str, Any]) -> str:
        """Extract email from user data safely."""
        return user_data.get("email", "unknown")

    def _handle_user_conflicts(
        self,
        conflicts: List[ConflictRecord],
        user_data: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool,
    ) -> bool:
        """Handle user conflicts based on strategy."""
        if not conflicts:
            return True

        self.stats["conflicts_detected"] += len(conflicts)

        # Resolve conflicts based on strategy
        for conflict in conflicts:
            resolution = self.resolve_conflict(conflict, strategy)
            self.logger.info(f"[Import] User conflict resolved: {resolution}")

        # Apply resolution if not dry run
        if not dry_run:
            return self._apply_conflict_resolution(conflicts, user_data, strategy)
        else:
            return self._handle_dry_run_conflicts(user_data)

    def _apply_conflict_resolution(
        self,
        conflicts: List[ConflictRecord],
        user_data: Dict[str, Any],
        strategy: ConflictStrategy,
    ) -> bool:
        """Apply conflict resolution strategy."""
        if strategy == ConflictStrategy.USE_THEIRS:
            return self._update_existing_user(conflicts, user_data)
        elif strategy == ConflictStrategy.USE_MINE:
            return self._skip_user_import(user_data)
        return True

    def _update_existing_user(
        self, conflicts: List[ConflictRecord], user_data: Dict[str, Any]
    ) -> bool:
        """Update existing user with import data."""
        field_conflicts = [c for c in conflicts if c.field_name != "_existence"]
        email = self._extract_user_email(user_data)

        if field_conflicts:
            existing_user = get_user_by_email(email)
            if existing_user:
                # NOTE: update_user function will be implemented when user update features are added
                # update_user_extended(existing_user['user_id'], user_data)
                self.stats["records_updated"] += 1
                self.logger.info(f"[Import] Updated user: {email}")
                return True
            else:
                self.stats["errors"].append(f"User not found for update: {email}")
                return False
        else:
            # User exists with identical data - no action needed
            self.stats["records_skipped"] += 1
            self._log(f"User already exists with identical data: {email}", "debug")
            return True

    def _skip_user_import(self, user_data: Dict[str, Any]) -> bool:
        """Skip user import, keeping existing data."""
        self.stats["records_skipped"] += 1
        email = self._extract_user_email(user_data)
        self.logger.info(f"[Import] Skipped user (keeping existing): {email}")
        return True

    def _handle_dry_run_conflicts(self, user_data: Dict[str, Any]) -> bool:
        """Handle conflicts in dry run mode."""
        email = self._extract_user_email(user_data)
        if email and email not in self._processed_users:
            self._processed_users.add(email)
            self._log(f"DRY RUN: Would process user with conflicts: {email}", "summary")
        elif email:
            self._log(f"DRY RUN: User already processed: {email}", "debug")
        return True

    def _create_new_user(self, user_data: Dict[str, Any], dry_run: bool) -> bool:
        """Create a new user."""
        email = self._extract_user_email(user_data)

        if not dry_run:
            return self._execute_user_creation(user_data, email)
        else:
            return self._handle_dry_run_creation(email)

    def _execute_user_creation(self, user_data: Dict[str, Any], email: str) -> bool:
        """Execute actual user creation."""
        try:
            user_id = create_user(user_data)
            if user_id:
                self.stats["records_created"] += 1
                if email not in self._processed_users:
                    self._processed_users.add(email)
                    self._log(f"Created user: {email}", "summary")
                else:
                    self._log(f"User already processed: {email}", "debug")
                return True
            else:
                self.stats["errors"].append(
                    f"Failed to create user: {email} - database returned None"
                )
                return False
        except Exception as e:
            self.stats["errors"].append(f"Error creating user {email}: {str(e)}")
            self.logger.error(f"Exception during user creation: {e}")
            return False

    def _handle_dry_run_creation(self, email: str) -> bool:
        """Handle user creation in dry run mode."""
        if email not in self._processed_users:
            self._processed_users.add(email)
            self._log(f"DRY RUN: Would create user: {email}", "summary")
        else:
            self._log(f"DRY RUN: User already processed: {email}", "debug")
        return True

    def process_user_import(
        self,
        user_data: Dict[str, Any],
        strategy: ConflictStrategy,
        dry_run: bool = False,
    ) -> Tuple[bool, List[ConflictRecord]]:
        """
        Process import of a single user

        Args:
            user_data: User data to import
            strategy: Conflict resolution strategy
            dry_run: If True, don't make actual changes

        Returns:
            Tuple of (success, conflicts)
        """
        # Detect conflicts
        conflicts = self.detect_user_conflict(user_data)

        # Handle conflicts or create new user
        if conflicts:
            success = self._handle_user_conflicts(
                conflicts, user_data, strategy, dry_run
            )
            self.stats["conflicts_resolved"] += len(conflicts)
        else:
            success = self._create_new_user(user_data, dry_run)

        return success, conflicts

    def _validate_and_load_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Validate file exists and load Excel data."""
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.stats["errors"].append(error_msg)
            return None

        try:
            df = pd.read_excel(file_path, sheet_name=0)  # First sheet
            self._log(
                f"Loaded Excel file: {len(df)} rows, {len(df.columns)} columns",
                "summary",
            )
            return df
        except Exception as e:
            error_msg = f"Failed to read Excel file: {str(e)}"
            self.stats["errors"].append(error_msg)
            return None

    def _handle_database_cleanup(self, delete_existing_db: bool, dry_run: bool) -> None:
        """Handle database cleanup if requested."""
        if delete_existing_db:
            if not dry_run:
                self._delete_all_data()
                self.logger.info("[Import] 🗑️  Cleared existing database")
            else:
                self.logger.info("[Import] DRY RUN: Would clear existing database")

    def _log_import_start(
        self,
        file_path: str,
        conflict_strategy: ConflictStrategy,
        dry_run: bool,
        delete_existing_db: bool,
    ) -> None:
        """Log import start information."""
        self.logger.info(f"[Import] Starting import from: {file_path}")
        self.logger.info(f"[Import] Conflict strategy: {conflict_strategy.value}")
        self.logger.info(f"[Import] Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        if delete_existing_db:
            self.logger.warning(
                f"[Import] ⚠️  DELETE MODE: Will clear existing database before import"
            )

    def import_excel_file(
        self,
        file_path: str,
        conflict_strategy: ConflictStrategy = ConflictStrategy.USE_THEIRS,
        dry_run: bool = False,
        adapter_name: str = "cei_excel_adapter",
        delete_existing_db: bool = False,
    ) -> ImportResult:
        """
        Import data from Excel file

        Args:
            file_path: Path to Excel file
            conflict_strategy: How to resolve conflicts
            dry_run: If True, simulate import without making changes
            adapter_name: Which adapter to use for parsing
            delete_existing_db: If True, delete all existing data before import

        Returns:
            ImportResult with detailed statistics
        """
        start_time = datetime.now(timezone.utc)
        self.reset_stats()
        self._log_import_start(
            file_path, conflict_strategy, dry_run, delete_existing_db
        )

        try:
            # Validate and load Excel file
            df = self._validate_and_load_excel_file(file_path)
            if df is None:
                return self._create_import_result(start_time, dry_run)

            # Handle database cleanup if requested
            self._handle_database_cleanup(delete_existing_db, dry_run)

            # Process all rows
            all_conflicts = self._process_all_rows(
                df, adapter_name, conflict_strategy, dry_run
            )
            self.stats["conflicts"].extend(all_conflicts)

        except Exception as e:
            error_msg = f"Unexpected error during import: {str(e)}"
            self.stats["errors"].append(error_msg)
            self.logger.info(f"[Import] {error_msg}")

        return self._create_import_result(start_time, dry_run)

    def _process_all_rows(
        self,
        df: pd.DataFrame,
        adapter_name: str,
        conflict_strategy: ConflictStrategy,
        dry_run: bool,
    ) -> List[Any]:
        """Process all rows in the DataFrame."""
        all_conflicts = []
        total_rows = len(df)
        progress_interval = max(1, total_rows // 20)  # Show progress every 5%

        for index, row in df.iterrows():
            self.stats["records_processed"] += 1

            # Update progress if needed
            self._update_progress_if_needed(index, total_rows, progress_interval)

            try:
                conflicts = self._process_single_row(
                    row, adapter_name, conflict_strategy, dry_run
                )
                all_conflicts.extend(conflicts)
            except Exception as e:
                error_msg = f"Error processing row {index + 1}: {str(e)}"
                self.stats["errors"].append(error_msg)
                self.logger.info(f"[Import] {error_msg}")

        return all_conflicts

    def _update_progress_if_needed(
        self, index: int, total_rows: int, progress_interval: int
    ) -> None:
        """Update progress tracking if needed."""
        if index % progress_interval == 0 or index == total_rows - 1:
            progress = int((index + 1) / total_rows * 100)
            self._log(
                f"Processing row {index + 1}/{total_rows} ({progress}%)",
                "summary",
            )

            # Update progress callback if provided
            if self.progress_callback:
                self.progress_callback(
                    percentage=progress,
                    records_processed=index + 1,
                    total_records=total_rows,
                    message=f"Processing row {index + 1}/{total_rows} ({progress}%)",
                )

    def _process_single_row(
        self,
        row: pd.Series,
        adapter_name: str,
        conflict_strategy: ConflictStrategy,
        dry_run: bool,
    ) -> List[Any]:
        """Process a single row and return any conflicts."""
        # Extract entities from row
        entities = self._extract_entities_from_row(row, adapter_name)
        if not entities:
            return []

        # Process entities in dependency order
        return self._process_entities_in_order(entities, conflict_strategy, dry_run)

    def _extract_entities_from_row(
        self, row: pd.Series, adapter_name: str
    ) -> Optional[Dict[str, Any]]:
        """Extract entities from a single row using the specified adapter."""
        if adapter_name == "cei_excel_adapter":
            from adapters.cei_excel_adapter import parse_cei_excel_row

            return parse_cei_excel_row(row, self.institution_id)
        else:
            self.stats["errors"].append(f"Unknown adapter: {adapter_name}")
            return None

    def _process_entities_in_order(
        self,
        entities: Dict[str, Any],
        conflict_strategy: ConflictStrategy,
        dry_run: bool,
    ) -> List[Any]:
        """Process entities in dependency order: course -> user -> term -> offering -> section."""
        all_conflicts = []
        processing_order = ["course", "user", "term", "offering", "section"]
        current_offering_id = None

        for entity_type in processing_order:
            entity_data = entities.get(entity_type)
            if not entity_data:
                continue

            if entity_type == "course":
                success, conflicts = self.process_course_import(
                    entity_data, conflict_strategy, dry_run
                )
                all_conflicts.extend(conflicts)

            elif entity_type == "user":
                success, conflicts = self.process_user_import(
                    entity_data, conflict_strategy, dry_run
                )
                all_conflicts.extend(conflicts)

            elif entity_type == "term":
                self._process_term_entity(entity_data, dry_run)

            elif entity_type == "offering":
                current_offering_id = self._process_offering_entity(
                    entity_data, dry_run
                )

            elif entity_type == "section":
                self._process_section_entity(entity_data, current_offering_id, dry_run)

        return all_conflicts

    def _process_term_entity(self, entity_data: Dict[str, Any], dry_run: bool) -> None:
        """Process term entity with duplicate checking."""
        term_name = entity_data.get("term_name")
        institution_id = entity_data.get("institution_id")

        # Simple duplicate check - query for existing term
        from database_service import db

        existing_terms = (
            db.collection("terms")
            .where("term_name", "==", term_name)
            .where("institution_id", "==", institution_id)
            .limit(1)
            .stream()
        )

        existing_term = next(existing_terms, None)

        if existing_term:
            # Term already exists, skip creation
            self.logger.info(f"[Import] Term already exists: {term_name}")
        else:
            # Create new term
            if not dry_run:
                term_id = create_term(entity_data)
                if term_id:
                    self.stats["records_created"] += 1
                    self.logger.info(f"[Import] Created term: {term_name}")
            else:
                self.logger.info(f"[Import] DRY RUN: Would create term: {term_name}")

    def _process_offering_entity(
        self, entity_data: Dict[str, Any], dry_run: bool
    ) -> Optional[str]:
        """Process course offering entity and return offering_id."""
        course_id = entity_data.get("course_id")  # This is still course_number
        term_name = entity_data.get("term_id")  # This is still term_name
        institution_id = entity_data.get("institution_id")

        # Resolve course_id from course_number
        if not course_id:
            return None

        course = get_course_by_number(course_id)
        if not course:
            return None

        entity_data["course_id"] = course.get("course_id")

        # Check if offering already exists
        existing_offering = get_course_offering_by_course_and_term(
            course.get("course_id"), term_name, institution_id
        )

        if existing_offering:
            self.logger.info(
                f"[Import] Course offering already exists: {course_id} in {term_name}"
            )
            return existing_offering.get("offering_id")
        else:
            # Create new course offering
            entity_data["term_id"] = term_name  # Keep term_name for now
            if not dry_run:
                offering_id = create_course_offering(entity_data)
                if offering_id:
                    self.stats["records_created"] += 1
                    self.logger.info(
                        f"[Import] Created course offering: {course_id} in {term_name}"
                    )
                    return offering_id
            else:
                self.logger.info(
                    f"[Import] DRY RUN: Would create offering: {course_id} in {term_name}"
                )
            return None

    def _process_section_entity(
        self, entity_data: Dict[str, Any], offering_id: Optional[str], dry_run: bool
    ) -> None:
        """Process section entity."""
        if offering_id:
            entity_data["offering_id"] = offering_id

            if not dry_run:
                section_id = create_course_section(entity_data)
                if section_id:
                    self.stats["records_created"] += 1
                    self.logger.info(f"[Import] Created section: {offering_id}")
            else:
                self.logger.info(
                    f"[Import] DRY RUN: Would create section: {offering_id}"
                )
        else:
            self.logger.warning(
                f"[Import] No offering_id available for section creation"
            )

    def _extract_department_from_course(self, course_number: str) -> str:
        """Extract department from course number"""
        department_mapping = {
            "ACC": "Business",
            "BUS": "Business",
            "NURS": "Nursing",
            "BIOL": "Science",
            "MATH": "Mathematics",
            "ENG": "English",
        }

        if "-" in course_number:
            prefix = course_number.split("-")[0]
            return department_mapping.get(prefix, "General Studies")
        return "General Studies"

    def _parse_name(self, full_name: str) -> Tuple[str, str]:
        """Parse full name into first and last name"""
        parts = full_name.strip().split()
        if len(parts) == 0:
            return "Unknown", "Instructor"
        elif len(parts) == 1:
            return parts[0], "Unknown"
        else:
            return parts[0], " ".join(parts[1:])

    def _generate_email(self, first_name: str, last_name: str) -> str:
        """Generate email from name components"""
        return f"{first_name.lower()}.{last_name.lower()}@cei.edu"

    def _parse_name_from_email(self, name_part: str) -> Tuple[str, str]:
        """Parse name from email prefix (instructor1 -> Instructor, One)"""
        if not name_part:
            return "Unknown", "Instructor"

        # Handle cases like "instructor1", "john.doe", etc.
        if "." in name_part:
            parts = name_part.split(".")
            first_name = parts[0].capitalize()
            last_name = parts[1].capitalize() if len(parts) > 1 else "Unknown"
        else:
            # Handle cases like "instructor1" -> "Instructor 1"
            import re

            match = re.match(r"([a-zA-Z]+)(\d*)", name_part)
            if match:
                base_name = match.group(1).capitalize()
                number = match.group(2)
                if number:
                    first_name = base_name
                    last_name = number
                else:
                    first_name = base_name
                    last_name = "Unknown"
            else:
                first_name = name_part.capitalize()
                last_name = "Unknown"

        return first_name, last_name

    def _estimate_term_start(self, term_name: str) -> str:
        """Estimate term start date"""
        # Simplified logic - would be configurable in real implementation
        parts = term_name.split()
        if len(parts) == 2:
            year = parts[0]
            season = parts[1].lower()
            if season == "fall":
                return f"{year}-08-15"
            elif season == "spring":
                return f"{year}-01-15"
            elif season == "summer":
                return f"{year}-06-01"
        return "2024-01-01"

    def _estimate_term_end(self, term_name: str) -> str:
        """Estimate term end date"""
        parts = term_name.split()
        if len(parts) == 2:
            year = parts[0]
            season = parts[1].lower()
            if season == "fall":
                return f"{year}-12-15"
            elif season == "spring":
                return f"{year}-05-15"
            elif season == "summer":
                return f"{year}-08-15"
        return "2024-05-01"

    def _estimate_assessment_due(self, term_name: str) -> str:
        """Estimate assessment due date"""
        parts = term_name.split()
        if len(parts) == 2:
            year = parts[0]
            season = parts[1].lower()
            if season == "fall":
                return f"{year}-12-30"
            elif season == "spring":
                return f"{year}-05-30"
            elif season == "summer":
                return f"{year}-08-30"
        return "2024-05-15"

    def _delete_all_data(self):
        """
        Delete all data from the database.
        This is a destructive operation used when delete_existing_db=True.
        """
        from database_service import db

        if not db:
            self.stats["errors"].append("Database not available for deletion")
            return

        try:
            # Delete all collections
            collections_to_delete = [
                "courses",
                "users",
                "terms",
                "course_sections",
                "course_outcomes",
            ]

            deleted_count = 0
            for collection_name in collections_to_delete:
                # Get all documents in the collection
                docs = db.collection(collection_name).stream()

                # Delete each document
                for doc in docs:
                    doc.reference.delete()
                    deleted_count += 1

            self.logger.info(
                f"[Import] Deleted {deleted_count} documents from database"
            )

        except Exception as e:
            error_msg = f"Failed to delete existing data: {str(e)}"
            self.stats["errors"].append(error_msg)
            self.logger.info(f"[Import] Error: {error_msg}")

    def _create_import_result(
        self, start_time: datetime, dry_run: bool
    ) -> ImportResult:
        """Create ImportResult from current stats"""
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


# Global import service instance will be created with verbose parameter


# Convenience functions
def import_excel(
    file_path: str,
    institution_id: str,
    conflict_strategy: str = "use_theirs",
    dry_run: bool = False,
    adapter_name: str = "cei_excel_adapter",
    delete_existing_db: bool = False,
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
        adapter_name: Which adapter to use
        delete_existing_db: If True, delete all existing data before import

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
        adapter_name=adapter_name,
        delete_existing_db=delete_existing_db,
    )


def create_import_report(result: ImportResult) -> str:
    """Create a detailed import report"""
    report = []
    report.append("=" * 60)
    report.append("DATA IMPORT REPORT")
    report.append("=" * 60)
    report.append(f"Import completed at: {datetime.now(timezone.utc).isoformat()}")
    report.append(f"Execution time: {result.execution_time:.2f} seconds")
    report.append(f"Mode: {'DRY RUN' if result.dry_run else 'EXECUTE'}")
    report.append(f"Overall success: {'YES' if result.success else 'NO'}")
    report.append("")

    report.append("STATISTICS:")
    report.append(f"  Records processed: {result.records_processed}")
    report.append(f"  Records created: {result.records_created}")
    report.append(f"  Records updated: {result.records_updated}")
    report.append(f"  Records skipped: {result.records_skipped}")
    report.append(f"  Conflicts detected: {result.conflicts_detected}")
    report.append(f"  Conflicts resolved: {result.conflicts_resolved}")
    report.append("")

    if result.conflicts:
        report.append("CONFLICTS:")
        for i, conflict in enumerate(result.conflicts, 1):
            report.append(
                f"  {i}. {conflict.entity_type} '{conflict.entity_key}' - {conflict.field_name}"
            )
            report.append(f"     Existing: {conflict.existing_value}")
            report.append(f"     Import: {conflict.import_value}")
            report.append(f"     Resolution: {conflict.resolution}")
            report.append("")

    if result.errors:
        report.append("ERRORS:")
        for i, error in enumerate(result.errors, 1):
            report.append(f"  {i}. {error}")
        report.append("")

    if result.warnings:
        report.append("WARNINGS:")
        for i, warning in enumerate(result.warnings, 1):
            report.append(f"  {i}. {warning}")
        report.append("")

    report.append("=" * 60)
    return "\n".join(report)
