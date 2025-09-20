"""Application constants and configuration values."""

# Institution ID constants
SITE_ADMIN_INSTITUTION_ID = (
    "*"  # Wildcard institution ID for site admins (grants access to all institutions)
)


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
