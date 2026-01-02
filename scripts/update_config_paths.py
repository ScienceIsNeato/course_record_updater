#!/usr/bin/env python3
"""
Update configuration files to reference new paths after reorganization.
"""

from pathlib import Path
import re

def update_pytest_ini():
    """Update pytest.ini paths."""
    file = Path('config/pytest.ini')
    content = file.read_text()
    
    # Already has pythonpath = src . which is correct
    # testpaths already correct
    
    print("✅ pytest.ini - no changes needed")

def update_sonar_properties():
    """Update sonar-project.properties paths."""
    file = Path('config/sonar-project.properties')
    content = file.read_text()
    
    # Update source paths
    content = re.sub(
        r'sonar\.sources=\.',
        'sonar.sources=src',
        content
    )
    
    # Coverage paths
    content = re.sub(
        r'sonar\.python\.coverage\.reportPaths=coverage\.xml',
        'sonar.python.coverage.reportPaths=build/coverage.xml',
        content
    )
    
    # JavaScript coverage
    content = re.sub(
        r'sonar\.javascript\.lcov\.reportPaths=coverage/lcov\.info',
        'sonar.javascript.lcov.reportPaths=build/coverage/lcov.info',
        content
    )
    
    file.write_text(content)
    print("✅ sonar-project.properties updated")

def update_coveragerc():
    """Update .coveragerc paths."""
    file = Path('config/.coveragerc')
    content = file.read_text()
    
    # Update source path
    content = re.sub(
        r'\[run\]\nsource = \.',
        '[run]\nsource = src',
        content
    )
    
    # Update omit patterns to exclude config, build, data
    if 'omit =' in content:
        content = re.sub(
            r'(omit =)',
            r'\1\n    config/*\n    build/*\n    data/*',
            content,
            count=1
        )
    
    file.write_text(content)
    print("✅ .coveragerc updated")

def update_eslintrc():
    """Update .eslintrc.js if needed."""
    file = Path('config/.eslintrc.js')
    # ESLint config is relative to where it's run from, should be OK
    print("✅ .eslintrc.js - no changes needed")

def main():
    """Update all config files."""
    print("Updating configuration files...\n")
    
    update_pytest_ini()
    update_sonar_properties()
    update_coveragerc()
    update_eslintrc()
    
    print("\n✅ All config files updated")

if __name__ == '__main__':
    main()
