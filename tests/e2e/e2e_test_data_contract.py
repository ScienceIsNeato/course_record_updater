"""
E2E Test Data Contract

Defines the data structure that seed scripts MUST provide for E2E tests to pass.
This contract serves as the single source of truth for test data expectations.

## Purpose
- Prevent brittle coupling between seed scripts and tests
- Make test data requirements explicit and discoverable
- Enable parallel test execution with proper data provisioning
- Fail fast if data doesn't meet requirements

## Usage
Seeding scripts import this to know what to create.
Tests import this to know what to expect.
"""

# =============================================================================
# Parallel Execution Configuration
# =============================================================================

# Maximum number of parallel pytest-xdist workers we want to support
# System will auto-scale to available CPU cores, but we pre-provision accounts
# for this many workers to handle peak capacity
MAX_PARALLEL_WORKERS = 16

# How many sections each instructor worker needs to have assigned
# Tests like "instructor updates section assessment" require assigned sections
SECTIONS_PER_INSTRUCTOR_WORKER = 3

# How many programs each program admin worker needs to have assigned
# Tests like "program admin creates course" require program membership
PROGRAMS_PER_ADMIN_WORKER = 2

# =============================================================================
# Derived Requirements (Computed from above)
# =============================================================================

# Total sections needed in the database to support parallel execution
# Note: Workers can share sections since each uses an isolated database copy
MIN_SECTIONS_REQUIRED_PER_INSTITUTION = (
    MAX_PARALLEL_WORKERS * SECTIONS_PER_INSTRUCTOR_WORKER
)

# Total programs needed (shared across workers is fine)
MIN_PROGRAMS_REQUIRED_PER_INSTITUTION = PROGRAMS_PER_ADMIN_WORKER

# =============================================================================
# Base Test Accounts (Non-Worker)
# =============================================================================

BASE_ACCOUNTS = {
    "site_admin": {
        "email": "siteadmin@system.local",
        "password": "SiteAdmin123!",
        "institution": "system",
    },
    "institution_admin": {
        "email": "sarah.admin@mocku.test",
        "password": "InstitutionAdmin123!",
        "institution": "mocku",
    },
    "program_admin": {
        "email": "lisa.prog@mocku.test",
        "password": "TestUser123!",
        "institution": "mocku",
    },
    "instructor": {
        "email": "john.instructor@mocku.test",
        "password": "TestUser123!",
        "institution": "mocku",
    },
}

# =============================================================================
# Worker Account Naming Convention
# =============================================================================


def get_worker_email(base_email: str, worker_id: int) -> str:
    """
    Generate worker-specific email from base email.

    Example:
        get_worker_email("john.instructor@mocku.test", 0)
        → "john.instructor_worker0@mocku.test"
    """
    email_parts = base_email.rsplit("@", 1)
    return f"{email_parts[0]}_worker{worker_id}@{email_parts[1]}"


def get_worker_id_from_email(email: str) -> int | None:
    """
    Extract worker ID from worker-specific email.
    Returns None if not a worker email.

    Example:
        get_worker_id_from_email("john.instructor_worker5@mocku.test")
        → 5
    """
    import re

    match = re.search(r"_worker(\d+)@", email)
    return int(match.group(1)) if match else None


# =============================================================================
# Test Data Validation
# =============================================================================


def validate_seeded_data(db_service) -> list[str]:
    """
    Validate that seeded data meets the contract.
    Returns list of validation errors (empty if valid).

    Usage in seed scripts:
        from tests.e2e.e2e_test_data_contract import validate_seeded_data
        import database_service as db

        errors = validate_seeded_data(db)
        if errors:
            for error in errors:
                print(f"❌ {error}")
            raise ValueError("Seeded data does not meet E2E test contract")
    """
    errors = []

    # Check MockU institution exists
    try:
        mocku = db_service.get_institution_by_short_name("MockU")
        if not mocku:
            errors.append("MockU institution not found")
            return errors  # Can't continue without institution

        institution_id = mocku["institution_id"]

        # Check sections
        sections = db_service.get_all_sections(institution_id)
        if len(sections) < MIN_SECTIONS_REQUIRED_PER_INSTITUTION:
            errors.append(
                f"Need {MIN_SECTIONS_REQUIRED_PER_INSTITUTION} sections for MockU, "
                f"but only {len(sections)} exist. "
                f"Required: {MAX_PARALLEL_WORKERS} workers × {SECTIONS_PER_INSTRUCTOR_WORKER} sections/worker"
            )

        # Check programs
        programs = db_service.get_programs_by_institution(institution_id)
        if len(programs) < MIN_PROGRAMS_REQUIRED_PER_INSTITUTION:
            errors.append(
                f"Need {MIN_PROGRAMS_REQUIRED_PER_INSTITUTION} programs for MockU, "
                f"but only {len(programs)} exist"
            )

        # Check base accounts exist (not worker accounts - those are optional)
        for role_key, account in BASE_ACCOUNTS.items():
            base_email = account["email"]
            user = db_service.get_user_by_email(base_email)
            if not user:
                errors.append(f"Base account not found: {base_email} ({role_key})")

    except Exception as e:
        errors.append(f"Validation error: {e}")

    return errors


# =============================================================================
# Documentation
# =============================================================================


def print_contract_summary():
    """Print human-readable summary of the contract."""
    print("\n" + "=" * 70)
    print("  E2E Test Data Contract Summary")
    print("=" * 70)
    print(f"\n📊 Parallel Execution:")
    print(f"   Max workers: {MAX_PARALLEL_WORKERS}")
    print(f"   Sections per instructor: {SECTIONS_PER_INSTRUCTOR_WORKER}")
    print(f"   Programs per admin: {PROGRAMS_PER_ADMIN_WORKER}")
    print(f"\n📋 Minimum Data Required:")
    print(f"   Sections: {MIN_SECTIONS_REQUIRED_PER_INSTITUTION}")
    print(f"   Programs: {MIN_PROGRAMS_REQUIRED_PER_INSTITUTION}")
    print(f"\n👥 Base Accounts: {len(BASE_ACCOUNTS)}")
    for role, account in BASE_ACCOUNTS.items():
        print(f"   {role}: {account['email']}")
    print(f"\n🔧 Worker Accounts: {MAX_PARALLEL_WORKERS * len(BASE_ACCOUNTS)}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Allow running this file directly to see the contract
    print_contract_summary()
