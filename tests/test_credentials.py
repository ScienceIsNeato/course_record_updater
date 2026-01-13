"""
Centralized Test Credentials Module

This file re-exports test credential constants from `src.utils.constants` so
existing tests that import `tests.test_credentials` continue to work while
`src.utils.constants` is the canonical source of truth.

Note: The actual secret values are defined in `src/utils/constants.py`.
"""

# pragma: allowlist secret - Centralized test credentials module (re-exports)

from src.utils.constants import (
    CS_DATA_STRUCTURES_COURSE,
    CS_INTRO_COURSE,
    CS_PROGRAM_NAME,
    DEFAULT_PASSWORD,
    DEMO_PASSWORD,
    EE_CIRCUITS_COURSE,
    EE_PROGRAM_NAME,
    INSTITUTION_ADMIN_EMAIL,
    INSTITUTION_ADMIN_PASSWORD,
    INSTRUCTOR_PASSWORD,
    INVALID_PASSWORD_NO_COMPLEXITY,
    INVALID_PASSWORD_SHORT,
    LONG_PASSWORD,
    NEW_PASSWORD,
    NEW_SECURE_PASSWORD,
    PROGRAM_ADMIN_EMAIL,
    PROGRAM_ADMIN_PASSWORD,
    INSTRUCTOR_EMAIL,
    RESET_PASSWORD,
    SECURE_PASSWORD,
    SITE_ADMIN_EMAIL,
    SITE_ADMIN_PASSWORD,
    STRONG_PASSWORD_1,
    STRONG_PASSWORD_2,
    TEST_PASSWORD,
    TEST_USER_PASSWORD,
    VALID_PASSWORD,
    WEAK_PASSWORD,
    WRONG_PASSWORD,
)

# Backwards-compatible map
BASE_ACCOUNTS = {
    "site_admin": {"email": SITE_ADMIN_EMAIL, "password": SITE_ADMIN_PASSWORD},
    "institution_admin": {
        "email": INSTITUTION_ADMIN_EMAIL,
        "password": INSTITUTION_ADMIN_PASSWORD,
    },
    "program_admin": {"email": PROGRAM_ADMIN_EMAIL, "password": PROGRAM_ADMIN_PASSWORD},
    "instructor": {"email": INSTRUCTOR_EMAIL, "password": INSTRUCTOR_PASSWORD},
}
