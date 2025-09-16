"""
API Routes Module

This module defines the new REST API endpoints for the CEI Course Management System.
These routes provide a proper REST API structure while maintaining backward compatibility
with the existing single-page application.
"""

import traceback

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

# Import our services
from auth_service import (
    get_current_institution_id,
    get_current_user,
    has_permission,
    login_required,
    permission_required,
)
from database_service import (
    add_course_to_program,
    bulk_add_courses_to_program,
    bulk_remove_courses_from_program,
    create_course,
    create_course_section,
    create_new_institution,
    create_program,
    create_term,
    delete_program,
    get_active_terms,
    get_all_courses,
    get_all_institutions,
    get_all_instructors,
    get_all_sections,
    get_course_by_number,
    get_courses_by_department,
    get_courses_by_program,
    get_institution_by_id,
    get_institution_instructor_count,
    get_program_by_id,
    get_programs_by_institution,
    get_sections_by_instructor,
    get_sections_by_term,
    get_users_by_role,
    remove_course_from_program,
    update_program,
)
from import_service import import_excel
from logging_config import get_logger
from models import Program
from registration_service import (
    RegistrationError,
    get_registration_status,
    register_institution_admin,
    resend_verification_email,
    verify_email,
)

# Create API blueprint
api = Blueprint("api", __name__, url_prefix="/api")

# Get logger for this module
logger = get_logger(__name__)


def handle_api_error(
    e, operation_name="API operation", user_message="An error occurred"
):
    """
    Securely handle API errors by logging full details while returning sanitized responses.

    Args:
        e: The exception that occurred
        operation_name: Description of what operation failed (for logging)
        user_message: Safe message to return to the user

    Returns:
        tuple: (JSON response, HTTP status code)
    """
    # Log full error details for debugging (includes stack trace)
    logger.error(
        f"{operation_name} failed: {str(e)}\n"
        f"Full traceback:\n{traceback.format_exc()}"
    )

    # Return sanitized response to user
    return jsonify({"success": False, "error": user_message}), 500


# ========================================
# DASHBOARD ROUTES (Role-based views)
# ========================================


@api.route("/dashboard")
@login_required
def dashboard():
    """
    Role-based dashboard - returns different views based on user role
    """
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    role = user["role"]

    if role == "instructor":
        return render_template("dashboard/instructor.html", user=user)
    elif role == "program_admin":
        return render_template("dashboard/program_admin.html", user=user)
    elif role == "site_admin":
        return render_template("dashboard/site_admin.html", user=user)
    else:
        flash("Unknown user role. Please contact administrator.", "danger")
        return redirect(url_for("index"))


# ========================================
# INSTITUTION MANAGEMENT API
# ========================================


@api.route("/institutions", methods=["GET"])
@permission_required("manage_institutions")
def list_institutions():
    """Get list of all institutions (site admin only)"""
    try:
        institutions = get_all_institutions()

        # Add current instructor counts
        for institution in institutions:
            institution["current_instructor_count"] = get_institution_instructor_count(
                institution["institution_id"]
            )

        return jsonify(
            {"success": True, "institutions": institutions, "count": len(institutions)}
        )

    except Exception as e:
        return handle_api_error(
            e, "Get institutions", "Failed to retrieve institutions"
        )


@api.route("/institutions", methods=["POST"])
def create_institution():
    """Create a new institution with its first admin user (public endpoint for registration)"""
    try:
        data = request.get_json()

        # Validate required fields
        required_institution_fields = ["name", "short_name", "domain"]
        required_user_fields = ["email", "first_name", "last_name", "password"]

        institution_data = data.get("institution", {})
        user_data = data.get("admin_user", {})

        # Validate institution data
        for field in required_institution_fields:
            if not institution_data.get(field):
                return (
                    jsonify(
                        {"success": False, "error": f"Institution {field} is required"}
                    ),
                    400,
                )

        # Validate user data
        for field in required_user_fields:
            if not user_data.get(field):
                return (
                    jsonify(
                        {"success": False, "error": f"Admin user {field} is required"}
                    ),
                    400,
                )

        # Create institution and admin user
        result = create_new_institution(institution_data, user_data)
        if not result:
            return (
                jsonify({"success": False, "error": "Failed to create institution"}),
                500,
            )

        institution_id, user_id = result

        return (
            jsonify(
                {
                    "success": True,
                    "institution_id": institution_id,
                    "admin_user_id": user_id,
                    "message": "Institution and admin user created successfully",
                }
            ),
            201,
        )

    except Exception as e:
        return handle_api_error(e, "Create institution", "Failed to create institution")


@api.route("/institutions/<institution_id>", methods=["GET"])
@login_required
def get_institution_details(institution_id: str):
    """Get institution details (users can only view their own institution)"""
    try:
        current_user = get_current_user()

        # Users can only view their own institution unless they're site admin
        if (
            current_user.get("institution_id") != institution_id
            and current_user.get("role") != "site_admin"
        ):
            return jsonify({"success": False, "error": "Access denied"}), 403

        institution = get_institution_by_id(institution_id)
        if not institution:
            return jsonify({"success": False, "error": "Institution not found"}), 404

        # Add current instructor count
        institution["current_instructor_count"] = get_institution_instructor_count(
            institution_id
        )

        return jsonify({"success": True, "institution": institution})

    except Exception as e:
        return handle_api_error(e, "Get institution", "Failed to retrieve institution")


# ========================================
# USER MANAGEMENT API
# ========================================


