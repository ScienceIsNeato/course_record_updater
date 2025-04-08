# tests/test_database_service_integration.py
import pytest
import os
import time
import socket

# Import the service functions
from database_service import save_course, get_all_courses, update_course, delete_course, db

# --- Test Setup and Markers --- 

EXPECTED_EMULATOR_HOST = "localhost"
EXPECTED_EMULATOR_PORT = 8086 # Updated Port
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
        pytest.skip("FIRESTORE_EMULATOR_HOST env var not set. Skipping integration tests.")
        return # Ensure fixture exits if skipping
        
    if emulator_host_env != EXPECTED_EMULATOR_ADDR:
         pytest.fail(
             f"FIRESTORE_EMULATOR_HOST is set to '{emulator_host_env}', "
             f"but tests expect '{EXPECTED_EMULATOR_ADDR}'. Please check env var and README."
         )
    
    # Check if the db client initialized correctly (depends on emulator being reachable)
    if db is None:
        pytest.fail(
            f"Firestore client failed to initialize in database_service.py, "
            f"even though FIRESTORE_EMULATOR_HOST was set to {emulator_host_env}. "
            f"Is the emulator running and accessible? See README."
        )

    # Optional: More robust check - try to connect to the socket
    try:
        with socket.create_connection((EXPECTED_EMULATOR_HOST, EXPECTED_EMULATOR_PORT), timeout=0.5):
            pass # Connection successful
        print(f"\nSuccessfully connected to emulator at {EXPECTED_EMULATOR_ADDR}.")
    except (socket.timeout, ConnectionRefusedError) as e:
        pytest.fail(
            f"Failed to connect to Firestore emulator at {EXPECTED_EMULATOR_ADDR}. "
            f"Is it running? (Error: {e}). See README."
        )
    except Exception as e:
         pytest.fail(f"An unexpected error occurred while checking emulator connection: {e}")

# --- Helper to Clean Up --- 
def cleanup_collection(collection_ref):
    """Deletes all documents in a collection (use with caution!)."""
    docs = collection_ref.stream()
    deleted = 0
    for doc in docs:
        # print(f'Deleting doc {doc.id} => {doc.to_dict()}')
        doc.reference.delete()
        deleted += 1
    # print(f"Deleted {deleted} documents.")

@pytest.fixture(autouse=True)
def manage_emulator_data():
    """Fixture to clear data before each test when emulator is active."""
    # Check env var directly again, as fixture execution order isn't guaranteed 
    # relative to the session-scoped check_emulator_is_running on subsequent runs within a session.
    if db and os.environ.get("FIRESTORE_EMULATOR_HOST") == EXPECTED_EMULATOR_ADDR:
        # print("\n--- Clearing Firestore Emulator Data ---") # Keep commented for less noise
        courses_ref = db.collection('courses') # Use the actual collection name
        cleanup_collection(courses_ref)
    yield
    

# --- Integration Tests --- 
# Remove @skip_if_no_emulator marker from tests below
# Fixture check_emulator_is_running handles skipping/failing session-wide

def test_save_and_get_course():
    """Test saving a course and retrieving it."""
    print("\n--- test_save_and_get_course START ---")
    # Arrange
    course_data = {
        'course_title': 'Integration Test Course',
        'course_number': 'INT101',
        'semester': 'TestSem',
        'year': 2024,
        'professor': 'Emulator Tester'
    }
    print(f"Arrange complete. Data: {course_data}")

    # Act
    print("Calling save_course...")
    saved_id = save_course(course_data)
    print(f"save_course returned ID: {saved_id}")
    
    print("Calling get_all_courses...")
    retrieved_courses = get_all_courses()
    print(f"get_all_courses returned {len(retrieved_courses)} courses.")

    # Assert
    print("Starting assertions...")
    assert saved_id is not None
    assert len(retrieved_courses) == 1
    retrieved_course = retrieved_courses[0]
    assert retrieved_course['id'] == saved_id
    assert retrieved_course['course_number'] == 'INT101'
    assert retrieved_course['professor'] == 'Emulator Tester'
    assert 'timestamp' in retrieved_course
    print("--- test_save_and_get_course END ---")

def test_update_course():
    """Test saving, updating, and retrieving a course."""
    print("\n--- test_update_course START ---")
    # Arrange: Save initial course
    initial_data = {
        'course_title': 'Update Test',
        'course_number': 'UPD200',
        'semester': 'UpdateSem',
        'year': 2025,
        'professor': 'Prof. Original'
    }
    print("Calling initial save_course...")
    saved_id = save_course(initial_data)
    print(f"Initial save_course returned ID: {saved_id}")
    assert saved_id is not None

    # Act: Update the course
    update_payload = {'professor': 'Prof. Updated', 'num_students': 75}
    print(f"Calling update_course for ID {saved_id} with payload: {update_payload}")
    update_result = update_course(saved_id, update_payload)
    print(f"update_course returned: {update_result}")
    
    print("Calling get_all_courses after update...")
    retrieved_courses = get_all_courses()
    print(f"get_all_courses returned {len(retrieved_courses)} courses.")

    # Assert
    print("Starting assertions...")
    assert update_result is True
    assert len(retrieved_courses) == 1
    updated_course = retrieved_courses[0]
    assert updated_course['id'] == saved_id
    assert updated_course['course_number'] == 'UPD200'
    assert updated_course['professor'] == 'Prof. Updated'
    assert updated_course['num_students'] == 75
    assert 'last_modified' in updated_course
    print("--- test_update_course END ---")

def test_delete_course():
    """Test saving and then deleting a course."""
    print("\n--- test_delete_course START ---")
    # Arrange: Save initial course
    initial_data = {
        'course_title': 'Delete Test',
        'course_number': 'DEL300',
        'semester': 'DeleteSem',
        'year': 2026,
        'professor': 'Prof. Temporary'
    }
    print("Calling initial save_course...")
    saved_id = save_course(initial_data)
    print(f"Initial save_course returned ID: {saved_id}")
    assert saved_id is not None
    
    print("Calling get_all_courses to verify existence...")
    initial_courses = get_all_courses()
    print(f"Verification get_all_courses returned {len(initial_courses)} courses.")
    assert len(initial_courses) == 1

    # Act: Delete the course
    print(f"Calling delete_course for ID: {saved_id}")
    delete_result = delete_course(saved_id)
    print(f"delete_course returned: {delete_result}")
    
    print("Calling get_all_courses after delete...")
    retrieved_courses_after_delete = get_all_courses()
    print(f"get_all_courses returned {len(retrieved_courses_after_delete)} courses.")

    # Assert
    print("Starting assertions...")
    assert delete_result is True
    assert len(retrieved_courses_after_delete) == 0
    print("--- test_delete_course END ---") 