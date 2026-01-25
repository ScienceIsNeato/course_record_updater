"""Users API routes for user management including CRUD, role management, and deactivation."""
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import (
    InstitutionContextMissingError, handle_api_error, resolve_institution_scope,
)
from src.database.database_service import (
    deactivate_user, delete_user, get_all_users, get_user_by_id,
    get_users_by_role, update_user, update_user_profile, update_user_role,
)
from src.database.database_service import create_user as create_user_db
from src.services.auth_service import (
    get_current_institution_id, get_current_user, has_permission,
    login_required, permission_required,
)
from src.utils.constants import (
    INSTITUTION_CONTEXT_REQUIRED_MSG, NO_DATA_PROVIDED_MSG, NO_JSON_DATA_PROVIDED_MSG,
    PERMISSION_DENIED_MSG, USER_NOT_FOUND_MSG,
)
from src.utils.logging_config import get_logger

users_bp = Blueprint("users", __name__, url_prefix="/api")
logger = get_logger(__name__)


def _get_current_user_safe() -> Dict[str, Any]:
    """Get current user, return empty dict if None (for type safety)."""
    return get_current_user() or {}

def _get_current_institution_id_safe() -> str:
    """Get current institution ID, return empty string if None."""
    return get_current_institution_id() or ""

def _resolve_users_scope() -> Tuple[Dict[str, Any], List[str], bool]:
    """Resolve institution scope for user listing."""
    try:
        return resolve_institution_scope(require=True)
    except InstitutionContextMissingError:
        raise ValueError(INSTITUTION_CONTEXT_REQUIRED_MSG)


def _get_users_by_scope(
    is_global: bool, institution_ids: List[str], role_filter: Optional[str]
) -> List[Dict[str, Any]]:
    """Get users based on scope (global vs institution) and role filter."""
    if is_global:
        if role_filter:
            users = get_users_by_role(role_filter)
            if institution_ids:
                users = [u for u in users if not u.get("institution_id")
                         or u.get("institution_id") in institution_ids]
            return users
        users = []
        for inst_id in institution_ids:
            users.extend(get_all_users(inst_id))
        return users
    # Single institution scope
    if role_filter:
        return [u for u in get_users_by_role(role_filter)
                if u.get("institution_id") == institution_ids[0]]
    return get_all_users(institution_ids[0])


def _validate_user_creation_permissions(
    current_user: Dict[str, Any], data: Dict[str, Any]
) -> Tuple[bool, Optional[Tuple[Any, int]]]:
    """Validate current user can create target user role. Returns (is_valid, error_response)."""
    current_role = current_user.get("role")
    target_role = data.get("role")

    if current_role == "program_admin":
        if target_role != "instructor":
            return False, (jsonify({"success": False,
                "error": "Program admins can only create instructor accounts"}), 403)
        target_inst = data.get("institution_id")
        if not target_inst:
            return False, (jsonify({"success": False, "error": "institution_id is required"}), 400)
        if target_inst != current_user.get("institution_id"):
            return False, (jsonify({"success": False,
                "error": "Program admins can only create users at their own institution"}), 403)

    if current_role == "institution_admin" and target_role == "site_admin":
        return False, (jsonify({"success": False,
            "error": "Institution admins cannot create site admin accounts"}), 403)

    return True, None


@users_bp.route("/me", methods=["GET"])
def get_current_user_info() -> ResponseReturnValue:
    """Get current authenticated user's information including program_ids for RBAC."""
    try:
        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Not authenticated"}), 401
        return jsonify({
            "success": True, "user_id": current_user["user_id"],
            "email": current_user["email"], "first_name": current_user.get("first_name"),
            "last_name": current_user.get("last_name"), "role": current_user["role"],
            "institution_id": current_user.get("institution_id"),
            "program_ids": current_user.get("program_ids", []),
        })
    except Exception as e:
        return handle_api_error(e, "Get current user", "Failed to get user information")


