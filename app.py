import logging
import os
import sys

from flask import Flask, flash, redirect, render_template, url_for

# Constants
DASHBOARD_ENDPOINT = "api.dashboard"

# Import new API routes and services
from api_routes import api
from auth_service import get_current_user, is_authenticated, login_required
from database_service import db as database_client
from logging_config import get_app_logger

# Unused imports removed


# get_courses_by_department import removed

app = Flask(__name__)


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

# Configure session service
from session_service import SessionService

SessionService.configure_app(app)

# Check database connection
if database_client is None:
    app.logger.error(
        "database_service failed to initialize Firestore client. Database operations will fail."
    )
else:
    app.logger.info("Database connection established successfully")


@app.route("/")
def index():
    """Render the main page with course management interface."""

    # Redirect to login if not authenticated
    if not is_authenticated():
        return redirect(url_for("login"))

    # For authenticated users, render the main interface
    user = get_current_user()
    return render_template("index.html", user=user)


# Authentication Routes
@app.route("/login")
def login():
    """Login page"""
    # Redirect to dashboard if already authenticated
    if is_authenticated():
        return redirect(url_for(DASHBOARD_ENDPOINT))

    return render_template("auth/login.html")


@app.route("/dashboard")
def dashboard_redirect():
    """Redirect to the API dashboard route for consistency"""
    return redirect(url_for(DASHBOARD_ENDPOINT))


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
    from auth_service import has_permission

    # Check if user has permission to manage users
    if not has_permission("manage_users"):
        flash("You don't have permission to access user management.", "error")
        return redirect(url_for(DASHBOARD_ENDPOINT))

    current_user = get_current_user()
    return render_template("admin/user_management.html", current_user=current_user)


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
