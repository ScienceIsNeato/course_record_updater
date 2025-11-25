"""
API package for Course Record Updater.

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
    from api.routes.audit import audit_bp
    from api.routes.bulk_email import bulk_email_bp
    from api.routes.clo_workflow import clo_workflow_bp
    from api.routes.dashboard import dashboard_bp
    from api.routes.management import management_bp

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(bulk_email_bp)
    app.register_blueprint(clo_workflow_bp)
    app.register_blueprint(management_bp)

    # TODO: Add more blueprints as we extract them:
    # from api.routes.terms import terms_bp
    # from api.routes.outcomes import outcomes_bp
    # from api.routes.offerings import offerings_bp
    # from api.routes.sections import sections_bp
    # from api.routes.courses import courses_bp
    # from api.routes.programs import programs_bp
    # from api.routes.users import users_bp
    # from api.routes.institutions import institutions_bp
    # from api.routes.import_export import import_export_bp
    
    # app.register_blueprint(audit_bp)
    # app.register_blueprint(terms_bp)
    # ... etc

