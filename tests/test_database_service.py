import pytest
from unittest.mock import MagicMock, patch, ANY # ANY helps match timestamp

# Import the module we are testing
import database_service

# Define sample data
SAMPLE_COURSE_DATA_VALID = {
    'course_title': 'Test Course',
    'course_number': 'TEST101',
    'semester': 'Fall',
    'year': '2023',
    'professor': 'Dr. Tester',
    'num_students': '50'
}

SAMPLE_COURSE_DOC_ID = "test_doc_id_123"

# --- Fixtures (Optional but can be helpful) ---
# You could use fixtures to set up the mock db for multiple tests

# --- Test save_course --- 

def test_save_course_success(mocker):
    """Test successful saving of course data."""
    # Arrange
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = SAMPLE_COURSE_DOC_ID
    
    # Configure mock methods
    mock_db.collection.return_value = mock_collection
    mock_collection.add.return_value = (None, mock_doc_ref) # Firestore add returns (timestamp, doc_ref)
    
    # Patch the db instance within the database_service module
    mocker.patch('database_service.db', mock_db)
    mocker.patch('database_service.firestore.SERVER_TIMESTAMP', 'mock_timestamp') # Mock server timestamp

    # Act
    result_id = database_service.save_course(SAMPLE_COURSE_DATA_VALID)

    # Assert
    assert result_id == SAMPLE_COURSE_DOC_ID
    mock_db.collection.assert_called_once_with(database_service.COURSES_COLLECTION)
    # Check that .add was called with data including the timestamp
    expected_data_to_save = SAMPLE_COURSE_DATA_VALID.copy()
    expected_data_to_save['timestamp'] = 'mock_timestamp'
    mock_collection.add.assert_called_once_with(expected_data_to_save)

def test_save_course_db_unavailable(mocker):
    """Test saving when Firestore client is None."""
    # Arrange
    mocker.patch('database_service.db', None)

    # Act
    result_id = database_service.save_course(SAMPLE_COURSE_DATA_VALID)

    # Assert
    assert result_id is None

def test_save_course_invalid_data_type(mocker):
    """Test saving with invalid data type (not dict)."""
     # Arrange
    mock_db = MagicMock() # Mock db so it doesn't fail on the None check first
    mocker.patch('database_service.db', mock_db)

    # Act
    result_id = database_service.save_course("not a dictionary")

    # Assert
    assert result_id is None

def test_save_course_firestore_exception(mocker):
    """Test handling of Firestore exception during save."""
    # Arrange
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.add.side_effect = Exception("Firestore unavailable")
    
    mocker.patch('database_service.db', mock_db)
    mocker.patch('database_service.firestore.SERVER_TIMESTAMP', 'mock_timestamp')

    # Act
    result_id = database_service.save_course(SAMPLE_COURSE_DATA_VALID)

    # Assert
    assert result_id is None
    mock_collection.add.assert_called_once() # Ensure it attempted the save

# --- Test get_all_courses --- 

def test_get_all_courses_success_empty(mocker):
    """Test successful retrieval when no courses exist."""
    # Arrange
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_query = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.order_by.return_value = mock_query
    mock_query.stream.return_value = iter([]) # Empty iterator

    mocker.patch('database_service.db', mock_db)

    # Act
    courses = database_service.get_all_courses()

    # Assert
    assert courses == []
    mock_db.collection.assert_called_once_with(database_service.COURSES_COLLECTION)
    mock_collection.order_by.assert_called_once_with('timestamp', direction=mocker.ANY) # Check ordering is applied
    mock_query.stream.assert_called_once()

def test_get_all_courses_success_with_data(mocker):
    """Test successful retrieval with multiple course documents."""
    # Arrange
    mock_doc1_data = {'course_number': 'CS101', 'timestamp': 'ts1'}
    mock_doc2_data = {'course_number': 'MA200', 'timestamp': 'ts2'} # Assume ts2 > ts1 for ordering
    
    mock_doc1 = MagicMock()
    mock_doc1.id = 'doc1'
    mock_doc1.to_dict.return_value = mock_doc1_data
    
    mock_doc2 = MagicMock()
    mock_doc2.id = 'doc2'
    mock_doc2.to_dict.return_value = mock_doc2_data

    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_query = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.order_by.return_value = mock_query
    # Simulate stream returning docs (implicitly in descending order by timestamp as mocked)
    mock_query.stream.return_value = iter([mock_doc2, mock_doc1]) 

    mocker.patch('database_service.db', mock_db)

    # Act
    courses = database_service.get_all_courses()

    # Assert
    assert len(courses) == 2
    # Check data includes the ID and is in the expected order
    assert courses[0]['id'] == 'doc2'
    assert courses[0]['course_number'] == 'MA200'
    assert courses[1]['id'] == 'doc1'
    assert courses[1]['course_number'] == 'CS101'
    mock_query.stream.assert_called_once()

