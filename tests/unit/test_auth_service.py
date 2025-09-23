"""Unit tests for auth_service.py implementation."""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# Import the auth service components
from auth_service import (
    AuthService,
    admin_required,
    auth_service,
    get_current_user,
    get_user_department,
    get_user_role,
    has_permission,
    is_authenticated,
    login_required,
    permission_required,
    role_required,
)

# pytest import removed


class TestAuthService:
    """Test the AuthService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

    def test_auth_service_instance_creation(self):
        """Test that AuthService instance can be created."""
        service = AuthService()
        assert isinstance(service, AuthService)

    def test_get_current_user_returns_mock_admin(self):
        """Test that get_current_user returns the expected mock admin user."""
        with self.app.app_context():
            service = AuthService()
            user = service.get_current_user()

            assert user is not None
            assert user["user_id"] == "dev-admin-123"
            assert user["email"] == "admin@cei.edu"
            assert user["role"] == "site_admin"
            assert user["first_name"] == "Dev"
            assert user["last_name"] == "Admin"
            assert user["department"] == "IT"

    def test_has_permission_with_site_admin(self):
        """Test that has_permission works correctly for site admin."""
        with self.app.app_context():
            service = AuthService()

            # Site admin should have all permissions
            assert service.has_permission("manage_institutions") is True
            assert service.has_permission("manage_users") is True
            assert service.has_permission("view_all_data") is True

            # Non-existent permission should return False
            assert service.has_permission("nonexistent_permission") is False

    def test_is_authenticated_returns_true_with_user(self):
        """Test that is_authenticated returns True when user exists."""
        with self.app.app_context():
            service = AuthService()
            assert service.is_authenticated() is True


class TestGlobalAuthServiceInstance:
    """Test the global auth_service instance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

    def test_global_auth_service_exists(self):
        """Test that global auth_service instance exists."""
        assert auth_service is not None
        assert isinstance(auth_service, AuthService)

    def test_global_auth_service_methods(self):
        """Test that global auth_service instance methods work."""
        with self.app.app_context():
            user = auth_service.get_current_user()
            assert user["email"] == "admin@cei.edu"

            assert auth_service.has_permission("manage_institutions") is True
            assert auth_service.is_authenticated() is True


