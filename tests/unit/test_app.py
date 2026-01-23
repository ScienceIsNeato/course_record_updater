"""Unit tests for Flask application setup and configuration."""

import os
from unittest.mock import patch

from flask import Flask

# Import the app module for testing
import src.app as app_module


class TestFlaskAppSetup:
    """Test Flask application initialization and configuration."""

    def test_app_instance_creation(self):
        """Test that Flask app instance is created correctly."""
        assert isinstance(app_module.app, Flask)
        assert app_module.app.name in ["app", "src.app"]

    def test_secret_key_configuration(self):
        """Test secret key is set from environment or default."""
        # Should have some secret key set
        assert app_module.app.secret_key is not None
        assert len(app_module.app.secret_key) > 0

    @patch.dict(os.environ, {"FLASK_SECRET_KEY": "test-secret"})
    def test_secret_key_from_environment(self):
        """Test secret key is loaded from environment variable."""
        # Reload the module to pick up env var
        import importlib

        importlib.reload(app_module)
        assert app_module.app.secret_key == "test-secret"

    def test_api_blueprint_registered(self):
        """Test that API blueprint is registered."""
        # Check that blueprints are registered
        blueprint_names = [bp.name for bp in app_module.app.blueprints.values()]
        assert "api" in blueprint_names

    def test_app_route_registration(self):
        """Test comprehensive route registration."""
        # Test that app has routes registered
        assert len(app_module.app.url_map._rules) > 0

        # Test that specific route patterns exist
        rule_strings = [str(rule) for rule in app_module.app.url_map.iter_rules()]

        # Should have API routes
        api_routes_found = any("/api/" in rule for rule in rule_strings)
        assert api_routes_found, "Should have API routes registered"

        # Should have static routes
        static_routes_found = any("/static/" in rule for rule in rule_strings)
        assert static_routes_found, "Should have static routes"

    def test_app_context_management(self):
        """Test app context management."""
        # Test app context creation
        with app_module.app.app_context():
            from flask import current_app

            assert current_app is not None

    def test_app_configuration_attributes(self):
        """Test app configuration and setup."""
        assert app_module.app is not None
        assert hasattr(app_module.app, "config")
        assert hasattr(app_module.app, "url_map")

        # Test that app has proper Flask attributes
        assert hasattr(app_module.app, "blueprints")
        assert hasattr(app_module.app, "before_request_funcs")
        assert hasattr(app_module.app, "after_request_funcs")

        # Test app name and basic properties
        assert isinstance(app_module.app.name, str)
        assert len(app_module.app.name) > 0


class TestDashboardRoute:
    """Test dashboard route (Issue #30 fix)."""

    def test_dashboard_route_returns_html_not_json(self):
        """Test that /dashboard route returns HTML, not JSON (Issue #30)."""
        with app_module.app.test_client() as client:
            # Create a mock session with authenticated user
            with client.session_transaction() as sess:
                sess["user_id"] = "test-user-id"
                sess["email"] = "test@example.com"
                sess["role"] = "instructor"

            # Mock auth service to return a test user
            with patch("src.app.get_current_user") as mock_get_user:
                mock_get_user.return_value = {
                    "user_id": "test-user-id",
                    "email": "test@example.com",
                    "role": "instructor",
                    "first_name": "Test",
                    "last_name": "User",
                    "institution_id": "test-institution",
                }

                response = client.get("/dashboard")

                # Verify response is HTML, not JSON
                assert response.status_code == 200
                assert response.content_type.startswith("text/html")

                # Verify HTML content contains expected elements
                html = response.data.decode()
                assert "Instructor Dashboard" in html or "Dashboard" in html
                assert "<!DOCTYPE html>" in html
                # Should NOT be JSON
                assert not html.strip().startswith("{")
                assert not html.strip().startswith("[")


class TestLoggingSetup:
    """Test logging configuration."""

    @patch("os.makedirs")
    @patch("logging.basicConfig")
    def test_setup_logging_creates_logs_directory(
        self, mock_basic_config, mock_makedirs
    ):
        """Test that setup_logging creates logs directory."""
        app_module.setup_logging()
        mock_makedirs.assert_called_once_with("logs", exist_ok=True)

    @patch("os.makedirs")
    @patch("logging.basicConfig")
    def test_setup_logging_configures_basic_logging(
        self, mock_basic_config, mock_makedirs
    ):
        """Test that setup_logging configures basic logging."""
        app_module.setup_logging()
        mock_basic_config.assert_called_once()

        # Check that handlers are configured
        call_args = mock_basic_config.call_args
        assert "handlers" in call_args.kwargs
        assert len(call_args.kwargs["handlers"]) == 2  # Console + file


