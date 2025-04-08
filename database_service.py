# database_service.py
"""Module to handle all interactions with Google Cloud Firestore."""

import datetime
from google.cloud import firestore

# --- Firestore Client Initialization ---

try:
    # Assumes GOOGLE_APPLICATION_CREDENTIALS environment variable is set.
    db = firestore.Client()
    print("Firestore client initialized successfully in database_service.")
except Exception as e:
    print(f"Error initializing Firestore client in database_service: {e}")
    db = None # Ensure db is None if initialization fails

COURSES_COLLECTION = 'courses' # Define collection name

# --- Service Functions ---

def save_course(course_data: dict):
    """
    Saves validated course data dictionary to Firestore.

    Args:
        course_data: A dictionary containing the validated course data.
                     It should NOT contain the 'id' or 'timestamp' yet.

    Returns:
        The new document ID if successful, None otherwise.
    """
    if not db:
        print("Firestore client not available. Cannot save course.")
        return None
    if not isinstance(course_data, dict):
        print("Error: Invalid data type provided to save_course.")
        return None

    try:
        # Prepare data for Firestore (add timestamp)
        data_to_save = course_data.copy()
        data_to_save['timestamp'] = firestore.SERVER_TIMESTAMP

        # Add document to the collection. Firestore auto-generates the ID.
        _, doc_ref = db.collection(COURSES_COLLECTION).add(data_to_save)
        print(f"Course data saved with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        print(f"Error saving course to Firestore: {e}")
        return None

def get_all_courses():
    """
    Retrieves all courses from Firestore, ordered by timestamp descending.

    Returns:
        A list of course dictionaries, each including its Firestore document ID.
        Returns an empty list if the client is unavailable or an error occurs.
    """
    if not db:
        print("Firestore client not available. Cannot retrieve courses.")
        return []

    try:
        courses_ref = db.collection(COURSES_COLLECTION)
        # Order by timestamp, newest first
        query = courses_ref.order_by('timestamp', direction=firestore.Query.DESCENDING)
        docs = query.stream()

        courses_list = []
        for doc in docs:
            course = doc.to_dict()
            course['id'] = doc.id # Add the document ID to the dictionary
            courses_list.append(course)
        print(f"Retrieved {len(courses_list)} courses from Firestore via service.")
        return courses_list
    except Exception as e:
        print(f"Error getting courses from Firestore: {e}")
        return []

# --- Other potential functions (for future milestones) ---

# def get_course_by_id(course_id: str):
#     pass

# def update_course(course_id: str, updated_data: dict):
#     pass

# def delete_course(course_id: str):
#     pass 