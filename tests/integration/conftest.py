"""
Integration Test Fixtures

Database isolation strategy:
1. Session scope: Seed ONCE using E2E manifest (creates all test users)
2. Function scope: Fork (copy) the seeded database per test
3. No resets needed - each test gets its own isolated copy

This is the Django/pytest-django pattern for SQLite integration tests.
"""

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def seeded_integration_db(tmp_path_factory):
    """
    Seed database ONCE for entire integration test session.

    Uses the E2E manifest to create all expected test users:
    - siteadmin@system.local (site_admin)
    - sarah.admin@mocku.test (institution_admin)
    - bob.programadmin@mocku.test (program_admin)
    - john.instructor@mocku.test (instructor)
    - jane.instructor@mocku.test (instructor)
    - mike.admin@riverside.edu (institution_admin)
    """
    import src.database.database_service as database_service

    # Create session-scoped database
    session_dir = tmp_path_factory.mktemp("integration_session")
    session_db = session_dir / "integration.db"

    os.environ["DATABASE_URL"] = f"sqlite:///{session_db}"
    os.environ["DATABASE_TYPE"] = "sqlite"
    os.environ["EMAIL_WHITELIST"] = (
        "*@inst.test,*@example.com,*@testu.edu,*@eu.edu,*@mocku.test,*@ethereal.email,*@system.local"
    )
    database_service.refresh_connection()

    # Load E2E manifest
    manifest_path = PROJECT_ROOT / "tests" / "fixtures" / "e2e_seed_manifest.json"
    manifest_data = None
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest_data = json.load(f)

    # Seed with manifest
    scripts_dir = PROJECT_ROOT / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from seed_db import BaselineTestSeeder

    seeder = BaselineTestSeeder()
    seeder.seed_baseline(manifest_data)
    print(f"✅ Seeded integration session database: {session_db}")

    yield session_db


@pytest.fixture(autouse=True)
def isolated_integration_db(seeded_integration_db, tmp_path):
    """
    Fork database for each test (true isolation).

    Copies the seeded session database to a test-specific location.
    Each test gets its own copy, so mutations don't affect other tests.
    No resets needed - database is fresh from the fork.
    """
    import src.database.database_service as database_service

    # Copy session DB to test-specific location
    test_db = tmp_path / "test.db"
    shutil.copy2(seeded_integration_db, test_db)

    # Point database service at the forked copy
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"
    database_service.refresh_connection()

    yield test_db
    # Cleanup is automatic via tmp_path - no reset needed


@pytest.fixture
def client(isolated_integration_db):
    """Create a Flask test client for integration tests."""
    import src.app as app

    app.app.config["TESTING"] = True

    with app.app.test_client() as client:
        with app.app.app_context():
            yield client


@pytest.fixture
def site_admin(isolated_integration_db):
    """Get the seeded site admin user."""
    import src.database.database_service as db
    from tests.test_credentials import SITE_ADMIN_EMAIL

    user = db.get_user_by_email(SITE_ADMIN_EMAIL)
    assert user, f"Site admin {SITE_ADMIN_EMAIL} not found in seeded data"
    return user


@pytest.fixture
def institution_admin(isolated_integration_db):
    """Get the seeded institution admin (Sarah)."""
    import src.database.database_service as db
    from tests.test_credentials import INSTITUTION_ADMIN_EMAIL

    user = db.get_user_by_email(INSTITUTION_ADMIN_EMAIL)
    assert user, f"Institution admin {INSTITUTION_ADMIN_EMAIL} not found"
    return user


@pytest.fixture
def program_admin(isolated_integration_db):
    """Get the seeded program admin (Bob)."""
    import src.database.database_service as db
    from tests.test_credentials import PROGRAM_ADMIN_EMAIL

    user = db.get_user_by_email(PROGRAM_ADMIN_EMAIL)
    assert user, f"Program admin {PROGRAM_ADMIN_EMAIL} not found"
    return user


@pytest.fixture
def instructor(isolated_integration_db):
    """Get the seeded instructor (John)."""
    import src.database.database_service as db
    from tests.test_credentials import INSTRUCTOR_EMAIL

    user = db.get_user_by_email(INSTRUCTOR_EMAIL)
    assert user, f"Instructor {INSTRUCTOR_EMAIL} not found"
    return user


@pytest.fixture
def mocku_institution(isolated_integration_db):
    """Get Mock University institution."""
    import src.database.database_service as db

    institutions = db.get_all_institutions() or []
    inst = next(
        (i for i in institutions if "Mock University" in i.get("name", "")), None
    )
    assert inst, "Mock University not found in seeded data"
    return inst
