import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional, Union

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.wrappers import Response

from src.database.database_service import check_db_connection, db
from src.database.database_validator import validate_schema_or_exit
from src.services.auth_service import (
    get_current_user,
    is_authenticated,
    login_required,
    permission_required,
)
from src.services.email_service import EmailService
from src.services.institution_service import InstitutionService

# Import constants and utilities
from src.utils.constants import (
    DASHBOARD_ENDPOINT,
    DATE_OVERRIDE_BANNER_PREFIX,
)
from src.utils.logging_config import get_app_logger
from src.utils.term_utils import get_current_term, get_term_display_name

from .api import register_blueprints  # Modular API structure

# Unused imports removed


# get_courses_by_department import removed

# Initialize logger
logger = get_app_logger()


# Shared services
institution_service = InstitutionService()

app = Flask(__name__, template_folder="../templates", static_folder="../static")

# Initialize CSRF protection (disabled during testing)
# Check if we're in test mode by looking for pytest in sys.modules

# SECURITY: CSRF protection configuration
# CSRF is ENABLED for all routes to prevent cross-site request forgery attacks
csrf_enabled = os.getenv("WTF_CSRF_ENABLED", "true").lower() != "false"
app.config["WTF_CSRF_ENABLED"] = csrf_enabled

csrf = CSRFProtect(app)


# CSRF error handler - return JSON for API routes, HTML for others
from flask_wtf.csrf import CSRFError


@app.errorhandler(CSRFError)
def handle_csrf_error(e: CSRFError) -> tuple[Any, int]:
    """Handle CSRF validation errors"""
    from flask import jsonify, request

    from src.utils.constants import CSRF_ERROR_MESSAGE

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
def inject_csrf_token() -> dict[str, Any]:
    from flask_wtf.csrf import generate_csrf

    return dict(csrf_token=generate_csrf)


@app.context_processor
def inject_institution_branding() -> dict[str, Any]:
    """Provide institution branding data to all templates."""
    user = get_current_user()
    institution_id = user.get("institution_id") if user else None
    branding = institution_service.build_branding(institution_id)
    return {"institution_branding": branding}


# Configure logging to ensure consistent output
def setup_logging() -> None:
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
register_blueprints(app)

# Configure email service (sets BASE_URL and other email settings)
EmailService.configure_app(app)


@app.before_request
def load_system_date_override() -> None:
    """Load system date override from current user into global context."""
    from datetime import datetime, timezone

    from flask import g

    # Use localized import if needed, or rely on top-level
    user = get_current_user()
    if user:
        # Check for override in user dict
        override = user.get("system_date_override")
        if override:
            # Parse if string (from session/JSON)
            if isinstance(override, str):
                try:
                    # Handle ISO string with potential Z
                    override = datetime.fromisoformat(override.replace("Z", "+00:00"))
                except ValueError:
                    return  # Invalid format, ignore

            # Ensure timezone awareness (UTC)
            if isinstance(override, datetime):
                if override.tzinfo is None:
                    override = override.replace(tzinfo=timezone.utc)
                g.system_date_override = override


# Secret key configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# Check database connection
if not check_db_connection():
    app.logger.error("Database connection unavailable; SQLite backend not reachable")
else:
    app.logger.info("Database connection established successfully (SQLite)")


@app.route("/")
def index() -> str:
    """Render the splash page - marketing/showcase page for the application."""
    # Always show splash page for unauthenticated users
    # Authenticated users should go directly to /dashboard
    return render_template("splash.html")


# Authentication Routes
@app.route("/login")
def login() -> Union[str, Response]:
    """Login page (supports deep linking via ?next parameter)"""
    # Allow forcing login page even if authenticated (for broken sessions)
    force_login = request.args.get("force") == "true"

    # If forcing login, clear any existing session first
    if force_login and is_authenticated():
        from src.services.login_service import LoginService

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
def reminder_login() -> Union[str, Response]:
    """
    Special login page for email reminders.
    Logs out any existing session to prevent wrong-user login.
    Preserves 'next' parameter for post-login redirect.
    """
    # Get the 'next' destination from query params
    next_url = request.args.get("next", "")

    # If someone is logged in, log them out and redirect to clear session
    if is_authenticated():
        from src.services.login_service import LoginService

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
def logout_view() -> Response:
    """
    Simple GET endpoint to clear the current session and redirect to login.

    Useful for local demo workflows where stale cookies need to be cleared
    without relying on the dashboard dropdown (which may not load yet).
    """
    from src.services.login_service import LoginService

    LoginService.logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/register")
