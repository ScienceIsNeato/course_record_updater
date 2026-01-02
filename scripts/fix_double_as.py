#!/usr/bin/env python3
"""
Fix double 'as' statements and other import issues created by the initial update.
"""

import re
from pathlib import Path

def fix_file(filepath):
    """Fix import issues in a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Fix double 'as' statements like "import src.X as X as Y" -> "import src.X as Y"
    content = re.sub(r'import (src\.\S+) as \S+ as (\w+)', r'import \1 as \2', content)
    
    # Fix "from src.app import src.app" -> "from src.app import app"
    content = re.sub(r'from (src\.\w+) import \1', r'from \1 import \2', content)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Fixed {filepath}")
        return True
    return False

def main():
    """Fix all Python files."""
    repo = Path('/Users/pacey/Documents/SourceCode/course_record_updater')
    fixed = 0
    
    for py_file in repo.rglob('*.py'):
        # Skip venv and other excluded dirs
        if any(x in str(py_file) for x in ['venv', 'node_modules', '__pycache__']):
            continue
        
        if fix_file(py_file):
            fixed += 1
    
    print(f"\n✅ Fixed {fixed} files")

if __name__ == '__main__':
    main()
