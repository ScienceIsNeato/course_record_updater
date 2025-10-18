"""Application constants and configuration values."""

# Server port constants
E2E_TEST_PORT = 3002  # Hardcoded port for E2E tests (separate from dev server on 3001)

# Institution ID constants
SITE_ADMIN_INSTITUTION_ID = (
    "*"  # Wildcard institution ID for site admins (grants access to all institutions)
)

# Default timezone for institutions
DEFAULT_INSTITUTION_TIMEZONE = "America/Denver"

# Database collection names
INSTITUTIONS_COLLECTION = "institutions"
USERS_COLLECTION = "users"
COURSES_COLLECTION = "courses"
TERMS_COLLECTION = "terms"
COURSE_OFFERINGS_COLLECTION = "course_offerings"
COURSE_SECTIONS_COLLECTION = "course_sections"
COURSE_OUTCOMES_COLLECTION = "course_outcomes"

# API error messages
NO_DATA_PROVIDED_MSG = "No data provided"
INSTITUTION_CONTEXT_REQUIRED_MSG = "Institution context required"
COURSE_NOT_FOUND_MSG = "Course not found"
PROGRAM_NOT_FOUND_MSG = "Program not found"
INVALID_EMAIL_FORMAT_MSG = "Invalid email format"
NO_JSON_DATA_PROVIDED_MSG = "No JSON data provided"
NOT_FOUND_MSG = "not found"
INVITATION_NOT_FOUND_MSG = "Invitation not found"
INVALID_CREDENTIALS_MSG = "Invalid email or password"
DB_CLIENT_NOT_AVAILABLE_MSG = "[DB Service] Database client not available."
PERMISSION_DENIED_MSG = "Permission denied"
USER_NOT_FOUND_MSG = "User not found"
USER_NOT_AUTHENTICATED_MSG = "User not authenticated"
INSTITUTION_NOT_FOUND_MSG = "Institution not found"
FAILED_TO_CREATE_INSTITUTION_MSG = "Failed to create institution"
TERM_NOT_FOUND_MSG = "Term not found"
SECTION_NOT_FOUND_MSG = "Section not found"
OUTCOME_NOT_FOUND_MSG = "Outcome not found"
COURSE_OFFERING_NOT_FOUND_MSG = "Course offering not found"
MISSING_REQUIRED_FIELD_EMAIL_MSG = "Missing required field: email"

# SonarLint configuration constants
SONAR_CLOUD_ORGANIZATION = "scienceisneat"
SONAR_PROJECT_KEY = "course-record-updater"
SONAR_REGION = "US"

# Application route constants
DASHBOARD_ENDPOINT = "dashboard"

# Common error messages
ERROR_COURSE_NOT_FOUND = "Course not found"
ERROR_PROGRAM_NOT_FOUND = "Program not found"
ERROR_INVITATION_NOT_FOUND = "Invitation not found"
ERROR_NO_JSON_DATA = "No JSON data provided"
ERROR_NO_DATA_PROVIDED = "No data provided"
ERROR_INVALID_EMAIL_FORMAT = "Invalid email format"
ERROR_INSTITUTION_CONTEXT_REQUIRED = "Institution context required"
ERROR_AUTHENTICATION_REQUIRED = "Authentication required"

# File extensions
EXCEL_EXTENSION = ".xlsx"

# Database error messages
DB_CLIENT_NOT_AVAILABLE_MSG = "[DB Service] Database client not available."

# Default values
DEFAULT_BASE_URL = "http://localhost:5000"
TIMEZONE_UTC_SUFFIX = "+00:00"
SYSTEM_USER_NAME = "System Administrator"

# Seed data constants
PROGRAM_COMPUTER_SCIENCE = "Computer Science"
PROGRAM_ELECTRICAL_ENGINEERING = "Electrical Engineering"
PROGRAM_DEFAULT_DESCRIPTION = "Default program for unassigned courses"
FACULTY_NAME_HEADER = "Faculty Name"


# User role constants
class UserRole:
    """User role constants."""

    SITE_ADMIN = "site_admin"
    INSTITUTION_ADMIN = "institution_admin"
    PROGRAM_ADMIN = "program_admin"
    INSTRUCTOR = "instructor"


# Permission constants
class Permission:
    """Permission constants."""

    # User management
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    DELETE_USER = "delete_user"

    # Institution management
    MANAGE_INSTITUTIONS = "manage_institutions"
    VIEW_INSTITUTIONS = "view_institutions"

    # Program management
    MANAGE_PROGRAMS = "manage_programs"
    VIEW_PROGRAMS = "view_programs"

    # Course management
    MANAGE_COURSES = "manage_courses"
    VIEW_COURSES = "view_courses"

    # Data import/export
    IMPORT_DATA = "import_data"
    EXPORT_DATA = "export_data"


# Seed data constants
DEPARTMENT_COMPUTER_SCIENCE = "Computer Science"
DEPARTMENT_ELECTRICAL_ENGINEERING = "Electrical Engineering"
PROGRAM_DEFAULT_DESCRIPTION = "Default program for unassigned courses"

# Authentication error messages
ERROR_AUTHENTICATION_REQUIRED = "Authentication required"

# API error messages
ERROR_PERMISSION_DENIED = "Permission denied"
