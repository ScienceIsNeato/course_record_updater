"""
Core session management operations.

Handles session creation, validation, destruction, and Flask-Session
configuration. This is the main session management interface.
"""

# isort: skip_file
# NOTE: isort disabled for this file due to persistent CI import ordering conflicts
# between flask/flask_session grouping that couldn't be resolved with standard
# isort configuration. The imports are manually organized and functional.

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import current_app, session
from flask_session import Session  # type: ignore

# Local imports
from logging_config import get_logger

from .config import FLASK_SESSION_CONFIG, get_session_lifetime
from .security import SessionSecurity

logger = get_logger(__name__)


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

        # Apply base configuration
        for key, value in FLASK_SESSION_CONFIG.items():
            app.config[key] = value

        # Security configuration (environment-dependent)
        app.config["SESSION_COOKIE_SECURE"] = app.config.get(
            "SESSION_COOKIE_SECURE", False
        )  # Set to True in production with HTTPS

        # Session lifetime
        app.config["PERMANENT_SESSION_LIFETIME"] = get_session_lifetime()

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
        session["csrf_token"] = SessionSecurity.generate_csrf_token()

        # Set session as permanent if remember me is enabled
        if remember_me:
            session.permanent = True
            current_app.permanent_session_lifetime = get_session_lifetime(
                remember_me=True
            )
            logger.info(
                "[Session Service] Extended session lifetime enabled (remember me)"
            )
        else:
            session.permanent = False
            current_app.permanent_session_lifetime = get_session_lifetime(
                remember_me=False
            )

        # Store IP address and user agent for security validation
        session["ip_address"] = SessionSecurity.get_client_ip()
        session["user_agent_hash"] = SessionSecurity.hash_user_agent()

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
            if SessionSecurity.is_session_expired():
                logger.warning("[Session Service] Session expired")
                SessionService.destroy_session()
                return False

            # Validate IP address (optional security check)
            if not SessionSecurity.validate_ip_consistency():
                logger.warning("[Session Service] IP address mismatch detected")
                SessionService.destroy_session()
                return False

            # Validate user agent (optional security check)
            if not SessionSecurity.validate_user_agent_consistency():
                logger.warning("[Session Service] User agent mismatch detected")
                SessionService.destroy_session()
                return False

            # Update last activity
            SessionSecurity.update_last_activity()

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
        return session_token is not None and session_token == token

    @staticmethod
    def refresh_session() -> None:
        """Refresh session activity timestamp"""
        if SessionService.is_user_logged_in():
            SessionSecurity.update_last_activity()
            logger.info("[Session Service] Session refreshed")

    @staticmethod
    def destroy_session() -> None:
        """
        Destroy current session and clear all data

        Performs secure session cleanup
        """
        if "user_id" in session:
            user_id = session.get("user_id")
            logger.info(f"[Session Service] Destroying session for user: {user_id}")

        # Clear all session data
        session.clear()

        # Regenerate session ID to prevent session fixation
        if hasattr(session, "regenerate"):
            session.regenerate()

        logger.info("[Session Service] Session destroyed successfully")

    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        """
        Get session information for debugging/monitoring

        Returns:
            Dictionary with session metadata
        """
        if not SessionService.is_user_logged_in():
            return {"logged_in": False}

        return {
            "logged_in": True,
            "user_id": session.get("user_id"),
            "email": session.get("email"),
            "role": session.get("role"),
            "created_at": session.get("created_at"),
            "last_activity": session.get("last_activity"),
            "remember_me": session.get("remember_me", False),
            "ip_address": session.get("ip_address"),
        }
