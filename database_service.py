# database_service.py
"""
Comprehensive Database Service for Google Cloud Firestore

This module handles all database interactions for the CEI Course Management System,
including user management, course management, term management, and course sections.
"""

import os  # Import os to check environment variables
from typing import Any, Dict, List, Optional

from google.cloud import firestore

# Import centralized logging
from logging_config import get_database_logger

# Import our data models
from models import User, validate_course_number, validate_email  # noqa: F401

# Get standardized logger
logger = get_database_logger()


def sanitize_for_logging(value: Any, max_length: int = 100) -> str:
    """
    Sanitize user input for safe logging to prevent log injection attacks.

    Args:
        value: The value to sanitize (will be converted to string)
        max_length: Maximum length of the sanitized string

    Returns:
        Sanitized string safe for logging
    """
    if value is None:
        return "None"

    # Convert to string and limit length
    str_value = str(value)[:max_length]

    # Remove/replace dangerous characters that could be used for log injection
    # Replace newlines, carriage returns, and other control characters
    sanitized = (
        str_value.replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\x00", "\\x00")  # null bytes
        .replace("\x1b", "\\x1b")  # escape sequences
    )

    # Remove any remaining control characters (ASCII 0-31 except tab, newline, carriage return)
    sanitized = "".join(
        char if ord(char) >= 32 or char in ["\t"] else f"\\x{ord(char):02x}"
        for char in sanitized
    )

    return sanitized


# --- Firestore Client Initialization ---

db = None
emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")

try:
    # The client library automatically uses FIRESTORE_EMULATOR_HOST if set.
    # No special arguments needed here for emulator detection.
    db = firestore.Client()
    if emulator_host:
        logger.info(
            f"Firestore client initialized, attempting to connect to emulator at: {emulator_host}"
        )
    else:
        logger.info("Firestore client initialized for cloud connection.")

except Exception as e:
    logger.error(f"Error initializing Firestore client: {e}")
    if emulator_host:
        logger.error(
            f"Ensure the Firestore emulator is running and accessible at {emulator_host}"
        )
    db = None  # Ensure db is None if initialization fails

