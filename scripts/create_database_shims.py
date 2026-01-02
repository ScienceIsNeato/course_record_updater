#!/usr/bin/env python3
"""
Create backward compatibility shims for moved modules.
"""

MODULES = [
    'database_factory',
    'database_interface',
    'database_service',
    'database_sql',
    'database_sqlite',
    'database_validator',
]

SHIM_TEMPLATE = '''"""
DEPRECATED: This module has moved to src.database.{module}
This file exists for backward compatibility during migration.
"""
import warnings
from src.database.{module} import *  # noqa: F401, F403

warnings.warn(
    "Importing from '{module}' is deprecated. Use 'from src.database.{module} import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)
'''

for module in MODULES:
    with open(f'{module}.py', 'w') as f:
        f.write(SHIM_TEMPLATE.format(module=module))
    print(f'Created shim for {module}')
