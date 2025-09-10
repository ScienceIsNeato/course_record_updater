"""
Extended Database Service Functions for Relational Model

This module contains the additional database functions for the new relational
data model. It imports the base database service and extends it with new
entity management functions.
"""

from typing import Any, Dict, List, Optional

from google.cloud import firestore

# Collection names (import from main service)
# Import base database service components
from database_service import (
    COURSE_OUTCOMES_COLLECTION,
    COURSE_SECTIONS_COLLECTION,
    COURSES_COLLECTION,
    TERMS_COLLECTION,
    USERS_COLLECTION,
    db,
)
from models import Course, CourseSection, Term, validate_course_number

# ========================================
# ADDITIONAL USER MANAGEMENT FUNCTIONS
# ========================================


def get_users_by_role(role: str) -> List[Dict[str, Any]]:
    """
    Retrieve all users with a specific role.

    Args:
        role: Role to filter by

    Returns:
        List of user dictionaries
    """
    print(f"[DB Service Extended] get_users_by_role called for role: {role}")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
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

        print(f"[DB Service Extended] Found {len(users)} users with role: {role}")
        return users

    except Exception as e:
        print(f"[DB Service Extended] Error getting users by role: {e}")
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
    print(f"[DB Service Extended] update_user called for ID: {user_id}")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return False

    try:
        doc_ref = db.collection(USERS_COLLECTION).document(user_id)
        update_data_with_ts = update_data.copy()
        update_data_with_ts["last_modified"] = firestore.SERVER_TIMESTAMP

        doc_ref.update(update_data_with_ts)
        print(f"[DB Service Extended] User updated: {user_id}")
        return True

    except Exception as e:
        print(f"[DB Service Extended] Error updating user: {e}")
        return False


# ========================================
# COURSE MANAGEMENT FUNCTIONS
# ========================================