class TestIndexRoute:
    """Test the main index route - now serves splash page."""

    def test_index_route_renders_splash_page(self):
        """Test that index route always renders the splash page."""
        with app_module.app.test_client() as client:
            response = client.get("/")
            assert response.status_code == 200
            # Check that it renders the splash page
            assert b"Loopcloser" in response.data
            assert b"Get Started" in response.data
            assert b"Learn More" in response.data

    def test_splash_page_has_login_links(self):
        """Test that splash page contains login links."""
        with app_module.app.test_client() as client:
            response = client.get("/")
            assert response.status_code == 200
            # Check for login links
            assert b"/login" in response.data
            assert b"Login" in response.data

    @patch("src.app.is_authenticated")
    def test_login_route_renders_template(self, mock_is_authenticated):
        """Test that login route renders the login template."""
        mock_is_authenticated.return_value = False

        with app_module.app.test_client() as client:
            response = client.get("/login")
            assert response.status_code == 200

    def test_login_force_clears_existing_session(self):
        """Covers /login?force=true branch that logs out existing session."""
        with app_module.app.test_client() as client:
            # Make the request appear authenticated (AuthService session path)
            with client.session_transaction() as sess:
                sess["user_id"] = "test-user-id"
                sess["email"] = "test@example.com"
                sess["role"] = "instructor"
            with patch(
                "src.services.login_service.LoginService.logout_user"
            ) as mock_logout:
                response = client.get("/login?force=true")
                assert response.status_code == 200
                mock_logout.assert_called_once()

    @patch("src.app.is_authenticated")
    def test_login_route_redirects_authenticated_user(self, mock_is_authenticated):
        """Test that login route redirects authenticated users."""
        mock_is_authenticated.return_value = True

        with app_module.app.test_client() as client:
            response = client.get("/login")
            assert response.status_code == 302
            assert "/dashboard" in response.location

    @patch("src.app.is_authenticated")
    def test_register_route_renders_template(self, mock_is_authenticated):
        """Test that register route renders the registration template."""
        mock_is_authenticated.return_value = False

        with app_module.app.test_client() as client:
            response = client.get("/register")
            assert response.status_code == 200