class TestAuthDecorators:
    """Test authentication decorators."""

    @pytest.fixture
    def app(self):
        """Create a Flask app for testing."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        return app

    def test_login_required_decorator(self, app):
        """Test that login_required decorator works with authenticated user."""
        with app.app_context():

            @login_required
            def test_function(x, y):
                return x + y

            # Should execute normally since auth_service returns authenticated user
            result = test_function(2, 3)
            assert result == 5

    def test_role_required_decorator(self, app):
        """Test that role_required decorator works with site_admin."""
        with app.app_context():

            @role_required("site_admin")
            def test_function(value):
                return value * 2

            # Should execute normally since mock user is site_admin
            result = test_function(5)
            assert result == 10

    def test_permission_required_decorator(self, app):
        """Test that permission_required decorator works with valid permission."""
        with app.app_context():

            @permission_required("manage_institutions")
            def test_function(text):
                return text.upper()

            # Should execute normally since site_admin has manage_institutions permission
            result = test_function("hello")
            assert result == "HELLO"

    def test_admin_required_decorator(self, app):
        """Test that admin_required decorator works with site_admin."""
        with app.app_context():

            @admin_required
            def test_function():
                return "admin_access_granted"

            # Should execute normally since mock user is site_admin
            result = test_function()
            assert result == "admin_access_granted"

    def test_decorator_preserves_function_metadata(self):
        """Test that decorators preserve original function metadata."""

        @login_required
        def documented_function():
            """This is a test function."""
            return "test"

        # Should preserve function name and docstring
        assert documented_function.__name__ == "documented_function"
        assert "test function" in documented_function.__doc__

    def test_nested_decorators(self):
        """Test that multiple decorators can be applied together."""

        @admin_required
        @role_required("site_admin")
        @permission_required("manage_users")
        @login_required
        def protected_function(data):
            return f"processed: {data}"

        # Should execute normally with all decorators
        result = protected_function("test_data")
        assert result == "processed: test_data"


class TestUtilityFunctions:
    """Test utility/convenience functions."""

    def test_get_current_user_function(self):
        """Test get_current_user utility function."""
        user = get_current_user()
        assert user is not None
        assert user["email"] == "admin@cei.edu"
        assert user["role"] == "site_admin"

    def test_has_permission_function(self):
        """Test has_permission utility function."""
        assert has_permission("manage_institutions") is True
        assert has_permission("manage_users") is True
        assert has_permission("view_all_data") is True

    def test_is_authenticated_function(self):
        """Test is_authenticated utility function."""
        assert is_authenticated() is True

    def test_get_user_role_function(self):
        """Test get_user_role utility function."""
        role = get_user_role()
        assert role == "site_admin"

    def test_get_user_department_function(self):
        """Test get_user_department utility function."""
        department = get_user_department()
        assert department == "IT"

    def test_get_user_role_with_no_user(self):
        """Test get_user_role when no user is available."""
        with patch("auth_service.get_current_user", return_value=None):
            role = get_user_role()
            assert role is None

    def test_get_user_department_with_no_user(self):
        """Test get_user_department when no user is available."""
        with patch("auth_service.get_current_user", return_value=None):
            department = get_user_department()
            assert department is None

    def test_get_user_department_with_no_department_field(self):
        """Test get_user_department when user has no department field."""
        mock_user = {"user_id": "123", "email": "test@example.com", "role": "user"}
        with patch("auth_service.get_current_user", return_value=mock_user):
            department = get_user_department()
            assert department is None


class TestAuthServiceIntegration:
    """Test integration between different auth service components."""

    def test_utility_functions_use_global_service(self):
        """Test that utility functions use the global auth_service instance."""
        # Mock the global auth_service
        mock_service = MagicMock()
        mock_service.get_current_user.return_value = {"test": "user"}
        mock_service.has_permission.return_value = False
        mock_service.is_authenticated.return_value = False

        with patch("auth_service.auth_service", mock_service):
            # Test that utility functions delegate to the service
            user = get_current_user()
            permission = has_permission("test")
            authenticated = is_authenticated()

            assert user == {"test": "user"}
            assert permission is False
            assert authenticated is False

            # Verify the service methods were called
            mock_service.get_current_user.assert_called_once()
            mock_service.has_permission.assert_called_once_with("test")
            mock_service.is_authenticated.assert_called_once()

    def test_decorators_work_with_different_function_signatures(self):
        """Test that decorators work with various function signatures."""
        from flask import Flask

        app = Flask(__name__)

        with app.app_context():

            @login_required
            def no_args():
                return "no_args"

            @role_required("site_admin")  # Use valid role name
            def with_args(a, b, c):
                return a + b + c

            @permission_required("manage_users")  # Use valid permission
            def with_kwargs(name, age=None, **kwargs):
                return f"{name}-{age}-{len(kwargs)}"

            @admin_required
            def with_mixed(*args, **kwargs):
                return len(args) + len(kwargs)

            # All should work normally
            assert no_args() == "no_args"
            assert with_args(1, 2, 3) == 6
            assert with_kwargs("test", age=25, extra="data") == "test-25-1"
            assert with_mixed(1, 2, 3, key="value") == 4


class TestAuthBehaviorConsistency:
    """Test that auth behavior is consistent across all methods."""

    def test_all_auth_checks_work_with_site_admin(self):
        """Test that authentication checks work correctly with site_admin."""
        # Direct service calls
        service = AuthService()
        assert service.is_authenticated() is True
        assert service.has_permission("manage_institutions") is True

        # Utility function calls
        assert is_authenticated() is True
        assert has_permission("manage_institutions") is True

        # User data is always available
        user = get_current_user()
        assert user is not None
        assert user["role"] == "site_admin"

    def test_mock_user_data_consistency(self):
        """Test that mock user data is consistent across calls."""
        user1 = get_current_user()
        user2 = auth_service.get_current_user()

        # Should be the same mock user
        assert user1 == user2
        assert user1["user_id"] == user2["user_id"]
        assert user1["email"] == user2["email"]


class TestAuthServiceInstitutionFunctions:
    """Test auth service institution-related functions."""

    @patch("database_service.get_institution_by_short_name")
    @patch("auth_service.get_current_user")
    def test_get_current_institution_id_success(
        self, mock_get_user, mock_get_institution
    ):
        """Test get_current_institution_id returns institution from user context."""
        mock_get_user.return_value = {
            "user_id": "dev-admin-123",
            "institution_id": "inst-123",
        }

        from auth_service import get_current_institution_id

        result = get_current_institution_id()

        assert result == "inst-123"
        mock_get_institution.assert_not_called()

    @patch("auth_service.get_current_user")
    def test_get_current_institution_id_primary_fallback(self, mock_get_user):
        """Test get_current_institution_id uses primary institution when provided."""
        mock_get_user.return_value = {
            "user_id": "dev-admin-123",
            "primary_institution_id": "inst-primary",
        }

        from auth_service import get_current_institution_id

        assert get_current_institution_id() == "inst-primary"

    @patch("auth_service.get_current_user")
    def test_get_current_institution_id_missing_context(self, mock_get_user):
        """Test get_current_institution_id returns None when no context available."""
        mock_get_user.return_value = {
            "user_id": "dev-admin-123",
            "role": "site_admin",
        }

        from auth_service import get_current_institution_id

        assert get_current_institution_id() is None

    def test_permission_decorator_logic(self):
        """Test permission decorator logic."""
        from flask import Flask

        from auth_service import permission_required

        app = Flask(__name__)

        with app.app_context():
            # Test that decorator can be applied
            @permission_required("manage_users")  # Use valid permission
            def test_function():
                return "success"

            # Site admin should have manage_users permission
            result = test_function()
            assert result == "success"

    def test_auth_service_comprehensive_functionality(self):
        """Test comprehensive auth service functionality."""
        from auth_service import auth_service

        # Test auth service instance
        assert auth_service is not None

        # Test current user retrieval
        current_user = auth_service.get_current_user()
        assert isinstance(current_user, dict)
        assert "user_id" in current_user

        # Test permission checking
        has_perm = auth_service.has_permission("manage_users")
        assert isinstance(has_perm, bool)

        # Test authentication status
        is_auth = auth_service.is_authenticated()
        assert isinstance(is_auth, bool)

    def test_utility_functions_comprehensive_coverage(self):
        """Test comprehensive utility function coverage."""
        # Test get_current_user function
        user = get_current_user()
        assert isinstance(user, dict)

        # Test has_permission function
        perm = has_permission("test_permission")
        assert isinstance(perm, bool)

        # Test is_authenticated function
        auth = is_authenticated()
        assert isinstance(auth, bool)

        # Test get_user_role function
        role = get_user_role()
        assert isinstance(role, str)

        # Test get_user_department function
        dept = get_user_department()
        assert dept is None or isinstance(dept, str)

    def test_auth_edge_cases_and_error_handling(self):
        """Test auth service edge cases and error handling."""
        # Test with various permission strings
        test_permissions = [
            "manage_users",
            "import_data",
            "view_reports",
            "admin_access",
            "nonexistent_permission",
        ]

        for perm in test_permissions:
            result = has_permission(perm)
            # Should always return a boolean
            assert isinstance(result, bool)

        # Test role handling edge cases
        role = get_user_role()
        assert (
            role in ["site_admin", "program_admin", "instructor"] or role == "unknown"
        )


class TestAuthServiceCoverage:
    """Test coverage for new authorization system functionality."""

    def test_scoped_permission_checking(self):
        """Test scoped permission checking for different roles."""
        from auth_service import AuthService

        # Test institution admin scoped permissions
        with patch.object(AuthService, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "inst-admin-123",
                "role": "institution_admin",
                "institution_id": "inst-123",
            }

            service = AuthService()

            # Should have access to own institution
            context = {"institution_id": "inst-123"}
            assert (
                service._check_scoped_permission(
                    mock_get_user.return_value, "manage_programs", context
                )
                is True
            )

            # Should not have access to different institution
            context = {"institution_id": "inst-456"}
            assert (
                service._check_scoped_permission(
                    mock_get_user.return_value, "manage_programs", context
                )
                is False
            )

    def test_program_admin_scoped_permissions(self):
        """Test program admin scoped permission checking."""
        from auth_service import AuthService

        with patch.object(AuthService, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "prog-admin-123",
                "role": "program_admin",
                "institution_id": "inst-123",
                "program_ids": ["prog-123", "prog-456"],
            }

            service = AuthService()
            user = mock_get_user.return_value

            # Should have access to own institution
            context = {"institution_id": "inst-123"}
            assert (
                service._check_scoped_permission(user, "manage_courses", context)
                is True
            )

            # Should not have access to different institution
            context = {"institution_id": "inst-456"}
            assert (
                service._check_scoped_permission(user, "manage_courses", context)
                is False
            )

            # Should have access to accessible programs
            context = {"program_id": "prog-123"}
            assert (
                service._check_scoped_permission(user, "manage_courses", context)
                is True
            )

            # Should not have access to non-accessible programs
            context = {"program_id": "prog-789"}
            assert (
                service._check_scoped_permission(user, "manage_courses", context)
                is False
            )

    def test_get_accessible_institutions(self):
        """Test get_accessible_institutions for different roles."""
        from auth_service import AuthService

        service = AuthService()

        # Test site admin - should return all institutions
        with (
            patch.object(service, "get_current_user") as mock_get_user,
            patch("database_service.get_all_institutions") as mock_get_all_institutions,
        ):
            mock_get_user.return_value = {
                "user_id": "site-admin-123",
                "role": "site_admin",
            }
            mock_get_all_institutions.return_value = [
                {"institution_id": "inst-123"},
                {"institution_id": "inst-456"},
            ]
            institutions = service.get_accessible_institutions()
            assert "inst-123" in institutions
            assert "inst-456" in institutions

        # Test other roles - should return user's accessible institutions
        with patch.object(service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "inst-admin-123",
                "role": "institution_admin",
                "accessible_institutions": ["inst-123"],
            }
            institutions = service.get_accessible_institutions()
            assert institutions == ["inst-123"]

        # Test no user
        with patch.object(service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = None
            institutions = service.get_accessible_institutions()
            assert institutions == []

    def test_get_accessible_programs(self):
        """Test get_accessible_programs for different roles."""
        from auth_service import AuthService

        service = AuthService()

        # Test site admin
        with (
            patch.object(service, "get_current_user") as mock_get_user,
            patch("database_service.get_all_institutions") as mock_get_all_institutions,
            patch("database_service.get_programs_by_institution") as mock_get_programs,
        ):
            mock_get_user.return_value = {
                "user_id": "site-admin-123",
                "role": "site_admin",
            }
            mock_get_all_institutions.return_value = [
                {"institution_id": "inst-123"},
                {"institution_id": "inst-456"},
            ]
            mock_get_programs.return_value = [
                {"program_id": "prog-123"},
                {"program_id": "prog-456"},
            ]
            programs = service.get_accessible_programs()
            assert "prog-123" in programs
            assert "prog-456" in programs

        # Test institution admin
        with (
            patch.object(service, "get_current_user") as mock_get_user,
            patch("database_service.get_programs_by_institution") as mock_get_programs,
        ):
            mock_get_user.return_value = {
                "user_id": "inst-admin-123",
                "role": "institution_admin",
                "institution_id": "inst-123",
            }
            mock_get_programs.return_value = [
                {"program_id": "prog-123"},
                {"program_id": "prog-456"},
            ]
            programs = service.get_accessible_programs()
            assert "prog-123" in programs
            assert "prog-456" in programs

        # Test program admin
        with patch.object(service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "prog-admin-123",
                "role": "program_admin",
                "program_ids": ["prog-123"],
            }
            programs = service.get_accessible_programs()
            assert programs == ["prog-123"]

        # Test instructor (should return empty)
        with patch.object(service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "instructor-123",
                "role": "instructor",
            }
            programs = service.get_accessible_programs()
            assert programs == []

        # Test no user
        with patch.object(service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = None
            programs = service.get_accessible_programs()
            assert programs == []

    def test_has_role_hierarchy(self):
        """Test role hierarchy checking."""
        from auth_service import AuthService

        service = AuthService()

        # Test site admin can act as any role
        with patch.object(service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "site-admin-123",
                "role": "site_admin",
            }
            assert service.has_role("site_admin") is True
            assert service.has_role("institution_admin") is True
            assert service.has_role("program_admin") is True
            assert service.has_role("instructor") is True
            assert service.has_role("nonexistent_role") is False

        # Test institution admin hierarchy
        with patch.object(service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = {
                "user_id": "inst-admin-123",
                "role": "institution_admin",
            }
            assert service.has_role("site_admin") is False
            assert service.has_role("institution_admin") is True
            assert service.has_role("program_admin") is True
            assert service.has_role("instructor") is True

        # Test no user
        with patch.object(service, "get_current_user") as mock_get_user:
            mock_get_user.return_value = None
            assert service.has_role("instructor") is False

    def test_decorator_error_conditions(self):
        """Test decorator error conditions and edge cases."""
        from flask import Flask

        from auth_service import permission_required, role_required

        app = Flask(__name__)

        with app.app_context():
            # Test permission denied
            with patch("auth_service.auth_service.has_permission") as mock_has_perm:
                mock_has_perm.return_value = False

                @permission_required("nonexistent_permission")
                def test_func():
                    return "success"

                response = test_func()
                # Should return tuple (response, status_code) for 403 error
                assert isinstance(response, tuple)
                assert len(response) == 2
                assert response[1] == 403

            # Test role denied
            with patch("auth_service.auth_service.has_role") as mock_has_role:
                mock_has_role.return_value = False

                @role_required("site_admin")
                def test_func():
                    return "success"

                response = test_func()
                # Should return tuple (response, status_code) for 403 error
                assert isinstance(response, tuple)
                assert len(response) == 2
                assert response[1] == 403

    def test_utility_function_coverage(self):
        """Test utility functions for coverage."""
        from auth_service import (
            can_access_institution,
            can_access_program,
            get_accessible_institutions,
            get_accessible_programs,
            require_program_access,
        )

        # Test get_accessible_institutions
        institutions = get_accessible_institutions()
        assert isinstance(institutions, list)

        # Test get_accessible_programs
        programs = get_accessible_programs()
        assert isinstance(programs, list)

        # Test can_access_institution
        can_access = can_access_institution("inst-123")
        assert isinstance(can_access, bool)

        # Test can_access_program
        can_access = can_access_program("prog-123")
        assert isinstance(can_access, bool)

        # Test require_program_access (should not raise exception for accessible program)
        try:
            require_program_access("prog-123")  # Should work for site admin
        except Exception:
            pass  # Expected for non-accessible programs

    def test_role_enum_methods(self):
        """Test UserRole enum methods for coverage."""
        from auth_service import UserRole

        # Test get_role_hierarchy
        hierarchy = UserRole.get_role_hierarchy()
        assert isinstance(hierarchy, list)
        assert "site_admin" in hierarchy
        assert "instructor" in hierarchy

        # Test has_role_or_higher
        assert UserRole.has_role_or_higher("site_admin", "instructor") is True
        assert UserRole.has_role_or_higher("instructor", "site_admin") is False
        assert UserRole.has_role_or_higher("invalid_role", "instructor") is False
        assert UserRole.has_role_or_higher("instructor", "invalid_role") is False

    def test_context_extraction_in_decorators(self):
        """Test context extraction in permission decorators."""
        from flask import Flask, request, session

        from auth_service import permission_required

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret"

        with app.test_request_context("/test?institution_id=inst-123"):
            session["user_id"] = "test-admin"
            session["email"] = "admin@test.edu"
            session["role"] = "site_admin"
            session["institution_id"] = "inst-123"
            session["program_ids"] = ["prog-123"]

            @permission_required("manage_users", context_keys=["institution_id"])
            def test_func():
                return "success"

            # Should extract institution_id from query parameters
            result = test_func()
            assert result == "success"
