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
    create_course,
    create_course_section,
    create_new_institution,
    create_term,
    get_active_terms,
    get_all_courses,
    get_all_institutions,
    get_all_instructors,
    get_all_sections,
    get_course_by_number,
    get_courses_by_department,
    get_institution_by_id,
    get_institution_instructor_count,
    get_sections_by_instructor,
    get_sections_by_term,
    get_users_by_role,
)
from import_service import import_excel
from logging_config import get_logger

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
# DEBUG ENDPOINTS (for development/testing)
# TODO: These debug endpoints will be removed in next PR - they're temporary development tools
# ========================================


@api.route("/debug/courses", methods=["GET"])
@login_required
def debug_list_courses():
    """Get sample list of courses for debugging"""
    try:
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        courses = get_all_courses(institution_id)
        # Return first 10 courses with basic info
        sample_courses = []
        for course in courses[:10]:
            sample_courses.append(
                {
                    "course_number": course.get("course_number", "N/A"),
                    "title": course.get("title", "N/A"),
                    "department": course.get("department", "N/A"),
                }
            )

        return jsonify(
            {
                "success": True,
                "total_count": len(courses),
                "sample_courses": sample_courses,
            }
        )
    except Exception as e:
        logger.error(f"Error in debug_list_courses: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/debug/instructors", methods=["GET"])
@login_required
def debug_list_instructors():
    """Get sample list of instructors for debugging"""
    try:
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        instructors = get_all_instructors(institution_id)
        # Return first 10 instructors with basic info
        sample_instructors = []
        for instructor in instructors[:10]:
            sample_instructors.append(
                {
                    "email": instructor.get("email", "N/A"),
                    "first_name": instructor.get("first_name", "N/A"),
                    "last_name": instructor.get("last_name", "N/A"),
                    "account_status": instructor.get("account_status", "N/A"),
                }
            )

        return jsonify(
            {
                "success": True,
                "total_count": len(instructors),
                "sample_instructors": sample_instructors,
            }
        )
    except Exception as e:
        logger.error(f"Error in debug_list_instructors: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/debug/sections", methods=["GET"])
@login_required
def debug_list_sections():
    """Get sample list of sections for debugging"""
    try:
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        sections = get_all_sections(institution_id)
        # Return first 10 sections with basic info
        sample_sections = []
        for section in sections[:10]:
            sample_sections.append(
                {
                    "section_number": section.get("section_number", "N/A"),
                    "course_number": section.get("course_number", "N/A"),
                    "instructor_email": section.get("instructor_email", "N/A"),
                    "offering_id": section.get("offering_id", "N/A"),
                }
            )

        return jsonify(
            {
                "success": True,
                "total_count": len(sections),
                "sample_sections": sample_sections,
            }
        )
    except Exception as e:
        logger.error(f"Error in debug_list_sections: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@api.route("/debug/terms", methods=["GET"])
@login_required
def debug_list_terms():
    """Get sample list of terms for debugging"""
    try:
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        terms = get_active_terms(institution_id)
        # Return all terms with basic info
        sample_terms = []
        for term in terms:
            sample_terms.append(
                {
                    "term_name": term.get("term_name", "N/A"),
                    "year": term.get("year", "N/A"),
                    "season": term.get("season", "N/A"),
                }
            )

        return jsonify(
            {"success": True, "total_count": len(terms), "sample_terms": sample_terms}
        )
    except Exception as e:
        logger.error(f"Error in debug_list_terms: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


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
