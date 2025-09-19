# database_service.py
"""
Comprehensive Database Service for Google Cloud Firestore

This module handles all database interactions for the CEI Course Management System,
including user management, course management, term management, and course sections.
"""

import os  # Import os to check environment variables
import signal
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import firestore

# Import centralized logging
from logging_config import get_database_logger

# Import our data models
from models import User, validate_course_number, validate_email  # noqa: F401

# Get standardized logger
logger = get_database_logger()

# Constants
DB_CLIENT_NOT_AVAILABLE_MSG = "[DB Service] Firestore client not available."


class DatabaseTimeoutError(Exception):
    """Raised when database operations timeout"""

    pass


@contextmanager
def db_operation_timeout(seconds=5):
    """
    Context manager to enforce timeouts on database operations

    Args:
        seconds: Timeout in seconds (default 5)

    Raises:
        DatabaseTimeoutError: If operation takes longer than specified timeout
    """

    def timeout_handler(signum, frame):
        raise DatabaseTimeoutError(
            f"Database operation timed out after {seconds} seconds"
        )

    # Set the signal handler and a alarm for the specified timeout
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore the old signal handler and cancel the alarm
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)


def check_db_connection() -> bool:
    """
    Check if database connection is available with fast timeout

    Returns:
        True if database is available, False otherwise
    """
    if not db:
        logger.error("[DB Service] Firestore client not initialized")
        return False

    try:
        with db_operation_timeout(2):  # Very short timeout for connection check
            # Try a simple operation to test connection
            db.collection("_connection_test").limit(1).get()
        return True
    except DatabaseTimeoutError:
        logger.error(
            "[DB Service] Database connection check timed out - database appears to be down"
        )
        return False
    except Exception as e:
        logger.error(f"[DB Service] Database connection check failed: {e}")
        return False


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
INSTITUTIONS_COLLECTION = "institutions"
USERS_COLLECTION = "users"
COURSES_COLLECTION = "courses"
TERMS_COLLECTION = "terms"
COURSE_OFFERINGS_COLLECTION = "course_offerings"
COURSE_SECTIONS_COLLECTION = "course_sections"
COURSE_OUTCOMES_COLLECTION = "course_outcomes"

# ========================================
# INSTITUTION MANAGEMENT FUNCTIONS
# ========================================


