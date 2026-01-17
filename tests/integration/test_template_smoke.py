"""
Smoke tests to verify all major templates can render without syntax errors.

These tests catch critical issues like missing Jinja closing braces that
would cause 500 errors on page load. They should run as part of CI to
prevent broken templates from being deployed.
"""

import pytest
from flask import Flask


def test_assessments_template_renders(client, authenticated_client):
    """Assessments page should render without template syntax errors."""
    response = authenticated_client.get("/assessments")

    # Should not be a 500 error
    assert response.status_code != 500, (
        f"Assessments page returned 500 error - likely template syntax error. "
        f"Check Jinja2 template for missing closing braces or other syntax issues."
    )

    # Should either be 200 (success) or redirect
    assert response.status_code in [
        200,
        302,
    ], f"Unexpected status code {response.status_code} for /assessments"


def test_dashboard_template_renders(client, authenticated_client):
    """Dashboard should render without template syntax errors."""
    response = authenticated_client.get("/dashboard")

    assert (
        response.status_code != 500
    ), "Dashboard returned 500 error - check template syntax"
    assert response.status_code in [200, 302]


def test_courses_template_renders(client, authenticated_client):
    """Courses page should render without template syntax errors."""
    response = authenticated_client.get("/courses")

    assert (
        response.status_code != 500
    ), "Courses page returned 500 error - check template syntax"
    assert response.status_code in [200, 302]


def test_admin_template_renders(client, authenticated_client):
    """Admin page should render without template syntax errors."""
    response = authenticated_client.get("/admin")

    assert (
        response.status_code != 500
    ), "Admin page returned 500 error - check template syntax"
    assert response.status_code in [
        200,
        302,
        403,
        404,
    ]  # 403 if not admin, 404 if route doesn't exist


def test_audit_template_renders(client, authenticated_client):
    """Audit page should render without template syntax errors."""
    response = authenticated_client.get("/audit")

    assert (
        response.status_code != 500
    ), "Audit page returned 500 error - check template syntax"
    assert response.status_code in [
        200,
        302,
        403,
        404,
    ]  # 403 if not admin, 404 if route doesn't exist


def test_login_template_renders(client):
    """Login page should render without template syntax errors."""
    response = client.get("/login")

    assert (
        response.status_code != 500
    ), "Login page returned 500 error - check template syntax"
    assert response.status_code == 200


def test_register_template_renders(client):
    """Register page should render without template syntax errors."""
    response = client.get("/register")

    assert (
        response.status_code != 500
    ), "Register page returned 500 error - check template syntax"
    assert response.status_code == 200


@pytest.mark.integration
def test_all_templates_compile(authenticated_client):
    """Test that all Jinja2 templates compile without syntax errors.

    This catches issues like:
    - Missing closing braces {{ ... }
    - Unmatched {% ... %}
    - Invalid Jinja2 syntax
    """
    from flask import current_app
    from jinja2.exceptions import TemplateSyntaxError

    env = authenticated_client.application.jinja_env

    template_files = [
        "assessments.html",
        "auth/login.html",
        "index.html",
        "components/app_header.html",
    ]

    errors = []
    for template_name in template_files:
        try:
            env.get_template(template_name)
        except TemplateSyntaxError as e:
            errors.append(f"{template_name}: {e}")

    assert not errors, f"Template syntax errors found:\\n" + "\\n".join(errors)
