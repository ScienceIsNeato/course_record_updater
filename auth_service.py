"""
Authentication Service Module

This module provides comprehensive authentication and authorization functionality
including role-based access control and permission management.
"""

from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional

from flask import jsonify, request, session

# Import our models and logging
from logging_config import get_logger

logger = get_logger(__name__)


class UserRole(Enum):
    """4-tier role hierarchy for access control"""

    SITE_ADMIN = "site_admin"
    INSTITUTION_ADMIN = "institution_admin"
    PROGRAM_ADMIN = "program_admin"
    INSTRUCTOR = "instructor"

    @classmethod
    def get_role_hierarchy(cls) -> List[str]:
        """Get roles in hierarchical order (highest to lowest privilege)"""
        return [
            cls.SITE_ADMIN.value,
            cls.INSTITUTION_ADMIN.value,
            cls.PROGRAM_ADMIN.value,
            cls.INSTRUCTOR.value,
        ]

    @classmethod
    def has_role_or_higher(cls, user_role: str, required_role: str) -> bool:
        """Check if user role has equal or higher privilege than required role"""
        hierarchy = cls.get_role_hierarchy()
        try:
            user_level = hierarchy.index(user_role)
            required_level = hierarchy.index(required_role)
            return user_level <= required_level  # Lower index = higher privilege
        except ValueError:
            return False


class Permission(Enum):
    """System permissions that can be granted to roles"""

    # Site admin permissions
    MANAGE_INSTITUTIONS = "manage_institutions"
    MANAGE_SITE_USERS = "manage_site_users"
    MANAGE_USERS = "manage_users"  # General user management
    VIEW_ALL_DATA = "view_all_data"
    IMPORT_DATA = "import_data"  # Import data from files
    EXPORT_DATA = "export_data"  # Export data to files

    # Institution admin permissions
    MANAGE_INSTITUTION_USERS = "manage_institution_users"
    MANAGE_PROGRAMS = "manage_programs"
    MANAGE_TERMS = "manage_terms"  # Create and manage terms
    VIEW_INSTITUTION_DATA = "view_institution_data"

    # Program admin permissions
    MANAGE_PROGRAM_USERS = "manage_program_users"
    MANAGE_COURSES = "manage_courses"
    VIEW_PROGRAM_DATA = "view_program_data"

    # Instructor permissions
    MANAGE_SECTIONS = "manage_sections"
    VIEW_SECTION_DATA = "view_section_data"
    SUBMIT_ASSESSMENTS = "submit_assessments"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    UserRole.SITE_ADMIN.value: [
        Permission.MANAGE_INSTITUTIONS.value,
        Permission.MANAGE_SITE_USERS.value,
        Permission.MANAGE_USERS.value,
        Permission.VIEW_ALL_DATA.value,
        Permission.IMPORT_DATA.value,
        Permission.EXPORT_DATA.value,
        Permission.MANAGE_INSTITUTION_USERS.value,
        Permission.MANAGE_PROGRAMS.value,
        Permission.MANAGE_TERMS.value,
        Permission.VIEW_INSTITUTION_DATA.value,
        Permission.MANAGE_PROGRAM_USERS.value,
        Permission.MANAGE_COURSES.value,
        Permission.VIEW_PROGRAM_DATA.value,
        Permission.MANAGE_SECTIONS.value,
        Permission.VIEW_SECTION_DATA.value,
        Permission.SUBMIT_ASSESSMENTS.value,
    ],
    UserRole.INSTITUTION_ADMIN.value: [
        Permission.MANAGE_INSTITUTION_USERS.value,
        Permission.MANAGE_USERS.value,  # Can manage users within their institution
        Permission.IMPORT_DATA.value,  # Can import data for their institution
        Permission.EXPORT_DATA.value,  # Can export data for their institution
        Permission.MANAGE_PROGRAMS.value,
        Permission.MANAGE_TERMS.value,  # Can manage terms for their institution
        Permission.VIEW_INSTITUTION_DATA.value,
        Permission.MANAGE_PROGRAM_USERS.value,
        Permission.MANAGE_COURSES.value,
        Permission.VIEW_PROGRAM_DATA.value,
        Permission.MANAGE_SECTIONS.value,
        Permission.VIEW_SECTION_DATA.value,
        Permission.SUBMIT_ASSESSMENTS.value,
    ],
    UserRole.PROGRAM_ADMIN.value: [
        Permission.MANAGE_PROGRAM_USERS.value,
        Permission.MANAGE_COURSES.value,
        Permission.VIEW_PROGRAM_DATA.value,
        Permission.MANAGE_SECTIONS.value,
        Permission.VIEW_SECTION_DATA.value,
        Permission.SUBMIT_ASSESSMENTS.value,
    ],
    UserRole.INSTRUCTOR.value: [
        Permission.MANAGE_SECTIONS.value,
        Permission.VIEW_SECTION_DATA.value,
        Permission.SUBMIT_ASSESSMENTS.value,
    ],
}


