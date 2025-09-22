"""
Integration test configuration and fixtures.

This module provides common fixtures for integration tests,
including database setup and institution creation.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_integration_test_data():
    """
    Set up integration test data including default CEI institution.

    This fixture runs once per test session and ensures that:
    1. A baseline CEI institution exists for historical test data
    2. Basic test data is available for integration tests
    """
    import os

    # Skip expensive Firestore setup when emulator isn't configured.
    emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
    if not emulator_host:
        print("ℹ️  Skipping CEI institution setup (FIRESTORE_EMULATOR_HOST not set)")
        return

    # Bail out quickly if the emulator host isn't reachable.
    try:
        host, port = emulator_host.split(":", 1)
        import socket

        with socket.create_connection((host, int(port)), timeout=1):
            pass
    except Exception:
        print("ℹ️  Skipping CEI institution setup (Firestore emulator unreachable)")
        return

    try:
        # Import and run the database seeder to create full test dataset
        import sys
        from pathlib import Path

        # Add scripts directory to path
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        from seed_db import DatabaseSeeder

        # Create full seeded dataset for integration tests
        seeder = DatabaseSeeder(verbose=False)  # Reduce noise in test output
        seeder.seed_full_dataset()
        print("✅ Seeded full database for integration tests")

    except Exception as e:
        print(f"⚠️  Warning: Could not seed database for integration tests: {e}")
        # Fallback to minimal CEI institution setup
        try:
            from database_service import create_default_cei_institution

            cei_id = create_default_cei_institution()
            if cei_id:
                print(f"✅ Created CEI institution for integration tests: {cei_id}")
            else:
                print("ℹ️  CEI institution already exists for integration tests")
        except Exception as fallback_e:
            print(f"⚠️  Warning: Fallback CEI creation also failed: {fallback_e}")
            # Don't fail the tests if this setup fails - let individual tests handle it