@api.route("/users", methods=["GET"])
@permission_required("manage_users")
def list_users():
    """
    Get list of users, optionally filtered by role

    Query parameters:
    - role: Filter by user role (optional)
    - department: Filter by department (optional)
    """
    try:
        role_filter = request.args.get("role")
        department_filter = request.args.get("department")

        if role_filter:
            users = get_users_by_role(role_filter)
        else:
            # TODO: Implement get_all_users function
            users = []

        # Filter by department if specified
        if department_filter and users:
            users = [u for u in users if u.get("department") == department_filter]

        return jsonify({"success": True, "users": users, "count": len(users)})

    except Exception as e:
        return handle_api_error(e, "Get users", "Failed to retrieve users")


@api.route("/users", methods=["POST"])
@permission_required("manage_users")
def create_user():
    """
    Create a new user

    Request body should contain:
    - email: User's email address
    - first_name: User's first name
    - last_name: User's last name
    - role: User's role (instructor, program_admin, site_admin)
    - department: User's department (optional)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["email", "first_name", "last_name", "role"]
        missing_fields = [f for f in required_fields if not data.get(f)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Missing required fields: {", ".join(missing_fields)}',
                    }
                ),
                400,
            )

        # TODO: Implement create_user in database_service_extended
        # user_id = create_user(data)
        user_id = "stub-user-id"  # Stub for now

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


@api.route("/users/<user_id>", methods=["GET"])
@login_required
def get_user(user_id: str):
    """
    Get user details by ID

    Users can only view their own details unless they have manage_users permission
    """
    try:
        current_user = get_current_user()

        # Check permissions - users can view their own info, admins can view any
        if user_id != current_user["user_id"] and not has_permission("manage_users"):
            return jsonify({"success": False, "error": "Permission denied"}), 403

        # TODO: Implement get_user_by_id function
        # user = get_user_by_id(user_id)
        user = None  # Stub for now

        if user:
            return jsonify({"success": True, "user": user})
        else:
            return jsonify({"success": False, "error": "User not found"}), 404

    except Exception as e:
        return handle_api_error(e, "Get user by email", "Failed to retrieve user")


# ========================================
# COURSE MANAGEMENT API
# ========================================


@api.route("/courses", methods=["GET"])
@login_required
def list_courses():
    """
    Get list of courses, optionally filtered by department

    Query parameters:
    - department: Filter by department (optional)
    """
    try:
        # Get institution context - for development, use CEI
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        department_filter = request.args.get("department")

        if department_filter:
            courses = get_courses_by_department(institution_id, department_filter)
        else:
            courses = get_all_courses(institution_id)

        return jsonify({"success": True, "courses": courses, "count": len(courses)})

    except Exception as e:
        return handle_api_error(e, "Get courses", "Failed to retrieve courses")


@api.route("/courses", methods=["POST"])
@permission_required("manage_courses")
def create_course_api():
    """
    Create a new course

    Request body should contain:
    - course_number: Course number (e.g., "ACC-201")
    - course_title: Course title
    - department: Department name
    - credit_hours: Number of credit hours (optional, default 3)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["course_number", "course_title", "department"]
        missing_fields = [f for f in required_fields if not data.get(f)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Missing required fields: {", ".join(missing_fields)}',
                    }
                ),
                400,
            )

        course_id = create_course(data)

        if course_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "course_id": course_id,
                        "message": "Course created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create course"}), 500

    except Exception as e:
        return handle_api_error(e, "Create course", "Failed to create course")


@api.route("/courses/<course_number>", methods=["GET"])
@login_required
def get_course(course_number: str):
    """Get course details by course number"""
    try:
        course = get_course_by_number(course_number)

        if course:
            return jsonify({"success": True, "course": course})
        else:
            return jsonify({"success": False, "error": "Course not found"}), 404

    except Exception as e:
        return handle_api_error(e, "Get course by number", "Failed to retrieve course")


# ========================================
# INSTRUCTOR MANAGEMENT API
# ========================================


@api.route("/instructors", methods=["GET"])
@login_required
def list_instructors():
    """Get list of all instructors"""
    try:
        # Get institution context - for development, use CEI
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        instructors = get_all_instructors(institution_id)

        return jsonify(
            {"success": True, "instructors": instructors, "count": len(instructors)}
        )

    except Exception as e:
        return handle_api_error(e, "Get instructors", "Failed to retrieve instructors")


# ========================================
# TERM MANAGEMENT API
# ========================================


@api.route("/terms", methods=["GET"])
@login_required
def list_terms():
    """Get list of active terms"""
    try:
        # Get institution context - for development, use CEI
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        terms = get_active_terms(institution_id)

        return jsonify({"success": True, "terms": terms, "count": len(terms)})

    except Exception as e:
        return handle_api_error(e, "Get terms", "Failed to retrieve terms")


