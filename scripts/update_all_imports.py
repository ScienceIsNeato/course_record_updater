#!/usr/bin/env python3
"""
Comprehensive import update script for repository reorganization.
Updates all imports across the entire codebase to use src.* paths.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Comprehensive mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # Utils
    r'\bfrom constants import': 'from src.utils.constants import',
    r'\bimport constants\b': 'import src.utils.constants as constants',
    r'\bfrom logging_config import': 'from src.utils.logging_config import',
    r'\bimport logging_config\b': 'import src.utils.logging_config as logging_config',
    r'\bfrom term_utils import': 'from src.utils.term_utils import',
    r'\bimport term_utils\b': 'import src.utils.term_utils as term_utils',
    
    # Models
    r'\bfrom models import': 'from src.models.models import',
    r'\bimport models\b': 'import src.models.models as models',
    r'\bfrom models_sql import': 'from src.models.models_sql import',
    r'\bimport models_sql\b': 'import src.models.models_sql as models_sql',
    
    # Database
    r'\bfrom database_factory import': 'from src.database.database_factory import',
    r'\bfrom database_interface import': 'from src.database.database_interface import',
    r'\bfrom database_service import': 'from src.database.database_service import',
    r'\bfrom database_sql import': 'from src.database.database_sql import',
    r'\bfrom database_sqlite import': 'from src.database.database_sqlite import',
    r'\bfrom database_validator import': 'from src.database.database_validator import',
    r'\bimport database_service\b': 'import src.database.database_service as database_service',
    
    # Services
    r'\bfrom auth_service import': 'from src.services.auth_service import',
    r'\bfrom audit_service import': 'from src.services.audit_service import',
    r'\bfrom dashboard_service import': 'from src.services.dashboard_service import',
    r'\bfrom email_service import': 'from src.services.email_service import',
    r'\bfrom import_service import': 'from src.services.import_service import',
    r'\bfrom invitation_service import': 'from src.services.invitation_service import',
    r'\bfrom login_service import': 'from src.services.login_service import',
    r'\bfrom password_service import': 'from src.services.password_service import',
    r'\bfrom password_reset_service import': 'from src.services.password_reset_service import',
    r'\bfrom registration_service import': 'from src.services.registration_service import',
    r'\bfrom export_service import': 'from src.services.export_service import',
    r'\bfrom bulk_email_service import': 'from src.services.bulk_email_service import',
    r'\bfrom clo_workflow_service import': 'from src.services.clo_workflow_service import',
    r'\bimport password_service\b': 'import src.services.password_service as password_service',
    
    # Core app
    r'\bfrom app import': 'from src.app import',
    r'\bimport app\b': 'import src.app as app',
    r'\bfrom api_routes import': 'from src.api_routes import',
    r'\bimport api_routes\b': 'import src.api_routes as api_routes',
    
    # Adapters
    r'\bfrom adapters\.': 'from src.adapters.',
    
    # API
    r'\bfrom api\.': 'from src.api.',
    
    # Email providers
    r'\bfrom email_providers\.': 'from src.email_providers.',
    
    # Bulk email models
    r'\bfrom bulk_email_models\.': 'from src.bulk_email_models.',
}

def update_imports_in_file(filepath: Path) -> Tuple[bool, List[str]]:
    """Update imports in a single file. Returns (changed, list of changes)."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Apply all mappings
        for old_pattern, new_import in IMPORT_MAPPINGS.items():
            if re.search(old_pattern, content):
                new_content = re.sub(old_pattern, new_import, content)
                if new_content != content:
                    # Find what changed
                    old_lines = set(line for line in content.split('\n') if re.search(old_pattern, line))
                    new_lines = set(line for line in new_content.split('\n') if new_import in line)
                    for old_line in old_lines:
                        changes.append(f"  {old_line.strip()}")
                    content = new_content
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        return False, []
    except Exception as e:
        print(f"❌ ERROR updating {filepath}: {e}")
        return False, []

def main():
    """Update all Python files in the repository."""
    repo_root = Path(__file__).parent.parent
    updated_files = []
    
    # Directories to process
    search_dirs = [
        repo_root / 'src',
        repo_root / 'tests',
        repo_root / 'scripts',
        repo_root / 'demos',
    ]
    
    # Also check root level files
    root_files = list(repo_root.glob('*.py'))
    
    exclude_dirs = {'venv', 'node_modules', '__pycache__', '.git', 
                    '.pytest_cache', '.mypy_cache', 'htmlcov', 'build'}
    
    all_files = []
    
    # Collect all Python files
    for search_dir in search_dirs:
        if search_dir.exists():
            for root, dirs, files in os.walk(search_dir):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if file.endswith('.py'):
                        all_files.append(Path(root) / file)
    
    # Add root level files
    all_files.extend(root_files)
    
    # Process all files
    total_changes = 0
    for filepath in sorted(set(all_files)):
        changed, changes = update_imports_in_file(filepath)
        if changed:
            print(f"\n📝 {filepath.relative_to(repo_root)}:")
            for change in changes[:5]:  # Show first 5 changes
                print(change)
            if len(changes) > 5:
                print(f"  ... and {len(changes) - 5} more")
            updated_files.append(str(filepath.relative_to(repo_root)))
            total_changes += len(changes)
    
    print(f"\n{'='*60}")
    print(f"✅ Updated {len(updated_files)} files with {total_changes} total changes")
    print(f"{'='*60}")
    
    if updated_files:
        print("\nUpdated files:")
        for f in updated_files[:20]:
            print(f"  - {f}")
        if len(updated_files) > 20:
            print(f"  ... and {len(updated_files) - 20} more")

if __name__ == "__main__":
    main()