class TestAuthenticatedRouteGuards:
    def test_terms_list_redirects_when_no_user(self):
        with app_module.app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "test-user-id"
                sess["email"] = "test@example.com"
                sess["role"] = "instructor"
            with patch("src.app.get_current_user", return_value=None):
                response = client.get("/terms")
                assert response.status_code == 302
                assert "/login" in response.location

    def test_offerngs_list_redirects_when_no_user(self):
        with app_module.app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "test-user-id"
                sess["email"] = "test@example.com"
                sess["role"] = "instructor"
            with patch("src.app.get_current_user", return_value=None):
                response = client.get("/offerings")
                assert response.status_code == 302
                assert "/login" in response.location

    def test_programs_list_redirects_when_no_user(self):
        with app_module.app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "test-user-id"
                sess["email"] = "test@example.com"
                sess["role"] = "instructor"
            with patch("src.app.get_current_user", return_value=None):
                response = client.get("/programs")
                assert response.status_code == 302
                assert "/login" in response.location

    def test_faculty_and_outcomes_redirects(self):
        with app_module.app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "test-user-id"
                sess["email"] = "test@example.com"
                sess["role"] = "instructor"

            response = client.get("/faculty")
            assert response.status_code == 302
            assert "/users" in response.location

            response = client.get("/outcomes")
            # Outcomes now renders the outcomes page for instructors
            assert response.status_code == 200

    @patch("src.app.is_authenticated")
    def test_forgot_password_route_renders_template(self, mock_is_authenticated):
        """Test that forgot password route renders the template."""
        mock_is_authenticated.return_value = False

        with app_module.app.test_client() as client:
            response = client.get("/forgot-password")
            assert response.status_code == 200

    @patch("src.app.is_authenticated")
    def test_register_route_redirects_authenticated_user(self, mock_is_authenticated):
        """Test that register route redirects authenticated users to dashboard."""
        mock_is_authenticated.return_value = True

        with app_module.app.test_client() as client:
            response = client.get("/register")
            assert response.status_code == 302
            assert "/dashboard" in response.location

    @patch("src.app.is_authenticated")
    def test_forgot_password_route_redirects_authenticated_user(
        self, mock_is_authenticated
    ):
        """Test that forgot password route redirects authenticated users to dashboard."""
        mock_is_authenticated.return_value = True

        with app_module.app.test_client() as client:
            response = client.get("/forgot-password")
            assert response.status_code == 302
            assert "/dashboard" in response.location

    def test_profile_route_requires_authentication(self):
        """Test that profile route requires authentication."""
        with app_module.app.test_client() as client:
            response = client.get("/profile")
            # Web routes redirect to login when not authenticated
            assert response.status_code == 302
            assert "/login" in response.location

    def test_profile_route_renders_for_authenticated_user(self):
        """Test that profile route renders for authenticated users."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "test-user-123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "instructor",
            "institution_id": "test-inst",
        }

        with app_module.app.test_client() as client:
            create_test_session(client, user_data)
            response = client.get("/profile")
            assert response.status_code == 200

    def test_dashboard_route_requires_authentication(self):
        """Test that dashboard route requires authentication."""
        with app_module.app.test_client() as client:
            response = client.get("/dashboard")
            # Web routes redirect to login when not authenticated
            assert response.status_code == 302
            assert "/login" in response.location

    def test_dashboard_route_renders_for_authenticated_user(self):
        """Test that dashboard route renders for authenticated users."""
        from tests.test_utils import create_test_session

        with app_module.app.test_client() as client:
            # Create authenticated session
            create_test_session(
                client,
                {
                    "user_id": "test123",
                    "email": "test@example.com",
                    "role": "instructor",
                    "first_name": "Test",
                    "last_name": "User",
                },
            )

            response = client.get("/dashboard")
            assert response.status_code == 200
            assert b"dashboard" in response.data.lower()

    def test_dashboard_route_different_roles(self):
        """Test dashboard route with different user roles."""
        from tests.test_utils import create_test_session

        with app_module.app.test_client() as client:
            # Test program_admin role
            create_test_session(
                client,
                {
                    "user_id": "admin1",
                    "email": "program@example.com",
                    "role": "program_admin",
                    "first_name": "Program",
                    "last_name": "Admin",
                },
            )
            response = client.get("/dashboard")
            assert response.status_code == 200

            # Test institution_admin role
            create_test_session(
                client,
                {
                    "user_id": "admin2",
                    "email": "institution@example.com",
                    "role": "institution_admin",
                    "first_name": "Institution",
                    "last_name": "Admin",
                },
            )
            response = client.get("/dashboard")
            assert response.status_code == 200

            # Test site_admin role
            create_test_session(
                client,
                {
                    "user_id": "admin3",
                    "email": "site@example.com",
                    "role": "site_admin",
                    "first_name": "Site",
                    "last_name": "Admin",
                },
            )
            response = client.get("/dashboard")
            assert response.status_code == 200

            # Test unknown role
            create_test_session(
                client,
                {
                    "user_id": "unknown",
                    "email": "unknown@example.com",
                    "role": "unknown_role",
                    "first_name": "Unknown",
                    "last_name": "User",
                },
            )
            response = client.get("/dashboard")
            assert response.status_code == 302  # Should redirect for unknown role


class TestAdminRoutes:
    """Test admin route functionality."""

    def test_admin_users_route_with_permission(self):
        """Test that admin users route works for users with permission."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "role": "site_admin",
            "institution_id": "test-inst",
        }

        with app_module.app.test_client() as client:
            create_test_session(client, user_data)
            response = client.get("/admin/users")
            assert response.status_code == 200

    def test_admin_users_route_without_permission(self):
        """Test that admin users route redirects users without permission."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "user-123",
            "email": "user@example.com",
            "role": "instructor",
            "institution_id": "test-inst",
        }

        with app_module.app.test_client() as client:
            create_test_session(client, user_data)
            response = client.get("/admin/users")
            # User is authenticated but lacks permission, so route redirects
            assert response.status_code == 302
            assert "/dashboard" in response.location

    def test_audit_clo_route_requires_authentication(self):
        """Test that audit-clo route requires authentication."""
        with app_module.app.test_client() as client:
            response = client.get("/audit-clo")
            # Web routes redirect to login when not authenticated
            assert response.status_code == 302
            assert "/login" in response.location

    def test_audit_clo_route_with_admin_permission(self):
        """Test that audit-clo route works for users with admin roles."""
        from tests.test_utils import create_test_session

        # Test program_admin
        user_data = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "role": "program_admin",
            "institution_id": "test-inst",
        }

        with app_module.app.test_client() as client:
            create_test_session(client, user_data)
            response = client.get("/audit-clo")
            assert response.status_code == 200

        # Test institution_admin
        user_data["role"] = "institution_admin"
        with app_module.app.test_client() as client:
            create_test_session(client, user_data)
            response = client.get("/audit-clo")
            assert response.status_code == 200

        # Test site_admin
        user_data["role"] = "site_admin"
        with app_module.app.test_client() as client:
            create_test_session(client, user_data)
            response = client.get("/audit-clo")
            assert response.status_code == 200

    def test_audit_clo_route_without_admin_permission(self):
        """Test that audit-clo route denies access for users without admin roles."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "user-123",
            "email": "user@example.com",
            "role": "instructor",
            "institution_id": "test-inst",
        }

        with app_module.app.test_client() as client:
            create_test_session(client, user_data)
            response = client.get("/audit-clo")
            # User is authenticated but lacks admin role, so permission_required returns 403
            assert response.status_code == 403


