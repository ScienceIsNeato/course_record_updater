#!/usr/bin/env python3
"""
Fix multiline patch strings in test files.
"""

import re
from pathlib import Path


def fix_file(filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    original_content = content

    # Pattern: patch(\n\s+"api_routes.
    # We want to match 'patch(' followed by any whitespace/newlines, followed by quote, followed by api_routes.

    # Fix api_routes
    content = re.sub(r'(patch\(\s*["\'])api_routes\.', r"\1src.api_routes.", content)

    # Fix adapters
    content = re.sub(r'(patch\(\s*["\'])adapters\.', r"\1src.adapters.", content)

    # Fix other common services if they appear in this format
    content = re.sub(
        r'(patch\(\s*["\'])auth_service\.', r"\1src.services.auth_service.", content
    )
    content = re.sub(
        r'(patch\(\s*["\'])database_service\.',
        r"\1src.database.database_service.",
        content,
    )

    if content != original_content:
        filepath.write_text(content, encoding="utf-8")
        print(f"Fixed {filepath}")


def main():
    test_dir = Path("tests/unit")
    for test_file in test_dir.rglob("*.py"):
        fix_file(test_file)


if __name__ == "__main__":
    main()
