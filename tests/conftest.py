"""
Global test configuration and fixtures.

This module provides common fixtures for all tests,
including database connection restoration.
"""

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True, scope="session")
def fail_fast_firestore_emulator():
    """Force Firestore connections to fail immediately when emulator is absent."""
    original_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
    original_grpc = os.environ.get("FIRESTORE_EMULATOR_GRPC_ADDRESS")

    # Point to a non-listening localhost port so connection errors surface instantly.
    fail_fast_endpoint = "127.0.0.1:46211"
    os.environ.setdefault("FIRESTORE_EMULATOR_HOST", fail_fast_endpoint)
    os.environ.setdefault("FIRESTORE_EMULATOR_GRPC_ADDRESS", fail_fast_endpoint)

    try:
        yield
    finally:
        if original_host is None:
            os.environ.pop("FIRESTORE_EMULATOR_HOST", None)
        else:
            os.environ["FIRESTORE_EMULATOR_HOST"] = original_host

        if original_grpc is None:
            os.environ.pop("FIRESTORE_EMULATOR_GRPC_ADDRESS", None)
        else:
            os.environ["FIRESTORE_EMULATOR_GRPC_ADDRESS"] = original_grpc


@pytest.fixture(autouse=True)
def restore_database_connection():
    """
    Ensure database connection is restored after each test.

    This fixture runs automatically after every test to ensure that
    unit tests that mock database_service.db don't break subsequent
    integration tests that rely on the real Firestore connection.
    """
    yield  # Run the test

    # After the test, ensure the database connection is restored
    try:
        import database_service

        # If db is None or mocked, reinitialize it
        if database_service.db is None or hasattr(database_service.db, "_mock_name"):

            # Re-import and reinitialize the connection
            import os

            from google.cloud import firestore

            emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
            if emulator_host:
                # For integration tests with emulator
                database_service.db = firestore.Client()
            else:
                # For unit tests, leave as None (they should mock as needed)
                database_service.db = None

    except Exception:
        # If restoration fails, don't break the test suite
        # Integration tests will handle connection errors appropriately
        pass