def create_course(course_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new course in the relational model.

    Args:
        course_data: Course information dictionary

    Returns:
        Course ID if successful, None if failed
    """
    print(f"[DB Service Extended] create_course called.")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return None

    try:
        # Validate required fields
        required_fields = ["course_number", "course_title", "department"]
        if not all(field in course_data for field in required_fields):
            print(f"[DB Service Extended] Missing required fields: {required_fields}")
            return None

        # Validate course number format
        if not validate_course_number(course_data["course_number"]):
            print(
                f"[DB Service Extended] Invalid course number format: {course_data['course_number']}"
            )
            return None

        # Check if course already exists
        existing_course = get_course_by_number(course_data["course_number"])
        if existing_course:
            print(
                f"[DB Service Extended] Course already exists: {course_data['course_number']}"
            )
            return None

        # Create course schema
        course_record = Course.create_schema(
            course_number=course_data["course_number"],
            course_title=course_data["course_title"],
            department=course_data["department"],
            credit_hours=course_data.get("credit_hours", 3),
            active=course_data.get("active", True),
        )

        # Save to Firestore
        course_record["created_at"] = firestore.SERVER_TIMESTAMP
        course_record["last_modified"] = firestore.SERVER_TIMESTAMP

        collection_ref = db.collection(COURSES_COLLECTION)
        _, doc_ref = collection_ref.add(course_record)

        print(f"[DB Service Extended] Course created with ID: {doc_ref.id}")
        return doc_ref.id

    except Exception as e:
        print(f"[DB Service Extended] Error creating course: {e}")
        return None


def get_course_by_number(course_number: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve course by course number.

    Args:
        course_number: Course number to search for (e.g., "ACC-201")

    Returns:
        Course dictionary if found, None otherwise
    """
    print(f"[DB Service Extended] get_course_by_number called for: {course_number}")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return None

    try:
        query = (
            db.collection(COURSES_COLLECTION)
            .where(
                filter=firestore.FieldFilter(
                    "course_number", "==", course_number.upper().strip()
                )
            )
            .limit(1)
        )

        docs = query.stream()
        first_doc = next(docs, None)

        if first_doc:
            course = first_doc.to_dict()
            course["course_id"] = first_doc.id
            print(f"[DB Service Extended] Found course: {course['course_number']}")
            return course
        else:
            print(f"[DB Service Extended] No course found: {course_number}")
            return None

    except Exception as e:
        print(f"[DB Service Extended] Error getting course by number: {e}")
        return None


def get_courses_by_department(department: str) -> List[Dict[str, Any]]:
    """
    Retrieve all courses in a department.

    Args:
        department: Department name

    Returns:
        List of course dictionaries
    """
    print(f"[DB Service Extended] get_courses_by_department called for: {department}")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return []

    try:
        query = (
            db.collection(COURSES_COLLECTION)
            .where(filter=firestore.FieldFilter("department", "==", department))
            .where(filter=firestore.FieldFilter("active", "==", True))
        )

        docs = query.stream()
        courses = []

        for doc in docs:
            course = doc.to_dict()
            course["course_id"] = doc.id
            courses.append(course)

        print(f"[DB Service Extended] Found {len(courses)} courses in {department}")
        return courses

    except Exception as e:
        print(f"[DB Service Extended] Error getting courses by department: {e}")
        return []


# ========================================
# TERM MANAGEMENT FUNCTIONS
# ========================================


def create_term(term_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new academic term.

    Args:
        term_data: Term information dictionary

    Returns:
        Term ID if successful, None if failed
    """
    print(f"[DB Service Extended] create_term called.")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return None

    try:
        # Validate required fields
        required_fields = ["name", "start_date", "end_date", "assessment_due_date"]
        if not all(field in term_data for field in required_fields):
            print(f"[DB Service Extended] Missing required fields: {required_fields}")
            return None

        # Check if term already exists
        existing_term = get_term_by_name(term_data["name"])
        if existing_term:
            print(f"[DB Service Extended] Term already exists: {term_data['name']}")
            return None

        # Create term schema
        term_record = Term.create_schema(
            name=term_data["name"],
            start_date=term_data["start_date"],
            end_date=term_data["end_date"],
            assessment_due_date=term_data["assessment_due_date"],
            active=term_data.get("active", True),
        )

        # Save to Firestore
        term_record["created_at"] = firestore.SERVER_TIMESTAMP
        term_record["last_modified"] = firestore.SERVER_TIMESTAMP

        collection_ref = db.collection(TERMS_COLLECTION)
        _, doc_ref = collection_ref.add(term_record)

        print(f"[DB Service Extended] Term created with ID: {doc_ref.id}")
        return doc_ref.id

    except Exception as e:
        print(f"[DB Service Extended] Error creating term: {e}")
        return None


def get_term_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve term by name.

    Args:
        name: Term name (e.g., "2024 Fall")

    Returns:
        Term dictionary if found, None otherwise
    """
    print(f"[DB Service Extended] get_term_by_name called for: {name}")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return None

    try:
        query = (
            db.collection(TERMS_COLLECTION)
            .where(filter=firestore.FieldFilter("name", "==", name.strip()))
            .limit(1)
        )

        docs = query.stream()
        first_doc = next(docs, None)

        if first_doc:
            term = first_doc.to_dict()
            term["term_id"] = first_doc.id
            print(f"[DB Service Extended] Found term: {term['name']}")
            return term
        else:
            print(f"[DB Service Extended] No term found: {name}")
            return None

    except Exception as e:
        print(f"[DB Service Extended] Error getting term by name: {e}")
        return None


def get_active_terms() -> List[Dict[str, Any]]:
    """
    Retrieve all active terms.

    Returns:
        List of term dictionaries
    """
    print(f"[DB Service Extended] get_active_terms called.")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return []

    try:
        query = (
            db.collection(TERMS_COLLECTION)
            .where(filter=firestore.FieldFilter("active", "==", True))
            .order_by("start_date", direction=firestore.Query.DESCENDING)
        )

        docs = query.stream()
        terms = []

        for doc in docs:
            term = doc.to_dict()
            term["term_id"] = doc.id
            terms.append(term)

        print(f"[DB Service Extended] Found {len(terms)} active terms")
        return terms

    except Exception as e:
        print(f"[DB Service Extended] Error getting active terms: {e}")
        return []


# ========================================
# COURSE SECTION MANAGEMENT FUNCTIONS
# ========================================


def create_course_section(section_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new course section.

    Args:
        section_data: Section information dictionary

    Returns:
        Section ID if successful, None if failed
    """
    print(f"[DB Service Extended] create_course_section called.")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return None

    try:
        # Validate required fields
        required_fields = ["course_id", "term_id"]
        if not all(field in section_data for field in required_fields):
            print(f"[DB Service Extended] Missing required fields: {required_fields}")
            return None

        # Create section schema
        section_record = CourseSection.create_schema(
            course_id=section_data["course_id"],
            term_id=section_data["term_id"],
            section_number=section_data.get("section_number", "001"),
            instructor_id=section_data.get("instructor_id"),
            enrollment=section_data.get("enrollment"),
            status=section_data.get("status", "assigned"),
        )

        # Save to Firestore
        section_record["created_at"] = firestore.SERVER_TIMESTAMP
        section_record["last_modified"] = firestore.SERVER_TIMESTAMP
        if section_record["assigned_date"]:
            section_record["assigned_date"] = firestore.SERVER_TIMESTAMP

        collection_ref = db.collection(COURSE_SECTIONS_COLLECTION)
        _, doc_ref = collection_ref.add(section_record)

        print(f"[DB Service Extended] Course section created with ID: {doc_ref.id}")
        return doc_ref.id

    except Exception as e:
        print(f"[DB Service Extended] Error creating course section: {e}")
        return None


def get_sections_by_instructor(instructor_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all sections assigned to an instructor.

    Args:
        instructor_id: Instructor's user ID

    Returns:
        List of section dictionaries
    """
    print(
        f"[DB Service Extended] get_sections_by_instructor called for: {instructor_id}"
    )
    if not db:
        print("[DB Service Extended] Firestore client not available.")
        return []

    try:
        query = (
            db.collection(COURSE_SECTIONS_COLLECTION)
            .where(filter=firestore.FieldFilter("instructor_id", "==", instructor_id))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
        )

        docs = query.stream()
        sections = []

        for doc in docs:
            section = doc.to_dict()
            section["section_id"] = doc.id
            sections.append(section)

        print(f"[DB Service Extended] Found {len(sections)} sections for instructor")
        return sections

    except Exception as e:
        print(f"[DB Service Extended] Error getting sections by instructor: {e}")
        return []


def get_sections_by_term(term_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all sections for a specific term.

    Args:
        term_id: Term ID

    Returns:
        List of section dictionaries
    """
    print(f"[DB Service Extended] get_sections_by_term called for: {term_id}")
    if not db:
        print("[DB Service Extended] Firestore client not available.")
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

        print(f"[DB Service Extended] Found {len(sections)} sections for term")
        return sections

    except Exception as e:
        print(f"[DB Service Extended] Error getting sections by term: {e}")
        return []


# Export all functions
__all__ = [
    "get_users_by_role",
    "update_user_extended",
    "create_course",
    "get_course_by_number",
    "get_courses_by_department",
    "create_term",
    "get_term_by_name",
    "get_active_terms",
    "create_course_section",
    "get_sections_by_instructor",
    "get_sections_by_term",
]