@api.route("/terms", methods=["POST"])
@permission_required("manage_terms")
def create_term_api():
    """
    Create a new academic term

    Request body should contain:
    - name: Term name (e.g., "2024 Fall")
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - assessment_due_date: Assessment due date (YYYY-MM-DD)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["name", "start_date", "end_date", "assessment_due_date"]
        missing_fields = [f for f in required_fields if not data.get(f)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Missing required fields: {", ".join(missing_fields)}',
                    }
                ),
                400,
            )

        term_id = create_term(data)

        if term_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "term_id": term_id,
                        "message": "Term created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create term"}), 500

    except Exception as e:
        return handle_api_error(e, "Create term", "Failed to create term")


# ========================================
# PROGRAM MANAGEMENT API
# ========================================


@api.route("/programs", methods=["GET"])
@login_required
def list_programs():
    """Get list of programs for the current institution"""
    try:
        institution_id = get_current_institution_id()
        if not institution_id:
            return jsonify({"success": False, "error": "Institution ID not found"}), 400

        programs = get_programs_by_institution(institution_id)

        return jsonify({"success": True, "programs": programs})

    except Exception as e:
        return handle_api_error(e, "List programs", "Failed to retrieve programs")


@api.route("/programs", methods=["POST"])
@permission_required("manage_programs")
def create_program_api():
    """Create a new program"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["name", "short_name"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Get current institution and user
        institution_id = get_current_institution_id()
        current_user = get_current_user()

        if not institution_id:
            return jsonify({"success": False, "error": "Institution ID not found"}), 400

        if not current_user:
            return jsonify({"success": False, "error": "User not found"}), 400

        # Create program schema
        program_data = Program.create_schema(
            name=data["name"],
            short_name=data["short_name"],
            institution_id=institution_id,
            created_by=current_user.get("user_id", "unknown"),
            description=data.get("description"),
            is_default=data.get("is_default", False),
            program_admins=data.get("program_admins", []),
        )

        # Create program in database
        program_id = create_program(program_data)

        if program_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "program_id": program_id,
                        "message": "Program created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create program"}), 500

    except Exception as e:
        return handle_api_error(e, "Create program", "Failed to create program")


@api.route("/programs/<program_id>", methods=["GET"])
@login_required
def get_program(program_id: str):
    """Get program details by ID"""
    try:
        program = get_program_by_id(program_id)

        if program:
            return jsonify({"success": True, "program": program})
        else:
            return jsonify({"success": False, "error": "Program not found"}), 404

    except Exception as e:
        return handle_api_error(e, "Get program", "Failed to retrieve program")


@api.route("/programs/<program_id>", methods=["PUT"])
@permission_required("manage_programs")
def update_program_api(program_id: str):
    """Update an existing program"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Validate program exists and user has permission
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": "Program not found"}), 404

        # Update program
        success = update_program(program_id, data)

        if success:
            return jsonify({"success": True, "message": "Program updated successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to update program"}), 500

    except Exception as e:
        return handle_api_error(e, "Update program", "Failed to update program")


@api.route("/programs/<program_id>", methods=["DELETE"])
@permission_required("manage_programs")
def delete_program_api(program_id: str):
    """Delete a program (with course reassignment to default)"""
    try:
        # Validate program exists and user has permission
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": "Program not found"}), 404

        # Prevent deletion of default program
        if program.get("is_default", False):
            return (
                jsonify({"success": False, "error": "Cannot delete default program"}),
                400,
            )

        # Get the default program for reassignment
        institution_id = get_current_institution_id()
        programs = get_programs_by_institution(institution_id)
        default_program = next(
            (p for p in programs if p.get("is_default", False)), None
        )

        if not default_program:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No default program found for course reassignment",
                    }
                ),
                500,
            )

        # Delete program and reassign courses
        success = delete_program(program_id, default_program["id"])

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "Program deleted successfully and courses reassigned",
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to delete program"}), 500

    except Exception as e:
        return handle_api_error(e, "Delete program", "Failed to delete program")


# ========================================
# COURSE-PROGRAM ASSOCIATION API
# ========================================


@api.route("/programs/<program_id>/courses", methods=["GET"])
@login_required
def get_program_courses(program_id: str):
    """Get all courses associated with a program"""
    try:
        # Validate program exists and user has access
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": "Program not found"}), 404

        courses = get_courses_by_program(program_id)

        return jsonify(
            {
                "success": True,
                "program_id": program_id,
                "program_name": program.get("name"),
                "courses": courses,
                "count": len(courses),
            }
        )

    except Exception as e:
        return handle_api_error(
            e, "Get program courses", "Failed to retrieve program courses"
        )


@api.route("/programs/<program_id>/courses", methods=["POST"])
@permission_required("manage_programs")
def add_course_to_program_api(program_id: str):
    """Add a course to a program"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        course_id = data.get("course_id")
        if not course_id:
            return (
                jsonify(
                    {"success": False, "error": "Missing required field: course_id"}
                ),
                400,
            )

        # Validate program exists
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": "Program not found"}), 404

        # Validate course exists
        course = get_course_by_number(
            course_id
        )  # Assuming course_id is course_number for now
        if not course:
            return jsonify({"success": False, "error": "Course not found"}), 404

        # Add course to program
        success = add_course_to_program(course["course_id"], program_id)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Course {course_id} added to program {program.get('name', program_id)}",
                }
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to add course to program"}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Add course to program", "Failed to add course to program"
        )


@api.route("/programs/<program_id>/courses/<course_id>", methods=["DELETE"])
@permission_required("manage_programs")
def remove_course_from_program_api(program_id: str, course_id: str):
    """Remove a course from a program"""
    try:
        # Validate program exists
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": "Program not found"}), 404

        # Get default program for orphan handling
        institution_id = get_current_institution_id()
        programs = get_programs_by_institution(institution_id)
        default_program = next(
            (p for p in programs if p.get("is_default", False)), None
        )

        default_program_id = default_program["id"] if default_program else None

        # Remove course from program
        success = remove_course_from_program(course_id, program_id, default_program_id)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Course {course_id} removed from program {program.get('name', program_id)}",
                }
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": "Failed to remove course from program"}
                ),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Remove course from program", "Failed to remove course from program"
        )