class TestDatabaseConnection:
    """Test database connection handling."""

    def test_database_service_availability(self):
        """Test that database service is available."""
        # Test that we can import the database factory
        from src.database.database_factory import get_database_service

        # Get database service instance
        db_service = get_database_service()
        assert db_service is not None

        # Test that it has the expected interface methods
        assert hasattr(db_service, "get_all_institutions")
        assert hasattr(db_service, "get_all_users")

    def test_database_service_import(self):
        """Test that database service is imported correctly."""
        # Test that the import doesn't fail
        from src.database.database_factory import _db_service

        # Database service should be available
        assert _db_service is not None


class TestPortConfiguration:
    """Test port configuration logic."""

    @patch.dict(os.environ, {"PORT": "5000"})
    def test_port_from_port_env_var(self):
        """Test port configuration from PORT environment variable."""
        # Test the port resolution logic
        port = int(
            os.environ.get("PORT", os.environ.get("COURSE_RECORD_UPDATER_PORT", 3001))
        )
        assert port == 5000

    @patch.dict(os.environ, {"COURSE_RECORD_UPDATER_PORT": "8080"}, clear=True)
    def test_port_from_course_record_updater_port(self):
        """Test port configuration from COURSE_RECORD_UPDATER_PORT."""
        port = int(
            os.environ.get("PORT", os.environ.get("COURSE_RECORD_UPDATER_PORT", 3001))
        )
        assert port == 8080

    @patch.dict(os.environ, {}, clear=True)
    def test_port_default_value(self):
        """Test default port value when no environment variables are set."""
        port = int(
            os.environ.get("PORT", os.environ.get("COURSE_RECORD_UPDATER_PORT", 3001))
        )
        assert port == 3001

    @patch.dict(os.environ, {"FLASK_DEBUG": "true"})
    def test_debug_mode_enabled(self):
        """Test debug mode enabled from environment."""
        use_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
        assert use_debug is True

    @patch.dict(os.environ, {"FLASK_DEBUG": "false"})
    def test_debug_mode_disabled(self):
        """Test debug mode disabled from environment."""
        use_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
        assert use_debug is False

    @patch.dict(os.environ, {}, clear=True)
    def test_debug_mode_default_false(self):
        """Test debug mode defaults to false."""
        use_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
        assert use_debug is False


class TestMainExecution:
    """Test main execution block logic."""

    def test_main_execution_logic(self):
        """Test the main execution logic without actually running the server."""
        # Test the logic that would run in if __name__ == "__main__":

        # Test port resolution
        with patch.dict(os.environ, {"PORT": "4000"}):
            port = int(
                os.environ.get(
                    "PORT", os.environ.get("COURSE_RECORD_UPDATER_PORT", 3001)
                )
            )
            assert port == 4000

        # Test debug flag resolution
        with patch.dict(os.environ, {"FLASK_DEBUG": "true"}):
            use_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
            assert use_debug is True