@users_bp.route("/users", methods=["GET"])
@permission_required("view_institution_data")
def list_users() -> ResponseReturnValue:
    """Get list of users, optionally filtered by role or department (read-only)."""
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
    """Create a new user. Requires email, first_name, last_name, role."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        required_fields = ["email", "first_name", "last_name", "role"]
        for field in required_fields:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({"success": False,
                    "error": f"{field.replace('_', ' ').title()} is required"}), 400

        current_user = _get_current_user_safe()
        is_valid, error_response = _validate_user_creation_permissions(current_user, data)
        if not is_valid and error_response:
            return error_response

        from src.models.models import User
        from src.services.password_service import hash_password

        password_hash = hash_password(data["password"]) if data.get("password") else None
        user_schema = User.create_schema(
            email=data["email"], first_name=data["first_name"], last_name=data["last_name"],
            role=data["role"], institution_id=data.get("institution_id"),
            password_hash=password_hash, account_status=data.get("account_status", "active"),
            program_ids=data.get("program_ids", []), display_name=data.get("display_name"),
        )
        if data.get("email_verified", False):
            user_schema["email_verified"] = True

        user_id = create_user_db(user_schema)
        if user_id:
            return jsonify({"success": True, "user_id": user_id,
                "message": "User created successfully"}), 201
        return jsonify({"success": False, "error": "Failed to create user"}), 500
    except Exception as e:
        return handle_api_error(e, "Create user", "Failed to create user")


@users_bp.route("/users/<user_id>", methods=["GET"])
@login_required
def get_user_api(user_id: str) -> ResponseReturnValue:
    """Get user details by ID. Users can view own details or need manage_users permission."""
    try:
        current_user = _get_current_user_safe()
        if user_id != current_user["user_id"] and not has_permission("manage_users"):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403
        user = get_user_by_id(user_id)
        if user:
            return jsonify({"success": True, "user": user})
        return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404
    except Exception as e:
        return handle_api_error(e, "Get user by ID", "Failed to retrieve user")


@users_bp.route("/users/<user_id>", methods=["PUT"])
@permission_required("manage_users")
def update_user_api(user_id: str) -> ResponseReturnValue:
    """Update user details (first_name, last_name, role, account_status)."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400
        if not get_user_by_id(user_id):
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404
        for field in ["first_name", "last_name"]:
            if field in data and not str(data.get(field)).strip():
                return jsonify({"success": False,
                    "error": f"{field.replace('_', ' ').title()} cannot be empty"}), 400
        if update_user(user_id, data):
            return jsonify({"success": True, "user": get_user_by_id(user_id),
                "message": "User updated successfully"})
        return jsonify({"success": False, "error": "Failed to update user"}), 500
    except Exception as e:
        return handle_api_error(e, "Update user", "Failed to update user")


@users_bp.route("/users/<user_id>/profile", methods=["PATCH"])
@login_required
def update_user_profile_endpoint(user_id: str) -> ResponseReturnValue:
    """Update user profile (self-service or admin with manage_users permission)."""
    try:
        current_user = _get_current_user_safe()
        if current_user["user_id"] != user_id and not has_permission("manage_users"):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400
        for field in ["first_name", "last_name"]:
            if field in data and not str(data.get(field)).strip():
                return jsonify({"success": False,
                    "error": f"{field.replace('_', ' ').title()} cannot be empty"}), 400
        if update_user_profile(user_id, data):
            return jsonify({"success": True, "user": get_user_by_id(user_id),
                "message": "Profile updated successfully"}), 200
        return jsonify({"success": False, "error": "Failed to update profile"}), 500
    except Exception as e:
        return handle_api_error(e, "Update user profile", "Failed to update user profile")


@users_bp.route("/users/<user_id>/role", methods=["PATCH"])
@permission_required("manage_users")
def update_user_role_endpoint(user_id: str) -> ResponseReturnValue:
    """Update a user's role (admin only). Role must be instructor/program_admin/institution_admin."""
    try:
        data = request.get_json(silent=True) or {}
        if not data or "role" not in data:
            return jsonify({"success": False, "error": "Role is required"}), 400
        new_role = data["role"]
        valid_roles = ["instructor", "program_admin", "institution_admin"]
        if new_role not in valid_roles:
            return jsonify({"success": False,
                "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}), 400
        user = get_user_by_id(user_id)
        if not user or user.get("institution_id") != _get_current_institution_id_safe():
            return jsonify({"success": False, "error": "User not found"}), 404
        if update_user_role(user_id, new_role, program_ids=None):
            return jsonify({"success": True, "user": get_user_by_id(user_id),
                "message": f"User role updated to {new_role}"}), 200
        return jsonify({"success": False, "error": "Failed to update role"}), 500
    except Exception as e:
        return handle_api_error(e, "Update user role", "Failed to update user role")


@users_bp.route("/users/<user_id>/deactivate", methods=["POST"])
@permission_required("manage_users")
def deactivate_user_endpoint(user_id: str) -> ResponseReturnValue:
    """Deactivate (soft delete) a user account. Sets account_status to 'suspended'."""
    try:
        if not get_user_by_id(user_id):
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404
        if deactivate_user(user_id):
            return jsonify({"success": True, "message": "User deactivated successfully"}), 200
        return jsonify({"success": False, "error": "Failed to deactivate user"}), 500
    except Exception as e:
        return handle_api_error(e, "Deactivate user", "Failed to deactivate user")


@users_bp.route("/users/<user_id>", methods=["DELETE"])
@permission_required("manage_users")
def delete_user_endpoint(user_id: str) -> ResponseReturnValue:
    """Delete user (hard delete - permanent removal). Consider deactivate for soft delete."""
    try:
        current_user = _get_current_user_safe()
        if current_user["user_id"] == user_id:
            return jsonify({"success": False, "error": "Cannot delete your own account"}), 400
        if not get_user_by_id(user_id):
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404
        if delete_user(user_id):
            return jsonify({"success": True, "message": "User deleted successfully"}), 200
        return jsonify({"success": False, "error": "Failed to delete user"}), 500
    except Exception as e:
        return handle_api_error(e, "Delete user", "Failed to delete user")
