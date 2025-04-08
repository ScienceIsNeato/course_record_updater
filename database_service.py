# database_service.py
"""Module to handle all interactions with Google Cloud Firestore."""

import datetime
import os # Import os to check environment variables
from google.cloud import firestore

# --- Firestore Client Initialization ---

db = None
emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")

try:
    # The client library automatically uses FIRESTORE_EMULATOR_HOST if set.
    # No special arguments needed here for emulator detection.
    db = firestore.Client()
    if emulator_host:
        print(f"Firestore client initialized, attempting to connect to emulator at: {emulator_host}")
        # Add a simple check to see if connection works (optional, might add overhead)
        # try:
        #    db.collection('_emulator_check').document('_ping').set({'status':'ok'})
        #    print("Emulator connection successful.")
        # except Exception as e:
        #    print(f"WARNING: Emulator host is set, but connection failed: {e}")
        #    db = None # Force db to None if emulator connection fails?
    else:
        print("Firestore client initialized for cloud connection.")

except Exception as e:
    print(f"Error initializing Firestore client: {e}")
    if emulator_host:
        print(f"Ensure the Firestore emulator is running and accessible at {emulator_host}")
    db = None # Ensure db is None if initialization fails

COURSES_COLLECTION = 'courses' # Define collection name

# Define unique key fields
UNIQUE_FIELDS = ['term', 'course_number', 'instructor_name']

# --- Service Functions ---

def check_course_exists(course_data: dict):
    """
    Checks if a course with the same unique fields already exists.

    Args:
        course_data: Dictionary containing at least the UNIQUE_FIELDS.

    Returns:
        The ID of the existing course if found, None otherwise.
        Returns None if DB is unavailable or an error occurs.
    """
    if not db:
        print("[DB Service] check_course_exists: DB unavailable.")
        return None
    
    # Ensure all unique fields are present
    if not all(field in course_data for field in UNIQUE_FIELDS):
        print(f"[DB Service] check_course_exists: Missing one or more unique fields ({UNIQUE_FIELDS}) in input.")
        # This case should ideally be caught by validation before calling DB
        return None 
        
    try:
        query = db.collection(COURSES_COLLECTION)
        # Build the query dynamically based on unique fields
        for field in UNIQUE_FIELDS:
            query = query.where(filter=firestore.FieldFilter(field, "==", course_data[field]))
            
        # Limit to 1 as we only need to know if *any* exist
        docs = query.limit(1).stream()
        
        # Attempt to get the first document
        first_doc = next(docs, None)
        
        if first_doc:
            print(f"[DB Service] check_course_exists: Found existing course with ID: {first_doc.id}")
            return first_doc.id
        else:
            print("[DB Service] check_course_exists: No existing course found.")
            return None
            
    except Exception as e:
        print(f"[DB Service] check_course_exists: Error querying Firestore: {e}")
        return None # Indicate error or uncertainty