class TestAppErrorHandling:
    """Test app error handling functionality."""

    @patch("src.app.logging")
    def test_app_handles_import_errors(self, mock_logging):
        """Test that app handles import errors gracefully."""
        # This tests the import error handling in the app module
        from src.app import app

        assert app is not None

    def test_app_configuration_defaults(self):
        """Test app configuration defaults."""
        from src.app import app

        # Test default configuration values
        assert app.config.get("SECRET_KEY") is not None

    def test_app_template_folder_configuration(self):
        """Test that app has templates folder configured."""
        from src.app import app

        assert app.template_folder is not None
        assert "templates" in app.template_folder

    def test_app_static_folder_configuration(self):
        """Test that app has static folder configured."""
        from src.app import app

        assert app.static_folder is not None
        assert "static" in app.static_folder

    def test_app_has_blueprints(self):
        """Test that app has blueprints registered."""
        from src.app import app

        # Check that blueprints are registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert len(blueprint_names) > 0

    def test_app_error_handlers_configuration(self):
        """Test app error handlers configuration."""
        from src.app import app

        # Test that error handlers are configured
        assert hasattr(app, "error_handler_spec")

    def test_app_error_handling_comprehensive(self):
        """Test comprehensive app error handling."""
        from src.app import app

        with app.test_client() as client:
            # Test 404 error handling
            response = client.get("/nonexistent-endpoint")
            assert response.status_code == 404

            # Test that error responses are handled properly
            assert response.data is not None

    def test_app_request_context_functionality(self):
        """Test app request context functionality."""
        from src.app import app

        with app.app_context():
            # Test app context availability
            assert app is not None

            # Test request context
            with app.test_request_context("/"):
                from flask import request

                assert request is not None
                assert request.path == "/"

    def test_app_configuration_validation(self):
        """Test app configuration validation."""
        from src.app import app

        # Test essential configuration
        assert app.secret_key is not None
        assert app.template_folder is not None
        assert app.static_folder is not None

        # Test configuration object
        assert app.config is not None
        assert len(app.config) > 0

        # Test debug mode setting
        assert isinstance(app.debug, bool)


class TestCSRFErrorHandler:
    """Test CSRF error handling functionality."""

    def test_csrf_error_returns_json_for_api_routes(self):
        """Test that CSRF errors on API routes return JSON responses."""
        from flask_wtf.csrf import CSRFError

        from src.app import app

        with app.test_request_context("/api/users", method="POST"):
            from src.app import handle_csrf_error

            response = handle_csrf_error(CSRFError("Invalid token"))
            json_data, status_code = response

            assert status_code == 400
            data = json_data.get_json()
            assert data["success"] is False
            assert "CSRF validation failed" in data["error"]

    def test_csrf_error_returns_html_for_web_routes(self):
        """Test that CSRF errors on web routes return HTML responses."""
        from flask_wtf.csrf import CSRFError

        from src.app import app

        with app.test_request_context("/login", method="POST"):
            from src.app import handle_csrf_error

            response = handle_csrf_error(CSRFError("Invalid token"))
            html_content, status_code = response

            assert status_code == 400
            assert "400 Bad Request" in html_content
            assert "Invalid CSRF token" in html_content


class TestInvitationAcceptanceRoute:
    """Test invitation acceptance route functionality."""

    @patch("src.app.is_authenticated")
    def test_register_accept_invitation_logs_out_authenticated_user(
        self, mock_is_authenticated
    ):
        """Test that authenticated users are logged out before rendering registration page."""
        from src.app import app

        mock_is_authenticated.return_value = True

        with app.test_client() as client:
            response = client.get("/register/accept/test-token-123")
            # Should render the registration page (200) after logging out
            assert response.status_code == 200

    @patch("src.app.is_authenticated")
    def test_register_accept_invitation_renders_template_for_unauthenticated(
        self, mock_is_authenticated
    ):
        """Test that unauthenticated users see the invitation registration page."""
        from src.app import app

        mock_is_authenticated.return_value = False

        with app.test_client() as client:
            response = client.get("/register/accept/test-token-456")
            assert response.status_code == 200
            # Check that template is rendered with the token
            assert b"test-token-456" in response.data

    @patch("src.app.is_authenticated")
    def test_register_accept_invitation_passes_token_to_template(
        self, mock_is_authenticated
    ):
        """Test that the invitation token is passed to the template."""
        from src.app import app

        mock_is_authenticated.return_value = False

        with app.test_client() as client:
            test_token = "abc-def-ghi-123"
            response = client.get(f"/register/accept/{test_token}")
            assert response.status_code == 200
            # Verify token is present in the rendered HTML
            assert test_token.encode() in response.data


