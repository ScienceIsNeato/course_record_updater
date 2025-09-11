import logging
import os
import sys
from datetime import datetime

from flask import Flask, render_template

# Import new API routes and services
from api_routes import api
from auth_service import get_current_user, is_authenticated
from database_service import db as database_client
from database_service import get_courses_by_department

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

    # Get current user info for display
    current_user = get_current_user()

    # For now, just show the import interface
    # Later we can add a proper dashboard with course listings
    return render_template(
        "index.html", current_user=current_user, is_authenticated=is_authenticated()
    )


if __name__ == "__main__":
    # Use PORT environment variable if available (common in deployment),
    # otherwise use COURSE_RECORD_UPDATER_PORT from .envrc, or default to 3001
    port = int(
        os.environ.get("PORT", os.environ.get("COURSE_RECORD_UPDATER_PORT", 3001))
    )
    # Debug mode should be controlled by FLASK_DEBUG environment variable
    use_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    print(
        f"INFO: Starting Course Record Updater on port {port} with debug mode: {use_debug}"
    )
    print(f"INFO: Access the application at http://localhost:{port}")
    print(
        f"INFO: To use a different port, set PORT environment variable: PORT=3002 python app.py"
    )

    app.run(host="0.0.0.0", port=port, debug=use_debug)
