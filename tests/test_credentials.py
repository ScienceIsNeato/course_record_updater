"""
Centralized Test Credentials Module

This module contains all test passwords and credentials used across the test suite.
All test passwords are defined here to avoid scattering credentials throughout the codebase.

This file is added to .secrets.baseline since it intentionally contains test passwords.
All other test files should import from this module instead of hardcoding passwords.

Usage:
    from tests.test_credentials import (
        SITE_ADMIN_PASSWORD,
        INSTITUTION_ADMIN_PASSWORD,
        TEST_USER_PASSWORD,
        # ... etc
    )
"""

# pragma: allowlist secret - Centralized test credentials module

# ============================================================================
# Admin Account Emails
# ============================================================================

SITE_ADMIN_EMAIL = "siteadmin@system.local"

# ============================================================================
# Admin Account Passwords
# ============================================================================

SITE_ADMIN_PASSWORD = "SiteAdmin123!"  # pragma: allowlist secret
INSTITUTION_ADMIN_PASSWORD = "InstitutionAdmin123!"  # pragma: allowlist secret
# Note: seed_db.py uses DEFAULT_PASSWORD (InstitutionAdmin123!) for all seeded users
PROGRAM_ADMIN_PASSWORD = "InstitutionAdmin123!"  # pragma: allowlist secret
DEFAULT_PASSWORD = INSTITUTION_ADMIN_PASSWORD  # pragma: allowlist secret

# ============================================================================
# User Account Passwords
# ============================================================================

TEST_USER_PASSWORD = "TestUser123!"  # pragma: allowlist secret
INSTRUCTOR_PASSWORD = "Instructor123!"  # pragma: allowlist secret

# ============================================================================
# Generic Test Passwords
# ============================================================================

# Standard test password for general test cases
TEST_PASSWORD = "TestPass123!"  # pragma: allowlist secret

# Secure password for password validation tests
SECURE_PASSWORD = "SecurePass123!"  # pragma: allowlist secret

# Password for new password tests
NEW_PASSWORD = "NewSecurePassword123!"  # pragma: allowlist secret
NEW_SECURE_PASSWORD = "NewSecurePassword123!"  # pragma: allowlist secret

# Password for password reset tests
RESET_PASSWORD = "NewSecurePassword123!"  # pragma: allowlist secret

# ============================================================================
# Password Validation Test Cases
# ============================================================================

# Wrong password for negative test cases
WRONG_PASSWORD = "WrongPass123!"  # pragma: allowlist secret

# Weak password for validation tests
WEAK_PASSWORD = "weak"  # pragma: allowlist secret

# Invalid password formats
INVALID_PASSWORD_SHORT = "a"
INVALID_PASSWORD_NO_COMPLEXITY = "password123"  # pragma: allowlist secret

# Strong password examples
STRONG_PASSWORD_1 = "Str0ng!Pass"  # pragma: allowlist secret
STRONG_PASSWORD_2 = "StrongPass1!"  # pragma: allowlist secret
VALID_PASSWORD = "ValidPassword123!"  # pragma: allowlist secret

# Long password for length validation tests
LONG_PASSWORD = "A" * 129 + "1!"  # pragma: allowlist secret

# ============================================================================
# Demo/Workflow Passwords
# ============================================================================

DEMO_PASSWORD = "Demo2025!"  # pragma: allowlist secret

# ============================================================================
# Email/Account Test Data
# ============================================================================

SITE_ADMIN_EMAIL = "siteadmin@system.local"
INSTITUTION_ADMIN_EMAIL = "sarah.admin@mocku.test"
PROGRAM_ADMIN_EMAIL = "lisa.prog@mocku.test"
INSTRUCTOR_EMAIL = "john.instructor@mocku.test"

# ============================================================================
# Course/Program Test Data
# ============================================================================

CS_INTRO_COURSE = "CS-101"
CS_DATA_STRUCTURES_COURSE = "CS-201"
EE_CIRCUITS_COURSE = "EE-101"
CS_PROGRAM_NAME = "Computer Science"
EE_PROGRAM_NAME = "Electrical Engineering"

# ============================================================================
# Legacy Compatibility
# ============================================================================

# For backward compatibility with existing code that uses these names
BASE_ACCOUNTS = {
    "site_admin": {
        "email": SITE_ADMIN_EMAIL,
        "password": SITE_ADMIN_PASSWORD,
    },
    "institution_admin": {
        "email": INSTITUTION_ADMIN_EMAIL,
        "password": INSTITUTION_ADMIN_PASSWORD,
    },
    "program_admin": {
        "email": PROGRAM_ADMIN_EMAIL,
        "password": PROGRAM_ADMIN_PASSWORD,
    },
    "instructor": {
        "email": INSTRUCTOR_EMAIL,
        "password": INSTRUCTOR_PASSWORD,
    },
}