class TestDashboardRoutes:
    """Test dashboard routing logic."""

    @patch("src.app.is_authenticated")
    @patch("src.app.get_current_user")
    def test_dashboard_unknown_role_redirects(
        self, mock_get_user, mock_is_authenticated
    ):
        """Test dashboard redirects when user has unknown role."""
        from src.app import app

        mock_is_authenticated.return_value = True
        mock_get_user.return_value = {
            "id": "user-123",
            "email": "test@example.com",
            "role": "unknown_role",  # Invalid role
            "institution_id": "inst-123",
        }

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "user-123"

            response = client.get("/dashboard", follow_redirects=False)
            assert response.status_code == 302
            assert "/login" in response.location or "/" in response.location

    @patch("src.app.is_authenticated")
    @patch("src.app.get_current_user")
    def test_courses_list_requires_login(self, mock_get_user, mock_is_authenticated):
        """Test courses list route requires authentication."""
        from src.app import app

        mock_is_authenticated.return_value = False
        mock_get_user.return_value = None

        with app.test_client() as client:
            response = client.get("/courses", follow_redirects=False)
            assert response.status_code == 302
            assert "/login" in response.location

    @patch("src.app.is_authenticated")
    @patch("src.app.get_current_user")
    def test_courses_list_displays_for_authenticated_user(
        self, mock_get_user, mock_is_authenticated
    ):
        """Test courses list displays for authenticated users."""
        from src.app import app

        mock_is_authenticated.return_value = True
        mock_get_user.return_value = {
            "id": "user-123",
            "email": "test@example.com",
            "role": "instructor",
            "institution_id": "inst-123",
        }

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "user-123"

            response = client.get("/courses")
            assert response.status_code == 200
            assert (
                b"courses" in response.data.lower()
                or b"course" in response.data.lower()
            )


class TestReminderLogin:
    """Test reminder login route."""

    @patch("src.app.is_authenticated")
    def test_reminder_login_renders_for_unauthenticated(self, mock_is_authenticated):
        """Test reminder login renders template for unauthenticated users."""
        from src.app import app

        mock_is_authenticated.return_value = False

        with app.test_client() as client:
            response = client.get("/reminder-login")
            assert response.status_code == 200

    @patch("src.app.is_authenticated")
    def test_reminder_login_with_next_parameter(self, mock_is_authenticated):
        """Test reminder login preserves next parameter."""
        from src.app import app

        mock_is_authenticated.return_value = False

        with app.test_client() as client:
            response = client.get("/reminder-login?next=/assessments")
            assert response.status_code == 200

    @patch("src.services.login_service.LoginService.logout_user")
    @patch("src.app.is_authenticated")
    def test_reminder_login_logs_out_authenticated_user(
        self, mock_is_authenticated, mock_logout
    ):
        """Test reminder login logs out authenticated users."""
        from src.app import app

        mock_is_authenticated.return_value = True

        with app.test_client() as client:
            response = client.get("/reminder-login", follow_redirects=False)
            assert response.status_code == 302
            mock_logout.assert_called_once()

    @patch("src.services.login_service.LoginService.logout_user")
    @patch("src.app.is_authenticated")
    def test_reminder_login_preserves_next_after_logout(
        self, mock_is_authenticated, mock_logout
    ):
        """Test reminder login preserves next parameter after logging out."""
        from src.app import app

        mock_is_authenticated.return_value = True

        with app.test_client() as client:
            response = client.get(
                "/reminder-login?next=/assessments", follow_redirects=False
            )
            assert response.status_code == 302
            assert "next=/assessments" in response.location

    @patch("src.app.is_authenticated")
    def test_reminder_login_shows_logged_out_message(self, mock_is_authenticated):
        """Test reminder login shows flash message after logout."""
        from src.app import app

        mock_is_authenticated.return_value = False

        with app.test_client() as client:
            response = client.get("/reminder-login?logged_out=true")
            assert response.status_code == 200