def test_get_all_courses_db_unavailable(mocker):
    """Test retrieval when Firestore client is None."""
    # Arrange
    mocker.patch('database_service.db', None)

    # Act
    courses = database_service.get_all_courses()

    # Assert
    assert courses == []

def test_get_all_courses_firestore_exception(mocker):
    """Test handling of Firestore exception during retrieval."""
    # Arrange
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_query = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.order_by.return_value = mock_query
    mock_query.stream.side_effect = Exception("Firestore query failed")

    mocker.patch('database_service.db', mock_db)

    # Act
    courses = database_service.get_all_courses()

    # Assert
    assert courses == []
    mock_query.stream.assert_called_once() # Ensure it attempted the query

# --- Test update_course ---

def test_update_course_success(mocker):
    """Test successful update of a course."""
    # Arrange
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    mocker.patch('database_service.db', mock_db)
    mocker.patch('database_service.firestore.SERVER_TIMESTAMP', 'mock_timestamp')

    course_id = "existing_doc_1"
    update_payload = {'professor': 'Prof. New Name', 'num_students': 60}
    expected_update_call = update_payload.copy()
    expected_update_call['last_modified'] = 'mock_timestamp'

    # Act
    result = database_service.update_course(course_id, update_payload)

    # Assert
    assert result is True
    mock_db.collection.assert_called_once_with(database_service.COURSES_COLLECTION)
    mock_collection.document.assert_called_once_with(course_id)
    mock_document.update.assert_called_once_with(expected_update_call)

def test_update_course_db_unavailable(mocker):
    """Test update when Firestore client is None."""
    mocker.patch('database_service.db', None)
    result = database_service.update_course("any_id", {'field': 'value'})
    assert result is False

def test_update_course_invalid_args(mocker):
    """Test update with invalid arguments."""
    mocker.patch('database_service.db', MagicMock()) # Ensure DB exists
    assert database_service.update_course(None, {'field': 'value'}) is False
    assert database_service.update_course("any_id", "not a dict") is False

def test_update_course_firestore_exception(mocker):
    """Test handling of Firestore exception during update."""
    # Arrange
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document
    mock_document.update.side_effect = Exception("Update failed")

    mocker.patch('database_service.db', mock_db)
    mocker.patch('database_service.firestore.SERVER_TIMESTAMP', 'mock_timestamp')

    # Act
    result = database_service.update_course("any_id", {'field': 'value'})

    # Assert
    assert result is False
    mock_document.update.assert_called_once()

# --- Test delete_course ---

def test_delete_course_success(mocker):
    """Test successful deletion of a course."""
    # Arrange
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document

    mocker.patch('database_service.db', mock_db)
    course_id = "doc_to_delete"

    # Act
    result = database_service.delete_course(course_id)

    # Assert
    assert result is True
    mock_db.collection.assert_called_once_with(database_service.COURSES_COLLECTION)
    mock_collection.document.assert_called_once_with(course_id)
    mock_document.delete.assert_called_once()

def test_delete_course_db_unavailable(mocker):
    """Test delete when Firestore client is None."""
    mocker.patch('database_service.db', None)
    result = database_service.delete_course("any_id")
    assert result is False

def test_delete_course_invalid_args(mocker):
    """Test delete with invalid arguments."""
    mocker.patch('database_service.db', MagicMock()) # Ensure DB exists
    assert database_service.delete_course(None) is False
    assert database_service.delete_course("") is False

def test_delete_course_firestore_exception(mocker):
    """Test handling of Firestore exception during delete."""
     # Arrange
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_document = MagicMock()
    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_document
    mock_document.delete.side_effect = Exception("Delete failed")

    mocker.patch('database_service.db', mock_db)

    # Act
    result = database_service.delete_course("any_id")

    # Assert
    assert result is False
    mock_document.delete.assert_called_once()
