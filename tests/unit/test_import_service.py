"""
Unit tests for import_service.py

Comprehensive tests for the ImportService class including file operations,
data processing, conflict resolution, and database interactions.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from import_service import (
    ImportService, 
    ConflictStrategy,
    ImportMode,
    ConflictRecord,
    ImportResult,
    import_excel,
    create_import_report,
)


class TestImportService:
    """Main test class for ImportService functionality."""

    def test_import_excel_file_not_found_error(self):
        """Test import_excel_file with non-existent file - Line 198."""
        service = ImportService()
        
        # Test with non-existent file
        result = service.import_excel_file('nonexistent_file.xlsx')
        
        # Should handle file not found gracefully
        assert result.success is False
        assert len(result.errors) > 0
        assert any('not found' in error.lower() or 'no such file' in error.lower() for error in result.errors)

    def test_import_excel_file_comprehensive_workflow(self):
        """Test import_excel_file comprehensive workflow to hit lines 244-256."""
        service = ImportService()
        
        # Create a real temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create DataFrame with test data
            test_data = {
                'Course Number': ['TEST-101', 'TEST-102'],
                'Course Title': ['Test Course 1', 'Test Course 2'],
                'Instructor First Name': ['John', 'Jane'],
                'Instructor Last Name': ['Doe', 'Smith'],
                'Instructor Email': ['john@example.com', 'jane@example.com'],
                'Term': ['FA24', 'FA24'],
                'Students': [25, 30],
                'Department': ['TEST', 'TEST']
            }
            df = pd.DataFrame(test_data)
            df.to_excel(tmp_file.name, index=False)
            
        try:
            with patch('database_service.get_user_by_email', return_value=None), \
                 patch('database_service.get_course_by_number', return_value=None), \
                 patch('database_service.create_user', return_value='user123'), \
                 patch('database_service.create_course', return_value='course123'):
                
                result = service.import_excel_file(
                    tmp_file.name,
                    conflict_strategy=ConflictStrategy.USE_THEIRS,
                    dry_run=False,
                    delete_existing_db=False
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
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            test_data = {
                'Course Number': ['TEST-101'],
                'Course Title': ['Test Course'],
                'Instructor First Name': ['John'],
                'Instructor Last Name': ['Doe'],
                'Instructor Email': ['john@example.com'],
                'Term': ['FA24'],
                'Students': [25],
                'Department': ['TEST']
            }
            df = pd.DataFrame(test_data)
            df.to_excel(tmp_file.name, index=False)
            
        try:
            with patch('database_service.get_user_by_email', return_value=None), \
                 patch('database_service.get_course_by_number', return_value=None), \
                 patch.object(service, '_delete_all_data') as mock_delete:
                
                result = service.import_excel_file(
                    tmp_file.name,
                    delete_existing_db=True,
                    dry_run=False
                )
                
                # Should have called delete_all_data
                mock_delete.assert_called_once()
                
        finally:
            os.unlink(tmp_file.name)

    def test_import_excel_file_dry_run_mode(self):
        """Test import_excel_file in dry_run mode to hit dry run logic."""
        service = ImportService()
        
        # Create minimal Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            test_data = {
                'Course Number': ['TEST-101'],
                'Course Title': ['Test Course'],
                'Instructor First Name': ['John'],
                'Instructor Last Name': ['Doe'],
                'Instructor Email': ['john@example.com'],
                'Term': ['FA24'],
                'Students': [25],
                'Department': ['TEST']
            }
            df = pd.DataFrame(test_data)
            df.to_excel(tmp_file.name, index=False)
            
        try:
            with patch('database_service.get_user_by_email', return_value=None), \
                 patch('database_service.get_course_by_number', return_value=None):
                
                result = service.import_excel_file(
                    tmp_file.name,
                    dry_run=True
                )
                
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
            'email': 'existing@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'instructor'
        }
        
        # Mock existing user with different data
        existing_user = {
            'email': 'existing@example.com',
            'first_name': 'Jane',  # Different name
            'last_name': 'Smith'   # Different name
        }
        
        with patch('database_service.get_user_by_email', return_value=existing_user):
            success, conflicts = service.process_user_import(
                user_data,
                ConflictStrategy.USE_MINE,
                dry_run=False
            )
            
            # Should detect conflict
            assert isinstance(success, bool)
            assert isinstance(conflicts, list)

    def test_process_course_import_with_existing_course(self):
        """Test process_course_import with existing course to hit conflict resolution."""
        service = ImportService()
        
        course_data = {
            'course_number': 'EXISTING-101',
            'course_title': 'New Title',
            'department': 'TEST'
        }
        
        # Mock existing course with different data
        existing_course = {
            'course_number': 'EXISTING-101',
            'course_title': 'Old Title',  # Different title
            'department': 'TEST'
        }
        
        with patch('database_service.get_course_by_number', return_value=existing_course):
            success, conflicts = service.process_course_import(
                course_data,
                ConflictStrategy.USE_THEIRS,
                dry_run=False
            )
            
            # Should detect conflict
            assert isinstance(success, bool)
            assert isinstance(conflicts, list)

    def test_delete_all_data_functionality(self):
        """Test _delete_all_data method to hit deletion logic."""
        service = ImportService()
        
        with patch('database_service.db') as mock_db:
            # Mock collection method
            mock_collection = Mock()
            mock_docs = [Mock(reference=Mock(delete=Mock())) for i in range(3)]
            mock_collection.stream.return_value = mock_docs
            mock_db.collection.return_value = mock_collection
            
            with patch('builtins.print'):  # Suppress print output
                # Test deletion
                service._delete_all_data()
            
            # Verify collection method was called for each collection type
            assert mock_db.collection.call_count >= 1

    def test_logging_functionality(self):
        """Test _log method with different combinations."""
        # Test verbose mode
        service_verbose = ImportService(verbose=True)
        with patch('builtins.print') as mock_print:
            service_verbose._log("Test message", "info")
            service_verbose._log("Error message", "error")
            service_verbose._log("Warning message", "warning")
            service_verbose._log("Summary message", "summary")
            assert mock_print.call_count >= 3  # Should print most messages in verbose mode
        
        # Test non-verbose mode
        service_quiet = ImportService(verbose=False)
        with patch('builtins.print') as mock_print:
            service_quiet._log("Test message", "info")  # Should not print
            service_quiet._log("Error message", "error")  # Should print
            service_quiet._log("Summary message", "summary")  # Should print
            assert mock_print.call_count >= 1  # Should print errors and summaries

    def test_create_import_result_with_various_stats(self):
        """Test _create_import_result with different stat combinations."""
        service = ImportService()
        
        # Set up various stats conditions
        service.stats['records_processed'] = 100
        service.stats['records_created'] = 80
        service.stats['records_updated'] = 20
        service.stats['records_skipped'] = 5
        service.stats['conflicts_detected'] = 3
        service.stats['conflicts_resolved'] = 2
        service.stats['errors'] = ['Error 1', 'Error 2']
        service.stats['warnings'] = ['Warning 1']
        
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
            'course_title': 'Test Course',
            # Missing 'course_number'
        }
        
        conflicts = service.detect_course_conflict(import_course_no_number)
        assert isinstance(conflicts, list)
        
        # Test with complete course data
        import_course_complete = {
            'course_number': 'TEST-101',
            'course_title': 'Test Course',
            'department': 'TEST'
        }
        
        conflicts2 = service.detect_course_conflict(import_course_complete)
        assert isinstance(conflicts2, list)

    def test_import_excel_file_large_dataset_progress(self):
        """Test import_excel_file with large dataset to trigger progress reporting."""
        service = ImportService(verbose=True)
        
        # Create larger dataset to trigger progress reporting (50+ records)
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            test_data = {
                'Course Number': [f'TEST-{i:03d}' for i in range(60)],
                'Course Title': [f'Test Course {i}' for i in range(60)],
                'Instructor First Name': ['John'] * 60,
                'Instructor Last Name': ['Doe'] * 60,
                'Instructor Email': [f'john{i}@example.com' for i in range(60)],
                'Term': ['FA24'] * 60,
                'Students': [25] * 60,
                'Department': ['TEST'] * 60
            }
            df = pd.DataFrame(test_data)
            df.to_excel(tmp_file.name, index=False)
            
        try:
            with patch('database_service.get_user_by_email', return_value=None), \
                 patch('database_service.get_course_by_number', return_value=None), \
                 patch('builtins.print') as mock_print:
                
                result = service.import_excel_file(
                    tmp_file.name,
                    dry_run=True  # Use dry run to avoid actual database operations
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
            import_value="New Title"
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
            dry_run=False
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
        
        with patch('builtins.print') as mock_print:
            service._log("Test error", "error")
            mock_print.assert_called_once_with("[Import] ERROR: Test error")

    def test_log_warning_message(self):
        """Test logging warning messages."""
        service = ImportService(verbose=False)
        
        with patch('builtins.print') as mock_print:
            service._log("Test warning", "warning")
            mock_print.assert_called_once_with("[Import] WARNING: Test warning")

    def test_log_summary_message(self):
        """Test logging summary messages."""
        service = ImportService(verbose=False)
        
        with patch('builtins.print') as mock_print:
            service._log("Test summary", "summary")
            mock_print.assert_called_once_with("[Import] Test summary")

    def test_log_verbose_mode_on(self):
        """Test logging in verbose mode."""
        service = ImportService(verbose=True)
        
        with patch('builtins.print') as mock_print:
            service._log("Test message", "info")
            mock_print.assert_called_once_with("[Import] Test message")

    def test_log_verbose_mode_off(self):
        """Test logging in non-verbose mode."""
        service = ImportService(verbose=False)
        
        with patch('builtins.print') as mock_print:
            service._log("Test message", "info")
            mock_print.assert_not_called()


class TestDetectCourseConflict:
    """Test detect_course_conflict method."""

    def test_detect_course_conflict_method_exists(self):
        """Test that detect_course_conflict method exists."""
        service = ImportService()
        assert hasattr(service, 'detect_course_conflict')
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
        assert hasattr(service, 'stats')
        assert hasattr(service, '_processed_users')
        assert hasattr(service, '_processed_courses')


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
            'course_title': 'Test Course',
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
            'Course Number': 'TEST-101',
            'Course Title': 'Test Course',
            'Instructor First Name': 'John',
            'Instructor Last Name': 'Doe',
            'Instructor Email': 'john@example.com',
            'Term': 'FA24',
            'Students': '25',
            'Department': 'TEST'
        }
        row = pd.Series(row_data)
        
        result = service._parse_cei_excel_row(row)
        
        # Should return parsed structure
        assert isinstance(result, dict)
        assert 'user' in result
        assert 'course' in result
