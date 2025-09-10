# database_service.py
"""Module to handle all interactions with Google Cloud Firestore."""

import os # Import os to check environment variables
from typing import Dict, Optional, Any
from google.cloud import firestore

# Import our data models
from models import (
    User, validate_email
)

# --- Firestore Client Initialization ---

db = None
emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")

try:
    # The client library automatically uses FIRESTORE_EMULATOR_HOST if set.
    # No special arguments needed here for emulator detection.
    db = firestore.Client()
    if emulator_host:
        print(f"Firestore client initialized, attempting to connect to emulator at: {emulator_host}")
    else:
        print("Firestore client initialized for cloud connection.")

except Exception as e:
    print(f"Error initializing Firestore client: {e}")
    if emulator_host:
        print(f"Ensure the Firestore emulator is running and accessible at {emulator_host}")
    db = None # Ensure db is None if initialization fails

# Relational model collections
USERS_COLLECTION = 'users'
COURSES_COLLECTION = 'courses'
TERMS_COLLECTION = 'terms'
COURSE_SECTIONS_COLLECTION = 'course_sections'
COURSE_OUTCOMES_COLLECTION = 'course_outcomes'

# ========================================
# USER MANAGEMENT FUNCTIONS
# ========================================

def create_user(user_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new user in the database
    
    Args:
        user_data: User data dictionary
        
    Returns:
        User ID if successful, None otherwise
    """
    print("[DB Service] create_user called.")
    if not db:
        print("[DB Service] Firestore client not available.")
        return None
    
    try:
        collection_ref = db.collection(USERS_COLLECTION)
        _, doc_ref = collection_ref.add(user_data)
        print(f"[DB Service] User created with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        print(f"[DB Service] Error creating user: {e}")
        return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email address
    
    Args:
        email: User email address
        
    Returns:
        User data if found, None otherwise
    """
    print(f"[DB Service] get_user_by_email called for: {email}")
    if not db:
        print("[DB Service] Firestore client not available.")
        return None
    
    try:
        query = db.collection(USERS_COLLECTION).where(
            filter=firestore.FieldFilter("email", "==", email)
        ).limit(1)
        
        docs = query.stream()
        
        for doc in docs:
            user_data = doc.to_dict()
            user_data['user_id'] = doc.id
            print(f"[DB Service] Found user: {user_data.get('email')}")
            return user_data
        
        print(f"[DB Service] No user found with email: {email}")
        return None
        
    except Exception as e:
        print(f"[DB Service] Error getting user by email: {e}")
        return None