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
    1. The CEI institution exists for auth service fallback
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
        from database_service import create_default_cei_institution

        # Create CEI institution if it doesn't exist
        # This supports the auth service fallback in get_current_institution_id()
        cei_id = create_default_cei_institution()
        if cei_id:
            print(f"✅ Created CEI institution for integration tests: {cei_id}")
        else:
            print("ℹ️  CEI institution already exists for integration tests")

    except Exception as e:
        print(
            f"⚠️  Warning: Could not set up CEI institution for integration tests: {e}"
        )
        # Don't fail the tests if this setup fails - let individual tests handle it
        pass
