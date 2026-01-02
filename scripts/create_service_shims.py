#!/usr/bin/env python3
"""
Create backward compatibility shims for service modules.
"""

SERVICE_MODULES = [
    "auth_service",
    "audit_service",
    "dashboard_service",
    "email_service",
    "import_service",
    "invitation_service",
    "login_service",
    "password_service",
    "password_reset_service",
    "registration_service",
    "export_service",
    "bulk_email_service",
    "clo_workflow_service",
]

SHIM_TEMPLATE = '''"""
DEPRECATED: This module has moved to src.services.{module}
This file exists for backward compatibility during migration.
"""
import warnings
from src.services.{module} import *  # noqa: F401, F403

warnings.warn(
    "Importing from '{module}' is deprecated. Use 'from src.services.{module} import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)
'''

for module in SERVICE_MODULES:
    with open(f"{module}.py", "w") as f:
        f.write(SHIM_TEMPLATE.format(module=module))
    print(f"Created shim for {module}")

print(f"\n✅ Created {len(SERVICE_MODULES)} service shims")
