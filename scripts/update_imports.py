#!/usr/bin/env python3
"""
Script to update import statements after repository reorganization.
"""

import os
import re
from pathlib import Path

# Mapping of old import to new import
IMPORT_MAPPINGS = {
    # Utilities
    r"^from src.utils.constants import": "from src.utils.constants import",
    r"^import src.utils.constants as constants$": "import src.utils.constants as constants",
    r"^from src.utils.logging_config import": "from src.utils.logging_config import",
    r"^import src.utils.logging_config as logging_config$": "import src.utils.logging_config as logging_config",
    r"^from src.utils.term_utils import": "from src.utils.term_utils import",
    r"^import src.utils.term_utils as term_utils$": "import src.utils.term_utils as term_utils",
}


def update_imports_in_file(filepath):
    """Update imports in a single file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")
        updated_lines = []

        for line in lines:
            updated_line = line
            for old_pattern, new_import in IMPORT_MAPPINGS.items():
                if re.match(old_pattern, line.strip()):
                    # Replace the old import with the new one
                    updated_line = re.sub(old_pattern, new_import, line)
                    print(f"  {filepath}: {line.strip()} -> {updated_line.strip()}")
                    break
            updated_lines.append(updated_line)

        new_content = "\n".join(updated_lines)

        if new_content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"ERROR updating {filepath}: {e}")
        return False


def main():
    """Main function to update all Python files."""
    repo_root = Path(__file__).parent.parent
    updated_count = 0

    # Find all Python files (excluding venv, node_modules, etc.)
    exclude_dirs = {
        ".git",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "build",
        "htmlcov",
        ".scannerwork",
    }

    for root, dirs, files in os.walk(repo_root):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                filepath = Path(root) / file
                if update_imports_in_file(filepath):
                    updated_count += 1

    print(f"\n✅ Updated {updated_count} files")


if __name__ == "__main__":
    main()
