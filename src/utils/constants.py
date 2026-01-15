"""Application constants and configuration values."""

# Server port constants
E2E_TEST_PORT = 3002  # Hardcoded port for E2E tests (separate from dev server on 3001)

# Institution ID constants
SITE_ADMIN_INSTITUTION_ID = (
    "*"  # Wildcard institution ID for site admins (grants access to all institutions)
)

# Default timezone for institutions
DEFAULT_INSTITUTION_TIMEZONE = "America/Denver"

# Default pagination and export limits
DEFAULT_PAGINATION_LIMIT = 50
DEFAULT_AUDIT_LOG_LIMIT = 20
DEFAULT_EXPORT_LIMIT = 1000

# Test secrets (placeholders used only in test environments)
# NOTE: Do NOT hardcode passwords in tests. Add new test passwords here
# and regenerate the .secrets.baseline when intentionally adding a new test secret.
TEST_USER_PASSWORD = "TestUser123!"
# Additional centralized test passwords (keep in sync with tests/test_credentials.py)
TEST_PASSWORD = "TestPass123!"
SECURE_PASSWORD = "SecurePassword123!"
NEW_PASSWORD = "NewSecurePassword123!"
NEW_SECURE_PASSWORD = "NewSecurePassword123!"
VALID_PASSWORD = "ValidPassword123!"
WRONG_PASSWORD = "WrongPass123!"
WEAK_PASSWORD = "weak"
INVALID_PASSWORD_SHORT = "a"
INVALID_PASSWORD_NO_COMPLEXITY = "password123"
STRONG_PASSWORD_1 = "Str0ng!Pass"
STRONG_PASSWORD_2 = "StrongPass1!"
LONG_PASSWORD = "A" * 129 + "1!"
DEMO_PASSWORD = "Demo2025!"

# Backwards-compatible aliases for test credentials module
SITE_ADMIN_PASSWORD = "SiteAdmin123!"
INSTITUTION_ADMIN_PASSWORD = "InstitutionAdmin123!"
PROGRAM_ADMIN_PASSWORD = INSTITUTION_ADMIN_PASSWORD
INSTRUCTOR_PASSWORD = "Instructor123!"
DEFAULT_PASSWORD = INSTITUTION_ADMIN_PASSWORD

# Test account emails and course constants (for tests re-export)
SITE_ADMIN_EMAIL = "siteadmin@system.local"
INSTITUTION_ADMIN_EMAIL = "sarah.admin@mocku.test"
PROGRAM_ADMIN_EMAIL = "lisa.prog@mocku.test"
INSTRUCTOR_EMAIL = "john.instructor@mocku.test"

# Course/program names used in tests
CS_INTRO_COURSE = "CS-101"
CS_DATA_STRUCTURES_COURSE = "CS-201"
EE_CIRCUITS_COURSE = "EE-101"
CS_PROGRAM_NAME = "Computer Science"
EE_PROGRAM_NAME = "Electrical Engineering"

# Password used for password reset tests
RESET_PASSWORD = NEW_SECURE_PASSWORD

# Branding defaults for institutions
DEFAULT_INSTITUTION_NAME = "Your Institution"
DEFAULT_INSTITUTION_SHORT_NAME = "YOUR INSTITUTION"
DEFAULT_INSTITUTION_LOGO_STATIC_PATH = "images/institution_placeholder.svg"

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
INVITATION_CREATED_AND_SENT_MSG = "Invitation created and sent successfully"
INVITATION_CREATED_EMAIL_FAILED_MSG = "Invitation created but email failed to send"
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

# System date override messaging
DATE_OVERRIDE_BANNER_PREFIX = "Date Override Mode"

# CSRF error messages
CSRF_ERROR_MESSAGE = "CSRF validation failed. Please refresh the page and try again."

# Email subject templates
EMAIL_SUBJECT_REMINDER_PREFIX = "Reminder: Please submit your course data"

# SonarCloud configuration
SONARCLOUD_PROJECT_KEY_DEFAULT = "ScienceIsNeato_course_record_updater"

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


# CLO Status constants
class CLOStatus:
    """Course Learning Outcome status constants."""

    UNASSIGNED = "unassigned"  # CLO exists but course section has no instructor
    ASSIGNED = "assigned"  # CLO exists, instructor assigned (ready to work)
    IN_PROGRESS = "in_progress"  # Instructor has started editing
    AWAITING_APPROVAL = (
        "awaiting_approval"  # Instructor submitted for review/needs rework
    )
    APPROVED = "approved"  # Final approval granted
    NEVER_COMING_IN = (
        "never_coming_in"  # Instructor left/non-responsive (CEI demo feedback)
    )
    COMPLETED = "completed"  # Deprecated alias for approved/completed workflows


# CLO Approval Status constants
class CLOApprovalStatus:
    """CLO approval decision constants."""

    PENDING = "pending"  # Not yet reviewed
    APPROVED = "approved"  # Approved by admin
    NEEDS_REWORK = "needs_rework"  # Requires changes
    NEVER_COMING_IN = (
        "never_coming_in"  # Instructor non-responsive/left (CEI demo feedback)
    )


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

    # CLO workflow permissions
    SUBMIT_CLO = "submit_clo"
    AUDIT_CLO = "audit_clo"
    AUDIT_ALL_CLO = "audit_all_clo"


# Seed data constants
DEPARTMENT_COMPUTER_SCIENCE = "Computer Science"
DEPARTMENT_ELECTRICAL_ENGINEERING = "Electrical Engineering"
PROGRAM_DEFAULT_DESCRIPTION = "Default program for unassigned courses"

# Authentication error messages
ERROR_AUTHENTICATION_REQUIRED = "Authentication required"

# API error messages
ERROR_PERMISSION_DENIED = "Permission denied"

# UI Messages - Outcome Management
MSG_NO_OUTCOMES_EXPORT = (
    "No Outcome records available to export for the selected filters."
)
MSG_OUTCOME_MARKED_NCI = "Outcome marked as Never Coming In (NCI)"
MSG_NO_OUTCOMES_PENDING_AUDIT = "No Outcomes pending audit"
MSG_NO_OUTCOMES_DEFINED = "No Outcomes defined"