def register() -> Union[str, Response]:
    """Registration page"""
    # Redirect to dashboard if already authenticated
    if is_authenticated():
        return redirect(url_for(DASHBOARD_ENDPOINT))

    return render_template("auth/register.html")


@app.route("/terms-of-service")
def terms_of_service() -> str:
    """Terms of Service page"""
    return render_template("legal/terms.html")


@app.route("/privacy")
def privacy_policy() -> str:
    """Privacy Policy page"""
    return render_template("legal/privacy.html")


@app.route("/register/accept/<token>")
def register_accept_invitation(token: str) -> str:
    """Accept invitation and complete registration"""
    # If user is logged in, log them out first to accept the new invitation
    if is_authenticated():
        from src.services.login_service import LoginService

        LoginService.logout_user()
        logger.info("[App] Logged out existing user to accept invitation")

    # Token will be validated by frontend via API call to /api/auth/invitation-status/<token>
    return render_template("auth/register_invitation.html", invitation_token=token)


@app.route("/forgot-password")
def forgot_password() -> Union[str, Response]:
    """Forgot password page"""
    # Redirect to dashboard if already authenticated
    if is_authenticated():
        return redirect(url_for(DASHBOARD_ENDPOINT))

    return render_template("auth/forgot_password.html")


@app.route("/reset-password/<token>")
def reset_password_form(token: str) -> Union[str, Response]:
    """
    Password reset form page - handles reset link from email

    Validates token and displays password reset form.
    The form will POST to /api/auth/reset-password when submitted.
    """
    from src.services.password_reset_service import PasswordResetService
    from src.utils.logging_config import get_logger

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
def profile() -> Union[str, Response]:
    """User profile/account settings page"""
    current_user = get_current_user()
    if not current_user:
        flash("Please log in to access your profile.", "error")
        return redirect(url_for("login"))

    override = current_user.get("system_date_override")
    if isinstance(override, str):
        try:
            parsed_override = datetime.fromisoformat(override.replace("Z", "+00:00"))
            if parsed_override.tzinfo is None:
                parsed_override = parsed_override.replace(tzinfo=timezone.utc)
            current_user = dict(current_user)
            current_user["system_date_override"] = parsed_override
        except ValueError:
            logger.warning(
                "Unable to parse system_date_override '%s' for user %s",
                override,
                current_user.get("user_id"),
            )

    member_since_display = _format_member_since(current_user.get("created_at"))
    return render_template(
        "auth/profile.html",
        current_user=current_user,
        user=current_user,
        date_override_banner_prefix=DATE_OVERRIDE_BANNER_PREFIX,
        member_since_display=member_since_display,
    )


def _format_member_since(created_at_value: Any) -> Optional[str]:
    """Build a human-readable 'Member Since' string for profiles."""
    if not created_at_value:
        return None

    parsed = None
    if isinstance(created_at_value, str):
        try:
            parsed = datetime.fromisoformat(created_at_value.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(
                "Unable to parse profile created_at value '%s'", created_at_value
            )
            return None
    elif isinstance(created_at_value, datetime):
        parsed = created_at_value
    else:
        return None

    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc)
    else:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.strftime("%B %d, %Y")


# Admin Routes
@app.route("/admin/users")
@login_required
def admin_users() -> Union[str, Response]:
    """Admin user management page"""
    # TODO: Add comprehensive UAT test cases for admin user management panel including:
    # - User creation, editing, and deactivation workflows
    # - Role assignment and permission validation
    # - Bulk operations and filtering functionality
    # - Cross-browser compatibility and responsive design
    from src.services.auth_service import has_permission

    # Check if user has permission to manage users
    if not has_permission("manage_users"):
        flash("You don't have permission to access user management.", "error")
        return redirect(url_for(DASHBOARD_ENDPOINT))

    current_user = get_current_user()
    return render_template("admin/user_management.html", current_user=current_user)


