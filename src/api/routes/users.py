"""User Management API Routes for user CRUD operations and instructor listing."""

from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import (
    InstitutionContextMissingError,
    get_current_institution_id_safe,
    get_current_user_safe,
    handle_api_error,
    resolve_institution_scope,
)
from src.database.database_service import create_user as create_user_db
from src.database.database_service import (
    deactivate_user,
    delete_user,
    get_all_instructors,
    get_all_users,
    get_user_by_id,
    get_users_by_role,
    update_user,
    update_user_profile,
    update_user_role,
)
from src.services.auth_service import (
    UserRole,
    has_permission,
    login_required,
    permission_required,
)
from src.utils.constants import (
    INSTITUTION_CONTEXT_REQUIRED_MSG,
    NO_DATA_PROVIDED_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    PERMISSION_DENIED_MSG,
    USER_NOT_FOUND_MSG,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

users_bp = Blueprint("users", __name__, url_prefix="/api")


def _resolve_users_scope() -> Tuple[Dict[str, Any], List[str], bool]:
    """Resolve institution scope for user listing."""
    try:
        return resolve_institution_scope()
    except InstitutionContextMissingError:
        raise ValueError(INSTITUTION_CONTEXT_REQUIRED_MSG)


def _get_users_by_scope(
    is_global: bool, institution_ids: List[str], role_filter: Optional[str]
) -> List[Dict[str, Any]]:
    """Get users based on scope and role filter."""
    if is_global:
        return _get_global_users(institution_ids, role_filter)
    else:
        return _get_institution_users(institution_ids[0], role_filter)


def _get_global_users(
    institution_ids: List[str], role_filter: Optional[str]
) -> List[Dict[str, Any]]:
    """Get users for global scope with optional role filtering."""
    if role_filter:
        users = get_users_by_role(role_filter)
        if institution_ids:
            users = [
                u
                for u in users
                if not u.get("institution_id")
                or u.get("institution_id") in institution_ids
            ]
        return users
    else:
        users = []
        for inst_id in institution_ids:
            users.extend(get_all_users(inst_id))
        return users


def _get_institution_users(
    institution_id: str, role_filter: Optional[str]
) -> List[Dict[str, Any]]:
    """Get users for a single institution with optional role filtering."""
    if role_filter:
        return [
            u
            for u in get_users_by_role(role_filter)
            if u.get("institution_id") == institution_id
        ]
    else:
        return get_all_users(institution_id)


def _permission_error(msg: str, code: int = 403) -> Tuple[Any, int]:
    """Return a JSON error response tuple."""
    return jsonify({"success": False, "error": msg}), code


def _validate_user_creation_permissions(
    current_user: Dict[str, Any], data: Dict[str, Any]
) -> Tuple[bool, Optional[Tuple[Any, int]]]:
    """Validate that current user can create target user role."""
    current_role = current_user.get("role")
    target_role = data.get("role")

    if current_role == "program_admin" and target_role != "instructor":
        return False, _permission_error(
            "Program admins can only create instructor accounts"
        )

    if current_role == "program_admin":
        target_institution_id = data.get("institution_id")
        if not target_institution_id:
            return False, _permission_error("institution_id is required", 400)
        if target_institution_id != current_user.get("institution_id"):
            return False, _permission_error(
                "Program admins can only create users at their own institution"
            )

    if current_role == "institution_admin" and target_role == "site_admin":
        return False, _permission_error(
            "Institution admins cannot create site admin accounts"
        )

    return True, None


@users_bp.route("/users", methods=["GET"])
@permission_required("view_institution_data")
def list_users() -> ResponseReturnValue:
    """Get list of users, optionally filtered by role and department."""
    try:
        _, institution_ids, is_global = _resolve_users_scope()

        role_filter = request.args.get("role")
        department_filter = request.args.get("department")

        users = _get_users_by_scope(is_global, institution_ids, role_filter)

        if department_filter and users:
            users = [u for u in users if u.get("department") == department_filter]

        return jsonify({"success": True, "users": users, "count": len(users)})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return handle_api_error(e, "Get users", "Failed to retrieve users")


@users_bp.route("/users", methods=["POST"])
@permission_required("manage_users")
def create_user() -> ResponseReturnValue:
    """Create a new user with role-based authorization checks."""
    try:
        data = request.get_json(silent=True) or {}

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        required_fields = ["email", "first_name", "last_name", "role"]

        for field in required_fields:
            if not data.get(field) or not str(data.get(field)).strip():
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"{field.replace('_', ' ').title()} is required",
                        }
                    ),
                    400,
                )

        current_user = get_current_user_safe()
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        if not is_valid and error_response:
            return error_response

        from src.models.models import User
        from src.services.password_service import hash_password

        password_hash = None
        if data.get("password"):
            password_hash = hash_password(data["password"])

        user_schema = User.create_schema(
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=data["role"],
            institution_id=data.get("institution_id"),
            password_hash=password_hash,
            account_status=data.get("account_status", "active"),
            program_ids=data.get("program_ids", []),
            display_name=data.get("display_name"),
        )

        if data.get("email_verified", False):
            user_schema["email_verified"] = True

        user_id = create_user_db(user_schema)

        if user_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "user_id": user_id,
                        "message": "User created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create user"}), 500

    except Exception as e:
        return handle_api_error(e, "Create user", "Failed to create user")


