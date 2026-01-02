#!/usr/bin/env python3
"""
Final cleanup: Fix all imports INSIDE src/ to use src.* absolute paths.
"""

import re
from pathlib import Path

FIXES = [
    # In src/ files, fix bare imports of src packages
    (r'\bfrom email_providers', 'from src.email_providers'),
    (r'\bfrom bulk_email_models', 'from src.bulk_email_models'),
    (r'\bfrom adapters\.', 'from src.adapters.'),
    (r'\bfrom api\.', 'from src.api.'),
    (r'\bimport adapters\.', 'import src.adapters.'),
    (r'\bimport api\.', 'import src.api.'),
]

def fix_file(filepath):
    """Fix imports in a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    for old, new in FIXES:
        content = re.sub(old, new, content)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all Python files in src/."""
    repo = Path('/Users/pacey/Documents/SourceCode/course_record_updater')
    src_dir = repo / 'src'
    fixed = 0
    
    for py_file in src_dir.rglob('*.py'):
        if fix_file(py_file):
            print(f"✅ {py_file.relative_to(repo)}")
            fixed += 1
    
    print(f"\n✅ Fixed {fixed} files")

if __name__ == '__main__':
    main()
