"""
API package for LoopCloser.

This package contains all REST API endpoints organized by domain.
Each domain has its own route module for better organization and testability.
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """
    Register all API blueprints with the Flask application.

    This function is called during application initialization to register
    all API route modules.

    Args:
        app: Flask application instance
    """
    # Import route modules
    from src.api.routes.audit import audit_bp
    from src.api.routes.auth import auth_bp
    from src.api.routes.bulk_email import bulk_email_bp
    from src.api.routes.clo_workflow import clo_workflow_bp
    from src.api.routes.courses import courses_bp
    from src.api.routes.dashboard import dashboard_bp
    from src.api.routes.data_export import data_export_bp
    from src.api.routes.data_import import data_import_bp
    from src.api.routes.institutions import institutions_bp
    from src.api.routes.invitations import invitations_bp
    from src.api.routes.management import management_bp
    from src.api.routes.offerings import offerings_bp
    from src.api.routes.outcomes import outcomes_bp
    from src.api.routes.programs import programs_bp
    from src.api.routes.registration import registration_bp
    from src.api.routes.sections import sections_bp
    from src.api.routes.system import system_bp
    from src.api.routes.terms import terms_bp
    from src.api.routes.users import users_bp

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(bulk_email_bp)
    app.register_blueprint(clo_workflow_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(data_export_bp)
    app.register_blueprint(data_import_bp)
    app.register_blueprint(institutions_bp)
    app.register_blueprint(invitations_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(offerings_bp)
    app.register_blueprint(outcomes_bp)
    app.register_blueprint(programs_bp)
    app.register_blueprint(registration_bp)
    app.register_blueprint(sections_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(terms_bp)
    app.register_blueprint(users_bp)