@api.route("/programs/<program_id>/courses/bulk", methods=["POST"])
@permission_required("manage_programs")
def bulk_manage_program_courses(program_id: str):
    """Bulk add or remove courses from a program"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        action = data.get("action")
        course_ids = data.get("course_ids", [])

        if not action or action not in ["add", "remove"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid or missing action. Use 'add' or 'remove'",
                    }
                ),
                400,
            )

        if not course_ids or not isinstance(course_ids, list):
            return (
                jsonify(
                    {"success": False, "error": "Missing or invalid course_ids array"}
                ),
                400,
            )

        # Validate program exists
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": "Program not found"}), 404

        if action == "add":
            result = bulk_add_courses_to_program(course_ids, program_id)
            message = f"Bulk add operation completed: {result['success_count']} added"
        else:  # remove
            # Get default program for orphan handling
            institution_id = get_current_institution_id()
            programs = get_programs_by_institution(institution_id)
            default_program = next(
                (p for p in programs if p.get("is_default", False)), None
            )
            default_program_id = default_program["id"] if default_program else None

            result = bulk_remove_courses_from_program(
                course_ids, program_id, default_program_id
            )
            message = (
                f"Bulk remove operation completed: {result['success_count']} removed"
            )

        return jsonify({"success": True, "message": message, "details": result})

    except Exception as e:
        return handle_api_error(
            e, "Bulk manage program courses", "Failed to bulk manage program courses"
        )


@api.route("/courses/<course_id>/programs", methods=["GET"])
@login_required
def get_course_programs(course_id: str):
    """Get all programs associated with a course"""
    try:
        # Get course to validate it exists
        course = get_course_by_number(
            course_id
        )  # Assuming course_id is course_number for now
        if not course:
            return jsonify({"success": False, "error": "Course not found"}), 404

        program_ids = course.get("program_ids", [])
        programs = []

        # Get program details for each program ID
        for program_id in program_ids:
            program = get_program_by_id(program_id)
            if program:
                programs.append(program)

        return jsonify(
            {
                "success": True,
                "course_id": course_id,
                "course_title": course.get("course_title"),
                "programs": programs,
                "count": len(programs),
            }
        )

    except Exception as e:
        return handle_api_error(
            e, "Get course programs", "Failed to retrieve course programs"
        )


# ========================================
# COURSE SECTION MANAGEMENT API
# ========================================


@api.route("/sections", methods=["GET"])
@login_required
def list_sections():
    """
    Get list of course sections

    Query parameters:
    - instructor_id: Filter by instructor (optional)
    - term_id: Filter by term (optional)
    """
    try:
        instructor_id = request.args.get("instructor_id")
        term_id = request.args.get("term_id")

        current_user = get_current_user()

        # If no filters specified, determine default based on role
        if not instructor_id and not term_id:
            if current_user["role"] == "instructor":
                # Instructors see only their own sections
                instructor_id = current_user["user_id"]
            # Program admins and site admins see all sections (no filter)

        # Apply filters
        if instructor_id:
            sections = get_sections_by_instructor(instructor_id)
        elif term_id:
            sections = get_sections_by_term(term_id)
        else:
            # Get institution context - for development, use CEI
            institution_id = get_current_institution_id()
            if not institution_id:
                return (
                    jsonify(
                        {"success": False, "error": "Institution context required"}
                    ),
                    400,
                )
            sections = get_all_sections(institution_id)

        # Filter based on permissions
        if current_user["role"] == "instructor" and not has_permission(
            "view_all_sections"
        ):
            # Ensure instructors only see their own sections
            sections = [
                s for s in sections if s.get("instructor_id") == current_user["user_id"]
            ]

        return jsonify({"success": True, "sections": sections, "count": len(sections)})

    except Exception as e:
        return handle_api_error(e, "Get sections", "Failed to retrieve sections")


@api.route("/sections", methods=["POST"])
@permission_required("manage_courses")
def create_section():
    """
    Create a new course section

    Request body should contain:
    - course_id: Course ID
    - term_id: Term ID
    - section_number: Section number (optional, default "001")
    - instructor_id: Instructor ID (optional)
    - enrollment: Number of enrolled students (optional)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["course_id", "term_id"]
        missing_fields = [f for f in required_fields if not data.get(f)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Missing required fields: {", ".join(missing_fields)}',
                    }
                ),
                400,
            )

        section_id = create_course_section(data)

        if section_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "section_id": section_id,
                        "message": "Course section created successfully",
                    }
                ),
                201,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to create course section"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Create section", "Failed to create section")


# ========================================
# IMPORT API (New Excel Import System)
# ========================================

# Simple in-memory progress tracking for imports
import threading
import time
import uuid
from typing import Any, Dict

_progress_store: Dict[str, Dict[str, Any]] = {}
_progress_lock = threading.Lock()


def create_progress_tracker() -> str:
    """Create a new progress tracker and return its ID"""
    progress_id = str(uuid.uuid4())
    with _progress_lock:
        _progress_store[progress_id] = {
            "status": "starting",
            "percentage": 0,
            "message": "Initializing import...",
            "records_processed": 0,
            "total_records": 0,
            "created_at": time.time(),
        }
    return progress_id


def update_progress(progress_id: str, **kwargs):
    """Update progress information"""
    with _progress_lock:
        if progress_id in _progress_store:
            _progress_store[progress_id].update(kwargs)


def get_progress(progress_id: str) -> Dict[str, Any]:
    """Get current progress information"""
    with _progress_lock:
        return _progress_store.get(progress_id, {})


def cleanup_progress(progress_id: str):
    """Remove progress tracker after completion"""
    with _progress_lock:
        _progress_store.pop(progress_id, None)


@api.route("/import/progress/<progress_id>", methods=["GET"])
def get_import_progress(progress_id: str):
    """Get the current progress of an import operation"""
    progress = get_progress(progress_id)
    if not progress:
        return jsonify({"error": "Progress ID not found"}), 404

    return jsonify(progress)


