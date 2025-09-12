"""
Unit tests for import_service.py

Comprehensive tests for the ImportService class including file operations,
data processing, conflict resolution, and database interactions.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pandas as pd

from import_service import (
    ConflictRecord,
    ConflictStrategy,
    ImportMode,
    ImportResult,
    ImportService,
    create_import_report,
    import_excel,
)

# pytest import removed


class TestImportService:
    """Main test class for ImportService functionality."""

    def test_import_excel_file_not_found_error(self):
        """Test import_excel_file with non-existent file - Line 198."""
        service = ImportService()

        # Test with non-existent file
        result = service.import_excel_file("nonexistent_file.xlsx")

        # Should handle file not found gracefully
        assert result.success is False
        assert len(result.errors) > 0
        assert any(
            "not found" in error.lower() or "no such file" in error.lower()
            for error in result.errors
        )

    def test_import_excel_file_comprehensive_workflow(self):
        """Test import_excel_file comprehensive workflow to hit lines 244-256."""
        service = ImportService()

        # Create a real temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            # Create DataFrame with test data
            test_data = {
                "Course Number": ["TEST-101", "TEST-102"],
                "Course Title": ["Test Course 1", "Test Course 2"],
                "Instructor First Name": ["John", "Jane"],
                "Instructor Last Name": ["Doe", "Smith"],
                "Instructor Email": ["john@example.com", "jane@example.com"],
                "Term": ["FA24", "FA24"],
                "Students": [25, 30],
                "Department": ["TEST", "TEST"],
            }
            df = pd.DataFrame(test_data)
            df.to_excel(tmp_file.name, index=False)

        try:
            with (
                patch("database_service.get_user_by_email", return_value=None),
                patch("database_service.get_course_by_number", return_value=None),
                patch("database_service.create_user", return_value="user123"),
                patch("database_service.create_course", return_value="course123"),
            ):
                result = service.import_excel_file(
                    tmp_file.name,
                    conflict_strategy=ConflictStrategy.USE_THEIRS,
                    dry_run=False,
                    delete_existing_db=False,
                )

                # Should process the Excel file successfully
                assert result.success is True
                assert result.records_processed == 2

        finally:
            os.unlink(tmp_file.name)

    def test_import_excel_file_with_delete_existing_db_option(self):
        """Test import_excel_file with delete_existing_db=True to hit deletion lines."""
        service = ImportService()

        # Create minimal Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            test_data = {
                "Course Number": ["TEST-101"],
                "Course Title": ["Test Course"],
                "Instructor First Name": ["John"],
                "Instructor Last Name": ["Doe"],
                "Instructor Email": ["john@example.com"],
                "Term": ["FA24"],
                "Students": [25],
                "Department": ["TEST"],
            }
            df = pd.DataFrame(test_data)
            df.to_excel(tmp_file.name, index=False)

        try:
            with (
                patch("database_service.get_user_by_email", return_value=None),
                patch("database_service.get_course_by_number", return_value=None),
                patch.object(service, "_delete_all_data") as mock_delete,
            ):
                result = service.import_excel_file(
                    tmp_file.name, delete_existing_db=True, dry_run=False
                )

                # Should have called delete_all_data
                mock_delete.assert_called_once()

        finally:
            os.unlink(tmp_file.name)

    def test_import_excel_file_dry_run_mode(self):
        """Test import_excel_file in dry_run mode to hit dry run logic."""
        service = ImportService()

        # Create minimal Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            test_data = {
                "Course Number": ["TEST-101"],
                "Course Title": ["Test Course"],
                "Instructor First Name": ["John"],
                "Instructor Last Name": ["Doe"],
                "Instructor Email": ["john@example.com"],
                "Term": ["FA24"],
                "Students": [25],
                "Department": ["TEST"],
            }
            df = pd.DataFrame(test_data)
            df.to_excel(tmp_file.name, index=False)

        try:
            with (
                patch("database_service.get_user_by_email", return_value=None),
                patch("database_service.get_course_by_number", return_value=None),
            ):
                result = service.import_excel_file(tmp_file.name, dry_run=True)

                # Should be successful dry run
                assert result.success is True
                assert result.dry_run is True
                assert result.records_processed == 1

        finally:
            os.unlink(tmp_file.name)

    def test_process_user_import_with_existing_user(self):
        """Test process_user_import with existing user to hit conflict resolution."""
        service = ImportService()

        user_data = {
            "email": "existing@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "instructor",
        }

        # Mock existing user with different data
        existing_user = {
            "email": "existing@example.com",
            "first_name": "Jane",  # Different name
            "last_name": "Smith",  # Different name
        }

        with patch("database_service.get_user_by_email", return_value=existing_user):
            success, conflicts = service.process_user_import(
                user_data, ConflictStrategy.USE_MINE, dry_run=False
            )

            # Should detect conflict
            assert isinstance(success, bool)
            assert isinstance(conflicts, list)

    def test_process_course_import_with_existing_course(self):
        """Test process_course_import with existing course to hit conflict resolution."""
        service = ImportService()

        course_data = {
            "course_number": "EXISTING-101",
            "course_title": "New Title",
            "department": "TEST",
        }

        # Mock existing course with different data
        existing_course = {
            "course_number": "EXISTING-101",
            "course_title": "Old Title",  # Different title
            "department": "TEST",
        }

        with patch(
            "database_service.get_course_by_number", return_value=existing_course
        ):
            success, conflicts = service.process_course_import(
                course_data, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            # Should detect conflict
            assert isinstance(success, bool)
            assert isinstance(conflicts, list)

    def test_delete_all_data_functionality(self):
        """Test _delete_all_data method to hit deletion logic."""
        service = ImportService()

        with patch("database_service.db") as mock_db:
            # Mock collection method
            mock_collection = Mock()
            mock_docs = [Mock(reference=Mock(delete=Mock())) for i in range(3)]
            mock_collection.stream.return_value = mock_docs
            mock_db.collection.return_value = mock_collection

            with patch("builtins.print"):  # Suppress print output
                # Test deletion
                service._delete_all_data()

            # Verify collection method was called for each collection type
            assert mock_db.collection.call_count >= 1

    def test_logging_functionality(self):
        """Test _log method with different combinations."""
        # Test verbose mode
        service_verbose = ImportService(verbose=True)
        with patch("builtins.print") as mock_print:
            service_verbose._log("Test message", "info")
            service_verbose._log("Error message", "error")
            service_verbose._log("Warning message", "warning")
            service_verbose._log("Summary message", "summary")
            assert (
                mock_print.call_count >= 3
            )  # Should print most messages in verbose mode

        # Test non-verbose mode
        service_quiet = ImportService(verbose=False)
        with patch("builtins.print") as mock_print:
            service_quiet._log("Test message", "info")  # Should not print
            service_quiet._log("Error message", "error")  # Should print
            service_quiet._log("Summary message", "summary")  # Should print
            assert mock_print.call_count >= 1  # Should print errors and summaries

    def test_create_import_result_with_various_stats(self):
        """Test _create_import_result with different stat combinations."""
        service = ImportService()

        # Set up various stats conditions
        service.stats["records_processed"] = 100
        service.stats["records_created"] = 80
        service.stats["records_updated"] = 20
        service.stats["records_skipped"] = 5
        service.stats["conflicts_detected"] = 3
        service.stats["conflicts_resolved"] = 2
        service.stats["errors"] = ["Error 1", "Error 2"]
        service.stats["warnings"] = ["Warning 1"]

        from datetime import datetime, timezone

        start_time = datetime.now(timezone.utc)

        # Test with dry_run=False
        result = service._create_import_result(start_time, dry_run=False)
        assert result.records_processed == 100
        assert result.records_created == 80
        assert result.records_updated == 20
        assert result.records_skipped == 5
        assert result.conflicts_detected == 3
        assert result.conflicts_resolved == 2
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert result.dry_run is False

        # Test with dry_run=True
        result_dry = service._create_import_result(start_time, dry_run=True)
        assert result_dry.dry_run is True

    def test_processed_tracking_sets(self):
        """Test processed users and courses tracking."""
        service = ImportService()

        # Test processed sets functionality
        service._processed_users.add("user1@example.com")
        service._processed_users.add("user2@example.com")
        service._processed_courses.add("COURSE-101")
        service._processed_courses.add("COURSE-102")

        assert len(service._processed_users) == 2
        assert len(service._processed_courses) == 2
        assert "user1@example.com" in service._processed_users
        assert "COURSE-101" in service._processed_courses

        # Test reset functionality - reset_stats doesn't clear processed sets
        # The processed sets are maintained across reset_stats calls
        service.reset_stats()
        # Processed sets should still contain data (this is the actual behavior)
        assert len(service._processed_users) == 2
        assert len(service._processed_courses) == 2

    def test_conflict_detection_edge_cases(self):
        """Test detect_course_conflict with edge cases."""
        service = ImportService()

        # Test with course missing course_number
        import_course_no_number = {
            "course_title": "Test Course",
            # Missing 'course_number'
        }

        conflicts = service.detect_course_conflict(import_course_no_number)
        assert isinstance(conflicts, list)

        # Test with complete course data
        import_course_complete = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "TEST",
        }

        conflicts2 = service.detect_course_conflict(import_course_complete)
        assert isinstance(conflicts2, list)

    def test_import_excel_file_large_dataset_progress(self):
        """Test import_excel_file with large dataset to trigger progress reporting."""
        service = ImportService(verbose=True)

        # Create larger dataset to trigger progress reporting (50+ records)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            test_data = {
                "Course Number": [f"TEST-{i:03d}" for i in range(60)],
                "Course Title": [f"Test Course {i}" for i in range(60)],
                "Instructor First Name": ["John"] * 60,
                "Instructor Last Name": ["Doe"] * 60,
                "Instructor Email": [f"john{i}@example.com" for i in range(60)],
                "Term": ["FA24"] * 60,
                "Students": [25] * 60,
                "Department": ["TEST"] * 60,
            }
            df = pd.DataFrame(test_data)
            df.to_excel(tmp_file.name, index=False)

        try:
            with (
                patch("database_service.get_user_by_email", return_value=None),
                patch("database_service.get_course_by_number", return_value=None),
                patch("builtins.print") as mock_print,
            ):
                result = service.import_excel_file(
                    tmp_file.name,
                    dry_run=True,  # Use dry run to avoid actual database operations
                )

                # Should have triggered progress reporting
                assert mock_print.called
                assert result.records_processed == 60

        finally:
            os.unlink(tmp_file.name)


class TestEnumsAndDataClasses:
    """Test enums and data classes."""

    def test_conflict_strategy_enum(self):
        """Test ConflictStrategy enum values."""
        assert ConflictStrategy.USE_MINE.value == "use_mine"
        assert ConflictStrategy.USE_THEIRS.value == "use_theirs"
        assert ConflictStrategy.MERGE.value == "merge"
        assert ConflictStrategy.MANUAL_REVIEW.value == "manual_review"

    def test_import_mode_enum(self):
        """Test ImportMode enum values."""
        assert ImportMode.DRY_RUN.value == "dry_run"
        assert ImportMode.EXECUTE.value == "execute"

    def test_conflict_record_creation(self):
        """Test ConflictRecord creation."""
        record = ConflictRecord(
            entity_type="course",
            entity_key="MATH-101",
            field_name="course_title",
            existing_value="Old Title",
            import_value="New Title",
        )

        assert record.entity_type == "course"
        assert record.entity_key == "MATH-101"
        assert record.field_name == "course_title"
        assert record.existing_value == "Old Title"
        assert record.import_value == "New Title"

    def test_import_result_creation(self):
        """Test ImportResult creation."""
        result = ImportResult(
            success=True,
            records_processed=10,
            records_created=5,
            records_updated=3,
            records_skipped=2,
            conflicts_detected=1,
            conflicts_resolved=1,
            errors=[],
            warnings=[],
            conflicts=[],
            execution_time=1.5,
            dry_run=False,
        )

        assert result.success is True
        assert result.records_processed == 10
        assert result.records_created == 5
        assert result.records_updated == 3
        assert result.records_skipped == 2
        assert result.conflicts_detected == 1
        assert result.conflicts_resolved == 1
        assert result.errors == []
        assert result.warnings == []
        assert result.conflicts == []
        assert result.execution_time == 1.5
        assert result.dry_run is False


class TestImportServiceInitialization:
    """Test ImportService initialization and basic methods."""

    def test_import_service_initialization_default(self):
        """Test ImportService initialization with defaults."""
        service = ImportService()

        assert service.verbose is False
        assert service._processed_users == set()
        assert service._processed_courses == set()
        assert isinstance(service.stats, dict)

    def test_import_service_initialization_verbose(self):
        """Test ImportService initialization with verbose mode."""
        service = ImportService(verbose=True)

        assert service.verbose is True

    def test_reset_stats(self):
        """Test reset_stats method."""
        service = ImportService()

        # Modify stats
        service.stats["records_processed"] = 10
        service.stats["errors"].append("test error")

        # Reset
        service.reset_stats()

        # Verify reset
        assert service.stats["records_processed"] == 0
        assert service.stats["records_created"] == 0
        assert service.stats["records_updated"] == 0
        assert service.stats["records_skipped"] == 0
        assert service.stats["conflicts_detected"] == 0
        assert service.stats["conflicts_resolved"] == 0
        assert service.stats["errors"] == []


class TestImportServiceLogging:
    """Test ImportService logging functionality."""

    def test_log_error_message(self):
        """Test logging error messages."""
        service = ImportService(verbose=False)

        with patch("builtins.print") as mock_print:
            service._log("Test error", "error")
            mock_print.assert_called_once_with("[Import] ERROR: Test error")

    def test_log_warning_message(self):
        """Test logging warning messages."""
        service = ImportService(verbose=False)

        with patch("builtins.print") as mock_print:
            service._log("Test warning", "warning")
            mock_print.assert_called_once_with("[Import] WARNING: Test warning")

    def test_log_summary_message(self):
        """Test logging summary messages."""
        service = ImportService(verbose=False)

        with patch("builtins.print") as mock_print:
            service._log("Test summary", "summary")
            mock_print.assert_called_once_with("[Import] Test summary")

    def test_log_verbose_mode_on(self):
        """Test logging in verbose mode."""
        service = ImportService(verbose=True)

        with patch("builtins.print") as mock_print:
            service._log("Test message", "info")
            mock_print.assert_called_once_with("[Import] Test message")

    def test_log_verbose_mode_off(self):
        """Test logging in non-verbose mode."""
        service = ImportService(verbose=False)

        with patch("builtins.print") as mock_print:
            service._log("Test message", "info")
            mock_print.assert_not_called()


class TestDetectCourseConflict:
    """Test detect_course_conflict method."""

    def test_detect_course_conflict_method_exists(self):
        """Test that detect_course_conflict method exists."""
        service = ImportService()
        assert hasattr(service, "detect_course_conflict")
        assert callable(service.detect_course_conflict)

    def test_detect_course_conflict_basic_functionality(self):
        """Test detect_course_conflict basic functionality."""
        service = ImportService()

        import_course = {
            "course_number": "MATH-101",
            "course_title": "Algebra",
            "department": "MATH",
        }

        conflicts = service.detect_course_conflict(import_course)
        assert isinstance(conflicts, list)


class TestImportExcelFunction:
    """Test the import_excel function - basic functionality."""

    def test_import_excel_function_exists(self):
        """Test that import_excel function exists and is callable."""
        assert callable(import_excel)

    def test_create_import_report_function_exists(self):
        """Test that create_import_report function exists and is callable."""
        assert callable(create_import_report)


class TestImportServiceIntegration:
    """Test ImportService integration aspects."""

    def test_import_service_stats_tracking(self):
        """Test that ImportService properly tracks statistics."""
        service = ImportService()

        # Verify initial state
        assert service.stats["records_processed"] == 0
        assert service.stats["errors"] == []

        # Modify stats (simulating import operations)
        service.stats["records_processed"] = 5
        service.stats["records_created"] = 3
        service.stats["errors"].append("Test error")

        # Verify changes
        assert service.stats["records_processed"] == 5
        assert service.stats["records_created"] == 3
        assert len(service.stats["errors"]) == 1

    def test_import_service_processed_tracking(self):
        """Test that ImportService tracks processed entities."""
        service = ImportService()

        # Add some processed entities
        service._processed_users.add("user1@example.com")
        service._processed_users.add("user2@example.com")
        service._processed_courses.add("MATH-101")

        # Verify tracking
        assert len(service._processed_users) == 2
        assert len(service._processed_courses) == 1
        assert "user1@example.com" in service._processed_users
        assert "MATH-101" in service._processed_courses

    def test_import_service_basic_functionality(self):
        """Test ImportService basic functionality."""
        service = ImportService()
        service.reset_stats()  # Initialize service

        # Test basic service functionality
        assert hasattr(service, "stats")
        assert hasattr(service, "_processed_users")
        assert hasattr(service, "_processed_courses")


class TestImportServiceErrorHandling:
    """Test ImportService error handling."""

    def test_import_service_handles_missing_dependencies(self):
        """Test ImportService handles missing dependencies gracefully."""
        service = ImportService()

        # This should not raise an exception
        service.reset_stats()
        service._log("Test message")

        # Basic functionality should work
        assert isinstance(service.stats, dict)
        assert isinstance(service._processed_users, set)
        assert isinstance(service._processed_courses, set)


class TestImportServiceEdgeCases:
    """Edge case testing for import service functionality."""

    def test_detect_course_conflict_no_course_number(self):
        """Test detect_course_conflict with missing course_number."""
        service = ImportService()

        # Test with import course missing course_number
        import_course = {
            "course_title": "Test Course",
            # Missing 'course_number'
        }

        conflicts = service.detect_course_conflict(import_course)

        # Should return empty conflicts due to missing course_number
        assert conflicts == []

    def test_parse_cei_excel_row_with_minimal_data(self):
        """Test _parse_cei_excel_row to hit various parsing lines."""
        service = ImportService()

        # Create minimal row data to hit parsing logic
        row_data = {
            "Course Number": "TEST-101",
            "Course Title": "Test Course",
            "Instructor First Name": "John",
            "Instructor Last Name": "Doe",
            "Instructor Email": "john@example.com",
            "Term": "FA24",
            "Students": "25",
            "Department": "TEST",
        }
        row = pd.Series(row_data)

        result = service._parse_cei_excel_row(row)

        # Should return parsed structure
        assert isinstance(result, dict)
        assert "user" in result
        assert "course" in result

    @patch("import_service.get_course_by_number")
    def test_detect_course_conflict_with_conflicts(self, mock_get_course):
        """Test detect_course_conflict when conflicts exist - lines 173-180."""
        service = ImportService()

        # Mock existing course with different data
        mock_get_course.return_value = {
            "course_number": "TEST-101",
            "course_title": "Old Course Title",
            "credit_hours": 3,
            "department": "OLD_DEPT",
        }

        # Import course with different values
        import_course = {
            "course_number": "TEST-101",
            "course_title": "New Course Title",  # Different title
            "credit_hours": 4,  # Different credits
            "department": "NEW_DEPT",  # Different department
        }

        conflicts = service.detect_course_conflict(import_course)

        # Should detect conflicts in title, credit_hours, and department, plus existence
        assert len(conflicts) >= 3
        conflict_fields = [c.field_name for c in conflicts]
        assert "course_title" in conflict_fields
        assert "credit_hours" in conflict_fields
        assert "department" in conflict_fields

        # Check specific conflict details
        title_conflict = next(c for c in conflicts if c.field_name == "course_title")
        assert title_conflict.existing_value == "Old Course Title"
        assert title_conflict.import_value == "New Course Title"
        assert title_conflict.entity_type == "course"

    @patch("import_service.get_user_by_email")
    def test_detect_user_conflict_with_conflicts(self, mock_get_user):
        """Test detect_user_conflict when conflicts exist - lines 205-219."""
        service = ImportService()

        # Mock existing user with different data
        mock_get_user.return_value = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Smith",  # Different last name
            "role": "instructor",
            "department": "MATH",  # Different department
        }

        # Import user with different values
        import_user = {
            "email": "john@example.com",
            "first_name": "John",  # Same first name
            "last_name": "Doe",  # Different last name
            "role": "instructor",  # Same role
            "department": "CS",  # Different department
        }

        conflicts = service.detect_user_conflict(import_user)

        # Should detect conflicts in last_name and department
        assert len(conflicts) == 2
        conflict_fields = [c.field_name for c in conflicts]
        assert "last_name" in conflict_fields
        assert "department" in conflict_fields

        # Check specific conflict details
        name_conflict = next(c for c in conflicts if c.field_name == "last_name")
        assert name_conflict.existing_value == "Smith"
        assert name_conflict.import_value == "Doe"
        assert name_conflict.entity_type == "user"
        assert name_conflict.entity_key == "john@example.com"

    @patch("import_service.get_user_by_email")
    def test_detect_user_conflict_no_conflicts(self, mock_get_user):
        """Test detect_user_conflict when no conflicts exist."""
        service = ImportService()

        # Mock existing user with same data
        mock_get_user.return_value = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "instructor",
            "department": "CS",
        }

        # Import user with same values
        import_user = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "instructor",
            "department": "CS",
        }

        conflicts = service.detect_user_conflict(import_user)

        # Should detect no conflicts
        assert len(conflicts) == 0

    def test_excel_file_read_exception(self):
        """Test import_excel_file when Excel reading fails - lines 492-495."""
        service = ImportService()

        # Create a file that exists but is not a valid Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            tmp_file.write(b"This is not an Excel file")
            tmp_file_path = tmp_file.name

        try:
            result = service.import_excel_file(tmp_file_path)

            # Should handle Excel read error gracefully
            assert result.success is False
            assert len(result.errors) > 0
            assert any("Failed to read Excel file" in error for error in result.errors)
        finally:
            os.unlink(tmp_file_path)

    @patch("import_service.get_course_by_number")
    @patch("import_service.create_course")
    def test_process_course_import_with_conflicts(
        self, mock_create_course, mock_get_course
    ):
        """Test process_course_import with conflict resolution - lines 278-294."""
        service = ImportService()

        # Mock existing course with different data
        mock_get_course.return_value = {
            "course_number": "TEST-101",
            "course_title": "Old Title",
            "credits": 3,
        }
        mock_create_course.return_value = "course123"

        # Import course with conflicts
        course_data = {
            "course_number": "TEST-101",
            "course_title": "New Title",
            "credits": 4,
        }

        # Test with USE_THEIRS strategy
        result = service.process_course_import(
            course_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        # Should detect and resolve conflicts
        assert service.stats["conflicts_detected"] > 0
        assert "TEST-101" in service._processed_courses

    def test_delete_all_data_dry_run(self):
        """Test delete_existing_db in dry run mode - line 482."""
        service = ImportService()

        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            # Create simple DataFrame
            df = pd.DataFrame(
                {
                    "Course Number": ["TEST-101"],
                    "Course Title": ["Test Course"],
                    "Instructor First Name": ["John"],
                    "Instructor Last Name": ["Doe"],
                    "Instructor Email": ["john@example.com"],
                    "Term": "Fall 2024",
                }
            )
            df.to_excel(tmp_file.name, index=False)
            tmp_file_path = tmp_file.name

        try:
            # Test dry run with delete_existing_db=True
            result = service.import_excel_file(
                tmp_file_path, dry_run=True, delete_existing_db=True
            )

            # Should complete without errors in dry run
            assert result.dry_run is True
            # In dry run, database shouldn't actually be deleted
        finally:
            os.unlink(tmp_file_path)

    def test_progress_reporting_large_dataset(self):
        """Test progress reporting for large datasets - lines 500-503."""
        service = ImportService()

        # Create a larger dataset to trigger progress reporting
        large_data = []
        for i in range(50):  # Create 50 rows to trigger progress intervals
            large_data.append(
                {
                    "Course Number": f"TEST-{i:03d}",
                    "Course Title": f"Test Course {i}",
                    "Instructor First Name": "John",
                    "Instructor Last Name": "Doe",
                    "Instructor Email": f"john{i}@example.com",
                    "Term": "Fall 2024",
                }
            )

        df = pd.DataFrame(large_data)

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            df.to_excel(tmp_file.name, index=False)
            tmp_file_path = tmp_file.name

        try:
            # Test with dry run to avoid database operations
            result = service.import_excel_file(tmp_file_path, dry_run=True)

            # Should process all records
            assert result.records_processed == 50
            assert result.dry_run is True
        finally:
            os.unlink(tmp_file_path)

    def test_resolve_conflict_strategies(self):
        """Test resolve_conflict with different strategies - lines 237-256."""
        service = ImportService()

        # Create a test conflict
        conflict = ConflictRecord(
            entity_type="course",
            entity_key="TEST-101",
            field_name="course_title",
            existing_value="Old Title",
            import_value="New Title",
        )

        # Test USE_MINE strategy - lines 237-238
        result = service.resolve_conflict(conflict, ConflictStrategy.USE_MINE)
        assert "Kept existing" in result
        assert conflict.resolution == "kept_existing"

        # Test USE_THEIRS strategy
        result = service.resolve_conflict(conflict, ConflictStrategy.USE_THEIRS)
        assert "Updated" in result
        assert conflict.resolution == "used_import"

        # Test MERGE strategy - lines 244-248
        result = service.resolve_conflict(conflict, ConflictStrategy.MERGE)
        assert "Merged" in result
        assert conflict.resolution == "merged_import"

        # Test MANUAL_REVIEW strategy - lines 250-252
        result = service.resolve_conflict(conflict, ConflictStrategy.MANUAL_REVIEW)
        assert "Flagged for manual review" in result
        assert conflict.resolution == "flagged_manual"

        # Test invalid strategy - lines 254-256
        result = service.resolve_conflict(conflict, "invalid_strategy")
        assert "Unresolved conflict" in result
        assert conflict.resolution == "unresolved"

    @patch("import_service.get_course_by_number")
    @patch("import_service.create_course")
    def test_process_course_import_creation_failure(
        self, mock_create_course, mock_get_course
    ):
        """Test process_course_import when course creation fails - lines 345-348."""
        service = ImportService()

        # Mock no existing course so it tries to create
        mock_get_course.return_value = None
        # Mock course creation failure
        mock_create_course.return_value = None

        course_data = {"course_number": "TEST-101", "course_title": "Test Course"}

        # Test course creation failure
        success, conflicts = service.process_course_import(
            course_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        # Should handle failure gracefully
        assert success is False
        assert len(service.stats["errors"]) > 0
        assert any(
            "Failed to create course" in error for error in service.stats["errors"]
        )

    def test_process_course_import_dry_run_creation(self):
        """Test process_course_import in dry run mode - lines 349-352."""
        service = ImportService()

        course_data = {"course_number": "TEST-101", "course_title": "Test Course"}

        # Test dry run mode
        success, conflicts = service.process_course_import(
            course_data, ConflictStrategy.USE_THEIRS, dry_run=True
        )

        # Should succeed in dry run without actual creation
        assert success is True

    @patch("import_service.get_user_by_email")
    def test_process_user_import_with_conflicts_use_theirs(self, mock_get_user):
        """Test process_user_import with USE_THEIRS strategy - lines 376-396."""
        service = ImportService()

        # Mock existing user
        mock_get_user.return_value = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Smith",
            "user_id": "user123",
        }

        # Import user with different data
        user_data = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",  # Different last name
        }

        # Test with USE_THEIRS strategy
        success, conflicts = service.process_user_import(
            user_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        # Should detect conflicts and attempt to resolve
        assert service.stats["conflicts_detected"] > 0
        assert service.stats["records_updated"] > 0

    @patch("import_service.get_user_by_email")
    def test_process_user_import_with_conflicts_use_mine(self, mock_get_user):
        """Test process_user_import with USE_MINE strategy - lines 398-403."""
        service = ImportService()

        # Mock existing user
        mock_get_user.return_value = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Smith",
        }

        # Import user with different data
        user_data = {
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
        }

        # Test with USE_MINE strategy
        success, conflicts = service.process_user_import(
            user_data, ConflictStrategy.USE_MINE, dry_run=False
        )

        # Should skip the import
        assert service.stats["records_skipped"] > 0

    def test_import_excel_convenience_function(self):
        """Test import_excel convenience function - lines 855-867."""
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            df = pd.DataFrame(
                {
                    "Course Number": ["TEST-101"],
                    "Course Title": ["Test Course"],
                    "Instructor First Name": ["John"],
                    "Instructor Last Name": ["Doe"],
                    "Instructor Email": ["john@example.com"],
                    "Term": "Fall 2024",
                }
            )
            df.to_excel(tmp_file.name, index=False)
            tmp_file_path = tmp_file.name

        try:
            # Test the convenience function with string strategy
            result = import_excel(
                file_path=tmp_file_path,
                conflict_strategy="use_theirs",
                dry_run=True,
                verbose=True,
            )

            # Should create ImportService and call import_excel_file
            assert isinstance(result, ImportResult)
            assert result.dry_run is True
            assert result.records_processed > 0
        finally:
            os.unlink(tmp_file_path)

    def test_import_excel_invalid_strategy(self):
        """Test import_excel with invalid strategy defaults to USE_THEIRS - line 862."""
        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            df = pd.DataFrame(
                {
                    "Course Number": ["TEST-101"],
                    "Course Title": ["Test Course"],
                    "Instructor First Name": ["John"],
                    "Instructor Last Name": ["Doe"],
                    "Instructor Email": ["john@example.com"],
                    "Term": "Fall 2024",
                }
            )
            df.to_excel(tmp_file.name, index=False)
            tmp_file_path = tmp_file.name

        try:
            # Test with invalid strategy
            result = import_excel(
                file_path=tmp_file_path,
                conflict_strategy="invalid_strategy",
                dry_run=True,
            )

            # Should default to USE_THEIRS and still work
            assert isinstance(result, ImportResult)
            assert result.dry_run is True
        finally:
            os.unlink(tmp_file_path)

    @patch("import_service.get_user_by_email")
    @patch("import_service.str")
    @patch("import_service.uuid.uuid4")
    def test_process_user_import_creation_failure(
        self, mock_uuid, mock_str, mock_get_user
    ):
        """Test process_user_import when user creation fails - lines 423-426."""
        service = ImportService()

        # Mock no existing user so it tries to create
        mock_get_user.return_value = None
        # Mock user creation failure by making str() return None (falsy)
        mock_str.return_value = None

        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }

        # Test user creation failure
        success, conflicts = service.process_user_import(
            user_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        # Should handle failure gracefully
        assert success is False
        assert len(service.stats["errors"]) > 0
        assert any(
            "Failed to create user" in error for error in service.stats["errors"]
        )

    def test_process_user_import_dry_run_duplicate_tracking(self):
        """Test process_user_import dry run with duplicate tracking - lines 428-433."""
        service = ImportService()

        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
        }

        # Test first dry run
        success1, conflicts1 = service.process_user_import(
            user_data, ConflictStrategy.USE_THEIRS, dry_run=True
        )

        # Test second dry run with same user (should detect duplicate)
        success2, conflicts2 = service.process_user_import(
            user_data, ConflictStrategy.USE_THEIRS, dry_run=True
        )

        # Both should succeed, but user should be tracked
        assert success1 is True
        assert success2 is True
        assert "test@example.com" in service._processed_users

    def test_import_excel_unknown_adapter(self):
        """Test import_excel_file with unknown adapter - lines 518-519."""
        service = ImportService()

        # Create a temporary Excel file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            df = pd.DataFrame(
                {
                    "Course Number": ["TEST-101"],
                    "Course Title": ["Test Course"],
                    "Instructor First Name": ["John"],
                    "Instructor Last Name": ["Doe"],
                    "Instructor Email": ["john@example.com"],
                    "Term": "Fall 2024",
                }
            )
            df.to_excel(tmp_file.name, index=False)
            tmp_file_path = tmp_file.name

        try:
            # Test with unknown adapter
            result = service.import_excel_file(
                tmp_file_path, adapter_name="unknown_adapter", dry_run=True
            )

            # Should handle unknown adapter gracefully
            assert len(service.stats["errors"]) > 0
            assert any("Unknown adapter" in error for error in service.stats["errors"])
        finally:
            os.unlink(tmp_file_path)

    def test_import_excel_course_processing_path(self):
        """Test import_excel_file course processing path - lines 524-527."""
        service = ImportService()

        # Create Excel file with course data
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            df = pd.DataFrame(
                {
                    "Course Number": ["MATH-101", "CS-201"],
                    "Course Title": ["Mathematics", "Computer Science"],
                    "Instructor First Name": ["John", "Jane"],
                    "Instructor Last Name": ["Doe", "Smith"],
                    "Instructor Email": ["john@example.com", "jane@example.com"],
                    "Term": ["Fall 2024", "Fall 2024"],
                }
            )
            df.to_excel(tmp_file.name, index=False)
            tmp_file_path = tmp_file.name

        try:
            # Test course processing
            result = service.import_excel_file(tmp_file_path, dry_run=True)

            # Should process courses successfully
            assert result.records_processed == 2
            assert result.dry_run is True
        finally:
            os.unlink(tmp_file_path)

    def test_create_import_report_function(self):
        """Test create_import_report function - lines 878-921."""
        # Create a sample ImportResult with various data
        conflicts = [
            ConflictRecord(
                entity_type="course",
                entity_key="TEST-101",
                field_name="course_title",
                existing_value="Old Title",
                import_value="New Title",
            )
        ]

        result = ImportResult(
            success=True,
            records_processed=10,
            records_created=5,
            records_updated=3,
            records_skipped=2,
            conflicts_detected=1,
            conflicts_resolved=1,
            conflicts=conflicts,
            execution_time=1.5,
            dry_run=False,
            errors=[],
            warnings=[],
        )

        # Test the report generation
        report = create_import_report(result)

        # Should contain key information
        assert "DATA IMPORT REPORT" in report
        assert "Records processed: 10" in report
        assert "Records created: 5" in report
        assert "Records updated: 3" in report
        assert "Records skipped: 2" in report
        assert "Conflicts detected: 1" in report
        assert "Conflicts resolved: 1" in report
        assert "Execution time: 1.50 seconds" in report
        assert "Mode: EXECUTE" in report
        assert "Overall success: YES" in report
        assert "CONFLICTS:" in report
        assert "TEST-101" in report

    def test_create_import_report_dry_run(self):
        """Test create_import_report with dry run mode."""
        result = ImportResult(
            success=True,
            records_processed=5,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            conflicts_detected=0,
            conflicts_resolved=0,
            conflicts=[],
            execution_time=0.8,
            dry_run=True,
            errors=[],
            warnings=[],
        )

        report = create_import_report(result)

        # Should indicate dry run mode
        assert "Mode: DRY RUN" in report
        assert "Records processed: 5" in report

    @patch("database_service.db")
    def test_delete_all_data_exception(self, mock_db):
        """Test _delete_all_data with exception - lines 802-805."""
        service = ImportService()

        # Mock database collection to raise exception during stream() call
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        mock_collection.stream.side_effect = Exception("Database connection failed")

        # Test delete operation with exception
        service._delete_all_data()

        # Should handle exception gracefully
        assert len(service.stats["errors"]) > 0
        assert any(
            "Failed to delete existing data" in error
            for error in service.stats["errors"]
        )

    def test_import_result_creation_with_stats(self):
        """Test _create_import_result method - lines 807-827."""
        service = ImportService()

        # Set up some stats
        service.stats["records_processed"] = 10
        service.stats["records_created"] = 5
        service.stats["records_updated"] = 3
        service.stats["records_skipped"] = 2
        service.stats["conflicts_detected"] = 1
        service.stats["conflicts_resolved"] = 1
        service.stats["errors"] = ["Test error"]
        service.stats["warnings"] = ["Test warning"]
        service.stats["conflicts"] = [
            ConflictRecord(
                entity_type="test",
                entity_key="key1",
                field_name="field1",
                existing_value="old",
                import_value="new",
            )
        ]

        # Create import result
        from datetime import datetime, timezone

        start_time = datetime.now(timezone.utc)
        result = service._create_import_result(start_time, dry_run=True)

        # Should have all the stats
        assert result.records_processed == 10
        assert result.records_created == 5
        assert result.records_updated == 3
        assert result.records_skipped == 2
        assert result.conflicts_detected == 1
        assert result.conflicts_resolved == 1
        assert result.dry_run is True
        assert len(result.conflicts) == 1
        assert result.execution_time > 0

    def test_import_excel_term_processing_path(self):
        """Test import_excel_file term processing path - lines 537-547."""
        service = ImportService()

        # Create Excel file with term data
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            df = pd.DataFrame(
                {
                    "Course Number": ["TEST-101"],
                    "Course Title": ["Test Course"],
                    "Instructor First Name": ["John"],
                    "Instructor Last Name": ["Doe"],
                    "Instructor Email": ["john@example.com"],
                    "Term": "Fall 2024",
                    "Start Date": "2024-08-01",
                    "End Date": "2024-12-15",
                }
            )
            df.to_excel(tmp_file.name, index=False)
            tmp_file_path = tmp_file.name

        try:
            # Test term processing in dry run
            result = service.import_excel_file(tmp_file_path, dry_run=True)

            # Should process terms successfully
            assert result.records_processed == 1
            assert result.dry_run is True
        finally:
            os.unlink(tmp_file_path)

    def test_import_excel_section_processing_path(self):
        """Test import_excel_file section processing path - lines 551-566."""
        service = ImportService()

        # Create Excel file with section data
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            df = pd.DataFrame(
                {
                    "Course Number": ["MATH-101"],
                    "Course Title": ["Mathematics"],
                    "Instructor First Name": ["Jane"],
                    "Instructor Last Name": ["Smith"],
                    "Instructor Email": ["jane@example.com"],
                    "Term": "Spring 2024",
                    "Section Number": "001",
                }
            )
            df.to_excel(tmp_file.name, index=False)
            tmp_file_path = tmp_file.name

        try:
            # Test section processing in dry run
            result = service.import_excel_file(tmp_file_path, dry_run=True)

            # Should process sections successfully
            assert result.records_processed == 1
            assert result.dry_run is True
        finally:
            os.unlink(tmp_file_path)

    def test_parse_cei_excel_row_exception_handling(self):
        """Test _parse_cei_excel_row exception handling - lines 662-664."""
        service = ImportService()

        # Create a row that will cause parsing errors
        row_data = {
            "Course Number": None,  # This will cause issues
            "Invalid Column": "Invalid Data",
        }
        row = pd.Series(row_data)

        # Test exception handling
        result = service._parse_cei_excel_row(row)

        # Should return empty structure on error
        assert result is not None
        assert result.get("course") is None
        assert result.get("user") is None
        assert result.get("term") is None
        assert result.get("section") is None

    def test_extract_department_from_course(self):
        """Test _extract_department_from_course function - lines 668-680."""
        service = ImportService()

        # Test known department mappings
        assert service._extract_department_from_course("ACC-101") == "Business"
        assert service._extract_department_from_course("BUS-201") == "Business"
        assert service._extract_department_from_course("NURS-301") == "Nursing"
        assert service._extract_department_from_course("BIOL-401") == "Science"
        assert service._extract_department_from_course("MATH-501") == "Mathematics"
        assert service._extract_department_from_course("ENG-601") == "English"

        # Test unknown department
        assert (
            service._extract_department_from_course("UNKNOWN-999") == "General Studies"
        )

        # Test course without dash
        assert service._extract_department_from_course("INVALID") == "General Studies"

    def test_parse_name_from_email(self):
        """Test _parse_name_from_email function - lines 698-724."""
        service = ImportService()

        # Test email with dot separator
        first, last = service._parse_name_from_email("john.doe")
        assert first == "John"
        assert last == "Doe"

        # Test email with number
        first, last = service._parse_name_from_email("instructor1")
        assert first == "Instructor"
        assert last == "1"

        # Test simple name
        first, last = service._parse_name_from_email("teacher")
        assert first == "Teacher"
        assert last == "Unknown"

        # Test empty name
        first, last = service._parse_name_from_email("")
        assert first == "Unknown"
        assert last == "Instructor"

        # Test complex email prefix
        first, last = service._parse_name_from_email("jane.smith")
        assert first == "Jane"
        assert last == "Smith"

    def test_parse_name_function(self):
        """Test _parse_name function - lines 684-690."""
        service = ImportService()

        # Test full name parsing
        first, last = service._parse_name("John Doe")
        assert first == "John"
        assert last == "Doe"

        # Test single name
        first, last = service._parse_name("John")
        assert first == "John"
        assert last == "Unknown"

        # Test multiple names
        first, last = service._parse_name("John Michael Doe")
        assert first == "John"
        assert last == "Michael Doe"

        # Test empty name
        first, last = service._parse_name("")
        assert first == "Unknown"
        assert last == "Instructor"

    def test_estimate_term_dates(self):
        """Test term date estimation functions - lines 729-739, 743-753."""
        service = ImportService()

        # Test fall term
        start_date = service._estimate_term_start("2024 Fall")
        end_date = service._estimate_term_end("2024 Fall")
        assert start_date == "2024-08-15"
        assert end_date == "2024-12-15"

        # Test spring term
        start_date = service._estimate_term_start("2024 Spring")
        end_date = service._estimate_term_end("2024 Spring")
        assert start_date == "2024-01-15"
        assert end_date == "2024-05-15"

        # Test summer term
        start_date = service._estimate_term_start("2024 Summer")
        end_date = service._estimate_term_end("2024 Summer")
        assert start_date == "2024-06-01"
        assert end_date == "2024-08-15"

        # Test invalid term format
        start_date = service._estimate_term_start("Invalid")
        end_date = service._estimate_term_end("Invalid")
        assert start_date == "2024-01-01"
        assert end_date == "2024-05-01"

    def test_generate_email_function(self):
        """Test _generate_email function - line 694."""
        service = ImportService()

        # Test email generation
        email = service._generate_email("John", "Doe")
        assert email == "john.doe@cei.edu"

        # Test with mixed case
        email = service._generate_email("JANE", "SMITH")
        assert email == "jane.smith@cei.edu"

        # Test with empty strings
        email = service._generate_email("", "")
        assert email == ".@cei.edu"
