#!/usr/bin/env python3
"""
Validate that actual password literals are not hardcoded in test/source files.

This script directly searches for known password patterns in code files,
rather than relying on detect-secrets baseline (which has many false positives).

Hardcoded passwords that should use constants instead:
- TestPass123!, ValidPassword123!, SecurePass123! -> GENERIC_PASSWORD
- password123 -> INVALID_PASSWORD
- weak (as password value) -> WEAK_PASSWORD
"""

import re
import sys
from pathlib import Path

# Actual password patterns to detect (not "Secret Keyword" false positives)
PASSWORD_PATTERNS = [
    (r'"TestPass123!"', "GENERIC_PASSWORD"),
    (r'"ValidPassword123!"', "GENERIC_PASSWORD"),
    (r'"SecurePass123!"', "GENERIC_PASSWORD"),
    (r'"Password123!"', "GENERIC_PASSWORD"),
    (r'"password123"', "INVALID_PASSWORD"),
    (r'password\s*=\s*"weak"', "WEAK_PASSWORD"),
]

# Files/patterns that are allowed to contain password constants
ALLOWED_PATTERNS = [
    "constants.py",
    "validate_secrets_location.py",  # This script contains patterns to match
    ".envrc",
    ".md",
    ".github/workflows/",
    "templates/",
    "static/",
    ".json",
]

# File patterns to scan
SCAN_PATTERNS = [
    "tests/**/*.py",
    "scripts/**/*.py",
    "src/**/*.py",
]


def is_file_allowed(filepath: str) -> bool:
    """Check if a file is allowed to contain password definitions."""
    filepath_lower = filepath.lower()
    for pattern in ALLOWED_PATTERNS:
        if pattern.lower() in filepath_lower:
            return True
    return False


def scan_file_for_passwords(filepath: Path) -> list[dict]:
    """Scan a single file for hardcoded password patterns."""
    violations = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, constant in PASSWORD_PATTERNS:
                # Use case-sensitive matching to avoid false positives
                # on intentionally invalid passwords like "TESTPASS123!"
                if re.search(pattern, line):
                    violations.append(
                        {
                            "file": str(filepath),
                            "line": line_num,
                            "pattern": pattern,
                            "suggested_constant": constant,
                            "line_content": line.strip()[:80],
                        }
                    )
    except Exception:
        pass  # Skip files that can't be read

    return violations


def scan_codebase() -> list[dict]:
    """Scan the entire codebase for hardcoded passwords."""
    violations = []
    project_root = Path(".")

    for glob_pattern in SCAN_PATTERNS:
        for filepath in project_root.glob(glob_pattern):
            if is_file_allowed(str(filepath)):
                continue
            if "__pycache__" in str(filepath):
                continue
            violations.extend(scan_file_for_passwords(filepath))

    return violations


def main() -> int:
    """Main entry point."""
    print("Scanning for hardcoded passwords...")
    print()

    violations = scan_codebase()

    if not violations:
        print("No hardcoded passwords found!")
        print()
        print("All password usage correctly imports from constants.py:")
        print("    GENERIC_PASSWORD = TestPass123!")
        print("    WEAK_PASSWORD = weak")
        print("    INVALID_PASSWORD = password123")
        return 0

    # Group violations by file for cleaner output
    files_with_violations: dict[str, list[dict]] = {}
    for v in violations:
        filename = v["file"]
        if filename not in files_with_violations:
            files_with_violations[filename] = []
        files_with_violations[filename].append(v)

    print("HARDCODED PASSWORDS FOUND!")
    print()
    print("=" * 70)
    print("PASSWORDS SHOULD NOT BE HARDCODED IN TEST OR SOURCE FILES!")
    print("=" * 70)
    print()
    print("Instead of hardcoding passwords, import them from constants:")
    print()
    print("    from src.utils.constants import GENERIC_PASSWORD, WEAK_PASSWORD")
    print()
    print("Available password constants:")
    print("    GENERIC_PASSWORD = TestPass123!  (valid test password)")
    print("    WEAK_PASSWORD = weak             (for testing validation)")
    print("    INVALID_PASSWORD = password123   (for testing rejection)")
    print()
    print("-" * 70)
    print("Files with hardcoded passwords:")
    print("-" * 70)

    for filename, file_violations in sorted(files_with_violations.items()):
        print(f"\n{filename}")
        for v in file_violations:
            print(f"   Line {v['line']}: Use {v['suggested_constant']} instead")
            print(f"      {v['line_content']}")

    print()
    print("-" * 70)
    print(
        f"Total: {len(violations)} password(s) in {len(files_with_violations)} file(s)"
    )
    print("-" * 70)
    print()
    print("To fix:")
    print("  1. Add import: from src.utils.constants import GENERIC_PASSWORD")
    print("  2. Replace the hardcoded password with the constant")
    print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
