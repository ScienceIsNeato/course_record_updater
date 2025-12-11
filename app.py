import logging
import os
import sys

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect

from api import register_blueprints  # New modular API structure

# Import new API routes and services
from api_routes import api
from auth_service import (
    get_current_user,
    is_authenticated,
    login_required,
    permission_required,
)

# Import constants
from constants import DASHBOARD_ENDPOINT
from database_service import check_db_connection, db
from database_validator import validate_schema_or_exit
from email_service import EmailService
from logging_config import get_app_logger

# Unused imports removed


# get_courses_by_department import removed

# Initialize logger
logger = get_app_logger()

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

    from constants import CSRF_ERROR_MESSAGE

    # Check if this is an API request
    if request.path.startswith("/api/"):
        return (
            jsonify(
                {
                    "success": False,
                    "error": CSRF_ERROR_MESSAGE,
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
    """Login page (supports deep linking via ?next parameter)"""
    # Allow forcing login page even if authenticated (for broken sessions)
    force_login = request.args.get("force") == "true"

    # If forcing login, clear any existing session first
    if force_login and is_authenticated():
        from login_service import LoginService

        LoginService.logout_user()
        # Flash message to inform user
        flash("Session cleared. Please log in again.", "info")

    # Redirect to dashboard if already authenticated (unless forced)
    if is_authenticated() and not force_login:
        return redirect(url_for(DASHBOARD_ENDPOINT))

    # Store 'next' URL in session for post-login redirect (fixes email deep link)
    next_url = request.args.get("next")
    if next_url:
        session["next_after_login"] = next_url

    return render_template("auth/login.html")


@app.route("/reminder-login")
def reminder_login():
    """
    Special login page for email reminders.
    Logs out any existing session to prevent wrong-user login.
    Preserves 'next' parameter for post-login redirect.
    """
    # Get the 'next' destination from query params
    next_url = request.args.get("next", "")

    # If someone is logged in, log them out and redirect to clear session
    if is_authenticated():
        from login_service import LoginService

        LoginService.logout_user()
        # Redirect to same route to get a fresh session with valid CSRF token
        # Preserve the 'next' parameter
        redirect_url = url_for("reminder_login") + "?logged_out=true"
        if next_url:
            redirect_url += f"&next={next_url}"
        return redirect(redirect_url)

    # Show flash message if just logged out
    if request.args.get("logged_out"):
        flash(
            "You have been logged out. Please log in with your instructor account.",
            "info",
        )

    # Store next_url in session so login handler can use it
    if next_url:
        session["next_after_login"] = next_url

    return render_template("auth/login.html")


@app.route("/logout")
def logout_view():
    """
    Simple GET endpoint to clear the current session and redirect to login.

    Useful for local demo workflows where stale cookies need to be cleared
    without relying on the dashboard dropdown (which may not load yet).
    """
    from login_service import LoginService

    LoginService.logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


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
    # If user is logged in, log them out first to accept the new invitation
    if is_authenticated():
        from login_service import LoginService

        LoginService.logout_user()
        logger.info("[App] Logged out existing user to accept invitation")

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


@app.route("/audit-clo")
@login_required
@permission_required("audit_clo")
def audit_clo_page():
    """
    Display CLO audit and approval page for admins.

    Allows program admins and institution admins to review and approve CLOs.
    """
    user = get_current_user()
    return render_template("audit_clo.html", user=user)


@app.route("/sections")
@login_required
def sections_list():
    """Display all course sections for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("sections_list.html", user=user)


@app.route("/terms")
@login_required
def terms_list():
    """Display all terms for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("terms_list.html", user=user)


@app.route("/programs")
@login_required
def programs_list():
    """Display all programs for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("programs_list.html", user=user)


@app.route("/faculty")
@login_required
def faculty_list():
    """Redirect to users list filtered for faculty/instructors"""
    return redirect(url_for("users_list", role="instructor"))


@app.route("/outcomes")
@login_required
def outcomes_page():
    """Redirect to assessments/outcomes page"""
    return redirect(url_for("assessments_page"))


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
    # 3. LOOPCLOSER_DEFAULT_PORT_DEV (local dev default from .envrc)
    # 4. 3001 (hardcoded fallback)
    port = int(
        os.environ.get(
            "PORT",
            os.environ.get(
                "DEFAULT_PORT", os.environ.get("LOOPCLOSER_DEFAULT_PORT_DEV", 3001)
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

    # Validate database schema before starting the application
    # This catches column name typos and schema mismatches at startup
    # validate_schema_or_exit handles all exceptions internally and will raise
    # SchemaValidationError if validation fails, blocking startup
    validate_schema_or_exit(db)

    app.run(host="0.0.0.0", port=port, debug=use_debug)
