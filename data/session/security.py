"""
Session security validation and utilities.

Handles CSRF tokens, IP validation, user agent validation,
session expiry checks, and other security-related session operations.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from flask import request, session

from src.utils.logging_config import get_logger

from .config import (
    CSRF_TOKEN_LENGTH,
    DEFAULT_SESSION_TIMEOUT_HOURS,
    REMEMBER_ME_TIMEOUT_DAYS,
)

logger = get_logger(__name__)


class SessionSecurityError(Exception):
    """Raised when session security validation fails"""

    pass


class SessionSecurity:
    """Session security validation and utilities"""

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a new CSRF token"""
        return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)

    @staticmethod
    def get_client_ip() -> str:
        """Get client IP address from request headers"""
        # Check for forwarded headers first (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Check other common proxy headers
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection
        return request.environ.get("REMOTE_ADDR", "unknown")

    @staticmethod
    def hash_user_agent() -> str:
        """Hash user agent for session validation"""
        user_agent = request.headers.get("User-Agent", "")
        return hashlib.sha256(user_agent.encode()).hexdigest()[:16]

    @staticmethod
    def is_session_expired() -> bool:
        """Check if current session is expired"""
        if not session.get("last_activity"):
            return True

        try:
            last_activity = datetime.fromisoformat(session["last_activity"])
            now = datetime.now(timezone.utc)

            # Remove timezone info for comparison if needed
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)

            # Check timeout based on remember_me setting
            remember_me = session.get("remember_me", False)
            if remember_me:
                timeout_hours = REMEMBER_ME_TIMEOUT_DAYS * 24
            else:
                timeout_hours = DEFAULT_SESSION_TIMEOUT_HOURS

            elapsed = now - last_activity
            return elapsed.total_seconds() > (timeout_hours * 3600)

        except (ValueError, TypeError) as e:
            logger.warning(f"[Session Security] Invalid timestamp in session: {e}")
            return True

    @staticmethod
    def validate_ip_consistency() -> bool:
        """Validate that client IP matches session IP"""
        session_ip = session.get("ip_address")
        current_ip = SessionSecurity.get_client_ip()

        if not session_ip:
            logger.warning("[Session Security] No IP address in session")
            return False

        # Allow some flexibility for dynamic IPs (same subnet)
        # This is a basic check - production might need more sophisticated logic
        return session_ip == current_ip

    @staticmethod
    def validate_user_agent_consistency() -> bool:
        """Validate that user agent hash matches session"""
        session_ua_hash = session.get("user_agent_hash")
        current_ua_hash = SessionSecurity.hash_user_agent()

        if not session_ua_hash:
            logger.warning("[Session Security] No user agent hash in session")
            return False

        return session_ua_hash == current_ua_hash

    @staticmethod
    def update_last_activity() -> None:
        """Update last activity timestamp in session"""
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
