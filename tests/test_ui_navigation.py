import pytest

import database_service
from app import app
from models import Institution, User


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for easier testing

    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def auth(client):
    """Authentication helper fixture"""

    class AuthActions:
        def __init__(self, client):
            self._client = client

        def login(self, email="test@example.com", password="TestUser123!"):
            # First mark email as verified
            user = database_service.get_user_by_email(email)
            if user:
                database_service.update_user(user["user_id"], {"email_verified": True})

            # Login via API
            return self._client.post(
                "/api/auth/login",
                json={"email": email, "password": password},
                content_type="application/json",
            )

    return AuthActions(client)


@pytest.fixture(autouse=True)
def setup_data():
    """Seed database with test user"""
    # Create institution
    inst_data = Institution.create_schema(
        name="Test University",
        short_name="TESTU",
        created_by="system",
        admin_email="admin@test.edu",
    )
    inst_id = database_service.create_institution(inst_data)

    # Create user
    user_data = User.create_schema(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role="institution_admin",
        institution_id=inst_id,
        password_hash=User.create_password_hash("TestUser123!"),
        account_status="active",
    )
    database_service.create_user(user_data)


def test_programs_route_exists(client, auth):
    """Test that the /programs route exists and returns 200."""
    auth.login()
    response = client.get("/programs")
    assert response.status_code == 200
    assert b"Programs" in response.data


def test_faculty_route_exists(client, auth):
    """Test that the /faculty route exists (or redirects) and returns 200."""
    auth.login()
    response = client.get("/faculty", follow_redirects=True)
    assert response.status_code == 200


def test_outcomes_route_exists(client, auth):
    """Test that the /outcomes route exists (or redirects) and returns 200."""
    auth.login()
    response = client.get("/outcomes", follow_redirects=True)
    assert response.status_code == 200


def test_dashboard_navigation_links(client, auth):
    """Test that the dashboard loads successfully."""
    auth.login()
    response = client.get("/dashboard")
    assert response.status_code == 200
    # Dashboard uses JavaScript-based filtering, not static nav links
    assert b"Dashboard" in response.data


def test_programs_page_content(client, auth):
    """Test that the programs page loads correctly."""
    auth.login()
    response = client.get("/programs")
    assert response.status_code == 200
    # Check for key elements in the programs list template
    assert b"All Programs" in response.data
    assert b"loadPrograms()" in response.data