# Relational model collections
USERS_COLLECTION = "users"
COURSES_COLLECTION = "courses"
TERMS_COLLECTION = "terms"
COURSE_SECTIONS_COLLECTION = "course_sections"
COURSE_OUTCOMES_COLLECTION = "course_outcomes"

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
    logger.info("[DB Service] create_user called.")
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return None

    try:
        collection_ref = db.collection(USERS_COLLECTION)
        _, doc_ref = collection_ref.add(user_data)
        logger.info(f"[DB Service] User created with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"[DB Service] Error creating user: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email address

    Args:
        email: User email address

    Returns:
        User data if found, None otherwise
    """
    logger.info(
        "[DB Service] get_user_by_email called for: %s", sanitize_for_logging(email)
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return None

    try:
        query = (
            db.collection(USERS_COLLECTION)
            .where(filter=firestore.FieldFilter("email", "==", email))
            .limit(1)
        )

        docs = query.stream()

        for doc in docs:
            user_data = doc.to_dict()
            user_data["user_id"] = doc.id
            logger.info(
                "[DB Service] Found user: %s",
                sanitize_for_logging(user_data.get("email")),
            )
            return user_data

        logger.info(
            "[DB Service] No user found with email: %s", sanitize_for_logging(email)
        )
        return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting user by email: {e}")
        return None


def get_users_by_role(role: str) -> List[Dict[str, Any]]:
    """
    Retrieve all users with a specific role.

    Args:
        role: Role to filter by

    Returns:
        List of user dictionaries
    """
    logger.info(
        "[DB Service] get_users_by_role called for role: %s", sanitize_for_logging(role)
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return []

    try:
        query = (
            db.collection(USERS_COLLECTION)
            .where(filter=firestore.FieldFilter("role", "==", role))
            .where(filter=firestore.FieldFilter("active", "==", True))
        )

        docs = query.stream()
        users = []

        for doc in docs:
            user = doc.to_dict()
            user["user_id"] = doc.id
            users.append(user)

        logger.info(
            "[DB Service] Found %d users with role: %s",
            len(users),
            sanitize_for_logging(role),
        )
        return users

    except Exception as e:
        logger.error(f"[DB Service] Error getting users by role: {e}")
        return []


def update_user_extended(user_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update an existing user.

    Args:
        user_id: ID of user to update
        update_data: Fields to update

    Returns:
        True if successful, False otherwise
    """
    logger.info(
        "[DB Service] update_user_extended called for user: %s",
        sanitize_for_logging(user_id),
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return False

    try:
        doc_ref = db.collection(USERS_COLLECTION).document(user_id)
        doc_ref.update(update_data)
        logger.info(
            "[DB Service] User %s updated successfully", sanitize_for_logging(user_id)
        )
        return True

    except Exception as e:
        logger.error(f"[DB Service] Error updating user: {e}")
        return False


# ========================================
# COURSE MANAGEMENT FUNCTIONS
# ========================================


def create_course(course_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new course.

    Args:
        course_data: Course data dictionary

    Returns:
        Course ID if successful, None otherwise
    """
    logger.info(
        "[DB Service] create_course called for: %s",
        sanitize_for_logging(course_data.get("course_number")),
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return None

    try:
        # Validate required fields
        if "course_number" not in course_data:
            logger.info("[DB Service] Missing required field: course_number")
            return None

        # Validate course number format
        if not validate_course_number(course_data["course_number"]):
            logger.info(
                "[DB Service] Invalid course number format: %s",
                sanitize_for_logging(course_data["course_number"]),
            )
            return None

        # Create course document
        collection_ref = db.collection(COURSES_COLLECTION)
        _, doc_ref = collection_ref.add(course_data)
        logger.info(f"[DB Service] Course created with ID: {doc_ref.id}")
        return doc_ref.id

    except Exception as e:
        logger.error(f"[DB Service] Error creating course: {e}")
        return None


def get_course_by_number(course_number: str) -> Optional[Dict[str, Any]]:
    """
    Get course by course number.

    Args:
        course_number: Course number (e.g., "MATH-101")

    Returns:
        Course data if found, None otherwise
    """
    logger.info(
        "[DB Service] get_course_by_number called for: %s",
        sanitize_for_logging(course_number),
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return None

    try:
        query = (
            db.collection(COURSES_COLLECTION)
            .where(filter=firestore.FieldFilter("course_number", "==", course_number))
            .limit(1)
        )

        docs = query.stream()

        for doc in docs:
            course_data = doc.to_dict()
            course_data["course_id"] = doc.id
            logger.info(
                f"[DB Service] Found course: {course_data.get('course_number')}"
            )
            return course_data

        logger.info(
            "[DB Service] No course found with number: %s",
            sanitize_for_logging(course_number),
        )
        return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting course by number: {e}")
        return None


def get_courses_by_department(department: str) -> List[Dict[str, Any]]:
    """
    Get all courses for a specific department.

    Args:
        department: Department name

    Returns:
        List of course dictionaries
    """
    logger.info(
        "[DB Service] get_courses_by_department called for: %s",
        sanitize_for_logging(department),
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return []

    try:
        query = db.collection(COURSES_COLLECTION).where(
            filter=firestore.FieldFilter("department", "==", department)
        )

        docs = query.stream()
        courses = []

        for doc in docs:
            course = doc.to_dict()
            course["course_id"] = doc.id
            courses.append(course)

        logger.info(
            "[DB Service] Found %d courses in department: %s",
            len(courses),
            sanitize_for_logging(department),
        )
        return courses

    except Exception as e:
        logger.error(f"[DB Service] Error getting courses by department: {e}")
        return []


# ========================================
# TERM MANAGEMENT FUNCTIONS
# ========================================


def create_term(term_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new term.

    Args:
        term_data: Term data dictionary

    Returns:
        Term ID if successful, None otherwise
    """
    logger.info(
        "[DB Service] create_term called for: %s",
        sanitize_for_logging(term_data.get("term_name")),
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return None

    try:
        # Validate required fields
        required_fields = ["term_name", "start_date", "end_date"]
        for field in required_fields:
            if field not in term_data:
                logger.info(
                    "[DB Service] Missing required field: %s",
                    sanitize_for_logging(field),
                )
                return None

        # Create term document
        collection_ref = db.collection(TERMS_COLLECTION)
        _, doc_ref = collection_ref.add(term_data)
        logger.info(f"[DB Service] Term created with ID: {doc_ref.id}")
        return doc_ref.id

    except Exception as e:
        logger.error(f"[DB Service] Error creating term: {e}")
        return None


def get_term_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Get term by name.

    Args:
        name: Term name (e.g., "FA24")

    Returns:
        Term data if found, None otherwise
    """
    logger.info(
        "[DB Service] get_term_by_name called for: %s", sanitize_for_logging(name)
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return None

    try:
        query = (
            db.collection(TERMS_COLLECTION)
            .where(filter=firestore.FieldFilter("term_name", "==", name))
            .limit(1)
        )

        docs = query.stream()

        for doc in docs:
            term_data = doc.to_dict()
            term_data["term_id"] = doc.id
            logger.info(
                "[DB Service] Found term: %s",
                sanitize_for_logging(term_data.get("term_name")),
            )
            return term_data

        logger.info(
            "[DB Service] No term found with name: %s", sanitize_for_logging(name)
        )
        return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting term by name: {e}")
        return None


def get_active_terms() -> List[Dict[str, Any]]:
    """
    Get all active terms.

    Returns:
        List of active term dictionaries
    """
    logger.info("[DB Service] get_active_terms called")
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return []

    try:
        query = db.collection(TERMS_COLLECTION).where(
            filter=firestore.FieldFilter("active", "==", True)
        )

        docs = query.stream()
        terms = []

        for doc in docs:
            term = doc.to_dict()
            term["term_id"] = doc.id
            terms.append(term)

        logger.info(f"[DB Service] Found {len(terms)} active terms")
        return terms

    except Exception as e:
        logger.error(f"[DB Service] Error getting active terms: {e}")
        return []


# ========================================
# COURSE SECTION MANAGEMENT FUNCTIONS
# ========================================


def create_course_section(section_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new course section.

    Args:
        section_data: Course section data dictionary

    Returns:
        Section ID if successful, None otherwise
    """
    logger.info("[DB Service] create_course_section called")
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return None

    try:
        # Validate required fields
        required_fields = ["course_id", "term_id", "section_number"]
        for field in required_fields:
            if field not in section_data:
                logger.info(
                    "[DB Service] Missing required field: %s",
                    sanitize_for_logging(field),
                )
                return None

        # Create section document
        collection_ref = db.collection(COURSE_SECTIONS_COLLECTION)
        _, doc_ref = collection_ref.add(section_data)
        logger.info(f"[DB Service] Course section created with ID: {doc_ref.id}")
        return doc_ref.id

    except Exception as e:
        logger.error(f"[DB Service] Error creating course section: {e}")
        return None


def get_sections_by_instructor(instructor_id: str) -> List[Dict[str, Any]]:
    """
    Get all sections taught by a specific instructor.

    Args:
        instructor_id: Instructor user ID

    Returns:
        List of section dictionaries
    """
    logger.info(
        "[DB Service] get_sections_by_instructor called for: %s",
        sanitize_for_logging(instructor_id),
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return []

    try:
        query = db.collection(COURSE_SECTIONS_COLLECTION).where(
            filter=firestore.FieldFilter("instructor_id", "==", instructor_id)
        )

        docs = query.stream()
        sections = []

        for doc in docs:
            section = doc.to_dict()
            section["section_id"] = doc.id
            sections.append(section)

        logger.info(
            "[DB Service] Found %d sections for instructor: %s",
            len(sections),
            sanitize_for_logging(instructor_id),
        )
        return sections

    except Exception as e:
        logger.error(f"[DB Service] Error getting sections by instructor: {e}")
        return []


def get_sections_by_term(term_id: str) -> List[Dict[str, Any]]:
    """
    Get all sections for a specific term.

    Args:
        term_id: Term ID

    Returns:
        List of section dictionaries
    """
    logger.info(
        "[DB Service] get_sections_by_term called for: %s",
        sanitize_for_logging(term_id),
    )
    if not db:
        logger.error("[DB Service] Firestore client not available.")
        return []

    try:
        query = db.collection(COURSE_SECTIONS_COLLECTION).where(
            filter=firestore.FieldFilter("term_id", "==", term_id)
        )

        docs = query.stream()
        sections = []

        for doc in docs:
            section = doc.to_dict()
            section["section_id"] = doc.id
            sections.append(section)

        logger.info(
            "[DB Service] Found %d sections for term: %s",
            len(sections),
            sanitize_for_logging(term_id),
        )
        return sections

    except Exception as e:
        logger.error(f"[DB Service] Error getting sections by term: {e}")
        return []
