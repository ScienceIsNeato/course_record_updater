"""
Test for the Import Service Conflict Detection Bug

This test reproduces the specific bug where:
1. A course already exists in the database
2. The import system fails to detect it as a conflict
3. It tries to create the course anyway and fails
4. This results in "Failed to create course" errors

The bug is in detect_course_conflict() method which only checks for field differences,
not for the existence of the course itself.
"""

from unittest.mock import MagicMock, patch

import pytest

from database_service_extended import create_course
from import_service import ConflictStrategy, ImportService


class TestImportServiceConflictBug:
    """Test cases for the course conflict detection bug"""

    def setup_method(self):
        """Set up test fixtures"""
        self.import_service = ImportService()

        # Sample course data that matches CEI format
        self.existing_course_data = {
            "course_number": "ACC-201",
            "course_title": "Principles of Accounting II",
            "department": "Business",
            "credit_hours": 3,
        }

        self.import_course_data = {
            "course_number": "ACC-201",
            "course_title": "Principles of Accounting II",  # Same title
            "department": "Business",  # Same department
            "credit_hours": 3,  # Same credit hours
        }

    @patch("import_service.get_course_by_number")
    @patch("import_service.create_course")
    def test_existing_course_with_identical_data_should_be_detected_as_conflict(
        self, mock_create_course, mock_get_course
    ):
        """
        FAILING TEST: Reproduces the bug where identical existing courses
        are not detected as conflicts with use_theirs strategy.

        Expected behavior:
        1. Course exists with identical data
        2. Should be detected as conflict (course exists)
        3. With use_theirs strategy, should skip creation (no change needed)
        4. Should NOT attempt to create the course

        Actual buggy behavior:
        1. Course exists with identical data
        2. No conflicts detected (BUG!)
        3. Attempts to create course anyway
        4. create_course fails because course exists
        5. Results in "Failed to create course" error
        """
        # Arrange: Course already exists in database
        mock_get_course.return_value = self.existing_course_data
        mock_create_course.return_value = None  # Simulates creation failure

        # Act: Try to import the same course with use_theirs strategy
        success, conflicts = self.import_service.process_course_import(
            course_data=self.import_course_data,
            strategy=ConflictStrategy.USE_THEIRS,
            dry_run=False,
        )

        # Assert: Should detect conflict and NOT attempt creation
        # CURRENTLY FAILS - This is the bug we're fixing
        assert len(conflicts) > 0, "Should detect existing course as a conflict"
        assert (
            success == True
        ), "Should succeed when handling existing course with use_theirs"

        # Should NOT attempt to create the course since it already exists
        mock_create_course.assert_not_called()

        # Should have either updated or skipped (not created)
        assert (
            self.import_service.stats["records_updated"] > 0
            or self.import_service.stats["records_skipped"] > 0
        )
        assert self.import_service.stats["records_created"] == 0
        assert len(self.import_service.stats["errors"]) == 0

    @patch("import_service.get_course_by_number")
    @patch("import_service.create_course")
    def test_existing_course_with_different_data_should_update_with_use_theirs(
        self, mock_create_course, mock_get_course
    ):
        """
        Test that when course exists with different data, use_theirs should update it
        """
        # Arrange: Course exists with different title
        existing_different = self.existing_course_data.copy()
        existing_different["course_title"] = "Old Accounting Title"

        mock_get_course.return_value = existing_different

        # Act: Import with different title using use_theirs
        success, conflicts = self.import_service.process_course_import(
            course_data=self.import_course_data,
            strategy=ConflictStrategy.USE_THEIRS,
            dry_run=False,
        )

        # Assert: Should detect conflict and attempt update
        assert len(conflicts) > 0, "Should detect field differences as conflicts"
        assert success == True, "Should succeed when updating existing course"

        # Should NOT attempt to create since course exists
        mock_create_course.assert_not_called()

        # Note: Currently update is not implemented (TODO in code)
        # But at minimum, should not attempt creation

    @patch("import_service.get_course_by_number")
    @patch("import_service.create_course")
    def test_existing_course_with_use_mine_should_skip_creation(
        self, mock_create_course, mock_get_course
    ):
        """
        Test that use_mine strategy properly skips existing courses
        """
        # Arrange: Course already exists
        mock_get_course.return_value = self.existing_course_data

        # Act: Try to import with use_mine strategy
        success, conflicts = self.import_service.process_course_import(
            course_data=self.import_course_data,
            strategy=ConflictStrategy.USE_MINE,
            dry_run=False,
        )

        # Assert: Should detect conflict and skip
        assert success == True, "Should succeed when skipping existing course"
        mock_create_course.assert_not_called()
        assert self.import_service.stats["records_skipped"] > 0
        assert self.import_service.stats["records_created"] == 0

    @patch("import_service.get_course_by_number")
    @patch("import_service.create_course")
    def test_new_course_should_be_created_successfully(
        self, mock_create_course, mock_get_course
    ):
        """
        Test that truly new courses are created successfully
        """
        # Arrange: Course does not exist
        mock_get_course.return_value = None
        mock_create_course.return_value = "new_course_id_123"

        # Act: Import new course
        success, conflicts = self.import_service.process_course_import(
            course_data=self.import_course_data,
            strategy=ConflictStrategy.USE_THEIRS,
            dry_run=False,
        )

        # Assert: Should create successfully
        assert len(conflicts) == 0, "Should not detect conflicts for new course"
        assert success == True, "Should succeed when creating new course"
        mock_create_course.assert_called_once()
        assert self.import_service.stats["records_created"] == 1
        assert len(self.import_service.stats["errors"]) == 0

    def test_detect_course_conflict_method_directly(self):
        """
        Test the detect_course_conflict method directly to isolate the bug
        """
        with patch("import_service.get_course_by_number") as mock_get_course:
            # Arrange: Course exists with identical data
            mock_get_course.return_value = self.existing_course_data

            # Act: Check for conflicts
            conflicts = self.import_service.detect_course_conflict(
                self.import_course_data
            )

            # Assert: CURRENTLY FAILS - This is the core bug
            # The method should detect that the course exists, even if data is identical
            # Because the existence itself is a "conflict" that needs resolution
            assert len(conflicts) > 0, (
                "BUG: detect_course_conflict should flag existing courses as conflicts, "
                "even when data is identical, so that conflict resolution strategy can decide "
                "whether to skip, update, or handle the existing course"
            )


if __name__ == "__main__":
    # Run the specific failing test to demonstrate the bug
    pytest.main(
        [
            __file__
            + "::TestImportServiceConflictBug::test_existing_course_with_identical_data_should_be_detected_as_conflict",
            "-v",
        ]
    )
