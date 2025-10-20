import logging
import os
import sys

from flask import Flask, flash, redirect, render_template, url_for
from flask_wtf.csrf import CSRFProtect

from api import register_blueprints  # New modular API structure

# Import new API routes and services
from api_routes import api
from auth_service import get_current_user, is_authenticated, login_required

# Import constants
from constants import DASHBOARD_ENDPOINT
from database_service import check_db_connection
from email_service import EmailService
from logging_config import get_app_logger

# Unused imports removed


# get_courses_by_department import removed

app = Flask(__name__)

# Initialize CSRF protection (disabled during testing)
# Check if we're in test mode by looking for pytest in sys.modules
import sys

# SECURITY: CSRF protection configuration
# CSRF is ENABLED for all routes to prevent cross-site request forgery attacks
csrf_enabled = os.getenv("WTF_CSRF_ENABLED", "true").lower() != "false"
app.config["WTF_CSRF_ENABLED"] = csrf_enabled

csrf = CSRFProtect(app)


# CSRF error handler - return JSON for API routes, HTML for others
from flask_wtf.csrf import CSRFError


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF validation errors"""
    from flask import jsonify, request

    # Check if this is an API request
    if request.path.startswith("/api/"):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "CSRF validation failed. Please refresh the page and try again.",
                }
            ),
            400,
        )
    # For non-API routes, return simple HTML error
    return (
        "<h1>400 Bad Request</h1><p>Invalid CSRF token. Please refresh and try again.</p>",
        400,
    )


# Make CSRF token available in templates
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf

    return dict(csrf_token=generate_csrf)


# Configure logging to ensure consistent output
def setup_logging():
    """Configure logging to write to both console and file"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),  # Console output
            logging.FileHandler("logs/server.log", mode="a"),  # File output
        ],
    )

    # Configure Flask's logger
    app.logger.setLevel(logging.INFO)

    # Configure Werkzeug (Flask's development server) logger
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.INFO)


# Setup logging
setup_logging()

# Register API blueprints
app.register_blueprint(api)  # Legacy monolithic API (being refactored)
register_blueprints(app)  # New modular API structure

# Configure email service (sets BASE_URL and other email settings)
EmailService.configure_app(app)

# Secret key configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# Check database connection
if not check_db_connection():
    app.logger.error("Database connection unavailable; SQLite backend not reachable")
else:
    app.logger.info("Database connection established successfully (SQLite)")


@app.route("/")
def index():
    """Render the splash page - marketing/showcase page for the application."""
    # Always show splash page for unauthenticated users
    # Authenticated users should go directly to /dashboard
    return render_template("splash.html")


# Authentication Routes
@app.route("/login")
def login():
    """Login page"""
    # Redirect to dashboard if already authenticated
    if is_authenticated():
        return redirect(url_for(DASHBOARD_ENDPOINT))

    return render_template("auth/login.html")


@app.route("/register")
def register():
    """Registration page"""
    # Redirect to dashboard if already authenticated
    if is_authenticated():
        return redirect(url_for(DASHBOARD_ENDPOINT))

    return render_template("auth/register.html")


@app.route("/register/accept/<token>")
def register_accept_invitation(token):
    """Accept invitation and complete registration"""
    # Redirect to dashboard if already authenticated
    if is_authenticated():
        return redirect(url_for(DASHBOARD_ENDPOINT))

    # Token will be validated by frontend via API call to /api/auth/invitation-status/<token>
    return render_template("auth/register_invitation.html", invitation_token=token)


@app.route("/forgot-password")
def forgot_password():
    """Forgot password page"""
    # Redirect to dashboard if already authenticated
    if is_authenticated():
        return redirect(url_for(DASHBOARD_ENDPOINT))

    return render_template("auth/forgot_password.html")


