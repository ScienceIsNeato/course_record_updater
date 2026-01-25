"""Unit tests for programs API routes (migrated from test_api_routes.py)."""

from unittest.mock import patch

import pytest


class TestRemoveCourseHelpers:
    """Test helper functions for remove_course_from_program_api."""

    def test_validate_program_for_removal_success(self):
        """Test _validate_program_for_removal with valid program."""
        from unittest.mock import patch

        from src.api.routes.programs import _validate_program_for_removal

        mock_program = {
            "id": "prog1",
            "institution_id": "inst1",
            "name": "Test Program",
        }

        with patch("src.api.routes.programs.get_program_by_id") as mock_get_program:
            mock_get_program.return_value = mock_program

            program, institution_id = _validate_program_for_removal("prog1")

            mock_get_program.assert_called_once_with("prog1")
            assert program == mock_program
            assert institution_id == "inst1"

    def test_validate_program_for_removal_not_found(self):
        """Test _validate_program_for_removal raises ValueError when program not found."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.programs import _validate_program_for_removal

        with patch("src.api.routes.programs.get_program_by_id") as mock_get_program:
            mock_get_program.return_value = None

            with pytest.raises(ValueError, match="Program not found"):
                _validate_program_for_removal("prog1")

    def test_get_default_program_id_with_default(self):
        """Test _get_default_program_id returns default program."""
        from unittest.mock import patch

        from src.api.routes.programs import _get_default_program_id

        mock_programs = [
            {"id": "prog1", "is_default": False},
            {"id": "prog2", "is_default": True},
            {"id": "prog3", "is_default": False},
        ]

        with patch(
            "src.api.routes.programs.get_programs_by_institution"
        ) as mock_get_programs:
            mock_get_programs.return_value = mock_programs

            result = _get_default_program_id("inst1")

            mock_get_programs.assert_called_once_with("inst1")
            assert result == "prog2"

    def test_get_default_program_id_no_default(self):
        """Test _get_default_program_id returns None when no default exists."""
        from unittest.mock import patch

        from src.api.routes.programs import _get_default_program_id

        mock_programs = [
            {"id": "prog1", "is_default": False},
            {"id": "prog2", "is_default": False},
        ]

        with patch(
            "src.api.routes.programs.get_programs_by_institution"
        ) as mock_get_programs:
            mock_get_programs.return_value = mock_programs

            result = _get_default_program_id("inst1")

            assert result is None

    def test_get_default_program_id_no_institution(self):
        """Test _get_default_program_id returns None when no institution_id."""
        from src.api.routes.programs import _get_default_program_id

        result = _get_default_program_id(None)
        assert result is None

        result = _get_default_program_id("")
        assert result is None

    def test_get_default_program_id_no_programs(self):
        """Test _get_default_program_id returns None when institution has no programs."""
        from unittest.mock import patch

        from src.api.routes.programs import _get_default_program_id

        with patch(
            "src.api.routes.programs.get_programs_by_institution"
        ) as mock_get_programs:
            mock_get_programs.return_value = None

            result = _get_default_program_id("inst1")

            assert result is None

    def test_remove_course_with_orphan_handling_success(self):
        """Test _remove_course_with_orphan_handling successfully removes course."""
        from unittest.mock import patch

        from src.api.routes.programs import _remove_course_with_orphan_handling

        with (
            patch("src.api.routes.programs.remove_course_from_program") as mock_remove,
            patch(
                "src.api.routes.programs.assign_course_to_default_program"
            ) as mock_assign,
        ):
            mock_remove.return_value = True

            result = _remove_course_with_orphan_handling(
                "course1", "prog1", "inst1", "default_prog"
            )

            mock_remove.assert_called_once_with("course1", "prog1")
            mock_assign.assert_called_once_with("course1", "inst1")
            assert result is True

    def test_remove_course_with_orphan_handling_no_default_program(self):
        """Test _remove_course_with_orphan_handling when no default program exists."""
        from unittest.mock import patch

        from src.api.routes.programs import _remove_course_with_orphan_handling

        with (
            patch("src.api.routes.programs.remove_course_from_program") as mock_remove,
            patch(
                "src.api.routes.programs.assign_course_to_default_program"
            ) as mock_assign,
        ):
            mock_remove.return_value = True

            result = _remove_course_with_orphan_handling(
                "course1", "prog1", "inst1", None
            )

            mock_remove.assert_called_once_with("course1", "prog1")
            # Should not try to assign when no default program
            mock_assign.assert_not_called()
            assert result is True

    def test_build_removal_response_success(self):
        """Test _build_removal_response builds success response."""
        from src.api.routes.programs import _build_removal_response
        from src.app import app

        with app.app_context():
            mock_program = {"name": "Test Program"}
            response = _build_removal_response(True, "course1", mock_program)

            data = response.get_json()
            assert data["success"] is True
            assert "removed from program Test Program" in data["message"]
            # Success case returns just response (defaults to 200)
            assert response.status_code == 200

    def test_build_removal_response_failure(self):
        """Test _build_removal_response builds failure response."""
        from src.api.routes.programs import _build_removal_response
        from src.app import app

        with app.app_context():
            mock_program = {"name": "Test Program"}
            response, status = _build_removal_response(False, "course1", mock_program)

            data = response.get_json()
            assert data["success"] is False
            assert "Failed to remove" in data["error"]
            assert status == 500


class TestBulkManageHelpers:
    """Test helper functions for bulk_manage_program_courses."""

    def test_validate_bulk_manage_request_success(self):
        """Test _validate_bulk_manage_request with valid data."""

        from src.api.routes.programs import _validate_bulk_manage_request
        from src.app import app

        with app.test_client() as client:
            with client.application.test_request_context(
                json={"action": "add", "course_ids": ["course1", "course2"]}
            ):
                result = _validate_bulk_manage_request()
                assert result is None  # No validation error

    def test_validate_bulk_manage_request_no_data(self):
        """Test _validate_bulk_manage_request with no data."""
        from src.api.routes.programs import _validate_bulk_manage_request
        from src.app import app

        with app.test_client() as client:
            # Empty dict is treated as "no data"
            with client.application.test_request_context(json={}):
                response, status = _validate_bulk_manage_request()
                data = response.get_json()
                assert data["success"] is False
                assert "No data provided" in data["error"]
                assert status == 400

    def test_validate_bulk_manage_request_invalid_action(self):
        """Test _validate_bulk_manage_request with invalid action."""

        from src.api.routes.programs import _validate_bulk_manage_request
        from src.app import app

        with app.test_client() as client:
            with client.application.test_request_context(
                json={"action": "invalid", "course_ids": ["course1"]}
            ):
                response, status = _validate_bulk_manage_request()
                data = response.get_json()
                assert data["success"] is False
                assert "Invalid or missing action" in data["error"]
                assert status == 400

    def test_validate_bulk_manage_request_missing_course_ids(self):
        """Test _validate_bulk_manage_request with missing course_ids."""

        from src.api.routes.programs import _validate_bulk_manage_request
        from src.app import app

        with app.test_client() as client:
            with client.application.test_request_context(json={"action": "add"}):
                response, status = _validate_bulk_manage_request()
                data = response.get_json()
                assert data["success"] is False
                assert "Missing or invalid course_ids" in data["error"]
                assert status == 400

    def test_execute_bulk_add(self):
        """Test _execute_bulk_add helper."""
        from unittest.mock import patch

        from src.api.routes.programs import _execute_bulk_add

        mock_result = {"success_count": 5, "failed_count": 0}

        with patch(
            "src.api.routes.programs.bulk_add_courses_to_program"
        ) as mock_bulk_add:
            mock_bulk_add.return_value = mock_result

            result, message = _execute_bulk_add(["course1", "course2"], "prog1")

            mock_bulk_add.assert_called_once_with(["course1", "course2"], "prog1")
            assert result == mock_result
            assert "5 added" in message

    def test_execute_bulk_remove_with_default_program(self):
        """Test _execute_bulk_remove with default program available."""
        from unittest.mock import patch

        from src.api.routes.programs import _execute_bulk_remove

        mock_result = {"removed": 3, "failed": 0}

        with (
            patch(
                "src.api.routes.programs.get_current_institution_id_safe"
            ) as mock_get_inst,
            patch(
                "src.api.routes.programs._get_default_program_id"
            ) as mock_get_default,
            patch(
                "src.api.routes.programs.bulk_remove_courses_from_program"
            ) as mock_bulk_remove,
            patch(
                "src.api.routes.programs.assign_course_to_default_program"
            ) as mock_assign,
        ):
            mock_get_inst.return_value = "inst1"
            mock_get_default.return_value = "default_prog"
            mock_bulk_remove.return_value = mock_result

            result, message = _execute_bulk_remove(
                ["course1", "course2", "course3"], "prog1"
            )

            mock_bulk_remove.assert_called_once_with(
                ["course1", "course2", "course3"], "prog1"
            )
            # Should assign all courses to default program
            assert mock_assign.call_count == 3
            assert result == mock_result
            assert "3 removed" in message

    def test_execute_bulk_remove_no_default_program(self):
        """Test _execute_bulk_remove when no default program exists."""
        from unittest.mock import patch

        from src.api.routes.programs import _execute_bulk_remove

        mock_result = {"removed": 2, "failed": 0}

        with (
            patch(
                "src.api.routes.programs.get_current_institution_id_safe"
            ) as mock_get_inst,
            patch(
                "src.api.routes.programs._get_default_program_id"
            ) as mock_get_default,
            patch(
                "src.api.routes.programs.bulk_remove_courses_from_program"
            ) as mock_bulk_remove,
            patch(
                "src.api.routes.programs.assign_course_to_default_program"
            ) as mock_assign,
        ):
            mock_get_inst.return_value = "inst1"
            mock_get_default.return_value = None  # No default program
            mock_bulk_remove.return_value = mock_result

            result, message = _execute_bulk_remove(["course1", "course2"], "prog1")

            # Should not try to assign when no default program
            mock_assign.assert_not_called()
            assert result == mock_result
            assert "2 removed" in message
