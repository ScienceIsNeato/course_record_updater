import logging
import os
import sys

from flask import Flask, flash, redirect, render_template, url_for
from flask_wtf.csrf import CSRFProtect

# Import new API routes and services
from api_routes import api
from auth_service import get_current_user, is_authenticated, login_required

# Import constants
from constants import DASHBOARD_ENDPOINT
from database_service import check_db_connection
from logging_config import get_app_logger

# Unused imports removed


# get_courses_by_department import removed

app = Flask(__name__)

# Initialize CSRF protection (disabled during testing)
# Check if we're in test mode by looking for pytest in sys.modules
import sys

# SECURITY: CSRF protection configuration
# CSRF is enabled by default for all environments
# Only disabled when explicitly set via environment variable for testing
csrf_enabled = os.getenv("WTF_CSRF_ENABLED", "true").lower() != "false"
app.config["WTF_CSRF_ENABLED"] = csrf_enabled

csrf = CSRFProtect(app)


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

# Register API blueprint
app.register_blueprint(api)

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


@app.route("/forgot-password")
def forgot_password():
    """Forgot password page"""
    # Redirect to dashboard if already authenticated
    if is_authenticated():
        return redirect(url_for(DASHBOARD_ENDPOINT))

    return render_template("auth/forgot_password.html")


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
        # Use new panel-based UI for site admin
        return render_template("dashboard/site_admin_panels.html", user=user)
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


@app.route("/sections")
@login_required
def sections_list():
    """Display all course sections for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("sections_list.html", user=user)


if __name__ == "__main__":
    # Use PORT environment variable if available (common in deployment),
    # otherwise use COURSE_RECORD_UPDATER_PORT from .envrc, or default to 3001
    port = int(
        os.environ.get("PORT", os.environ.get("COURSE_RECORD_UPDATER_PORT", 3001))
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