@app.route("/reset-password/<token>")
def reset_password_form(token):
    """
    Password reset form page - handles reset link from email

    Validates token and displays password reset form.
    The form will POST to /api/auth/reset-password when submitted.
    """
    from logging_config import get_logger
    from password_reset_service import PasswordResetService

    logger = get_logger(__name__)

    try:
        # Validate the reset token
        validation_result = PasswordResetService.validate_reset_token(token)

        if validation_result.get("valid"):
            # Token is valid - show reset form with token and email
            return render_template(
                "auth/reset_password.html",
                token=token,
                email=validation_result.get("email"),
            )

        # Token invalid or expired
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for("forgot_password"))

    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Password reset token validation error: {e}")
        flash("An error occurred. Please request a new password reset link.", "danger")
        return redirect(url_for("forgot_password"))


@app.route("/profile")
@login_required
def profile():
    """User profile/account settings page"""
    current_user = get_current_user()
    if not current_user:
        flash("Please log in to access your profile.", "error")
        return redirect(url_for("login"))

    return render_template("auth/profile.html", current_user=current_user)


# Admin Routes
@app.route("/admin/users")
@login_required
def admin_users():
    """Admin user management page"""
    # TODO: Add comprehensive UAT test cases for admin user management panel including:
    # - User creation, editing, and deactivation workflows
    # - Role assignment and permission validation
    # - Bulk operations and filtering functionality
    # - Cross-browser compatibility and responsive design
    from auth_service import has_permission

    # Check if user has permission to manage users
    if not has_permission("manage_users"):
        flash("You don't have permission to access user management.", "error")
        return redirect(url_for(DASHBOARD_ENDPOINT))

    current_user = get_current_user()
    return render_template("admin/user_management.html", current_user=current_user)


# Dashboard Routes
@app.route("/dashboard")
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
    elif role == "institution_admin":
        return render_template("dashboard/institution_admin.html", user=user)
    elif role == "site_admin":
        # Use simplified site admin UI with working create modals
        return render_template("dashboard/site_admin.html", user=user)
    else:
        flash("Unknown user role. Please contact administrator.", "danger")
        return redirect(url_for("index"))


@app.route("/courses")
@login_required
def courses_list():
    """Display all courses for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("courses_list.html", user=user)


@app.route("/users")
@login_required
def users_list():
    """Display all users for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("users_list.html", user=user)


@app.route("/assessments")
@login_required
def assessments_page():
    """Display assessment/outcomes page for instructors"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("assessments.html", user=user)


@app.route("/sections")
@login_required
def sections_list():
    """Display all course sections for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("sections_list.html", user=user)


# Health check endpoint for parallel E2E testing
# This endpoint is registered AFTER all other initialization, so when it responds
# we know Flask is fully ready to serve requests (not just that the port is open)
@app.route("/health")
def health_check():
    """
    Health check endpoint for E2E test infrastructure.
    Returns 200 OK when Flask is fully initialized and ready to serve requests.
    """
    return {"status": "ok", "ready": True}, 200


if __name__ == "__main__":
    # Port selection priority (for CI/multi-environment compatibility):
    # 1. PORT (standard env var, used by CI)
    # 2. DEFAULT_PORT (CI fallback)
    # 3. LASSIE_DEFAULT_PORT_DEV (local dev default from .envrc)
    # 4. 3001 (hardcoded fallback)
    port = int(
        os.environ.get(
            "PORT",
            os.environ.get(
                "DEFAULT_PORT", os.environ.get("LASSIE_DEFAULT_PORT_DEV", 3001)
            ),
        )
    )
    # Debug mode should be controlled by FLASK_DEBUG environment variable
    use_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    logger = get_app_logger()
    logger.info(
        "Starting Course Record Updater on port %s with debug mode: %s", port, use_debug
    )
    logger.info("Access the application at http://localhost:%s", port)
    logger.info(
        "To use a different port, set PORT environment variable: PORT=3002 python app.py"
    )

    app.run(host="0.0.0.0", port=port, debug=use_debug)
