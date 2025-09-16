"""
Unit tests for Session Management Service

Tests secure session creation, validation, timeout, and security features.
"""

import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from session_service import (
    SessionSecurityError,
    SessionService,
    create_user_session,
    destroy_session,
    get_csrf_token,
    get_current_user,
    is_user_logged_in,
    validate_csrf_token,
    validate_session,
)


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True

    # Configure session service
    SessionService.configure_app(app)

    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Create app context for testing"""
    with app.app_context():
        yield app


@pytest.fixture
def request_context(app):
    """Create request context for testing"""
    with app.test_request_context():
        yield


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "user_id": "user123",
        "email": "test@example.com",
        "role": "instructor",
        "institution_id": "inst123",
        "program_ids": ["prog1", "prog2"],
        "first_name": "John",
        "last_name": "Doe",
        "display_name": "John Doe",
    }


class TestSessionConfiguration:
    """Test session configuration and setup"""

    def test_configure_app_sets_correct_config(self, app):
        """Test that app configuration is set correctly"""
        assert app.config["SESSION_TYPE"] == "filesystem"
        assert app.config["SESSION_PERMANENT"] is False
        assert app.config["SESSION_USE_SIGNER"] is True
        assert app.config["SESSION_KEY_PREFIX"] == "course_app:"
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
        assert app.config["SESSION_COOKIE_NAME"] == "course_session"

    def test_configure_app_sets_session_lifetime(self, app):
        """Test that session lifetime is configured correctly"""
        expected_lifetime = timedelta(hours=8)
        assert app.config["PERMANENT_SESSION_LIFETIME"] == expected_lifetime


class TestSessionCreation:
    """Test session creation functionality"""

    def test_create_user_session_basic(self, request_context, sample_user_data):
        """Test basic user session creation"""
        create_user_session(sample_user_data)

        assert is_user_logged_in()

        current_user = get_current_user()
        assert current_user["user_id"] == "user123"
        assert current_user["email"] == "test@example.com"
        assert current_user["role"] == "instructor"
        assert current_user["institution_id"] == "inst123"
        assert current_user["program_ids"] == ["prog1", "prog2"]
        assert current_user["display_name"] == "John Doe"

    def test_create_user_session_with_remember_me(
        self, request_context, sample_user_data
    ):
        """Test session creation with remember me enabled"""
        create_user_session(sample_user_data, remember_me=True)

        current_user = get_current_user()
        assert current_user["remember_me"] is True

    def test_create_user_session_without_display_name(self, request_context):
        """Test session creation without explicit display name"""
        user_data = {
            "user_id": "user123",
            "email": "test@example.com",
            "role": "instructor",
            "institution_id": "inst123",
            "first_name": "Jane",
            "last_name": "Smith",
        }

        create_user_session(user_data)

        current_user = get_current_user()
        assert current_user["display_name"] == "Jane Smith"

    def test_create_user_session_generates_csrf_token(
        self, request_context, sample_user_data
    ):
        """Test that CSRF token is generated"""
        create_user_session(sample_user_data)

        csrf_token = get_csrf_token()
        assert csrf_token is not None
        assert len(csrf_token) > 0

    @patch("session_service.SessionService._get_client_ip")
    @patch("session_service.SessionService._hash_user_agent")
    def test_create_user_session_stores_security_data(
        self, mock_hash_ua, mock_get_ip, request_context, sample_user_data
    ):
        """Test that security data is stored in session"""
        mock_get_ip.return_value = "192.168.1.1"
        mock_hash_ua.return_value = "hash123"

        create_user_session(sample_user_data)

        from flask import session

        assert session["ip_address"] == "192.168.1.1"
        assert session["user_agent_hash"] == "hash123"

    def test_create_user_session_regenerates_session_id(
        self, request_context, sample_user_data
    ):
        """Test that session ID is regenerated for security"""
        from flask import session

        # Create a mock session with regenerate method
        mock_session = MagicMock()
        mock_session.regenerate = MagicMock()

        with patch("session_service.session", mock_session):
            create_user_session(sample_user_data)

            # Verify regenerate was called
            mock_session.regenerate.assert_called_once()


class TestSessionValidation:
    """Test session validation functionality"""

    def test_validate_session_when_logged_in(self, request_context, sample_user_data):
        """Test session validation for logged in user"""
        create_user_session(sample_user_data)

        assert validate_session() is True

    def test_validate_session_when_not_logged_in(self, request_context):
        """Test session validation when not logged in"""
        assert validate_session() is False

    @patch("session_service.SessionService._is_session_expired")
    def test_validate_session_when_expired(
        self, mock_is_expired, request_context, sample_user_data
    ):
        """Test session validation when session is expired"""
        create_user_session(sample_user_data)
        mock_is_expired.return_value = True

        assert validate_session() is False
        assert not is_user_logged_in()  # Session should be destroyed

    @patch("session_service.SessionService._validate_ip_consistency")
    def test_validate_session_ip_mismatch(
        self, mock_validate_ip, request_context, sample_user_data
    ):
        """Test session validation with IP address mismatch"""
        create_user_session(sample_user_data)
        mock_validate_ip.return_value = False

        assert validate_session() is False
        assert not is_user_logged_in()  # Session should be destroyed

    @patch("session_service.SessionService._validate_user_agent_consistency")
    def test_validate_session_user_agent_mismatch(
        self, mock_validate_ua, request_context, sample_user_data
    ):
        """Test session validation with user agent mismatch"""
        create_user_session(sample_user_data)
        mock_validate_ua.return_value = False

        assert validate_session() is False
        assert not is_user_logged_in()  # Session should be destroyed


class TestSessionTimeout:
    """Test session timeout functionality"""

    def test_session_expiry_regular_session(self, request_context, sample_user_data):
        """Test session expiry for regular session"""
        create_user_session(sample_user_data)

        # Manually set an old timestamp to simulate expiry
        from flask import session

        old_time = datetime.now(timezone.utc) - timedelta(hours=9)
        session["last_activity"] = old_time.isoformat()

        assert SessionService._is_session_expired() is True

    def test_session_expiry_remember_me_session(
        self, request_context, sample_user_data
    ):
        """Test session expiry for remember me session"""
        create_user_session(sample_user_data, remember_me=True)

        from flask import session

        # Test within 30-day remember me timeout (20 days old)
        recent_time = datetime.now(timezone.utc) - timedelta(days=20)
        session["last_activity"] = recent_time.isoformat()

        assert SessionService._is_session_expired() is False

        # Test past 30-day remember me timeout (31 days old)
        old_time = datetime.now(timezone.utc) - timedelta(days=31)
        session["last_activity"] = old_time.isoformat()

        assert SessionService._is_session_expired() is True

    def test_session_expiry_invalid_timestamp(self, request_context, sample_user_data):
        """Test session expiry with invalid timestamp"""
        create_user_session(sample_user_data)

        from flask import session

        session["last_activity"] = "invalid-timestamp"

        assert SessionService._is_session_expired() is True


class TestCSRFProtection:
    """Test CSRF token functionality"""

    def test_csrf_token_generation(self, request_context, sample_user_data):
        """Test CSRF token generation"""
        create_user_session(sample_user_data)

        token = get_csrf_token()
        assert token is not None
        assert len(token) > 20  # Should be a reasonable length

    def test_csrf_token_validation_valid(self, request_context, sample_user_data):
        """Test CSRF token validation with valid token"""
        create_user_session(sample_user_data)

        token = get_csrf_token()
        assert validate_csrf_token(token) is True

    def test_csrf_token_validation_invalid(self, request_context, sample_user_data):
        """Test CSRF token validation with invalid token"""
        create_user_session(sample_user_data)

        invalid_token = "invalid-token"
        assert validate_csrf_token(invalid_token) is False

    def test_csrf_token_validation_no_session(self, request_context):
        """Test CSRF token validation without session"""
        token = "some-token"
        assert validate_csrf_token(token) is False

    def test_csrf_token_validation_empty_token(self, request_context, sample_user_data):
        """Test CSRF token validation with empty token"""
        create_user_session(sample_user_data)

        assert validate_csrf_token("") is False
        assert validate_csrf_token(None) is False


class TestSessionDestruction:
    """Test session destruction functionality"""

    def test_destroy_session_clears_data(self, request_context, sample_user_data):
        """Test that session destruction clears all data"""
        create_user_session(sample_user_data)

        assert is_user_logged_in()

        destroy_session()

        assert not is_user_logged_in()
        assert get_current_user() is None
        assert get_csrf_token() is None

    def test_destroy_session_when_not_logged_in(self, request_context):
        """Test destroying session when not logged in"""
        # Should not raise exception
        destroy_session()

        assert not is_user_logged_in()


class TestSessionInfo:
    """Test session information functionality"""

    def test_get_session_info_when_logged_in(self, request_context, sample_user_data):
        """Test getting session info when logged in"""
        create_user_session(sample_user_data)

        info = SessionService.get_session_info()

        assert info["logged_in"] is True
        assert info["user_id"] == "user123"
        assert info["email"] == "test@example.com"
        assert info["role"] == "instructor"
        assert "created_at" in info
        assert "last_activity" in info
        assert info["remember_me"] is False

    def test_get_session_info_when_not_logged_in(self, request_context):
        """Test getting session info when not logged in"""
        info = SessionService.get_session_info()

        assert info["logged_in"] is False
        assert len(info) == 1  # Only logged_in field

    def test_get_session_info_with_remember_me(self, request_context, sample_user_data):
        """Test getting session info with remember me enabled"""
        create_user_session(sample_user_data, remember_me=True)

        info = SessionService.get_session_info()

        assert info["remember_me"] is True


class TestSessionRefresh:
    """Test session refresh functionality"""

    @patch("session_service.datetime")
    def test_refresh_session_updates_activity(
        self, mock_datetime, request_context, sample_user_data
    ):
        """Test that session refresh updates last activity"""
        # Set initial time
        initial_time = datetime.now(timezone.utc)
        mock_datetime.now.return_value = initial_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        create_user_session(sample_user_data)

        initial_activity = get_current_user()["last_activity"]

        # Move time forward
        future_time = initial_time + timedelta(minutes=30)
        mock_datetime.now.return_value = future_time

        SessionService.refresh_session()

        updated_activity = get_current_user()["last_activity"]

        assert updated_activity != initial_activity

    def test_refresh_session_when_not_logged_in(self, request_context):
        """Test refreshing session when not logged in"""
        # Should not raise exception
        SessionService.refresh_session()


class TestSecurityHelpers:
    """Test security helper functions"""

    def test_get_client_ip_direct(self, request_context):
        """Test getting client IP from direct connection"""
        with patch("session_service.request") as mock_request:
            mock_request.environ = {"REMOTE_ADDR": "192.168.1.1"}

            ip = SessionService._get_client_ip()
            assert ip == "192.168.1.1"

    def test_get_client_ip_forwarded(self, request_context):
        """Test getting client IP from forwarded header"""
        with patch("session_service.request") as mock_request:
            mock_request.environ = {
                "HTTP_X_FORWARDED_FOR": "10.0.0.1, 192.168.1.1",
                "REMOTE_ADDR": "192.168.1.1",
            }

            ip = SessionService._get_client_ip()
            assert ip == "10.0.0.1"

    def test_hash_user_agent(self, request_context):
        """Test user agent hashing"""
        with patch("session_service.request") as mock_request:
            mock_request.headers = {"User-Agent": "Mozilla/5.0 Test Browser"}

            hash1 = SessionService._hash_user_agent()
            hash2 = SessionService._hash_user_agent()

            assert hash1 == hash2  # Same user agent should produce same hash
            assert isinstance(hash1, str)


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_convenience_functions_work(self, request_context, sample_user_data):
        """Test that all convenience functions work correctly"""
        # Test session creation
        create_user_session(sample_user_data)

        # Test login check
        assert is_user_logged_in()

        # Test get current user
        user = get_current_user()
        assert user["user_id"] == "user123"

        # Test session validation
        assert validate_session()

        # Test CSRF token functions
        token = get_csrf_token()
        assert validate_csrf_token(token)

        # Test session destruction
        destroy_session()
        assert not is_user_logged_in()