def save_course(course_data: dict):
    """
    Saves validated course data dictionary to Firestore, checking for duplicates first.

    Args:
        course_data: A dictionary containing the validated course data.

    Returns:
        The new document ID if successful.
        "DUPLICATE:{id}" if a duplicate is found (where {id} is the existing doc ID).
        None if saving fails for other reasons (DB unavailable, error).
    """
    print("[DB Service] save_course called.")
    if not db:
        print("[DB Service] Firestore client not available. Cannot save course.")
        return None
    if not isinstance(course_data, dict):
        print("[DB Service] Error: Invalid data type provided to save_course.")
        return None

    # --- Check for Duplicates --- 
    existing_id = check_course_exists(course_data)
    if existing_id:
        print(f"[DB Service] Duplicate detected. Existing ID: {existing_id}")
        return f"DUPLICATE:{existing_id}" # Return special indicator string
    if existing_id is None and not db: # Check if check_course_exists failed due to DB issue
         print("[DB Service] Cannot save course, DB unavailable during duplicate check.")
         return None
         
    # --- Proceed with Saving --- 
    try:
        data_to_save = course_data.copy()
        data_to_save['timestamp'] = firestore.SERVER_TIMESTAMP
        collection_ref = db.collection(COURSES_COLLECTION)
        _, doc_ref = collection_ref.add(data_to_save)
        print(f"[DB Service] Course data saved with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        print(f"[DB Service] Error saving course to Firestore: {e}")
        return None

def get_all_courses():
    """
    Retrieves all courses from Firestore, ordered by timestamp descending.

    Returns:
        A list of course dictionaries, each including its Firestore document ID.
        Returns an empty list if the client is unavailable or an error occurs.
    """
    print("[DB Service] get_all_courses called.")
    if not db:
        print("[DB Service] Firestore client not available. Cannot retrieve courses.")
        return []

    try:
        print(f"[DB Service] Getting collection: {COURSES_COLLECTION}")
        courses_ref = db.collection(COURSES_COLLECTION)
        print("[DB Service] Ordering query by timestamp DESC.")
        query = courses_ref.order_by('timestamp', direction=firestore.Query.DESCENDING)
        print("[DB Service] Calling query.stream()...")
        docs = query.stream()
        print("[DB Service] Query stream obtained. Iterating...")
        
        courses_list = []
        count = 0
        for doc in docs:
            count += 1
            course = doc.to_dict()
            course['id'] = doc.id 
            courses_list.append(course)
        print(f"[DB Service] Finished iterating stream. Found {count} documents.")
        print(f"[DB Service] Retrieved {len(courses_list)} courses from Firestore via service.")
        return courses_list
    except Exception as e:
        print(f"[DB Service] Error getting courses from Firestore: {e}")
        return []

def update_course(course_id: str, update_data: dict):
    """
    Updates an existing course document in Firestore.

    Args:
        course_id: The ID of the Firestore document to update.
        update_data: A dictionary containing the fields to update.
                     Should not contain 'id'. Can include a new timestamp.

    Returns:
        True if update was successful, False otherwise.
    """
    print(f"[DB Service] update_course called for ID: {course_id}")
    if not db:
        print("[DB Service] Firestore client not available. Cannot update course.")
        return False
    if not course_id or not isinstance(update_data, dict):
        print("[DB Service] Error: Invalid arguments provided to update_course.")
        return False

    try:
        print(f"[DB Service] Getting document reference for ID: {course_id}")
        doc_ref = db.collection(COURSES_COLLECTION).document(course_id)
        update_data_with_ts = update_data.copy()
        update_data_with_ts['last_modified'] = firestore.SERVER_TIMESTAMP
        print(f"[DB Service] Calling doc_ref.update() with data: {update_data_with_ts}")
        doc_ref.update(update_data_with_ts)
        print(f"[DB Service] Course data updated for ID: {course_id}")
        return True
    except Exception as e:
        print(f"[DB Service] Error updating course {course_id} in Firestore: {e}")
        return False

def delete_course(course_id: str):
    """
    Deletes a course document from Firestore.

    Args:
        course_id: The ID of the Firestore document to delete.

    Returns:
        True if deletion was successful, False otherwise.
    """
    print(f"[DB Service] delete_course called for ID: {course_id}")
    if not db:
        print("[DB Service] Firestore client not available. Cannot delete course.")
        return False
    if not course_id:
        print("[DB Service] Error: Invalid course_id provided to delete_course.")
        return False

    try:
        print(f"[DB Service] Getting document reference for ID: {course_id}")
        doc_ref = db.collection(COURSES_COLLECTION).document(course_id)
        print(f"[DB Service] Calling doc_ref.delete() for ID: {course_id}")
        doc_ref.delete()
        print(f"[DB Service] Course data deleted for ID: {course_id}")
        return True
    except Exception as e:
        print(f"[DB Service] Error deleting course {course_id} from Firestore: {e}")
        return False

# --- Other potential functions (for future milestones) ---

# def get_course_by_id(course_id: str):
#     pass

# def update_course(course_id: str, updated_data: dict):
#     pass

# def delete_course(course_id: str):
#     pass 