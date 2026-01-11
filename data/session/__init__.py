"""
Session Management Package

Provides secure session management using Flask-Session with comprehensive
security features for the LoopCloser authentication system.

Features:
- Flask-Session integration with secure configuration
- 8-hour session timeout with idle detection
- Secure cookie configuration (HTTPOnly, Secure, SameSite)
- Session fixation prevention
- Remember me functionality
- Proper session cleanup
- Session security middleware
"""

from typing import Any, Dict, Optional

from .manager import SessionService
from .security import SessionSecurityError


# Public API - convenience functions for easy import
def create_user_session(user_data: Dict[str, Any], remember_me: bool = False) -> None:
    """Convenience function for creating user sessions"""
    SessionService.create_user_session(user_data, remember_me)


def validate_session() -> bool:
    """Convenience function for validating sessions"""
    return SessionService.validate_session()


def is_user_logged_in() -> bool:
    """Convenience function for checking login status"""
    return SessionService.is_user_logged_in()


def get_current_user() -> Optional[Dict[str, Any]]:
    """Convenience function for getting current user"""
    return SessionService.get_current_user()


def get_csrf_token() -> Optional[str]:
    """Convenience function for getting CSRF token"""
    return SessionService.get_csrf_token()


def validate_csrf_token(token: str) -> bool:
    """Convenience function for validating CSRF token"""
    return SessionService.validate_csrf_token(token)


def refresh_session() -> None:
    """Convenience function for refreshing session"""
    return SessionService.refresh_session()


def destroy_session() -> None:
    """Convenience function for destroying session"""
    return SessionService.destroy_session()


def get_session_info() -> Dict[str, Any]:
    """Convenience function for getting session info"""
    return SessionService.get_session_info()


# Export main classes and functions
__all__ = [
    "SessionService",
    "SessionSecurityError",
    "create_user_session",
    "validate_session",
    "is_user_logged_in",
    "get_current_user",
    "get_csrf_token",
    "validate_csrf_token",
    "refresh_session",
    "destroy_session",
    "get_session_info",
]