@users_bp.route("/users/<user_id>", methods=["GET"])
@login_required
def get_user_api(user_id: str) -> ResponseReturnValue:
    """Get user details by ID (own details or admin access)."""
    try:
        current_user = get_current_user_safe()

        if user_id != current_user["user_id"] and not has_permission("manage_users"):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        user = get_user_by_id(user_id)

        if user:
            return jsonify({"success": True, "user": user})
        else:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404

    except Exception as e:
        return handle_api_error(e, "Get user by ID", "Failed to retrieve user")


@users_bp.route("/users/<user_id>", methods=["PUT"])
@permission_required("manage_users")
def update_user_api(user_id: str) -> ResponseReturnValue:
    """Update user details."""
    try:
        data = request.get_json(silent=True) or {}

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        existing_user = get_user_by_id(user_id)
        if not existing_user:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404

        for field in ["first_name", "last_name"]:
            if field in data and not str(data.get(field)).strip():
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"{field.replace('_', ' ').title()} cannot be empty",
                        }
                    ),
                    400,
                )

        success = update_user(user_id, data)

        if success:
            updated_user = get_user_by_id(user_id)
            return jsonify(
                {
                    "success": True,
                    "user": updated_user,
                    "message": "User updated successfully",
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to update user"}), 500

    except Exception as e:
        return handle_api_error(e, "Update user", "Failed to update user")


@users_bp.route("/users/<user_id>/profile", methods=["PATCH"])
@login_required
def update_user_profile_endpoint(user_id: str) -> ResponseReturnValue:
    """Update user profile (self-service or admin)."""
    try:
        current_user = get_current_user_safe()

        if current_user["user_id"] != user_id and not has_permission("manage_users"):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        for field in ["first_name", "last_name"]:
            if field in data and not str(data.get(field)).strip():
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"{field.replace('_', ' ').title()} cannot be empty",
                        }
                    ),
                    400,
                )

        success = update_user_profile(user_id, data)

        if success:
            updated_user = get_user_by_id(user_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "user": updated_user,
                        "message": "Profile updated successfully",
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to update profile"}), 500

    except Exception as e:
        return handle_api_error(
            e, "Update user profile", "Failed to update user profile"
        )


@users_bp.route("/users/<user_id>/role", methods=["PATCH"])
@permission_required("manage_users")
def update_user_role_endpoint(user_id: str) -> ResponseReturnValue:
    """Update a user's role (admin only)."""
    try:
        data = request.get_json(silent=True) or {}
        if not data or "role" not in data:
            return jsonify({"success": False, "error": "Role is required"}), 400

        new_role = data["role"]
        valid_roles = ["instructor", "program_admin", "institution_admin"]

        if new_role not in valid_roles:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                    }
                ),
                400,
            )

        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        current_institution_id = get_current_institution_id_safe()
        if user.get("institution_id") != current_institution_id:
            return jsonify({"success": False, "error": "User not found"}), 404

        success = update_user_role(user_id, new_role, program_ids=None)

        if success:
            updated_user = get_user_by_id(user_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "user": updated_user,
                        "message": f"User role updated to {new_role}",
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to update role"}), 500

    except Exception as e:
        return handle_api_error(e, "Update user role", "Failed to update user role")


@users_bp.route("/users/<user_id>/deactivate", methods=["POST"])
@permission_required("manage_users")
def deactivate_user_endpoint(user_id: str) -> ResponseReturnValue:
    """Deactivate (soft delete) a user account."""
    try:
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404

        success = deactivate_user(user_id)

        if success:
            return (
                jsonify({"success": True, "message": "User deactivated successfully"}),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to deactivate user"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Deactivate user", "Failed to deactivate user")


@users_bp.route("/users/<user_id>", methods=["DELETE"])
@permission_required("manage_users")
def delete_user_endpoint(user_id: str) -> ResponseReturnValue:
    """Delete user permanently (hard delete)."""
    try:
        current_user = get_current_user_safe()

        if current_user["user_id"] == user_id:
            return (
                jsonify({"success": False, "error": "Cannot delete your own account"}),
                400,
            )

        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404

        success = delete_user(user_id)

        if success:
            return (
                jsonify({"success": True, "message": "User deleted successfully"}),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to delete user"}), 500

    except Exception as e:
        return handle_api_error(e, "Delete user", "Failed to delete user")


@users_bp.route("/instructors", methods=["GET"])
@permission_required("view_program_data")
def list_instructors() -> ResponseReturnValue:
    """Get list of instructors, scoped by role permissions."""
    try:
        try:
            _, institution_ids, is_global = resolve_institution_scope()
        except InstitutionContextMissingError:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        if is_global:
            instructors: List[Dict[str, Any]] = []
            for inst_id in institution_ids:
                instructors.extend(get_all_instructors(inst_id))
        else:
            instructors = get_all_instructors(institution_ids[0])

        current_user = get_current_user_safe()
        if current_user and current_user.get("role") == UserRole.PROGRAM_ADMIN.value:
            user_program_ids = current_user.get("program_ids", [])
            if user_program_ids:
                instructors = [
                    instructor
                    for instructor in instructors
                    if any(
                        pid in user_program_ids
                        for pid in instructor.get("program_ids", [])
                    )
                ]

        return jsonify(
            {"success": True, "instructors": instructors, "count": len(instructors)}
        )

    except Exception as e:
        return handle_api_error(e, "Get instructors", "Failed to retrieve instructors")
