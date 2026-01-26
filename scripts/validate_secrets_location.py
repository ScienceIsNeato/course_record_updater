#!/usr/bin/env python3
"""
Validate that secrets/passwords are only defined in authorized files.

This script checks .secrets.baseline and ensures that any detected secrets
(particularly passwords) are only in files that are authorized to contain them.

Authorized files:
- Files with "constant" in the filename (e.g., constants.py)
- Configuration templates (e.g., .envrc.template)
- Documentation files (e.g., *.md)
- Workflow files (e.g., .github/workflows/*.yml)
- Template files (e.g., templates/*.html)
- Static files (e.g., static/*.js)
- JSON fixtures (e.g., *.json)

This prevents test files and source code from having hardcoded passwords
scattered throughout the codebase. All passwords should be imported from
a central constants file.
"""

import json
import sys
from pathlib import Path

# Files/patterns that are allowed to contain secrets
ALLOWED_PATTERNS = [
    # Central password constants file
    "constant",
    # Configuration templates
    ".envrc",
    # Documentation (examples, setup guides)
    ".md",
    # GitHub workflows (encrypted secrets references)
    ".github/workflows/",
    # HTML templates (form field names, not actual passwords)
    "templates/",
    # Static JS files (form handling, not actual passwords)
    "static/",
    # JSON fixtures (test data - these should also use constants ideally)
    ".json",
]


def is_file_allowed(filename: str) -> bool:
    """Check if a file is allowed to contain secrets."""
    filename_lower = filename.lower()
    for pattern in ALLOWED_PATTERNS:
        if pattern.lower() in filename_lower:
            return True
    return False


def validate_secrets_baseline(baseline_path: str = ".secrets.baseline") -> list[dict]:
    """
    Validate that all detected secrets are in allowed files.

    Returns a list of violations (files with secrets that shouldn't have them).
    """
    baseline_file = Path(baseline_path)
    if not baseline_file.exists():
        print(f"⚠️  No {baseline_path} file found - skipping validation")
        return []

    with open(baseline_file) as f:
        data = json.load(f)

    violations = []
    results = data.get("results", {})

    for filename, secrets in results.items():
        if not is_file_allowed(filename):
            # This file shouldn't have secrets
            for secret in secrets:
                violations.append(
                    {
                        "file": filename,
                        "type": secret.get("type", "Unknown"),
                        "line": secret.get("line_number", "?"),
                    }
                )

    return violations


def main() -> int:
    """Main entry point."""
    print("🔐 Validating secrets are in authorized locations...")
    print()

    violations = validate_secrets_baseline()

    if not violations:
        print("✅ All detected secrets are in authorized files!")
        print()
        print("Authorized file patterns:")
        for pattern in ALLOWED_PATTERNS:
            print(f"  • {pattern}")
        return 0

    # Group violations by file for cleaner output
    files_with_violations: dict[str, list[dict]] = {}
    for v in violations:
        filename = v["file"]
        if filename not in files_with_violations:
            files_with_violations[filename] = []
        files_with_violations[filename].append(v)

    print("❌ SECURITY VIOLATION: Secrets found in unauthorized files!")
    print()
    print("=" * 70)
    print("⚠️  PASSWORDS SHOULD NOT BE HARDCODED IN TEST OR SOURCE FILES!")
    print("=" * 70)
    print()
    print("Instead of hardcoding passwords, import them from constants:")
    print()
    print("    from src.utils.constants import GENERIC_PASSWORD, WEAK_PASSWORD")
    print()
    print("Available password constants:")
    print("    • GENERIC_PASSWORD = 'TestPass123!'  (valid test password)")
    print("    • WEAK_PASSWORD = 'weak'             (for testing validation)")
    print("    • INVALID_PASSWORD = 'password123'   (for testing rejection)")
    print()
    print("-" * 70)
    print("Files with unauthorized secrets:")
    print("-" * 70)

    for filename, file_violations in sorted(files_with_violations.items()):
        print(f"\n📁 {filename}")
        for v in file_violations:
            print(f"   Line {v['line']}: {v['type']}")

    print()
    print("-" * 70)
    print(f"Total: {len(violations)} secret(s) in {len(files_with_violations)} file(s)")
    print("-" * 70)
    print()
    print("To fix:")
    print("  1. Replace hardcoded passwords with imports from constants.py")
    print("  2. Run: detect-secrets scan --baseline .secrets.baseline")
    print("  3. Verify the violations are resolved")
    print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
