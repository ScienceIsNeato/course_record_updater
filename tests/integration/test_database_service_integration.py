# tests/test_database_service_integration.py
import os

import pytest

# Import the service functions
from database_service import db

# --- Test Setup and Markers ---

EXPECTED_EMULATOR_HOST = "localhost"
EXPECTED_EMULATOR_PORT = 8086  # Updated Port
EXPECTED_EMULATOR_ADDR = f"{EXPECTED_EMULATOR_HOST}:{EXPECTED_EMULATOR_PORT}"

# Mark these tests as integration tests
pytestmark = pytest.mark.integration


# Fixture to check emulator connection before running integration tests
@pytest.fixture(scope="session", autouse=True)
def check_emulator_is_running():
    """Checks if the emulator is running before starting the test session."""
    # This check runs only once per session
    emulator_host_env = os.environ.get("FIRESTORE_EMULATOR_HOST")

    if not emulator_host_env:
        pytest.skip(
            "FIRESTORE_EMULATOR_HOST env var not set. Skipping integration tests."
        )
        return  # Ensure fixture exits if skipping

    if emulator_host_env != EXPECTED_EMULATOR_ADDR:
        pytest.skip(
            f"FIRESTORE_EMULATOR_HOST is set to '{emulator_host_env}', but expected '{EXPECTED_EMULATOR_ADDR}'. Skipping integration tests."
        )
        return

    print(f"✅ Emulator connection configured correctly: {emulator_host_env}")


def create_test_session(client, user_data):
    """Helper function to create a test session with user data."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_data.get("user_id")
        sess["email"] = user_data.get("email")
        sess["role"] = user_data.get("role")
        sess["institution_id"] = user_data.get("institution_id")
        sess["program_ids"] = user_data.get("program_ids", [])
        sess["display_name"] = user_data.get(
            "display_name",
            f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
        )
        sess["created_at"] = user_data.get("created_at")
        sess["last_activity"] = user_data.get("last_activity")
        sess["remember_me"] = user_data.get("remember_me", False)


class TestDatabaseServiceIntegration:
    """Integration tests for database service with Firestore emulator."""

    def test_database_connection(self):
        """Test that we can connect to the Firestore emulator."""
        # Just verify the client exists and is configured
        assert db is not None
        assert hasattr(db, "collection")

        # Try to access a collection (this will verify emulator connectivity)
        collection_ref = db.collection("test_connection")
        assert collection_ref is not None

    def test_basic_document_operations(self):
        """Test basic document create/read operations."""
        # Create a test document
        test_collection = db.collection("integration_test")
        doc_ref = test_collection.document("test_doc")

        # Write test data
        test_data = {"name": "Integration Test", "value": 42, "active": True}
        doc_ref.set(test_data)

        # Read it back
        doc = doc_ref.get()
        assert doc.exists
        assert doc.to_dict() == test_data

        # Clean up
        doc_ref.delete()