# Dashboard Routes
def _parse_date_to_naive(date_value: Any) -> Any:
    """Parse a date value to timezone-naive datetime for comparison."""
    if isinstance(date_value, str):
        return datetime.fromisoformat(date_value.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
    elif hasattr(date_value, "replace"):
        return date_value.replace(tzinfo=None) if date_value.tzinfo else date_value
    return date_value


def _find_matching_term(
    terms: list[dict[str, Any]], effective_date_naive: datetime
) -> Optional[str]:
    """Find term where effective_date falls within start/end dates OR the most recent started term."""
    # 1. First pass: Check for strictly active term (current date within start-end)
    started_terms = []

    for term in terms:
        start_date = term.get("start_date")
        end_date = term.get("end_date")

        if not start_date or not end_date:
            continue

        start_naive = _parse_date_to_naive(start_date)
        end_naive = _parse_date_to_naive(end_date)

        # Optimization: Track all terms that have started for fallback
        if start_naive <= effective_date_naive:
            started_terms.append((start_naive, term))

        # Strict match: Date is currently inside the term
        if start_naive <= effective_date_naive <= end_naive:
            return term.get("name") or term.get("term_name") or "Current Term"

    # 2. Second pass: If no term is strictly active, use the most recent one that has started
    # This covers the "gap" between terms (e.g., Winter break) where the previous Fall term
    # should effectively remain active until Spring starts.
    if started_terms:
        # Sort by start date descending (newest first)
        started_terms.sort(key=lambda x: x[0], reverse=True)
        most_recent_term = started_terms[0][1]
        return (
            most_recent_term.get("name")
            or most_recent_term.get("term_name")
            or "Current Term"
        )

    return None


def _get_current_term_from_db(user: dict[str, Any], effective_date: Any) -> str:
    """
    Find the current term based on effective date by querying the database.

    Returns the term name where effective_date falls between start_date and end_date.
    Falls back to a generated term name if no matching term is found.
    """
    institution_id = user.get("institution_id")
    if not institution_id:
        return get_term_display_name(get_current_term())

    try:
        from src.database.database_service import get_all_terms

        terms = get_all_terms(institution_id)
        if not terms:
            return get_term_display_name(get_current_term())

        effective_date_naive = _parse_date_to_naive(effective_date)
        term_name = _find_matching_term(terms, effective_date_naive)

        return term_name or get_term_display_name(get_current_term())

    except Exception as e:
        logger.warning(f"Failed to get current term from DB: {e}")
        return get_term_display_name(get_current_term())


def get_header_context(user: dict[str, Any]) -> dict[str, Any]:
    """
    Generate header context with current term and date information

    Args:
        user: The current user object

    Returns:
        dict: Header context with term and date information
    """
    # Get effective date - use override if set, otherwise current time
    effective_date = user.get("system_date_override") or datetime.now(timezone.utc)

    # Format date for display
    if isinstance(effective_date, str):
        # If it's a string, try to parse it
        try:
            effective_date = datetime.fromisoformat(
                effective_date.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            effective_date = datetime.now(timezone.utc)

    # Format the date for display
    date_format = "%b %d, %Y %I:%M %p %Z"
    effective_date_display = effective_date.strftime(date_format)

    # Determine current term based on effective date and actual term records
    current_term_display = _get_current_term_from_db(user, effective_date)

    return {
        "current_term": current_term_display,
        "current_term_display": current_term_display,
        "effective_date": effective_date,
        "effective_date_display": effective_date_display,
        "is_override": bool(user.get("system_date_override")),
    }


@app.context_processor
def inject_header_context() -> dict[str, Any]:
    """Always inject current term/date info into dashboard pages."""
    user = get_current_user()
    if not user:
        return {}
    header_context = get_header_context(user)
    return {"header_context": header_context}


@app.route("/dashboard")
@login_required
def dashboard() -> Union[str, Response]:
    """
    Role-based dashboard - returns different views based on user role
    """
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    role = user["role"]
    header_context = get_header_context(user)
    template_kwargs = {
        "user": user,
        "header_context": header_context,
        "DATE_OVERRIDE_BANNER_PREFIX": DATE_OVERRIDE_BANNER_PREFIX,
    }

    if role == "instructor":
        return render_template("dashboard/instructor.html", **template_kwargs)
    elif role == "program_admin":
        return render_template("dashboard/program_admin.html", **template_kwargs)
    elif role == "institution_admin":
        return render_template("dashboard/institution_admin.html", **template_kwargs)
    elif role == "site_admin":
        # Use simplified site admin UI with working create modals
        return render_template("dashboard/site_admin.html", **template_kwargs)
    else:
        flash("Unknown user role. Please contact administrator.", "danger")
        return redirect(url_for("index"))


@app.route("/courses")
@login_required
def courses_list() -> Union[str, Response]:
    """Display all courses for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("courses_list.html", user=user)


@app.route("/users")
@login_required
def users_list() -> Union[str, Response]:
    """Display all users for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("users_list.html", user=user)


@app.route("/assessments")
@login_required
def assessments_page() -> Union[str, Response]:
    """Display assessment/outcomes page for instructors"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("assessments.html", user=user)


@app.route("/audit-clo")
@login_required
@permission_required("audit_clo")
def audit_clo_page() -> str:
    """
    Display CLO audit and approval page for admins.

    Allows program admins and institution admins to review and approve CLOs.
    """
    user = get_current_user()
    return render_template("audit_clo.html", user=user)


@app.route("/audit-logs")
@login_required
@permission_required("manage_institution_users")
def audit_logs_page() -> str:
    """
    Display full audit log viewer page for admins.
    """
    user = get_current_user()
    return render_template("audit_logs.html", user=user)


@app.route("/sections")
@login_required
def sections_list() -> Union[str, Response]:
    """Display all course sections for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template(
        "sections_list.html",
        user=user,
        current_user=user,
    )


@app.route("/terms")
@login_required
def terms_list() -> Union[str, Response]:
    """Display all terms for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("terms_list.html", user=user)


@app.route("/offerings")
@login_required
def offerings_list() -> Union[str, Response]:
    """Display all course offerings for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("offerings_list.html", user=user)


@app.route("/programs")
@login_required
def programs_list() -> Union[str, Response]:
    """Display all programs for the current user's institution"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("programs_list.html", user=user)


@app.route("/faculty")
@login_required
def faculty_list() -> Response:
    """Redirect to users list filtered for faculty/instructors"""
    return redirect(url_for("users_list", role="instructor"))


@app.route("/outcomes")
@login_required
def outcomes_page() -> Union[str, Response]:
    """Display course outcomes management page"""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("outcomes_list.html", user=user)


# Health check endpoint for parallel E2E testing
# This endpoint is registered AFTER all other initialization, so when it responds
# we know Flask is fully ready to serve requests (not just that the port is open)
@app.route("/health")
def health_check() -> tuple[dict[str, Any], int]:
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
    logger.info("Starting LoopCloser on port %s with debug mode: %s", port, use_debug)
    logger.info("Access the application at http://localhost:%s", port)
    logger.info(
        "To use a different port, set PORT environment variable: PORT=3002 python app.py"
    )

    # Validate database schema before starting the application
    # This catches column name typos and schema mismatches at startup
    # validate_schema_or_exit handles all exceptions internally and will raise
    # SchemaValidationError if validation fails, blocking startup
    validate_schema_or_exit(db)

    # SECURITY: Only bind to all interfaces (0.0.0.0) in container/CI environments
    # In local development, bind to localhost only to prevent network exposure
    # B104: This is intentional for containerized deployments
    bind_all = os.environ.get("BIND_ALL_INTERFACES", "false").lower() == "true"
    host = (
        "0.0.0.0" if bind_all else "127.0.0.1"  # nosec B104 - intentional for bind_all
    )
    app.run(host=host, port=port, debug=use_debug)
