"""
Session configuration constants and settings.

Centralized configuration for session management including timeouts,
security settings, and Flask-Session configuration.
"""

import os
from datetime import timedelta

# Session configuration constants
DEFAULT_SESSION_TIMEOUT_HOURS = 8
REMEMBER_ME_TIMEOUT_DAYS = 30
SESSION_KEY_PREFIX = "course_app:"
CSRF_TOKEN_LENGTH = 32

# Session file directory (relative to project root)
SESSION_FILE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "flask_session",
)

# Flask-Session configuration
FLASK_SESSION_CONFIG = {
    "SESSION_TYPE": "filesystem",  # Use Redis in production
    "SESSION_PERMANENT": False,
    "SESSION_USE_SIGNER": True,
    "SESSION_KEY_PREFIX": SESSION_KEY_PREFIX,
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    "SESSION_COOKIE_NAME": "course_session",
    "SESSION_FILE_DIR": SESSION_FILE_DIR,
}


def get_session_lifetime(remember_me: bool = False) -> timedelta:
    """Get session lifetime based on remember_me setting"""
    if remember_me:
        return timedelta(days=REMEMBER_ME_TIMEOUT_DAYS)
    return timedelta(hours=DEFAULT_SESSION_TIMEOUT_HOURS)