def create_institution(institution_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new institution in the database

    Args:
        institution_data: Institution data dictionary

    Returns:
        Institution ID if successful, None otherwise
    """
    logger.info("[DB Service] create_institution called.")
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        collection_ref = db.collection(INSTITUTIONS_COLLECTION)
        _, doc_ref = collection_ref.add(institution_data)
        logger.info(f"[DB Service] Institution created with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"[DB Service] Error creating institution: {e}")
        return None


def get_institution_by_id(institution_id: str) -> Optional[Dict[str, Any]]:
    """
    Get institution by ID

    Args:
        institution_id: Institution ID

    Returns:
        Institution dictionary if found, None otherwise
    """
    logger.info(
        "[DB Service] get_institution_by_id called for: %s",
        sanitize_for_logging(institution_id),
    )
    if not check_db_connection():
        return None

    try:
        with db_operation_timeout(5):
            doc_ref = db.collection(INSTITUTIONS_COLLECTION).document(institution_id)
            doc = doc_ref.get()

            if doc.exists:
                institution = doc.to_dict()
                institution["institution_id"] = doc.id
                logger.info(
                    "[DB Service] Found institution: %s",
                    sanitize_for_logging(institution_id),
                )
                return institution
            else:
                logger.info(
                    "[DB Service] No institution found with ID: %s",
                    sanitize_for_logging(institution_id),
                )
                return None

    except DatabaseTimeoutError:
        logger.error(
            f"[DB Service] Timeout getting institution by ID: {institution_id}"
        )
        return None
    except Exception as e:
        logger.error(f"[DB Service] Error getting institution by ID: {e}")
        return None


def get_all_institutions() -> List[Dict[str, Any]]:
    """
    Get all active institutions

    Returns:
        List of institution dictionaries
    """
    logger.info("[DB Service] get_all_institutions called")
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return []

    try:
        query = db.collection(INSTITUTIONS_COLLECTION).where(
            filter=firestore.FieldFilter("is_active", "==", True)
        )

        docs = query.stream()
        institutions = []

        for doc in docs:
            institution = doc.to_dict()
            institution["institution_id"] = doc.id
            institutions.append(institution)

        logger.info("[DB Service] Found %d active institutions", len(institutions))
        return institutions

    except Exception as e:
        logger.error(f"[DB Service] Error getting all institutions: {e}")
        return []


def create_default_cei_institution() -> Optional[str]:
    """
    Create the default CEI institution record if it doesn't exist

    Returns:
        Institution ID if successful, None otherwise
    """
    logger.info("[DB Service] create_default_cei_institution called")

    # Check if CEI institution already exists
    existing_cei = get_institution_by_short_name("CEI")
    if existing_cei:
        logger.info("[DB Service] CEI institution already exists")
        return existing_cei["institution_id"]

    from datetime import datetime, timezone

    cei_data = {
        "name": "College of Eastern Idaho",
        "short_name": "CEI",
        "domain": "cei.edu",
        "timezone": "America/Denver",
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
        "billing_settings": {
            "instructor_seat_limit": 100,  # Generous limit for CEI
            "current_instructor_count": 0,
            "subscription_status": "active",
        },
        "settings": {
            "default_credit_hours": 3,
            "academic_year_start_month": 8,
            "grading_scale": "traditional",
        },
    }

    return create_institution(cei_data)


def create_new_institution(
    institution_data: Dict[str, Any], admin_user_data: Dict[str, Any]
) -> Optional[Tuple[str, str]]:
    """
    Create a new institution along with its first admin user

    Args:
        institution_data: Institution details (name, domain, etc.)
        admin_user_data: First admin user details

    Returns:
        Tuple of (institution_id, user_id) if successful, None otherwise
    """
    logger.info("[DB Service] create_new_institution called")

    try:
        from datetime import datetime, timezone

        # Create institution record
        full_institution_data = {
            **institution_data,
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
            "billing_settings": {
                "instructor_seat_limit": 10,  # Default starter limit
                "current_instructor_count": 1,  # Admin user
                "subscription_status": "trial",
            },
            "settings": {
                "default_credit_hours": 3,
                "academic_year_start_month": 8,
                "grading_scale": "traditional",
            },
        }

        institution_id = create_institution(full_institution_data)
        if not institution_id:
            logger.error("[DB Service] Failed to create institution")
            return None

        # Create admin user for this institution
        full_user_data = {
            **admin_user_data,
            "institution_id": institution_id,
            "role": "admin",
            "is_institution_admin": True,
            "created_by": None,  # Self-created
            "invitation_status": "accepted",
            "created_at": datetime.now(timezone.utc),
        }

        user_id = create_user(full_user_data)
        if not user_id:
            logger.error("[DB Service] Failed to create admin user")
            # NOTE: Institution rollback is handled by the calling service
            # to maintain transaction boundaries and error handling consistency
            return None

        logger.info(
            f"[DB Service] Successfully created institution {institution_id} with admin user {user_id}"
        )
        return (institution_id, user_id)

    except Exception as e:
        logger.error(f"[DB Service] Error creating new institution: {e}")
        return None


def get_institution_instructor_count(institution_id: str) -> int:
    """
    Get current count of instructors for an institution

    Args:
        institution_id: Institution ID

    Returns:
        Number of instructors in the institution
    """
    logger.info(
        "[DB Service] get_institution_instructor_count called for: %s",
        sanitize_for_logging(institution_id),
    )

    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return 0

    try:
        query = (
            db.collection(USERS_COLLECTION)
            .where(filter=firestore.FieldFilter("institution_id", "==", institution_id))
            .where(filter=firestore.FieldFilter("role", "==", "instructor"))
        )

        docs = list(query.stream())
        count = len(docs)

        logger.info(
            "[DB Service] Found %d instructors for institution: %s",
            count,
            sanitize_for_logging(institution_id),
        )
        return count

    except Exception as e:
        logger.error(f"[DB Service] Error getting instructor count: {e}")
        return 0


def get_institution_by_short_name(short_name: str) -> Optional[Dict[str, Any]]:
    """
    Get institution by short name (e.g., "CEI")

    Args:
        short_name: Institution short name

    Returns:
        Institution dictionary if found, None otherwise
    """
    logger.info(
        "[DB Service] get_institution_by_short_name called for: %s",
        sanitize_for_logging(short_name),
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        query = db.collection(INSTITUTIONS_COLLECTION).where(
            filter=firestore.FieldFilter("short_name", "==", short_name)
        )

        docs = list(query.stream())

        if docs:
            doc = docs[0]  # Take first match
            institution = doc.to_dict()
            institution["institution_id"] = doc.id
            logger.info(
                "[DB Service] Found institution: %s", sanitize_for_logging(short_name)
            )
            return institution
        else:
            logger.info(
                "[DB Service] No institution found with short_name: %s",
                sanitize_for_logging(short_name),
            )
            return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting institution by short_name: {e}")
        return None


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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        collection_ref = db.collection(USERS_COLLECTION)
        result = collection_ref.add(user_data)

        # Handle both tuple and direct document reference returns
        if isinstance(result, tuple):
            _, doc_ref = result
        else:
            doc_ref = result

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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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


def get_user_by_reset_token(reset_token: str) -> Optional[Dict[str, Any]]:
    """
    Get user by password reset token

    Args:
        reset_token: Password reset token to search for

    Returns:
        User data if found, None otherwise
    """
    logger.info("[DB Service] get_user_by_reset_token called")
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        with db_operation_timeout(5):
            query = (
                db.collection(USERS_COLLECTION)
                .where(
                    filter=firestore.FieldFilter(
                        "password_reset_token", "==", reset_token
                    )
                )
                .limit(1)
            )

            docs = query.stream()

            for doc in docs:
                user_data = doc.to_dict()
                user_data["user_id"] = doc.id
                logger.info("[DB Service] Found user by reset token")
                return user_data

            logger.info("[DB Service] No user found with reset token")
            return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting user by reset token: {e}")
        return None


def get_all_users(institution_id: str) -> List[Dict[str, Any]]:
    """
    Get all users for a specific institution.

    Args:
        institution_id: Institution ID to filter by

    Returns:
        List of user dictionaries
    """
    logger.info(
        "[DB Service] get_all_users called for institution: %s",
        sanitize_for_logging(institution_id),
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return []

    try:
        query = db.collection(USERS_COLLECTION).where(
            filter=firestore.FieldFilter("institution_id", "==", institution_id)
        )

        docs = query.stream()
        users = []

        for doc in docs:
            user = doc.to_dict()
            user["user_id"] = doc.id
            user["id"] = doc.id  # Add id field for consistency
            users.append(user)

        logger.info(
            "[DB Service] Found %d users for institution: %s",
            len(users),
            sanitize_for_logging(institution_id),
        )
        return users

    except Exception as e:
        logger.error(f"[DB Service] Error getting all users: {e}")
        return []


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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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
            user["id"] = doc.id  # Add id field for consistency
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


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by ID.

    Args:
        user_id: User ID

    Returns:
        User data if found, None otherwise
    """
    logger.info(
        "[DB Service] get_user_by_id called for: %s", sanitize_for_logging(user_id)
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        doc = db.collection(USERS_COLLECTION).document(user_id).get()

        if doc.exists:
            user_data = doc.to_dict()
            user_data["user_id"] = doc.id
            user_data["id"] = doc.id  # Add id field for consistency
            logger.info(
                "[DB Service] Found user: %s",
                sanitize_for_logging(user_data.get("email")),
            )
            return user_data
        else:
            logger.info(
                "[DB Service] No user found with ID: %s", sanitize_for_logging(user_id)
            )
            return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting user by ID: {e}")
        return None


def update_user(user_id: str, user_data: Dict[str, Any]) -> bool:
    """
    Update user information.

    Args:
        user_id: User ID to update
        user_data: Dictionary containing fields to update

    Returns:
        True if successful, False otherwise
    """
    logger.info(
        "[DB Service] update_user called for: %s", sanitize_for_logging(user_id)
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return False

    try:
        # Remove fields that shouldn't be updated directly
        update_data = {
            k: v
            for k, v in user_data.items()
            if k not in ["id", "user_id", "email", "created_at"]
        }

        # Add updated timestamp
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        doc_ref = db.collection(USERS_COLLECTION).document(user_id)
        doc_ref.update(update_data)

        logger.info(
            "[DB Service] Successfully updated user: %s", sanitize_for_logging(user_id)
        )
        return True

    except Exception as e:
        logger.error(f"[DB Service] Error updating user: {e}")
        return False


def update_user_active_status(user_id: str, active_user: bool) -> bool:
    """
    Update a user's active_user status for billing purposes.

    Args:
        user_id: The user ID to update
        active_user: Whether the user should be considered active for billing

    Returns:
        True if successful, False otherwise
    """
    logger.info(
        f"[DB Service] update_user_active_status called for user: {sanitize_for_logging(user_id)}"
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return False

    try:
        doc_ref = db.collection(USERS_COLLECTION).document(user_id)
        doc_ref.update(
            {
                "active_user": active_user,
                "last_modified": firestore.SERVER_TIMESTAMP,
            }
        )

        logger.info(
            f"[DB Service] Updated active_user status to {active_user} for user: {sanitize_for_logging(user_id)}"
        )
        return True

    except Exception as e:
        logger.error(f"[DB Service] Error updating user active status: {e}")
        return False


def calculate_and_update_active_users(institution_id: str) -> int:
    """
    Calculate and update active_user status for all users in an institution.

    A user is considered active if:
    - Account status is 'active' (they've accepted invite)
    - They have courses in current or upcoming terms

    Args:
        institution_id: Institution ID to process

    Returns:
        Number of users updated
    """
    logger.info(
        f"[DB Service] calculate_and_update_active_users called for institution: {sanitize_for_logging(institution_id)}"
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return 0

    try:
        # Get all users for the institution
        users_query = db.collection(USERS_COLLECTION).where(
            filter=firestore.FieldFilter("institution_id", "==", institution_id)
        )

        users_docs = users_query.stream()
        updated_count = 0

        for user_doc in users_docs:
            user = user_doc.to_dict()
            user_id = user_doc.id

            # Check if user has courses in current/upcoming terms
            # For now, we'll consider any user with sections as having active courses
            # NOTE: Term date checking will be implemented in Phase 2 when term
            # start/end dates are added to the data model
            sections_query = (
                db.collection(COURSE_SECTIONS_COLLECTION)
                .where(filter=firestore.FieldFilter("instructor_id", "==", user_id))
                .limit(1)
            )

            has_sections = len(list(sections_query.stream())) > 0

            # Calculate active status using the model's logic
            from models import User

            should_be_active = User.calculate_active_status(
                user.get("account_status", "imported"), has_sections
            )

            # Update if status has changed
            current_active = user.get("active_user", False)
            if current_active != should_be_active:
                if update_user_active_status(user_id, should_be_active):
                    updated_count += 1

        logger.info(
            f"[DB Service] Updated active status for {updated_count} users in institution: {sanitize_for_logging(institution_id)}"
        )
        return updated_count

    except Exception as e:
        logger.error(f"[DB Service] Error calculating active users: {e}")
        return 0


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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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


def get_courses_by_department(
    institution_id: str, department: str
) -> List[Dict[str, Any]]:
    """
    Get all courses for a specific department and institution.

    Args:
        institution_id: Institution ID to filter by
        department: Department name

    Returns:
        List of course dictionaries
    """
    logger.info(
        "[DB Service] get_courses_by_department called for institution: %s, department: %s",
        sanitize_for_logging(institution_id),
        sanitize_for_logging(department),
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return []

    try:
        query = (
            db.collection(COURSES_COLLECTION)
            .where(filter=firestore.FieldFilter("institution_id", "==", institution_id))
            .where(filter=firestore.FieldFilter("department", "==", department))
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


def get_all_courses(institution_id: str) -> List[Dict[str, Any]]:
    """
    Get all courses for a specific institution.

    Args:
        institution_id: Institution ID to filter by

    Returns:
        List of course dictionaries
    """
    logger.info(
        "[DB Service] get_all_courses called for institution: %s",
        sanitize_for_logging(institution_id),
    )
    if not check_db_connection():
        return []

    try:
        with db_operation_timeout(
            10
        ):  # Longer timeout for potentially large result sets
            query = db.collection(COURSES_COLLECTION).where(
                filter=firestore.FieldFilter("institution_id", "==", institution_id)
            )

            docs = query.stream()
            courses = []

            for doc in docs:
                course = doc.to_dict()
                course["course_id"] = doc.id
                courses.append(course)

            logger.info(
                "[DB Service] Found %d courses for institution: %s",
                len(courses),
                sanitize_for_logging(institution_id),
            )
            return courses

    except DatabaseTimeoutError:
        logger.error(
            f"[DB Service] Timeout getting courses for institution: {institution_id}"
        )
        return []
    except Exception as e:
        logger.error(f"[DB Service] Error getting courses for institution: {e}")
        return []


def get_all_instructors(institution_id: str) -> List[Dict[str, Any]]:
    """
    Get all users with instructor role for a specific institution.

    Args:
        institution_id: Institution ID to filter by

    Returns:
        List of instructor user dictionaries
    """
    logger.info(
        "[DB Service] get_all_instructors called for institution: %s",
        sanitize_for_logging(institution_id),
    )
    if not check_db_connection():
        return []

    try:
        with db_operation_timeout(10):
            query = (
                db.collection(USERS_COLLECTION)
                .where(filter=firestore.FieldFilter("role", "==", "instructor"))
                .where(
                    filter=firestore.FieldFilter("institution_id", "==", institution_id)
                )
            )

            docs = query.stream()
            instructors = []

            for doc in docs:
                instructor = doc.to_dict()
                instructor["user_id"] = doc.id
                instructors.append(instructor)

            logger.info(
                "[DB Service] Found %d instructors for institution: %s",
                len(instructors),
                sanitize_for_logging(institution_id),
            )
            return instructors

    except DatabaseTimeoutError:
        logger.error(
            f"[DB Service] Timeout getting instructors for institution: {institution_id}"
        )
        return []
    except Exception as e:
        logger.error(f"[DB Service] Error getting instructors for institution: {e}")
        return []


def get_all_sections(institution_id: str) -> List[Dict[str, Any]]:
    """
    Get all course sections for a specific institution.

    Args:
        institution_id: Institution ID to filter by

    Returns:
        List of section dictionaries
    """
    logger.info(
        "[DB Service] get_all_sections called for institution: %s",
        sanitize_for_logging(institution_id),
    )
    if not check_db_connection():
        return []

    try:
        with db_operation_timeout(10):
            query = db.collection(COURSE_SECTIONS_COLLECTION).where(
                filter=firestore.FieldFilter("institution_id", "==", institution_id)
            )

            docs = query.stream()
            sections = []

            for doc in docs:
                section = doc.to_dict()
                section["section_id"] = doc.id
                sections.append(section)

            logger.info(
                "[DB Service] Found %d sections for institution: %s",
                len(sections),
                sanitize_for_logging(institution_id),
            )
            return sections

    except DatabaseTimeoutError:
        logger.error(
            f"[DB Service] Timeout getting sections for institution: {institution_id}"
        )
        return []
    except Exception as e:
        logger.error(f"[DB Service] Error getting sections for institution: {e}")
        return []


# ========================================
# COURSE OFFERING MANAGEMENT FUNCTIONS
# ========================================


def create_course_offering(offering_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new course offering.

    Args:
        offering_data: Dictionary containing course offering information

    Returns:
        The offering_id if successful, None otherwise
    """
    logger.info("[DB Service] create_course_offering called")
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        # Generate offering ID if not provided
        if "offering_id" not in offering_data:
            offering_data["offering_id"] = str(uuid.uuid4())

        offering_id = offering_data["offering_id"]

        # Add timestamp
        offering_data["created_at"] = firestore.SERVER_TIMESTAMP
        offering_data["last_modified"] = firestore.SERVER_TIMESTAMP

        # Create the offering document
        doc_ref = db.collection(COURSE_OFFERINGS_COLLECTION).document(offering_id)
        doc_ref.set(offering_data)

        logger.info(
            f"[DB Service] Successfully created course offering: {sanitize_for_logging(offering_id)}"
        )
        return offering_id

    except Exception as e:
        logger.error(f"[DB Service] Error creating course offering: {e}")
        return None


def get_course_offering(offering_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a course offering by ID.

    Args:
        offering_id: The offering ID to search for

    Returns:
        Course offering dictionary if found, None otherwise
    """
    logger.info(
        "[DB Service] get_course_offering called for offering: %s",
        sanitize_for_logging(offering_id),
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        doc_ref = db.collection(COURSE_OFFERINGS_COLLECTION).document(offering_id)
        doc = doc_ref.get()

        if doc.exists:
            offering = doc.to_dict()
            offering["offering_id"] = doc.id
            logger.info(
                f"[DB Service] Found course offering: {sanitize_for_logging(offering_id)}"
            )
            return offering
        else:
            logger.info(
                f"[DB Service] Course offering not found: {sanitize_for_logging(offering_id)}"
            )
            return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting course offering: {e}")
        return None


def get_course_offering_by_course_and_term(
    course_id: str, term_id: str, institution_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a course offering by course and term.

    Args:
        course_id: The course ID
        term_id: The term ID
        institution_id: The institution ID

    Returns:
        Course offering dictionary if found, None otherwise
    """
    logger.info(
        "[DB Service] get_course_offering_by_course_and_term called for course: %s, term: %s",
        sanitize_for_logging(course_id),
        sanitize_for_logging(term_id),
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        query = (
            db.collection(COURSE_OFFERINGS_COLLECTION)
            .where(filter=firestore.FieldFilter("course_id", "==", course_id))
            .where(filter=firestore.FieldFilter("term_id", "==", term_id))
            .where(filter=firestore.FieldFilter("institution_id", "==", institution_id))
            .limit(1)
        )

        docs = query.stream()
        for doc in docs:
            offering = doc.to_dict()
            offering["offering_id"] = doc.id
            logger.info(
                f"[DB Service] Found course offering: {sanitize_for_logging(doc.id)}"
            )
            return offering

        logger.info(
            "[DB Service] No course offering found for course: %s, term: %s",
            sanitize_for_logging(course_id),
            sanitize_for_logging(term_id),
        )
        return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting course offering: {e}")
        return None


def get_all_course_offerings(institution_id: str) -> List[Dict[str, Any]]:
    """
    Get all course offerings for a specific institution.

    Args:
        institution_id: Institution ID to filter by

    Returns:
        List of course offering dictionaries
    """
    logger.info(
        "[DB Service] get_all_course_offerings called for institution: %s",
        sanitize_for_logging(institution_id),
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return []

    try:
        query = db.collection(COURSE_OFFERINGS_COLLECTION).where(
            filter=firestore.FieldFilter("institution_id", "==", institution_id)
        )

        docs = query.stream()
        offerings = []

        for doc in docs:
            offering = doc.to_dict()
            offering["offering_id"] = doc.id
            offerings.append(offering)

        logger.info(
            f"[DB Service] Retrieved {len(offerings)} course offerings for institution: {sanitize_for_logging(institution_id)}"
        )
        return offerings

    except Exception as e:
        logger.error(f"[DB Service] Error getting course offerings: {e}")
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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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


def get_active_terms(institution_id: str) -> List[Dict[str, Any]]:
    """
    Get all active terms for a specific institution.

    Args:
        institution_id: Institution ID to filter by

    Returns:
        List of active term dictionaries
    """
    logger.info(
        "[DB Service] get_active_terms called for institution: %s",
        sanitize_for_logging(institution_id),
    )
    if not check_db_connection():
        return []

    try:
        with db_operation_timeout(10):
            # For now, get all terms for the institution (not filtering by active status)
            # NOTE: Active status filtering will be added when term lifecycle
            # management is implemented in future sprint
            query = db.collection(TERMS_COLLECTION).where(
                filter=firestore.FieldFilter("institution_id", "==", institution_id)
            )

            docs = query.stream()
            terms = []

            for doc in docs:
                term = doc.to_dict()
                term["term_id"] = doc.id
                terms.append(term)

            logger.info(
                "[DB Service] Found %d active terms for institution: %s",
                len(terms),
                sanitize_for_logging(institution_id),
            )
            return terms

    except DatabaseTimeoutError:
        logger.error(
            f"[DB Service] Timeout getting active terms for institution: {institution_id}"
        )
        return []
    except Exception as e:
        logger.error(f"[DB Service] Error getting active terms for institution: {e}")
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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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


def get_user_by_verification_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email verification token

    Args:
        token: Email verification token

    Returns:
        User document or None if not found
    """
    logger.info("[DB Service] get_user_by_verification_token called")
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        with db_operation_timeout(10):
            check_db_connection()
            query = (
                db.collection(USERS_COLLECTION)
                .where(
                    filter=firestore.FieldFilter(
                        "email_verification_token", "==", token
                    )
                )
                .limit(1)
            )
            docs = query.stream()

            for doc in docs:
                user_data = doc.to_dict()
                user_data["id"] = doc.id
                logger.info(
                    f"[DB Service] Found user by verification token: {user_data['id']}"
                )
                return user_data

            logger.info("[DB Service] No user found with verification token")
            return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting user by verification token: {e}")
        return None


def create_program(program_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new program

    Args:
        program_data: Program data dictionary

    Returns:
        Program ID if successful, None otherwise
    """
    logger.info("[DB Service] create_program called")
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        with db_operation_timeout(15):
            check_db_connection()
            program_id = program_data.get("id")
            if not program_id:
                raise ValueError("Program data must include 'id' field")

            # Remove id from data before storing
            data_to_store = {k: v for k, v in program_data.items() if k != "id"}

            programs_ref = db.collection("programs")
            programs_ref.document(program_id).set(data_to_store)

            logger.info(f"[DB Service] Created program: {program_id}")
            return program_id

    except Exception as e:
        logger.error(f"[DB Service] Error creating program: {e}")
        return None


def get_programs_by_institution(institution_id: str) -> List[Dict[str, Any]]:
    """
    Get all programs for a specific institution

    Args:
        institution_id: Institution identifier

    Returns:
        List of program dictionaries
    """
    logger.info(
        f"[DB Service] get_programs_by_institution called for: {institution_id}"
    )

    try:
        # Temporarily disable timeout to fix threading issue
        # with db_operation_timeout():
        programs_ref = db.collection("programs")
        query = programs_ref.where("institution_id", "==", institution_id)
        programs = []

        for doc in query.stream():
            program_data = doc.to_dict()
            program_data["id"] = doc.id
            programs.append(program_data)

        logger.info(
            f"[DB Service] Retrieved {len(programs)} programs for institution {institution_id}"
        )
        return programs

    except Exception as e:
        logger.error(
            f"[DB Service] Error retrieving programs for institution {institution_id}: {e}"
        )
        return []


def get_program_by_id(program_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a program by its ID

    Args:
        program_id: Program identifier

    Returns:
        Program dictionary if found, None otherwise
    """
    logger.info(f"[DB Service] get_program_by_id called for: {program_id}")

    try:
        with db_operation_timeout():
            program_ref = db.collection("programs").document(program_id)
            program_doc = program_ref.get()

            if program_doc.exists:
                program_data = program_doc.to_dict()
                program_data["id"] = program_doc.id
                logger.info(f"[DB Service] Retrieved program: {program_id}")
                return program_data
            else:
                logger.info(f"[DB Service] Program not found: {program_id}")
                return None

    except Exception as e:
        logger.error(f"[DB Service] Error retrieving program {program_id}: {e}")
        return None


def get_program_by_name_and_institution(
    program_name: str, institution_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a program by its name and institution ID (for idempotent seeding)

    Args:
        program_name: Program name
        institution_id: Institution identifier

    Returns:
        Program dictionary if found, None otherwise
    """
    logger.info(
        f"[DB Service] get_program_by_name_and_institution called for: {program_name} in {institution_id}"
    )

    try:
        with db_operation_timeout():
            programs_ref = db.collection("programs")
            query = programs_ref.where("name", "==", program_name).where(
                "institution_id", "==", institution_id
            )
            docs = query.limit(1).get()

            if docs:
                program_doc = docs[0]
                program_data = program_doc.to_dict()
                program_data["id"] = program_doc.id
                logger.info(f"[DB Service] Found program: {program_name}")
                return program_data
            else:
                logger.info(f"[DB Service] Program not found: {program_name}")
                return None

    except Exception as e:
        logger.error(f"[DB Service] Error finding program {program_name}: {e}")
        return None


def update_program(program_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update a program's information

    Args:
        program_id: Program identifier
        updates: Dictionary of fields to update

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"[DB Service] update_program called for: {program_id}")

    try:
        with db_operation_timeout():
            program_ref = db.collection("programs").document(program_id)

            # Add timestamp
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            program_ref.update(updates)
            logger.info(f"[DB Service] Updated program: {program_id}")
            return True

    except Exception as e:
        logger.error(f"[DB Service] Error updating program {program_id}: {e}")
        return False


def delete_program(program_id: str, reassign_to_program_id: str) -> bool:
    """
    Delete a program and reassign its courses to another program

    Args:
        program_id: Program identifier to delete
        reassign_to_program_id: Program ID to reassign courses to

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"[DB Service] delete_program called for: {program_id}")

    try:
        with db_operation_timeout():
            # First, reassign all courses from this program to the default program
            courses_ref = db.collection("courses")
            query = courses_ref.where("program_ids", "array_contains", program_id)

            batch = db.batch()

            for doc in query.stream():
                course_data = doc.to_dict()
                program_ids = course_data.get("program_ids", [])

                # Remove the deleted program and add the reassignment program
                if program_id in program_ids:
                    program_ids.remove(program_id)

                if reassign_to_program_id not in program_ids:
                    program_ids.append(reassign_to_program_id)

                # Update the course
                batch.update(
                    doc.reference,
                    {
                        "program_ids": program_ids,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            # Delete the program
            program_ref = db.collection("programs").document(program_id)
            batch.delete(program_ref)

            # Commit all changes
            batch.commit()

            logger.info(
                f"[DB Service] Deleted program {program_id} and reassigned courses to {reassign_to_program_id}"
            )
            return True

    except Exception as e:
        logger.error(f"[DB Service] Error deleting program {program_id}: {e}")
        return False


def get_courses_by_program(program_id: str) -> List[Dict[str, Any]]:
    """
    Get all courses associated with a specific program

    Args:
        program_id: Program identifier

    Returns:
        List of course dictionaries
    """
    logger.info(f"[DB Service] get_courses_by_program called for: {program_id}")

    try:
        with db_operation_timeout():
            courses_ref = db.collection("courses")
            query = courses_ref.where("program_ids", "array_contains", program_id)
            courses = []

            for doc in query.stream():
                course_data = doc.to_dict()
                course_data["id"] = doc.id
                courses.append(course_data)

            logger.info(
                f"[DB Service] Retrieved {len(courses)} courses for program {program_id}"
            )
            return courses

    except Exception as e:
        logger.error(
            f"[DB Service] Error retrieving courses for program {program_id}: {e}"
        )
        return []


def get_unassigned_courses(institution_id: str) -> List[Dict[str, Any]]:
    """
    Get all courses that are not assigned to any program within an institution.
    These courses need default program assignment.

    Args:
        institution_id: Institution identifier

    Returns:
        List of unassigned course dictionaries
    """
    logger.info(
        f"[DB Service] get_unassigned_courses called for institution: {institution_id}"
    )

    try:
        with db_operation_timeout():
            courses_ref = db.collection("courses")
            query = courses_ref.where("institution_id", "==", institution_id)
            unassigned_courses = []

            for doc in query.stream():
                course_data = doc.to_dict()
                course_data["id"] = doc.id

                # Check if course has no program assignments
                program_ids = course_data.get("program_ids", [])
                if not program_ids or len(program_ids) == 0:
                    unassigned_courses.append(course_data)

            logger.info(
                f"[DB Service] Found {len(unassigned_courses)} unassigned courses for institution {institution_id}"
            )
            return unassigned_courses

    except Exception as e:
        logger.error(
            f"[DB Service] Error retrieving unassigned courses for institution {institution_id}: {e}"
        )
        return []


def assign_course_to_default_program(course_id: str, institution_id: str) -> bool:
    """
    Assign a course to the default program for an institution.
    Creates a "General" program if none exists.

    Args:
        course_id: Course identifier
        institution_id: Institution identifier

    Returns:
        True if assignment successful, False otherwise
    """
    logger.info(
        f"[DB Service] assign_course_to_default_program called for course: {course_id}"
    )

    try:
        with db_operation_timeout():
            # Look for existing "General" program
            programs_ref = db.collection("programs")
            query = programs_ref.where("institution_id", "==", institution_id).where(
                "name", "==", "General"
            )

            general_program_id = None
            for doc in query.stream():
                general_program_id = doc.id
                break

            # Create General program if it doesn't exist
            if not general_program_id:
                general_program_data = {
                    "name": "General",
                    "description": "Default program for unassigned courses",
                    "institution_id": institution_id,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                doc_ref = programs_ref.add(general_program_data)
                general_program_id = doc_ref[1].id
                logger.info(
                    f"[DB Service] Created default 'General' program: {general_program_id}"
                )

            # Assign course to the General program
            if general_program_id:
                success = add_course_to_program(course_id, general_program_id)
                if success:
                    logger.info(
                        f"[DB Service] Assigned course {course_id} to default program {general_program_id}"
                    )
                return success

            return False

    except Exception as e:
        logger.error(
            f"[DB Service] Error assigning course {course_id} to default program: {e}"
        )
        return False


def add_course_to_program(course_id: str, program_id: str) -> bool:
    """
    Add a course to a program

    Args:
        course_id: Course identifier
        program_id: Program identifier

    Returns:
        True if successful, False otherwise
    """
    logger.info(
        f"[DB Service] add_course_to_program called: course={course_id}, program={program_id}"
    )

    try:
        with db_operation_timeout():
            course_ref = db.collection("courses").document(course_id)
            course_doc = course_ref.get()

            if not course_doc.exists:
                logger.error(f"[DB Service] Course not found: {course_id}")
                return False

            course_data = course_doc.to_dict()
            program_ids = course_data.get("program_ids", [])

            # Add program if not already present
            if program_id not in program_ids:
                program_ids.append(program_id)
                course_ref.update(
                    {
                        "program_ids": program_ids,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                logger.info(
                    f"[DB Service] Added course {course_id} to program {program_id}"
                )
            else:
                logger.info(
                    f"[DB Service] Course {course_id} already in program {program_id}"
                )

            return True

    except Exception as e:
        logger.error(
            f"[DB Service] Error adding course {course_id} to program {program_id}: {e}"
        )
        return False


def remove_course_from_program(
    course_id: str, program_id: str, default_program_id: Optional[str] = None
) -> bool:
    """
    Remove a course from a program, optionally assigning to default program if orphaned

    Args:
        course_id: Course identifier
        program_id: Program identifier to remove from
        default_program_id: Default program ID to assign if course becomes orphaned

    Returns:
        True if successful, False otherwise
    """
    logger.info(
        f"[DB Service] remove_course_from_program called: course={course_id}, program={program_id}"
    )

    try:
        with db_operation_timeout():
            course_ref = db.collection("courses").document(course_id)
            course_doc = course_ref.get()

            if not course_doc.exists:
                logger.error(f"[DB Service] Course not found: {course_id}")
                return False

            course_data = course_doc.to_dict()
            program_ids = course_data.get("program_ids", [])

            # Remove program if present
            if program_id in program_ids:
                program_ids.remove(program_id)

                # If course becomes orphaned and default program provided, add to default
                if not program_ids and default_program_id:
                    program_ids.append(default_program_id)
                    logger.info(
                        f"[DB Service] Course {course_id} orphaned, assigned to default program {default_program_id}"
                    )

                course_ref.update(
                    {
                        "program_ids": program_ids,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                logger.info(
                    f"[DB Service] Removed course {course_id} from program {program_id}"
                )
            else:
                logger.info(
                    f"[DB Service] Course {course_id} not in program {program_id}"
                )

            return True

    except Exception as e:
        logger.error(
            f"[DB Service] Error removing course {course_id} from program {program_id}: {e}"
        )
        return False


def bulk_add_courses_to_program(
    course_ids: List[str], program_id: str
) -> Dict[str, Any]:
    """
    Add multiple courses to a program in a batch operation

    Args:
        course_ids: List of course identifiers
        program_id: Program identifier

    Returns:
        Dictionary with success/failure counts and details
    """
    logger.info(
        f"[DB Service] bulk_add_courses_to_program called: {len(course_ids)} courses to program {program_id}"
    )

    result: Dict[str, Any] = {
        "success_count": 0,
        "failure_count": 0,
        "failures": [],
        "already_assigned": 0,
    }

    try:
        with db_operation_timeout():
            batch = db.batch()

            for course_id in course_ids:
                try:
                    course_ref = db.collection("courses").document(course_id)
                    course_doc = course_ref.get()

                    if not course_doc.exists:
                        result["failure_count"] += 1
                        result["failures"].append(
                            {"course_id": course_id, "error": "Course not found"}
                        )
                        continue

                    course_data = course_doc.to_dict()
                    program_ids = course_data.get("program_ids", [])

                    if program_id in program_ids:
                        result["already_assigned"] += 1
                        continue

                    program_ids.append(program_id)
                    batch.update(
                        course_ref,
                        {
                            "program_ids": program_ids,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    result["success_count"] += 1

                except Exception as e:
                    result["failure_count"] += 1
                    result["failures"].append({"course_id": course_id, "error": str(e)})

            # Commit all changes
            if result["success_count"] > 0:
                batch.commit()
                logger.info(
                    f"[DB Service] Bulk added {result['success_count']} courses to program {program_id}"
                )

            return result

    except Exception as e:
        logger.error(f"[DB Service] Error in bulk_add_courses_to_program: {e}")
        result["failure_count"] = len(course_ids)
        result["success_count"] = 0
        result["failures"] = [{"course_id": cid, "error": str(e)} for cid in course_ids]
        return result


def bulk_remove_courses_from_program(
    course_ids: List[str], program_id: str, default_program_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Remove multiple courses from a program in a batch operation

    Args:
        course_ids: List of course identifiers
        program_id: Program identifier to remove from
        default_program_id: Default program ID to assign if courses become orphaned

    Returns:
        Dictionary with success/failure counts and details
    """
    logger.info(
        f"[DB Service] bulk_remove_courses_from_program called: {len(course_ids)} courses from program {program_id}"
    )

    result: Dict[str, Any] = {
        "success_count": 0,
        "failure_count": 0,
        "failures": [],
        "not_assigned": 0,
        "orphaned_assigned_to_default": 0,
    }

    try:
        with db_operation_timeout():
            batch = db.batch()

            for course_id in course_ids:
                try:
                    course_ref = db.collection("courses").document(course_id)
                    course_doc = course_ref.get()

                    if not course_doc.exists:
                        result["failure_count"] += 1
                        result["failures"].append(
                            {"course_id": course_id, "error": "Course not found"}
                        )
                        continue

                    course_data = course_doc.to_dict()
                    program_ids = course_data.get("program_ids", [])

                    if program_id not in program_ids:
                        result["not_assigned"] += 1
                        continue

                    program_ids.remove(program_id)

                    # If course becomes orphaned and default program provided
                    if not program_ids and default_program_id:
                        program_ids.append(default_program_id)
                        result["orphaned_assigned_to_default"] += 1

                    batch.update(
                        course_ref,
                        {
                            "program_ids": program_ids,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    result["success_count"] += 1

                except Exception as e:
                    result["failure_count"] += 1
                    result["failures"].append({"course_id": course_id, "error": str(e)})

            # Commit all changes
            if result["success_count"] > 0:
                batch.commit()
                logger.info(
                    f"[DB Service] Bulk removed {result['success_count']} courses from program {program_id}"
                )

            return result

    except Exception as e:
        logger.error(f"[DB Service] Error in bulk_remove_courses_from_program: {e}")
        result["failure_count"] = len(course_ids)
        result["success_count"] = 0
        result["failures"] = [{"course_id": cid, "error": str(e)} for cid in course_ids]
        return result


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
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
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


# Invitation Management Methods


def create_invitation(invitation_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new user invitation

    Args:
        invitation_data: Invitation data dictionary

    Returns:
        Invitation ID if created successfully, None otherwise
    """
    logger.info("[DB Service] create_invitation called")
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        with db_operation_timeout(10):
            # Add timestamps
            invitation_data["created_at"] = datetime.now(timezone.utc).isoformat()
            invitation_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            doc_ref = db.collection("invitations").add(invitation_data)
            invitation_id = doc_ref[1].id

            logger.info(f"[DB Service] Created invitation with ID: {invitation_id}")
            return invitation_id

    except Exception as e:
        logger.error(f"[DB Service] Error creating invitation: {e}")
        return None


def get_invitation_by_id(invitation_id: str) -> Optional[Dict[str, Any]]:
    """
    Get invitation by ID

    Args:
        invitation_id: Invitation ID

    Returns:
        Invitation dictionary if found, None otherwise
    """
    logger.info(
        f"[DB Service] get_invitation_by_id called for: {sanitize_for_logging(invitation_id)}"
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        with db_operation_timeout(10):
            doc_ref = db.collection("invitations").document(invitation_id)
            doc = doc_ref.get()

            if doc.exists:
                invitation = doc.to_dict()
                invitation["id"] = doc.id
                logger.info(f"[DB Service] Found invitation: {invitation_id}")
                return invitation
            else:
                logger.info(
                    f"[DB Service] No invitation found with ID: {invitation_id}"
                )
                return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting invitation by ID: {e}")
        return None


def get_invitation_by_token(invitation_token: str) -> Optional[Dict[str, Any]]:
    """
    Get invitation by token

    Args:
        invitation_token: Invitation token

    Returns:
        Invitation dictionary if found, None otherwise
    """
    logger.info("[DB Service] get_invitation_by_token called")
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        with db_operation_timeout(10):
            query = db.collection("invitations").where(
                filter=firestore.FieldFilter("token", "==", invitation_token)
            )

            docs = list(query.stream())

            if docs:
                doc = docs[0]  # Take first match
                invitation = doc.to_dict()
                invitation["id"] = doc.id
                logger.info("[DB Service] Found invitation by token")
                return invitation
            else:
                logger.info("[DB Service] No invitation found with token")
                return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting invitation by token: {e}")
        return None


def get_invitation_by_email(
    invitee_email: str, institution_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get invitation by email and institution

    Args:
        invitee_email: Email address of invitee
        institution_id: Institution ID

    Returns:
        Invitation dictionary if found, None otherwise
    """
    logger.info(
        f"[DB Service] get_invitation_by_email called for: {sanitize_for_logging(invitee_email)}"
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return None

    try:
        with db_operation_timeout(10):
            query = (
                db.collection("invitations")
                .where(filter=firestore.FieldFilter("email", "==", invitee_email))
                .where(
                    filter=firestore.FieldFilter("institution_id", "==", institution_id)
                )
            )

            docs = list(query.stream())

            if docs:
                doc = docs[0]  # Take first match
                invitation = doc.to_dict()
                invitation["id"] = doc.id
                logger.info(
                    f"[DB Service] Found invitation for email: {sanitize_for_logging(invitee_email)}"
                )
                return invitation
            else:
                logger.info(
                    f"[DB Service] No invitation found for email: {sanitize_for_logging(invitee_email)}"
                )
                return None

    except Exception as e:
        logger.error(f"[DB Service] Error getting invitation by email: {e}")
        return None


def update_invitation(invitation_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update an invitation

    Args:
        invitation_id: Invitation ID
        updates: Dictionary of fields to update

    Returns:
        True if updated successfully, False otherwise
    """
    logger.info(
        f"[DB Service] update_invitation called for: {sanitize_for_logging(invitation_id)}"
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return False

    try:
        with db_operation_timeout(10):
            # Add updated timestamp
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()

            doc_ref = db.collection("invitations").document(invitation_id)
            doc_ref.update(updates)

            logger.info(f"[DB Service] Updated invitation: {invitation_id}")
            return True

    except Exception as e:
        logger.error(f"[DB Service] Error updating invitation: {e}")
        return False


def list_invitations(
    institution_id: str, status: Optional[str] = None, limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List invitations for an institution

    Args:
        institution_id: Institution ID
        status: Optional status filter
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of invitation dictionaries
    """
    logger.info(
        f"[DB Service] list_invitations called for institution: {sanitize_for_logging(institution_id)}"
    )
    if not db:
        logger.error(DB_CLIENT_NOT_AVAILABLE_MSG)
        return []

    try:
        with db_operation_timeout(10):
            query = db.collection("invitations").where(
                filter=firestore.FieldFilter("institution_id", "==", institution_id)
            )

            # Add status filter if provided
            if status:
                query = query.where(
                    filter=firestore.FieldFilter("status", "==", status)
                )

            # Order by invited_at descending
            query = query.order_by("invited_at", direction=firestore.Query.DESCENDING)

            # Apply pagination
            if offset > 0:
                query = query.offset(offset)
            query = query.limit(limit)

            docs = list(query.stream())
            invitations = []

            for doc in docs:
                invitation = doc.to_dict()
                invitation["id"] = doc.id
                invitations.append(invitation)

            logger.info(
                f"[DB Service] Found {len(invitations)} invitations for institution: {sanitize_for_logging(institution_id)}"
            )
            return invitations

    except Exception as e:
        logger.error(f"[DB Service] Error listing invitations: {e}")
        return []
