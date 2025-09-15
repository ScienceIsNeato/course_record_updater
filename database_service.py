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
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import firestore

# Import centralized logging
from logging_config import get_database_logger

# Import our data models
from models import User, validate_course_number, validate_email  # noqa: F401

# Get standardized logger
logger = get_database_logger()


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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
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
            # TODO: Should rollback institution creation here
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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
        return 0

    try:
        # Get all users for the institution
        users_query = db.collection(USERS_COLLECTION).where(
            filter=firestore.FieldFilter("institution_id", "==", institution_id)
        )

        users_docs = users_query.stream()
        updated_count = 0

        # Get current date for term comparison
        from datetime import datetime, timezone

        current_date = datetime.now(timezone.utc)

        for user_doc in users_docs:
            user = user_doc.to_dict()
            user_id = user_doc.id

            # Check if user has accepted invite
            account_active = user.get("account_status") == "active"

            # Check if user has courses in current/upcoming terms
            # For now, we'll consider any user with sections as having active courses
            # TODO: Implement proper term date checking
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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
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
        logger.error("[DB Service] Firestore client not available.")
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
            # TODO: Add active field to terms and filter properly
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
