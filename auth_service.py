"""
Authentication Service Module - STUB VERSION

This module provides the authentication framework foundation.
Full implementation is a separate task to avoid blocking current progress.
"""

from functools import wraps
from typing import Any, Dict, Optional

# Unused Flask imports removed

# Import our models
# ROLES import removed


class AuthService:
    """STUB: Service class for handling authentication operations"""

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        STUB: Get the current authenticated user from session.
        For now, returns a mock admin user for development.
        """
        # STUB: Return mock admin user for development
        return {
            "user_id": "dev-admin-123",
            "email": "admin@cei.edu",
            "role": "site_admin",
            "first_name": "Dev",
            "last_name": "Admin",
            "department": "IT",
        }

    def has_permission(self, required_permission: str) -> bool:
        """
        STUB: Check if current user has a specific permission.
        For development, always returns True (admin access).
        """
        # STUB: Always return True for development
        return True

    def is_authenticated(self) -> bool:
        """STUB: Check if user is authenticated. Always True for development."""
        return True


# Global auth service instance
auth_service = AuthService()


# STUB Authentication decorators (pass-through for development)
def login_required(f):
    """STUB: Decorator to require authentication. Currently passes through."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # STUB: Skip auth check for development
        return f(*args, **kwargs)

    return decorated_function


def role_required(required_role: str):
    """STUB: Decorator to require a specific role. Currently passes through."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # STUB: Skip role check for development
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def permission_required(required_permission: str):
    """STUB: Decorator to require a specific permission. Currently passes through."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # STUB: Skip permission check for development
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    """STUB: Decorator to require site admin role. Currently passes through."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # STUB: Skip admin check for development
        return f(*args, **kwargs)

    return decorated_function


# Utility functions (working stubs)
def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current user (convenience function)."""
    return auth_service.get_current_user()


def has_permission(permission: str) -> bool:
    """Check if current user has permission (convenience function)."""
    return auth_service.has_permission(permission)


def is_authenticated() -> bool:
    """Check if user is authenticated (convenience function)."""
    return auth_service.is_authenticated()


def get_user_role() -> Optional[str]:
    """Get current user's role (convenience function)."""
    user = get_current_user()
    return user["role"] if user else None


def get_user_department() -> Optional[str]:
    """Get current user's department (convenience function)."""
    user = get_current_user()
    return user.get("department") if user else None
