#!/usr/bin/env python3
"""
Update imports inside src/ directory to use relative imports.
This prevents circular imports when using backward compat shims.
"""

import os
import re
from pathlib import Path

# Map of old imports to new imports for files in src/
IMPORT_MAPPINGS = {
    # Within database package
    "src/database": {
        r"^from src.database.database_interface import": "from .database_interface import",
        r"^from src.database.database_sqlite import": "from .database_sqlite import",
        r"^from src.database.database_sql import": "from .database_sql import",
        r"^from src.database.database_factory import": "from .database_factory import",
        r"^from src.database.database_service import": "from .database_service import",
        r"^from src.database.database_validator import": "from .database_validator import",
        r"^import database_": "from . import database_",
    },
    # Within models package
    "src/models": {
        r"^from src.models.models_sql import": "from .models_sql import",
        r"^from src.models.models import": "from .models import",
        r"^import src.models.models_sql as models_sql$": "from . import src.models.models_sql as models_sql",
        r"^import src.models.models as models$": "from . import src.models.models as models",
    },
    # Within services package
    "src/services": {
        r"^from src.services.auth_service import": "from .auth_service import",
        r"^from src.services.audit_service import": "from .audit_service import",
        r"^from src.services.email_service import": "from .email_service import",
        r"^from src.services.password_service import": "from .password_service import",
        # Add others as needed
    },
    # Cross-package imports (from any src/ subdirectory)
    "src": {
        # Database to models
        r"^from src.models.models_sql import": "from src.models.models_sql import",
        r"^from src.models.models import": "from src.models.models import",
        r"^import src.models.models_sql as models_sql$": "import src.models.models_sql as models_sql",
        r"^import src.models.models as models$": "import src.models.models as models",
        # Database to utils
        r"^from src.utils.constants import": "from src.utils.constants import",
        r"^from src.utils.logging_config import": "from src.utils.logging_config import",
        r"^from src.utils.term_utils import": "from src.utils.term_utils import",
        # Services to database
        r"^from src.database.database_service import": "from src.database.database_service import",
        r"^import src.database.database_service as database_service$": "import src.database.database_service as database_service",
        # Any to database
        r"^from src.database.database_factory import": "from src.database.database_factory import",
        r"^from src.database.database_interface import": "from src.database.database_interface import",
        r"^from src.database.database_sqlite import": "from src.database.database_sqlite import",
        r"^from src.database.database_sql import": "from src.database.database_sql import",
        r"^from src.database.database_validator import": "from src.database.database_validator import",
    },
}


def get_package_mappings(filepath):
    """Get the appropriate mappings for a file based on its location."""
    path_str = str(filepath)

    # Determine which package we're in
    if "/src/database/" in path_str:
        return {
            **IMPORT_MAPPINGS.get("src/database", {}),
            **IMPORT_MAPPINGS.get("src", {}),
        }
    elif "/src/models/" in path_str:
        return {
            **IMPORT_MAPPINGS.get("src/models", {}),
            **IMPORT_MAPPINGS.get("src", {}),
        }
    elif "/src/services/" in path_str:
        return {
            **IMPORT_MAPPINGS.get("src/services", {}),
            **IMPORT_MAPPINGS.get("src", {}),
        }
    elif "/src/utils/" in path_str:
        return IMPORT_MAPPINGS.get("src", {})
    else:
        return IMPORT_MAPPINGS.get("src", {})


def update_imports_in_file(filepath):
    """Update imports in a single file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        lines = content.split("\n")
        updated_lines = []
        mappings = get_package_mappings(filepath)
        changes_made = []

        for line_num, line in enumerate(lines, 1):
            updated_line = line
            for old_pattern, new_import in mappings.items():
                if re.match(old_pattern, line.strip()):
                    updated_line = re.sub(old_pattern, new_import, line)
                    if updated_line != line:
                        changes_made.append(
                            f"  Line {line_num}: {line.strip()} -> {updated_line.strip()}"
                        )
                    break
            updated_lines.append(updated_line)

        new_content = "\n".join(updated_lines)

        if new_content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            if changes_made:
                print(f"\n{filepath}:")
                for change in changes_made:
                    print(change)
            return True
        return False
    except Exception as e:
        print(f"ERROR updating {filepath}: {e}")
        return False


def main():
    """Update all Python files in src/ directory."""
    repo_root = Path(__file__).parent.parent
    src_dir = repo_root / "src"
    updated_count = 0

    if not src_dir.exists():
        print(f"ERROR: {src_dir} does not exist")
        return

    # Find all Python files in src/
    for root, dirs, files in os.walk(src_dir):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                filepath = Path(root) / file
                if update_imports_in_file(filepath):
                    updated_count += 1

    print(f"\n✅ Updated {updated_count} files in src/")


if __name__ == "__main__":
    main()