class AuthService:
    """Service class for handling authentication and authorization operations"""

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get the current authenticated user from session.
        Returns None if no user is authenticated.
        """
        # Use session-based authentication
        try:
            return self._get_session_user()
        except RuntimeError:
            # Outside of application context (e.g., in standalone tests)
            # Default to mock user behavior for backward compatibility
            return self._get_mock_user()

    def _get_session_user(self) -> Optional[Dict[str, Any]]:
        """Session-based authentication"""
        from session import SessionService

        if not SessionService.is_user_logged_in():
            return None

        return SessionService.get_current_user()

    def _get_mock_user(self) -> Optional[Dict[str, Any]]:
        """Mock user for development and testing"""
        from flask import session

        base_user = {
            "user_id": "dev-admin-123",
            "email": "admin@cei.edu",
            "role": "site_admin",
            "first_name": "Dev",
            "last_name": "Admin",
            "department": "IT",
            "institution_id": "inst-123",
            "primary_institution_id": "inst-123",
            "accessible_institutions": ["inst-123"],
            "program_ids": [
                "prog-123",
                "prog-456",
                "prog-789",
            ],  # Populated for context switching
        }

        # Override with session data when available (for test compatibility)
        try:
            # Check if we have test session data - use it to override defaults
            session_user_id = session.get("user_id")
            if session_user_id:
                # Use session data when available (makes tests work in both mock and real mode)
                session_overrides = {
                    "user_id": session.get("user_id", base_user["user_id"]),
                    "email": session.get("email", base_user["email"]),
                    "role": session.get("role", base_user["role"]),
                    "first_name": session.get("first_name", base_user["first_name"]),
                    "last_name": session.get("last_name", base_user["last_name"]),
                    "institution_id": session.get(
                        "institution_id", base_user["institution_id"]
                    ),
                }
                base_user.update(session_overrides)

            # Add current program context from session if available
            current_program_id = session.get("current_program_id")
            if current_program_id:
                base_user["current_program_id"] = current_program_id
        except RuntimeError:
            # Outside of application context (e.g., in tests)
            pass

        return base_user

    def has_permission(
        self, required_permission: str, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if current user has a specific permission.

        Args:
            required_permission: Permission string to check
            context: Optional context for scoped permissions (e.g., program_id, institution_id)

        Returns:
            True if user has permission, False otherwise
        """
        user = self.get_current_user()
        if not user:
            logger.warning("Permission check failed: No authenticated user")
            return False

        user_role = user.get("role")
        if not user_role:
            logger.warning(
                f"Permission check failed: User {user.get('user_id')} has no role"
            )
            return False

        # Check if user's role grants the required permission
        role_permissions = ROLE_PERMISSIONS.get(user_role, [])
        has_base_permission = required_permission in role_permissions

        if not has_base_permission:
            logger.info(
                f"Permission denied: User {user.get('user_id')} with role {user_role} lacks permission {required_permission}"
            )
            return False

        # Apply context-based scoping for program_admin and institution_admin
        if context and user_role in [
            UserRole.PROGRAM_ADMIN.value,
            UserRole.INSTITUTION_ADMIN.value,
        ]:
            return self._check_scoped_permission(user, required_permission, context)

        logger.debug(
            f"Permission granted: User {user.get('user_id')} has permission {required_permission}"
        )
        return True

    def _check_scoped_permission(
        self, user: Dict[str, Any], permission: str, context: Dict[str, Any]
    ) -> bool:
        """
        Check scoped permissions for program_admin and institution_admin roles.

        Args:
            user: Current user data
            permission: Permission being checked
            context: Context with institution_id, program_id, etc.

        Returns:
            True if user has permission in the given context
        """
        user_role = user.get("role")

        # Institution admin: can access their institution's data
        if user_role == UserRole.INSTITUTION_ADMIN.value:
            required_institution = context.get("institution_id")
            if required_institution and required_institution != user.get(
                "institution_id"
            ):
                logger.info(
                    f"Scoped permission denied: Institution admin {user.get('user_id')} cannot access institution {required_institution}"
                )
                return False

        # Program admin: can access their programs' data
        elif user_role == UserRole.PROGRAM_ADMIN.value:
            required_program = context.get("program_id")
            required_institution = context.get("institution_id")

            # Must be in same institution
            if required_institution and required_institution != user.get(
                "institution_id"
            ):
                logger.info(
                    f"Scoped permission denied: Program admin {user.get('user_id')} cannot access institution {required_institution}"
                )
                return False

            # Must have access to the specific program (if specified)
            if required_program:
                accessible_programs = user.get("program_ids", [])
                if required_program not in accessible_programs:
                    logger.info(
                        f"Scoped permission denied: Program admin {user.get('user_id')} cannot access program {required_program}"
                    )
                    return False

        return True

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        user = self.get_current_user()
        return user is not None

    def has_role(self, required_role: str) -> bool:
        """
        Check if current user has a specific role or higher.

        Args:
            required_role: Minimum role required

        Returns:
            True if user has the role or higher privilege
        """
        user = self.get_current_user()
        if not user:
            return False

        user_role = user.get("role")
        return UserRole.has_role_or_higher(user_role, required_role)

    def get_accessible_institutions(self) -> List[str]:
        """Get list of institution IDs the current user can access."""
        user = self.get_current_user()
        if not user:
            return []

        user_role = user.get("role")

        # Site admin can access all institutions
        if user_role == UserRole.SITE_ADMIN.value:
            # TODO: Return all institution IDs from database
            return ["inst-123", "inst-456"]  # Mock data

        # Other roles can only access their institution
        return user.get("accessible_institutions", [])

    def get_accessible_programs(
        self, institution_id: Optional[str] = None
    ) -> List[str]:
        """Get list of program IDs the current user can access."""
        user = self.get_current_user()
        if not user:
            return []

        user_role = user.get("role")

        # Site admin and institution admin can access all programs in their scope
        if user_role in [UserRole.SITE_ADMIN.value, UserRole.INSTITUTION_ADMIN.value]:
            # TODO: Return programs from database based on institution scope
            # For now, use institution_id if provided for future database filtering
            _ = institution_id  # Acknowledge parameter for future use
            return ["prog-123", "prog-456"]  # Mock data

        # Program admin can only access their specific programs
        elif user_role == UserRole.PROGRAM_ADMIN.value:
            return user.get("program_ids", [])

        return []


