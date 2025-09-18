"""
Session Management Service

Provides secure session management using Flask-Session with comprehensive
security features for the Course Record Updater authentication system.

Features:
- Flask-Session integration with secure configuration
- 8-hour session timeout with idle detection
- Secure cookie configuration (HTTPOnly, Secure, SameSite)
- Session fixation prevention
- Remember me functionality
- Proper session cleanup
- Session security middleware
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from flask import current_app, request, session

from flask_session import Session  # type: ignore

# Import centralized logging
from logging_config import get_logger

# Get standardized logger
logger = get_logger(__name__)

# Session configuration constants
DEFAULT_SESSION_TIMEOUT_HOURS = 8
REMEMBER_ME_TIMEOUT_DAYS = 30
SESSION_KEY_PREFIX = "course_app:"
CSRF_TOKEN_LENGTH = 32


class SessionSecurityError(Exception):
    """Raised when session security validation fails"""

    pass


class SessionService:
    """
    Comprehensive session management service

    Handles secure session creation, validation, timeout, and cleanup
    """

    @staticmethod
    def configure_app(app) -> None:
        """
        Configure Flask app with secure session settings

        Args:
            app: Flask application instance
        """
        logger.info("[Session Service] Configuring Flask-Session")

        # Basic session configuration
        app.config["SESSION_TYPE"] = "filesystem"  # Use Redis in production
        app.config["SESSION_FILE_DIR"] = (
            "flask_session"  # Store sessions in dedicated directory
        )
        app.config["SESSION_PERMANENT"] = False
        app.config["SESSION_USE_SIGNER"] = True
        app.config["SESSION_KEY_PREFIX"] = SESSION_KEY_PREFIX

        # Security configuration
        app.config["SESSION_COOKIE_SECURE"] = app.config.get(
            "SESSION_COOKIE_SECURE", False
        )  # Set to True in production with HTTPS
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        app.config["SESSION_COOKIE_NAME"] = "course_session"

        # Session lifetime
        app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
            hours=app.config.get("SESSION_TIMEOUT_HOURS", DEFAULT_SESSION_TIMEOUT_HOURS)
        )

        # Initialize Flask-Session
        Session(app)

        logger.info("[Session Service] Flask-Session configured successfully")

    @staticmethod
    def create_user_session(
        user_data: Dict[str, Any], remember_me: bool = False
    ) -> None:
        """
        Create a secure user session with anti-fixation protection

        Args:
            user_data: User information to store in session
            remember_me: Whether to extend session lifetime
        """
        logger.info(
            f"[Session Service] Creating session for user: {user_data.get('user_id')}"
        )

        # Clear existing session to prevent fixation attacks
        session.clear()

        # Regenerate session ID for security
        if hasattr(session, "regenerate"):
            session.regenerate()

        # Store user data in session
        session["user_id"] = user_data.get("user_id")
        session["email"] = user_data.get("email")
        session["role"] = user_data.get("role")
        session["institution_id"] = user_data.get("institution_id")
        session["program_ids"] = user_data.get("program_ids", [])
        session["display_name"] = (
            user_data.get("display_name")
            or f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
        )

        # Session metadata
        session["created_at"] = datetime.now(timezone.utc).isoformat()
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        session["remember_me"] = remember_me
        session["csrf_token"] = secrets.token_urlsafe(CSRF_TOKEN_LENGTH)

        # Set session as permanent if remember me is enabled
        if remember_me:
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(
                days=REMEMBER_ME_TIMEOUT_DAYS
            )
            logger.info(
                "[Session Service] Extended session lifetime enabled (remember me)"
            )
        else:
            session.permanent = False
            current_app.permanent_session_lifetime = timedelta(
                hours=DEFAULT_SESSION_TIMEOUT_HOURS
            )

        # Store IP address for security validation
        session["ip_address"] = SessionService._get_client_ip()
        session["user_agent_hash"] = SessionService._hash_user_agent()

        logger.info("[Session Service] User session created successfully")

    @staticmethod
    def validate_session() -> bool:
        """
        Validate current session for security and timeout

        Returns:
            True if session is valid, False otherwise
        """
        if not SessionService.is_user_logged_in():
            return False

        try:
            # Check session timeout
            if SessionService._is_session_expired():
                logger.warning("[Session Service] Session expired")
                SessionService.destroy_session()
                return False

            # Validate IP address (optional security check)
            if not SessionService._validate_ip_consistency():
                logger.warning("[Session Service] IP address mismatch detected")
                SessionService.destroy_session()
                return False

            # Validate user agent (optional security check)
            if not SessionService._validate_user_agent_consistency():
                logger.warning("[Session Service] User agent mismatch detected")
                SessionService.destroy_session()
                return False

            # Update last activity
            SessionService._update_last_activity()

            return True

        except Exception as e:
            logger.error(f"[Session Service] Session validation error: {e}")
            SessionService.destroy_session()
            return False

    @staticmethod
    def is_user_logged_in() -> bool:
        """
        Check if user is currently logged in

        Returns:
            True if user is logged in, False otherwise
        """
        return "user_id" in session and session.get("user_id") is not None

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """
        Get current user information from session

        Returns:
            User data dictionary or None if not logged in
        """
        if not SessionService.is_user_logged_in():
            return None

        return {
            "user_id": session.get("user_id"),
            "email": session.get("email"),
            "role": session.get("role"),
            "institution_id": session.get("institution_id"),
            "program_ids": session.get("program_ids", []),
            "display_name": session.get("display_name"),
            "created_at": session.get("created_at"),
            "last_activity": session.get("last_activity"),
            "remember_me": session.get("remember_me", False),
        }

    @staticmethod
    def get_csrf_token() -> Optional[str]:
        """
        Get CSRF token from current session

        Returns:
            CSRF token string or None if not available
        """
        return session.get("csrf_token")

    @staticmethod
    def validate_csrf_token(token: str) -> bool:
        """
        Validate CSRF token against session

        Args:
            token: CSRF token to validate

        Returns:
            True if token is valid, False otherwise
        """
        session_token = session.get("csrf_token")
        if not session_token or not token:
            return False

        return secrets.compare_digest(session_token, token)

    @staticmethod
    def destroy_session() -> None:
        """
        Completely destroy user session and clear all data
        """
        user_id = session.get("user_id")
        logger.info(f"[Session Service] Destroying session for user: {user_id}")

        # Clear all session data
        session.clear()

        # If using server-side sessions, this would also clear server storage
        logger.info("[Session Service] Session destroyed successfully")

    @staticmethod
    def refresh_session() -> None:
        """
        Refresh session to extend timeout without full re-authentication
        """
        if SessionService.is_user_logged_in():
            SessionService._update_last_activity()
            logger.info("[Session Service] Session refreshed")

    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        """
        Get session information for debugging/monitoring

        Returns:
            Dictionary with session metadata
        """
        if not SessionService.is_user_logged_in():
            return {"logged_in": False}

        created_at_str = session.get("created_at")
        last_activity_str = session.get("last_activity")

        created_at = None
        last_activity = None

        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except ValueError:
                pass

        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
            except ValueError:
                pass

        return {
            "logged_in": True,
            "user_id": session.get("user_id"),
            "email": session.get("email"),
            "role": session.get("role"),
            "created_at": created_at,
            "last_activity": last_activity,
            "remember_me": session.get("remember_me", False),
            "permanent": session.permanent,
        }

    # Private helper methods

    @staticmethod
    def _is_session_expired() -> bool:
        """Check if session has expired based on last activity"""
        last_activity_str = session.get("last_activity")
        if not last_activity_str:
            return True

        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            now = datetime.now(timezone.utc)

            if session.get("remember_me", False):
                timeout = timedelta(days=REMEMBER_ME_TIMEOUT_DAYS)
            else:
                timeout = timedelta(hours=DEFAULT_SESSION_TIMEOUT_HOURS)

            return (now - last_activity) > timeout

        except ValueError:
            return True

    @staticmethod
    def _update_last_activity() -> None:
        """Update last activity timestamp"""
        session["last_activity"] = datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _get_client_ip() -> str:
        """Get client IP address from request"""
        # Check for forwarded headers (load balancer/proxy)
        if request.environ.get("HTTP_X_FORWARDED_FOR"):
            return request.environ["HTTP_X_FORWARDED_FOR"].split(",")[0].strip()
        elif request.environ.get("HTTP_X_REAL_IP"):
            return request.environ["HTTP_X_REAL_IP"]
        else:
            return request.environ.get("REMOTE_ADDR", "unknown")

    @staticmethod
    def _hash_user_agent() -> str:
        """Create hash of user agent for consistency checking"""
        user_agent = request.headers.get("User-Agent", "")
        return str(hash(user_agent))

    @staticmethod
    def _validate_ip_consistency() -> bool:
        """Validate that IP address hasn't changed (optional security check)"""
        stored_ip = session.get("ip_address")
        current_ip = SessionService._get_client_ip()

        # In development or when behind load balancers, IP might change
        # This check can be disabled by returning True
        if not stored_ip:
            return True

        return stored_ip == current_ip

    @staticmethod
    def _validate_user_agent_consistency() -> bool:
        """Validate that user agent hasn't changed (optional security check)"""
        stored_hash = session.get("user_agent_hash")
        current_hash = SessionService._hash_user_agent()

        if not stored_hash:
            return True

        return stored_hash == current_hash


# Convenience functions for easy import
def create_user_session(user_data: Dict[str, Any], remember_me: bool = False) -> None:
    """Convenience function for creating user sessions"""
    return SessionService.create_user_session(user_data, remember_me)


def is_user_logged_in() -> bool:
    """Convenience function to check login status"""
    return SessionService.is_user_logged_in()


def get_current_user() -> Optional[Dict[str, Any]]:
    """Convenience function to get current user"""
    return SessionService.get_current_user()


def validate_session() -> bool:
    """Convenience function to validate current session"""
    return SessionService.validate_session()


def destroy_session() -> None:
    """Convenience function to destroy session"""
    return SessionService.destroy_session()


def get_csrf_token() -> Optional[str]:
    """Convenience function to get CSRF token"""
    return SessionService.get_csrf_token()


def validate_csrf_token(token: str) -> bool:
    """Convenience function to validate CSRF token"""
    return SessionService.validate_csrf_token(token)