@api.route("/import/excel", methods=["POST"])
@permission_required("import_data")
def import_excel_api():
    """
    Import data from Excel file with conflict resolution

    Form data:
    - file: Excel file upload
    - conflict_strategy: "use_mine", "use_theirs", "merge", or "manual_review"
    - dry_run: "true" or "false" (optional, default false)
    - adapter_name: Import adapter to use (optional, default "cei_excel_adapter")
    """
    try:
        # Check if file was uploaded
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Get parameters
        conflict_strategy = request.form.get("conflict_strategy", "use_theirs")
        dry_run = request.form.get("dry_run", "false").lower() == "true"
        adapter_name = request.form.get("adapter_name", "cei_excel_adapter")
        delete_existing_db = (
            request.form.get("delete_existing_db", "false").lower() == "true"
        )
        verbose = request.form.get("verbose_output", "false").lower() == "true"

        # Validate file type
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid file type. Only Excel files (.xlsx, .xls) are supported.",
                    }
                ),
                400,
            )

        # Save uploaded file temporarily
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name

        # Create progress tracker
        progress_id = create_progress_tracker()

        # Start import in background thread
        import threading

        def create_progress_callback(progress_id: str):
            """Create a progress callback function for the given progress_id"""

            def progress_callback(**kwargs):
                update_progress(progress_id, **kwargs)

            return progress_callback

        def run_import():
            try:
                update_progress(
                    progress_id, status="running", message="Starting import..."
                )

                # Perform the import
                institution_id = get_current_institution_id()
                if not institution_id:
                    raise ValueError("Unable to determine current institution ID")

                result = import_excel(
                    file_path=temp_file_path,
                    institution_id=institution_id,
                    conflict_strategy=conflict_strategy,
                    dry_run=dry_run,
                    adapter_name=adapter_name,
                    delete_existing_db=delete_existing_db,
                    verbose=verbose,
                    progress_callback=create_progress_callback(progress_id),
                )

                # Update with final results
                update_progress(
                    progress_id,
                    status="completed",
                    percentage=100,
                    message=(
                        "Import completed successfully!"
                        if result.success
                        else "Import failed"
                    ),
                    result=result,
                )

            except Exception as e:
                update_progress(
                    progress_id, status="error", message=f"Import failed: {str(e)}"
                )
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass

                # Clean up progress tracker after a delay to allow final status retrieval
                def delayed_cleanup():
                    time.sleep(30)  # Wait 30 seconds before cleanup
                    cleanup_progress(progress_id)

                cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
                cleanup_thread.start()

        # Start background thread
        thread = threading.Thread(target=run_import, daemon=True)
        thread.start()

        # Return progress ID immediately
        return (
            jsonify(
                {
                    "success": True,
                    "progress_id": progress_id,
                    "message": "Import started. Use /api/import/progress/{progress_id} to track progress.",
                }
            ),
            202,
        )

    except Exception as e:
        return handle_api_error(e, "Excel import", "Failed to process file upload")


@api.route("/import/validate", methods=["POST"])
@permission_required("import_data")
def validate_import_file():
    """
    Validate Excel file format without importing

    Form data:
    - file: Excel file upload
    - adapter_name: Import adapter to use (optional, default "cei_excel_adapter")
    """
    try:
        # Check if file was uploaded
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Get parameters
        adapter_name = request.form.get("adapter_name", "cei_excel_adapter")

        # Validate file type
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid file type. Only Excel files (.xlsx, .xls) are supported.",
                    }
                ),
                400,
            )

        # Save uploaded file temporarily
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name

        try:
            # Perform dry run validation
            institution_id = get_current_institution_id()
            if not institution_id:
                raise ValueError("Unable to determine current institution ID")

            result = import_excel(
                file_path=temp_file_path,
                institution_id=institution_id,
                conflict_strategy="use_theirs",
                dry_run=True,  # Always dry run for validation
                adapter_name=adapter_name,
            )

            # Create validation response
            validation_result = {
                "valid": result.success and len(result.errors) == 0,
                "records_found": result.records_processed,
                "potential_conflicts": result.conflicts_detected,
                "errors": result.errors,
                "warnings": result.warnings,
                "file_info": {"filename": file.filename, "adapter": adapter_name},
            }

            return jsonify({"success": True, "validation": validation_result})

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

    except Exception as e:
        return handle_api_error(e, "Import validation", "Failed to validate file")


# ========================================
# HEALTH CHECK API
# ========================================


@api.route("/health", methods=["GET"])
def health_check():
    """API health check endpoint"""
    return jsonify(
        {
            "success": True,
            "status": "healthy",
            "message": "CEI Course Management API is running",
            "version": "2.0.0",
        }
    )


# ========================================
# ========================================
# ERROR HANDLERS
# ========================================


@api.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors for API routes"""
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@api.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors for API routes"""
    return jsonify({"success": False, "error": "Internal server error"}), 500


# =============================================================================
# REGISTRATION API ENDPOINTS (Story 2.1)
# =============================================================================


