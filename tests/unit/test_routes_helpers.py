"""Unit tests for helpers API routes (migrated from test_api_routes.py)."""

from unittest.mock import patch

import pytest

from src.api.utils import (
    InstitutionContextMissingError,
    handle_api_error,
    resolve_institution_scope,
)
from src.app import app


class TestAPIRoutesExtended:
    """Test missing coverage lines in API routes."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def test_api_error_handler_comprehensive(self):
        """Test API error handler function directly."""
        from src.api.utils import handle_api_error
        from src.app import app

        # Test error handler with app context
        with app.app_context():
            test_exception = Exception("Test error message")

            result = handle_api_error(test_exception, "Test operation", "User message")

            # Should return tuple with JSON response and status code
            assert isinstance(result, tuple)
            assert len(result) == 2

            _, status_code = result
            assert status_code == 500

            # Test with default parameters
            result2 = handle_api_error(test_exception)
            assert isinstance(result2, tuple)
            assert result2[1] == 500

    @patch("src.api.routes.courses.get_all_courses")
    @patch("src.api.utils.get_all_institutions")
    @patch("src.api.utils.get_current_institution_id_safe")
    def test_list_courses_global_scope(
        self, mock_get_mocku_id, mock_get_institutions, mock_get_all_courses
    ):
        """Site admin without institution context should see system-wide courses."""
        self._login_site_admin()
        mock_get_mocku_id.return_value = None
        mock_get_institutions.return_value = [
            {"institution_id": "inst-1"},
            {"institution_id": "inst-2"},
        ]
        mock_get_all_courses.side_effect = [
            [{"course_id": "c1", "department": "ENG"}],
            [{"course_id": "c2", "department": "SCI"}],
        ]

        response = self.client.get("/api/courses")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2
        returned_ids = {course["course_id"] for course in data["courses"]}
        assert returned_ids == {"c1", "c2"}

    @patch("src.api.utils.get_current_institution_id_safe")
    @patch("src.api.routes.courses.get_courses_by_department")
    def test_list_courses_with_department(self, mock_get_courses, mock_get_inst_id):
        """Test list_courses with department filter."""
        self._login_site_admin()
        mock_get_inst_id.return_value = "institution123"
        mock_get_courses.return_value = [{"course_id": "1", "department": "MATH"}]

        response = self.client.get("/api/courses?department=MATH")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["courses"]) == 1

    @patch("src.api.routes.courses.resolve_institution_scope")
    @patch("src.api.routes.courses.get_current_program_id")
    @patch("src.api.routes.courses.get_courses_by_program")
    def test_list_courses_with_program_override(
        self, mock_get_by_program, mock_get_program_id, mock_scope
    ):
        """Test list_courses with program_id override parameter."""
        self._login_site_admin()
        mock_scope.return_value = (
            {"user_id": "admin1", "role": "site_admin", "institution_id": "inst1"},
            ["inst1"],
            False,
        )
        mock_get_program_id.return_value = None
        mock_get_by_program.return_value = [
            {"course_id": "c1", "program_ids": ["prog1"]}
        ]

        response = self.client.get("/api/courses?program_id=prog1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["courses"]) == 1
        assert data["current_program_id"] == "prog1"
        mock_get_by_program.assert_called_once_with("prog1")


class TestAPIRoutesHelpers:
    """Test helper functions in API routes."""

    def test_resolve_institution_scope_missing_context(self):
        """Test _resolve_institution_scope raises error when context missing and required."""
        from src.api.utils import (
            InstitutionContextMissingError,
            resolve_institution_scope,
        )

        with patch(
            "src.api.utils.get_current_user", return_value={"role": "instructor"}
        ):
            with patch("src.api.utils.get_current_institution_id", return_value=None):
                with pytest.raises(InstitutionContextMissingError):
                    resolve_institution_scope(require=True)

    def test_resolve_institution_scope_no_require(self):
        """Test _resolve_institution_scope returns empty list when not required."""
        from src.api.utils import resolve_institution_scope

        with patch(
            "src.api.utils.get_current_user", return_value={"role": "instructor"}
        ):
            with patch("src.api.utils.get_current_institution_id", return_value=None):
                user, institutions, is_global = resolve_institution_scope(require=False)
                assert user == {"role": "instructor"}
                assert institutions == []
                assert is_global is False

    def test_create_progress_tracker(self):
        """Test create_progress_tracker function."""
        from src.api.routes.imports import create_progress_tracker

        progress_id = create_progress_tracker()
        assert isinstance(progress_id, str)
        assert len(progress_id) > 0

    def test_update_progress(self):
        """Test update_progress function."""
        from src.api.routes.imports import create_progress_tracker, update_progress

        progress_id = create_progress_tracker()
        update_progress(progress_id, status="processing", message="Test update")
        # Should not raise an exception

    def test_get_progress(self):
        """Test get_progress function."""
        from src.api.routes.imports import (
            create_progress_tracker,
            get_progress,
            update_progress,
        )

        progress_id = create_progress_tracker()
        update_progress(progress_id, status="processing", message="Test message")

        progress = get_progress(progress_id)
        assert isinstance(progress, dict)
        assert progress.get("status") == "processing"
        assert progress.get("message") == "Test message"

    def test_cleanup_progress(self):
        """Test cleanup_progress function."""
        from src.api.routes.imports import cleanup_progress, create_progress_tracker

        progress_id = create_progress_tracker()
        cleanup_progress(progress_id)
        # Should not raise an exception


class TestAPIRoutesHelperFunctions:
    """Test helper functions for course listing complexity reduction."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_resolve_courses_scope_success(self):
        """Test _resolve_courses_scope with valid scope."""
        from unittest.mock import patch

        from src.api.routes.courses import _resolve_courses_scope

        mock_user = {"role": "site_admin"}
        mock_institutions = ["inst1"]
        mock_global = False

        with patch("src.api.routes.courses.resolve_institution_scope") as mock_resolve:
            mock_resolve.return_value = (mock_user, mock_institutions, mock_global)

            user, institutions, is_global = _resolve_courses_scope()

            assert user == mock_user
            assert institutions == mock_institutions
            assert is_global == mock_global

    def test_resolve_courses_scope_missing_context(self):
        """Test _resolve_courses_scope with missing institution context."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.courses import _resolve_courses_scope
        from src.api.utils import InstitutionContextMissingError

        with patch("src.api.routes.courses.resolve_institution_scope") as mock_resolve:
            mock_resolve.side_effect = InstitutionContextMissingError("Missing context")

            with pytest.raises(ValueError, match="Institution context required"):
                _resolve_courses_scope()

    def test_user_can_access_program_site_admin(self):
        """Test _user_can_access_program for site admin."""
        from src.api.routes.courses import _user_can_access_program

        user = {"role": "site_admin"}
        program_id = "test-program"

        result = _user_can_access_program(user, program_id)
        assert result is True

    def test_user_can_access_program_with_access(self):
        """Test _user_can_access_program for user with program access."""
        from src.api.routes.courses import _user_can_access_program

        user = {"role": "program_admin", "program_ids": ["prog1", "prog2"]}
        program_id = "prog1"

        result = _user_can_access_program(user, program_id)
        assert result is True

    def test_user_can_access_program_without_access(self):
        """Test _user_can_access_program for user without program access."""
        from src.api.routes.courses import _user_can_access_program

        user = {"role": "program_admin", "program_ids": ["prog1", "prog2"]}
        program_id = "prog3"

        result = _user_can_access_program(user, program_id)
        assert result is False

    def test_user_can_access_program_no_user(self):
        """Test _user_can_access_program with no user."""
        from src.api.routes.courses import _user_can_access_program

        result = _user_can_access_program(None, "test-program")
        assert result is False

    def test_resolve_program_override_no_override(self):
        """Test _resolve_program_override with no override."""
        from unittest.mock import patch

        from src.api.routes.courses import _resolve_program_override

        with self.app.test_request_context("/?"):
            with patch(
                "src.api.routes.courses.get_current_program_id"
            ) as mock_get_program:
                mock_get_program.return_value = "current-program"

                result = _resolve_program_override({"role": "user"})
                assert result == "current-program"

    def test_resolve_program_override_with_access(self):
        """Test _resolve_program_override with valid override."""
        from unittest.mock import patch

        from src.api.routes.courses import _resolve_program_override

        user = {"role": "site_admin"}

        with self.app.test_request_context("/?program_id=override-program"):
            with patch(
                "src.api.routes.courses.get_current_program_id"
            ) as mock_get_program:
                mock_get_program.return_value = "current-program"

                result = _resolve_program_override(user)
                assert result == "override-program"

    def test_resolve_program_override_without_access(self):
        """Test _resolve_program_override with invalid override."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.courses import _resolve_program_override

        user = {"role": "program_admin", "program_ids": ["other-program"]}

        with self.app.test_request_context("/?program_id=override-program"):
            with patch(
                "src.api.routes.courses.get_current_program_id"
            ) as mock_get_program:
                mock_get_program.return_value = "current-program"

                with pytest.raises(
                    PermissionError, match="Access denied to specified program"
                ):
                    _resolve_program_override(user)

    def test_get_global_courses_no_filter(self):
        """Test _get_global_courses without department filter."""
        from unittest.mock import patch

        from src.api.routes.courses import _get_global_courses

        institution_ids = ["inst1", "inst2"]
        mock_courses_1 = [{"id": "c1", "department": "CS"}]
        mock_courses_2 = [{"id": "c2", "department": "MATH"}]

        with patch("src.api.routes.courses.get_all_courses") as mock_get_courses:
            mock_get_courses.side_effect = [mock_courses_1, mock_courses_2]

            courses, context = _get_global_courses(institution_ids, None)

            assert len(courses) == 2
            assert context == "system-wide"

    def test_get_global_courses_with_filter(self):
        """Test _get_global_courses with department filter."""
        from unittest.mock import patch

        from src.api.routes.courses import _get_global_courses

        institution_ids = ["inst1", "inst2"]
        mock_courses_1 = [{"id": "c1", "department": "CS"}]
        mock_courses_2 = [{"id": "c2", "department": "MATH"}]

        with patch("src.api.routes.courses.get_all_courses") as mock_get_courses:
            mock_get_courses.side_effect = [mock_courses_1, mock_courses_2]

            courses, context = _get_global_courses(institution_ids, "CS")

            assert len(courses) == 1
            assert courses[0]["id"] == "c1"
            assert context == "system-wide, department CS"

    def test_get_program_courses_no_filter(self):
        """Test _get_program_courses without department filter."""
        from unittest.mock import patch

        from src.api.routes.courses import _get_program_courses

        program_id = "test-program"
        mock_courses = [
            {"id": "c1", "department": "CS"},
            {"id": "c2", "department": "MATH"},
        ]

        with patch("src.api.routes.courses.get_courses_by_program") as mock_get_courses:
            mock_get_courses.return_value = mock_courses

            courses, context = _get_program_courses(program_id, None)

            assert len(courses) == 2
            assert context == f"program {program_id}"

    def test_get_program_courses_with_filter(self):
        """Test _get_program_courses with department filter."""
        from unittest.mock import patch

        from src.api.routes.courses import _get_program_courses

        program_id = "test-program"
        mock_courses = [
            {"id": "c1", "department": "CS"},
            {"id": "c2", "department": "MATH"},
        ]

        with patch("src.api.routes.courses.get_courses_by_program") as mock_get_courses:
            mock_get_courses.return_value = mock_courses

            courses, context = _get_program_courses(program_id, "CS")

            assert len(courses) == 1
            assert courses[0]["id"] == "c1"

    def test_resolve_users_scope_success(self):
        """Test _resolve_users_scope with valid scope."""
        from unittest.mock import patch

        from src.api.routes.users import _resolve_users_scope

        mock_user = {"role": "site_admin"}
        mock_institutions = ["inst1"]
        mock_global = False

        with patch("src.api.routes.users.resolve_institution_scope") as mock_resolve:
            mock_resolve.return_value = (mock_user, mock_institutions, mock_global)

            user, institutions, is_global = _resolve_users_scope()

            assert user == mock_user
            assert institutions == mock_institutions
            assert is_global == mock_global

    def test_resolve_users_scope_missing_context(self):
        """Test _resolve_users_scope with missing institution context."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.users import _resolve_users_scope
        from src.api.utils import InstitutionContextMissingError

        with patch("src.api.routes.users.resolve_institution_scope") as mock_resolve:
            mock_resolve.side_effect = InstitutionContextMissingError("Missing context")

            with pytest.raises(ValueError, match="Institution context required"):
                _resolve_users_scope()

    def test_get_users_by_scope_global(self):
        """Test _get_users_by_scope for global scope."""
        from unittest.mock import patch

        from src.api.routes.users import _get_users_by_scope

        institution_ids = ["inst1", "inst2"]
        role_filter = "admin"

        with patch("src.api.routes.users._get_global_users") as mock_global:
            mock_global.return_value = [{"id": "user1"}]

            result = _get_users_by_scope(True, institution_ids, role_filter)

            mock_global.assert_called_once_with(institution_ids, role_filter)
            assert result == [{"id": "user1"}]

    def test_get_users_by_scope_institution(self):
        """Test _get_users_by_scope for institution scope."""
        from unittest.mock import patch

        from src.api.routes.users import _get_users_by_scope

        institution_ids = ["inst1"]
        role_filter = "admin"

        with patch("src.api.routes.users._get_institution_users") as mock_institution:
            mock_institution.return_value = [{"id": "user1"}]

            result = _get_users_by_scope(False, institution_ids, role_filter)

            mock_institution.assert_called_once_with("inst1", role_filter)
            assert result == [{"id": "user1"}]

    def test_get_global_users_with_role_filter(self):
        """Test _get_global_users with role filter."""
        from unittest.mock import patch

        from src.api.routes.users import _get_global_users

        institution_ids = ["inst1", "inst2"]
        role_filter = "admin"
        mock_users = [
            {"id": "user1", "institution_id": "inst1"},
            {"id": "user2", "institution_id": "inst3"},  # Should be filtered out
            {"id": "user3", "institution_id": "inst2"},
        ]

        with patch("src.api.routes.users.get_users_by_role") as mock_get_users:
            mock_get_users.return_value = mock_users

            result = _get_global_users(institution_ids, role_filter)

            mock_get_users.assert_called_once_with(role_filter)
            assert len(result) == 2
            assert result[0]["id"] == "user1"
            assert result[1]["id"] == "user3"

    def test_get_global_users_without_role_filter(self):
        """Test _get_global_users without role filter."""
        from unittest.mock import patch

        from src.api.routes.users import _get_global_users

        institution_ids = ["inst1", "inst2"]
        mock_users_1 = [{"id": "user1"}]
        mock_users_2 = [{"id": "user2"}]

        with patch("src.api.routes.users.get_all_users") as mock_get_users:
            mock_get_users.side_effect = [mock_users_1, mock_users_2]

            result = _get_global_users(institution_ids, None)

            assert mock_get_users.call_count == 2
            assert len(result) == 2
            assert result[0]["id"] == "user1"
            assert result[1]["id"] == "user2"

    def test_get_institution_users_with_role_filter(self):
        """Test _get_institution_users with role filter."""
        from unittest.mock import patch

        from src.api.routes.users import _get_institution_users

        institution_id = "inst1"
        role_filter = "admin"
        mock_users = [
            {"id": "user1", "institution_id": "inst1"},
            {"id": "user2", "institution_id": "inst2"},  # Should be filtered out
        ]

        with patch("src.api.routes.users.get_users_by_role") as mock_get_users:
            mock_get_users.return_value = mock_users

            result = _get_institution_users(institution_id, role_filter)

            mock_get_users.assert_called_once_with(role_filter)
            assert len(result) == 1
            assert result[0]["id"] == "user1"

    def test_get_institution_users_without_role_filter(self):
        """Test _get_institution_users without role filter."""
        from unittest.mock import patch

        from src.api.routes.users import _get_institution_users

        institution_id = "inst1"
        mock_users = [{"id": "user1"}, {"id": "user2"}]

        with patch("src.api.routes.users.get_all_users") as mock_get_users:
            mock_get_users.return_value = mock_users

            result = _get_institution_users(institution_id, None)

            mock_get_users.assert_called_once_with(institution_id)
            assert result == mock_users