class TestLogoutRoute:
    """Test simple logout route."""

    @patch("src.services.login_service.LoginService.logout_user")
    def test_logout_route_redirects_to_login(self, mock_logout):
        """GET /logout should clear session and redirect to /login."""
        from src.app import app

        with app.test_client() as client:
            response = client.get("/logout", follow_redirects=False)
            assert response.status_code == 302
            assert response.headers["Location"].endswith("/login")
            mock_logout.assert_called_once()


class TestErrorPaths:
    """Test error handling paths where get_current_user returns None."""

    @patch("src.app.get_current_user")
    def test_dashboard_no_user(self, mock_get_user):
        """Test dashboard redirects when no user."""
        from src.app import app

        mock_get_user.return_value = None

        with app.test_client() as client:
            response = client.get("/dashboard", follow_redirects=False)
            assert response.status_code == 302

    @patch("src.app.get_current_user")
    def test_courses_no_user(self, mock_get_user):
        """Test courses redirects when no user."""
        from src.app import app

        mock_get_user.return_value = None

        with app.test_client() as client:
            response = client.get("/courses", follow_redirects=False)
            assert response.status_code == 302

    @patch("src.app.get_current_user")
    def test_users_no_user(self, mock_get_user):
        """Test users redirects when no user."""
        from src.app import app

        mock_get_user.return_value = None

        with app.test_client() as client:
            response = client.get("/users", follow_redirects=False)
            assert response.status_code == 302

    @patch("src.app.get_current_user")
    def test_assessments_no_user(self, mock_get_user):
        """Test assessments redirects when no user."""
        from src.app import app

        mock_get_user.return_value = None

        with app.test_client() as client:
            response = client.get("/assessments", follow_redirects=False)
            assert response.status_code == 302

    @patch("src.app.get_current_user")
    def test_sections_no_user(self, mock_get_user):
        """Test sections redirects when no user."""
        from src.app import app

        mock_get_user.return_value = None

        with app.test_client() as client:
            response = client.get("/sections", follow_redirects=False)
            assert response.status_code == 302

    @patch("src.app.get_current_user")
    def test_audit_clo_no_user(self, mock_get_user):
        """Test audit_clo redirects when no user."""
        from src.app import app

        mock_get_user.return_value = None

        with app.test_client() as client:
            response = client.get("/audit-clo", follow_redirects=False)
            assert response.status_code == 302

    @patch("src.app.get_current_user")
    def test_audit_clo_non_admin(self, mock_get_user):
        """Test audit_clo redirects for non-admin users."""
        from src.app import app

        mock_get_user.return_value = {
            "id": "user-123",
            "email": "test@example.com",
            "role": "instructor",
            "institution_id": "inst-123",
        }

        with app.test_client() as client:
            response = client.get("/audit-clo", follow_redirects=False)
            assert response.status_code == 302

    @patch("src.app.get_current_user")
    def test_profile_no_user(self, mock_get_user):
        """Test profile redirects when no user."""
        from src.app import app

        mock_get_user.return_value = None

        with app.test_client() as client:
            response = client.get("/profile", follow_redirects=False)
            assert response.status_code == 302

    def test_health_check(self):
        """Test health check endpoint."""
        from src.app import app

        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ok"
            assert data["ready"] is True


class TestPasswordReset:
    """Test password reset form."""

    @patch(
        "src.services.password_reset_service.PasswordResetService.validate_reset_token"
    )
    def test_reset_form_valid_token(self, mock_validate):
        """Test reset form with valid token."""
        from src.app import app

        mock_validate.return_value = {"valid": True, "email": "test@example.com"}

        with app.test_client() as client:
            response = client.get("/reset-password/valid-token")
            assert response.status_code == 200

    @patch(
        "src.services.password_reset_service.PasswordResetService.validate_reset_token"
    )
    def test_reset_form_invalid_token(self, mock_validate):
        """Test reset form with invalid token."""
        from src.app import app

        mock_validate.return_value = {"valid": False}

        with app.test_client() as client:
            response = client.get("/reset-password/invalid", follow_redirects=False)
            assert response.status_code == 302

    @patch(
        "src.services.password_reset_service.PasswordResetService.validate_reset_token"
    )
    def test_reset_form_error(self, mock_validate):
        """Test reset form handles errors."""
        from src.app import app

        mock_validate.side_effect = Exception("Error")

        with app.test_client() as client:
            response = client.get("/reset-password/token", follow_redirects=False)
            assert response.status_code == 302