@api.route("/auth/register", methods=["POST"])
def register_institution_admin_api():
    """
    Register a new institution administrator

    Expected JSON payload:
    {
        "email": "admin@example.com",
        "password": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "institution_name": "Example University",
        "website_url": "https://example.edu"  // optional
    }

    Returns:
    {
        "success": true,
        "message": "Registration successful! Please check your email to verify your account.",
        "user_id": "user-123",
        "institution_id": "inst-123"
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "institution_name",
        ]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Missing required fields: {', '.join(missing_fields)}",
                    }
                ),
                400,
            )

        # Extract data
        email = data["email"].strip().lower()
        password = data["password"]
        first_name = data["first_name"].strip()
        last_name = data["last_name"].strip()
        institution_name = data["institution_name"].strip()
        website_url = data.get("website_url", "").strip() or None

        # Validate email format
        if "@" not in email or "." not in email:
            return jsonify({"success": False, "error": "Invalid email format"}), 400

        # Register the admin
        result = register_institution_admin(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            institution_name=institution_name,
            website_url=website_url,
        )

        # Return success response (exclude sensitive data)
        return (
            jsonify(
                {
                    "success": result["success"],
                    "message": result["message"],
                    "user_id": result["user_id"],
                    "institution_id": result["institution_id"],
                    "email_sent": result["email_sent"],
                }
            ),
            201,
        )

    except RegistrationError as e:
        logger.warning(f"Registration failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in registration: {e}")
        return (
            jsonify(
                {"success": False, "error": "Registration failed due to server error"}
            ),
            500,
        )


@api.route("/auth/verify-email/<token>", methods=["GET"])
def verify_email_api(token):
    """
    Verify user's email address using verification token

    URL: /api/auth/verify-email/{verification_token}

    Returns:
    {
        "success": true,
        "message": "Email verified successfully! Your account is now active.",
        "user_id": "user-123",
        "already_verified": false
    }
    """
    try:
        # Validate token
        if not token or len(token) < 10:
            return (
                jsonify({"success": False, "error": "Invalid verification token"}),
                400,
            )

        # Verify email
        result = verify_email(token)

        # Return success response
        return (
            jsonify(
                {
                    "success": result["success"],
                    "message": result["message"],
                    "user_id": result["user_id"],
                    "already_verified": result.get("already_verified", False),
                    "email": result.get("email"),
                    "display_name": result.get("display_name"),
                    "institution_name": result.get("institution_name"),
                }
            ),
            200,
        )

    except RegistrationError as e:
        logger.warning(f"Email verification failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in email verification: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Email verification failed due to server error",
                }
            ),
            500,
        )


@api.route("/auth/resend-verification", methods=["POST"])
def resend_verification_email_api():
    """
    Resend verification email for pending user

    Expected JSON payload:
    {
        "email": "admin@example.com"
    }

    Returns:
    {
        "success": true,
        "message": "Verification email sent! Please check your email.",
        "email_sent": true
    }
    """
    try:
        data = request.get_json()

        # Validate email
        email = data.get("email", "").strip().lower()
        if not email:
            return (
                jsonify({"success": False, "error": "Email address is required"}),
                400,
            )

        if "@" not in email or "." not in email:
            return jsonify({"success": False, "error": "Invalid email format"}), 400

        # Resend verification email
        result = resend_verification_email(email)

        # Return success response
        return (
            jsonify(
                {
                    "success": result["success"],
                    "message": result["message"],
                    "email_sent": result["email_sent"],
                }
            ),
            200,
        )

    except RegistrationError as e:
        logger.warning(f"Resend verification failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in resend verification: {e}")
        return (
            jsonify({"success": False, "error": "Failed to resend verification email"}),
            500,
        )


@api.route("/auth/registration-status/<email>", methods=["GET"])
def get_registration_status_api(email):
    """
    Get registration status for an email address

    URL: /api/auth/registration-status/{email}

    Returns:
    {
        "exists": true,
        "status": "active",  // or "pending_verification", "not_registered"
        "user_id": "user-123",
        "message": "Account is active and verified"
    }
    """
    try:
        # Validate email
        email = email.strip().lower()
        if not email or "@" not in email or "." not in email:
            return (
                jsonify(
                    {
                        "exists": False,
                        "status": "invalid_email",
                        "message": "Invalid email format",
                    }
                ),
                400,
            )

        # Get registration status
        result = get_registration_status(email)

        # Return status
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Unexpected error in registration status check: {e}")
        return (
            jsonify(
                {
                    "exists": False,
                    "status": "error",
                    "message": "Failed to check registration status",
                }
            ),
            500,
        )


# ===== INVITATION API ENDPOINTS =====


@api.route("/auth/invite", methods=["POST"])
@login_required
def create_invitation_api():
    """
    Create and send a user invitation

    JSON Body:
    {
        "invitee_email": "instructor@example.com",
        "invitee_role": "instructor",
        "program_ids": ["prog-123"],  // Optional, for program_admin role
        "personal_message": "Welcome to our team!"  // Optional
    }

    Returns:
        201: Invitation created and sent successfully
        400: Invalid request data
        403: Insufficient permissions
        409: User already exists or invitation pending
        500: Server error
    """
    try:
        from auth_service import get_current_institution_id, get_current_user
        from invitation_service import InvitationService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Validate required fields
        required_fields = ["invitee_email", "invitee_role"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Get current user and institution
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "User not authenticated"}), 401

        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        # Create invitation
        invitation = InvitationService.create_invitation(
            inviter_user_id=current_user["id"],
            inviter_email=current_user["email"],
            invitee_email=data["invitee_email"],
            invitee_role=data["invitee_role"],
            institution_id=institution_id,
            program_ids=data.get("program_ids", []),
            personal_message=data.get("personal_message"),
        )

        # Send invitation email
        email_sent = InvitationService.send_invitation(invitation)

        return (
            jsonify(
                {
                    "success": True,
                    "invitation_id": invitation["id"],
                    "message": (
                        "Invitation created and sent successfully"
                        if email_sent
                        else "Invitation created but email failed to send"
                    ),
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        if "already exists" in str(e) or "already exists" in str(e):
            return jsonify({"success": False, "error": str(e)}), 409
        elif "Invalid role" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Failed to create invitation"}),
                500,
            )


@api.route("/auth/accept-invitation", methods=["POST"])
def accept_invitation_api():
    """
    Accept an invitation and create user account

    JSON Body:
    {
        "invitation_token": "secure-token-here",
        "password": "newpassword123",
        "display_name": "John Doe"  // Optional
    }

    Returns:
        200: Invitation accepted and account created
        400: Invalid request data or token
        410: Invitation expired or already accepted
        500: Server error
    """
    try:
        from invitation_service import InvitationService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Validate required fields
        required_fields = ["invitation_token", "password"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Accept invitation
        user = InvitationService.accept_invitation(
            invitation_token=data["invitation_token"],
            password=data["password"],
            display_name=data.get("display_name"),
        )

        return (
            jsonify(
                {
                    "success": True,
                    "user_id": user["id"],
                    "email": user["email"],
                    "role": user["role"],
                    "message": "Invitation accepted and account created successfully",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        if "expired" in str(e).lower() or "already been accepted" in str(e):
            return jsonify({"success": False, "error": str(e)}), 410
        elif "Invalid" in str(e) or "not available" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Failed to accept invitation"}),
                500,
            )


@api.route("/auth/invitation-status/<invitation_token>", methods=["GET"])
def get_invitation_status_api(invitation_token):
    """
    Get invitation status by token

    URL: /api/auth/invitation-status/{invitation_token}

    Returns:
        200: Invitation status retrieved
        404: Invitation not found
        500: Server error
    """
    try:
        from invitation_service import InvitationService

        # Get invitation status
        status = InvitationService.get_invitation_status(invitation_token)

        return jsonify({"success": True, **status}), 200

    except Exception as e:
        logger.error(f"Error getting invitation status: {e}")
        if "not found" in str(e).lower():
            return jsonify({"success": False, "error": "Invitation not found"}), 404
        else:
            return (
                jsonify({"success": False, "error": "Failed to get invitation status"}),
                500,
            )


@api.route("/auth/resend-invitation/<invitation_id>", methods=["POST"])
@login_required
def resend_invitation_api(invitation_id):
    """
    Resend an existing invitation

    URL: /api/auth/resend-invitation/{invitation_id}

    Returns:
        200: Invitation resent successfully
        400: Cannot resend invitation (wrong status)
        404: Invitation not found
        500: Server error
    """
    try:
        from invitation_service import InvitationService

        # Resend invitation
        success = InvitationService.resend_invitation(invitation_id)

        if success:
            return (
                jsonify({"success": True, "message": "Invitation resent successfully"}),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to resend invitation"}),
                500,
            )

    except Exception as e:
        logger.error(f"Error resending invitation: {e}")
        if "not found" in str(e).lower():
            return jsonify({"success": False, "error": "Invitation not found"}), 404
        elif "Cannot resend" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Failed to resend invitation"}),
                500,
            )


@api.route("/auth/invitations", methods=["GET"])
@login_required
def list_invitations_api():
    """
    List invitations for current user's institution

    Query Parameters:
    - status: Filter by status (pending, sent, accepted, expired, cancelled)
    - limit: Number of results (default 50, max 100)
    - offset: Offset for pagination (default 0)

    Returns:
        200: List of invitations
        400: Invalid parameters
        500: Server error
    """
    try:
        from auth_service import get_current_institution_id
        from invitation_service import InvitationService

        # Get institution context
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        # Get query parameters
        status = request.args.get("status")
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = int(request.args.get("offset", 0))

        # List invitations
        invitations = InvitationService.list_invitations(
            institution_id=institution_id, status=status, limit=limit, offset=offset
        )

        return (
            jsonify(
                {
                    "success": True,
                    "invitations": invitations,
                    "count": len(invitations),
                    "limit": limit,
                    "offset": offset,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error listing invitations: {e}")
        return jsonify({"success": False, "error": "Failed to list invitations"}), 500


@api.route("/auth/cancel-invitation/<invitation_id>", methods=["DELETE"])
@login_required
def cancel_invitation_api(invitation_id):
    """
    Cancel a pending invitation

    URL: /api/auth/cancel-invitation/{invitation_id}

    Returns:
        200: Invitation cancelled successfully
        400: Cannot cancel invitation (wrong status)
        404: Invitation not found
        500: Server error
    """
    try:
        from invitation_service import InvitationService

        # Cancel invitation
        success = InvitationService.cancel_invitation(invitation_id)

        if success:
            return (
                jsonify(
                    {"success": True, "message": "Invitation cancelled successfully"}
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to cancel invitation"}),
                500,
            )

    except Exception as e:
        logger.error(f"Error cancelling invitation: {e}")
        if "not found" in str(e).lower():
            return jsonify({"success": False, "error": "Invitation not found"}), 404
        elif "Cannot cancel" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Failed to cancel invitation"}),
                500,
            )


# ===== LOGIN/LOGOUT API ENDPOINTS =====


@api.route("/auth/login", methods=["POST"])
def login_api():
    """
    Authenticate user and create session

    JSON Body:
    {
        "email": "user@example.com",
        "password": "password123",
        "remember_me": false  // Optional, default false
    }

    Returns:
        200: Login successful
        400: Invalid request data
        401: Invalid credentials
        423: Account locked
        500: Server error
    """
    try:
        from login_service import LoginService
        from password_service import AccountLockedError

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Validate required fields
        required_fields = ["email", "password"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Authenticate user
        result = LoginService.authenticate_user(
            email=data["email"],
            password=data["password"],
            remember_me=data.get("remember_me", False),
        )

        return (
            jsonify({"success": True, **result}),
            200,
        )

    except AccountLockedError as e:
        logger.warning(
            f"Account locked during login attempt: {data.get('email', 'unknown')}"
        )
        return jsonify({"success": False, "error": str(e)}), 423
    except Exception as e:
        logger.error(f"Login error: {e}")
        if "Invalid email or password" in str(e) or "Account" in str(e):
            return jsonify({"success": False, "error": str(e)}), 401
        else:
            return jsonify({"success": False, "error": "Login failed"}), 500


@api.route("/auth/logout", methods=["POST"])
def logout_api():
    """
    Logout current user and destroy session

    Returns:
        200: Logout successful
        500: Server error
    """
    try:
        from login_service import LoginService

        # Logout user
        result = LoginService.logout_user()

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"success": False, "error": "Logout failed"}), 500


@api.route("/auth/status", methods=["GET"])
def login_status_api():
    """
    Get current login status

    Returns:
        200: Status retrieved successfully
        500: Server error
    """
    try:
        from login_service import LoginService

        # Get login status
        status = LoginService.get_login_status()

        return jsonify({"success": True, **status}), 200

    except Exception as e:
        logger.error(f"Error getting login status: {e}")
        return jsonify({"success": False, "error": "Failed to get login status"}), 500


@api.route("/auth/refresh", methods=["POST"])
def refresh_session_api():
    """
    Refresh current user session

    Returns:
        200: Session refreshed successfully
        401: No active session
        500: Server error
    """
    try:
        from login_service import LoginService

        # Refresh session
        result = LoginService.refresh_session()

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        if "No active session" in str(e):
            return jsonify({"success": False, "error": str(e)}), 401
        else:
            return (
                jsonify({"success": False, "error": "Failed to refresh session"}),
                500,
            )


@api.route("/auth/lockout-status/<email>", methods=["GET"])
def check_lockout_status_api(email):
    """
    Check account lockout status for an email

    URL: /api/auth/lockout-status/{email}

    Returns:
        200: Lockout status retrieved
        500: Server error
    """
    try:
        from login_service import LoginService

        # Check lockout status
        status = LoginService.check_account_lockout_status(email)

        return jsonify({"success": True, **status}), 200

    except Exception as e:
        logger.error(f"Error checking lockout status: {e}")
        return (
            jsonify({"success": False, "error": "Failed to check lockout status"}),
            500,
        )


@api.route("/auth/unlock-account", methods=["POST"])
@login_required
def unlock_account_api():
    """
    Manually unlock a locked account (admin function)

    JSON Body:
    {
        "email": "user@example.com"
    }

    Returns:
        200: Account unlocked successfully
        400: Invalid request data
        403: Insufficient permissions
        500: Server error
    """
    try:
        from auth_service import get_current_user
        from login_service import LoginService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        if "email" not in data:
            return (
                jsonify({"success": False, "error": "Missing required field: email"}),
                400,
            )

        # Get current user (admin check would go here)
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        # For now, allow any logged-in user to unlock accounts
        # In production, this should check for admin role

        # Unlock account
        result = LoginService.unlock_account(data["email"], current_user["id"])

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Account unlock error: {e}")
        return jsonify({"success": False, "error": "Failed to unlock account"}), 500


# ===== PASSWORD RESET API ENDPOINTS =====


@api.route("/auth/forgot-password", methods=["POST"])
def forgot_password_api():
    """
    Request password reset email

    JSON Body:
    {
        "email": "user@example.com"
    }

    Returns:
        200: Reset email sent (or would be sent)
        400: Invalid request data
        429: Too many requests
        500: Server error
    """
    try:
        from password_reset_service import PasswordResetService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        if "email" not in data:
            return (
                jsonify({"success": False, "error": "Missing required field: email"}),
                400,
            )

        # Request password reset
        result = PasswordResetService.request_password_reset(data["email"])

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        if "Too many" in str(e):
            return jsonify({"success": False, "error": str(e)}), 429
        elif "restricted in development" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Password reset request failed"}),
                500,
            )


@api.route("/auth/reset-password", methods=["POST"])
def reset_password_api():
    """
    Complete password reset with new password

    JSON Body:
    {
        "reset_token": "secure-reset-token",
        "new_password": "newSecurePassword123!"
    }

    Returns:
        200: Password reset successful
        400: Invalid request data or token
        500: Server error
    """
    try:
        from password_reset_service import PasswordResetService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Validate required fields
        required_fields = ["reset_token", "new_password"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Reset password
        result = PasswordResetService.reset_password(
            reset_token=data["reset_token"], new_password=data["new_password"]
        )

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Password reset error: {e}")
        if any(
            phrase in str(e) for phrase in ["Invalid", "expired", "validation failed"]
        ):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return jsonify({"success": False, "error": "Password reset failed"}), 500


@api.route("/auth/validate-reset-token/<reset_token>", methods=["GET"])
def validate_reset_token_api(reset_token):
    """
    Validate a password reset token

    URL: /api/auth/validate-reset-token/{token}

    Returns:
        200: Token validation result
        500: Server error
    """
    try:
        from password_reset_service import PasswordResetService

        # Validate reset token
        result = PasswordResetService.validate_reset_token(reset_token)

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return (
            jsonify({"success": False, "error": "Failed to validate reset token"}),
            500,
        )


@api.route("/auth/reset-status/<email>", methods=["GET"])
def reset_status_api(email):
    """
    Get password reset status for an email

    URL: /api/auth/reset-status/{email}

    Returns:
        200: Reset status retrieved
        500: Server error
    """
    try:
        from password_reset_service import PasswordResetService

        # Get reset status
        result = PasswordResetService.get_reset_status(email)

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Reset status error: {e}")
        return jsonify({"success": False, "error": "Failed to get reset status"}), 500