# Global auth service instance
auth_service = AuthService()


# Authentication and Authorization Decorators
def login_required(f):
    """Decorator to require authentication with smart response handling."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not auth_service.is_authenticated():
            logger.warning(f"Unauthorized access attempt to {f.__name__}")

            # Detect if this is an API request or web page request
            from flask import redirect, request, url_for

            # Detect AJAX/programmatic requests vs browser requests
            # AJAX requests should get JSON responses
            # Browser requests (even to /api/ URLs) should redirect to login
            is_ajax_request = (
                request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or request.headers.get("Content-Type") == "application/json"
                or (
                    request.headers.get("Accept", "").startswith("application/json")
                    and "text/html" not in request.headers.get("Accept", "")
                )
                or request.path.startswith(
                    "/api/"
                )  # All API endpoints should return JSON
            )

            if is_ajax_request:
                # Return JSON response for AJAX requests
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Authentication required",
                            "error_code": "AUTH_REQUIRED",
                        }
                    ),
                    401,
                )
            else:
                # Redirect to login page for browser requests (including /api/ URLs)
                return redirect(url_for("api.login_api"))

        return f(*args, **kwargs)

    return decorated_function


def role_required(required_role: str):
    """Decorator to require a specific role or higher."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not auth_service.is_authenticated():
                logger.warning(f"Unauthorized access attempt to {f.__name__}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Authentication required",
                            "error_code": "AUTH_REQUIRED",
                        }
                    ),
                    401,
                )

            if not auth_service.has_role(required_role):
                user = auth_service.get_current_user()
                logger.warning(
                    f"Insufficient role: User {user.get('user_id')} with role {user.get('role')} attempted to access {f.__name__} requiring {required_role}"
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Insufficient privileges",
                            "error_code": "INSUFFICIENT_ROLE",
                            "required_role": required_role,
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def permission_required(
    required_permission: str, context_keys: Optional[List[str]] = None
):
    """
    Decorator to require a specific permission.

    Args:
        required_permission: Permission string required
        context_keys: List of request parameter keys to extract for context (e.g., ['institution_id', 'program_id'])
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not auth_service.is_authenticated():
                logger.warning(f"Unauthorized access attempt to {f.__name__}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Authentication required",
                            "error_code": "AUTH_REQUIRED",
                        }
                    ),
                    401,
                )

            # Build context from request parameters if specified
            context = {}
            if context_keys:
                # Check URL parameters, JSON body, and form data
                for key in context_keys:
                    value = None
                    # Try URL parameters first
                    if hasattr(request, "view_args") and request.view_args:
                        value = request.view_args.get(key)
                    # Try JSON body
                    if not value and request.is_json:
                        value = request.json.get(key)
                    # Try form data
                    if not value and request.form:
                        value = request.form.get(key)
                    # Try query parameters
                    if not value:
                        value = request.args.get(key)

                    if value:
                        context[key] = value

            if not auth_service.has_permission(required_permission, context):
                user = auth_service.get_current_user()
                logger.warning(
                    f"Permission denied: User {user.get('user_id')} attempted to access {f.__name__} requiring {required_permission}"
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Permission denied",
                            "error_code": "PERMISSION_DENIED",
                            "required_permission": required_permission,
                        }
                    ),
                    403,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    """Decorator to require site admin role."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        return role_required(UserRole.SITE_ADMIN.value)(f)(*args, **kwargs)

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


def get_current_institution_id() -> Optional[str]:
    """Get current user's active institution ID (convenience function)."""
    user = get_current_user()
    if user:
        # Get institution from user context
        institution_id = user.get("institution_id") or user.get(
            "primary_institution_id"
        )
        if institution_id:
            return institution_id

    logger.warning("No institution context available for current user")
    return None


def get_current_program_id() -> Optional[str]:
    """Get current user's active program ID (for program-scoped operations)."""
    user = get_current_user()
    if user:
        # Get current program from session context
        return user.get("current_program_id")
    return None


def set_current_program_id(program_id: str) -> bool:
    """Set current user's active program context (for program switching)."""
    try:
        from flask import session

        user = get_current_user()
        if not user:
            return False

        # Verify user has access to this program
        accessible_programs = user.get("program_ids", [])
        if program_id not in accessible_programs:
            logger.warning(
                f"User {user.get('user_id')} attempted to switch to unauthorized program {program_id}"
            )
            return False

        # Update session context
        session["current_program_id"] = program_id
        logger.info(
            f"User {user.get('user_id')} switched to program context: {program_id}"
        )
        return True

    except Exception as e:
        logger.error(f"Error setting current program ID: {e}")
        return False


def clear_current_program_id() -> bool:
    """Clear current user's active program context (return to institution-wide view)."""
    try:
        from flask import session

        user = get_current_user()
        if not user:
            return False

        # Remove program context from session
        session.pop("current_program_id", None)
        logger.info(f"User {user.get('user_id')} cleared program context")
        return True

    except Exception as e:
        logger.error(f"Error clearing current program ID: {e}")
        return False


def has_role(required_role: str) -> bool:
    """Check if current user has role or higher (convenience function)."""
    return auth_service.has_role(required_role)


def get_accessible_institutions() -> List[str]:
    """Get list of institutions current user can access."""
    return auth_service.get_accessible_institutions()


def get_accessible_programs(institution_id: Optional[str] = None) -> List[str]:
    """Get list of programs current user can access."""
    return auth_service.get_accessible_programs(institution_id)


def can_access_institution(institution_id: str) -> bool:
    """Check if current user can access a specific institution."""
    accessible = get_accessible_institutions()
    return institution_id in accessible


def can_access_program(program_id: str, institution_id: Optional[str] = None) -> bool:
    """Check if current user can access a specific program."""
    # First check institution access if specified
    if institution_id and not can_access_institution(institution_id):
        return False

    accessible = get_accessible_programs(institution_id)
    return program_id in accessible


def require_program_access(
    program_id: str, institution_id: Optional[str] = None
) -> Optional[tuple]:
    """
    Check program access and return error response if denied.

    Returns:
        None if access is allowed, error response tuple if denied
    """
    if not can_access_program(program_id, institution_id):
        user = get_current_user()
        logger.warning(
            f"Program access denied: User {user.get('user_id') if user else 'unknown'} cannot access program {program_id}"
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Program access denied",
                    "error_code": "PROGRAM_ACCESS_DENIED",
                    "program_id": program_id,
                }
            ),
            403,
        )
    return None
