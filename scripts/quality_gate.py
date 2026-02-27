#!/usr/bin/env python3
"""Quality gate wrapper that delegates to slop-mop (sm).

This thin wrapper translates the legacy --checks CLI syntax into
slop-mop's verb-based ``sm validate`` syntax and invokes ``sm`` as
a subprocess.  slop-mop is installed externally (via pipx or pip)
— it is NOT bundled as a submodule.

Usage:
    python scripts/quality_gate.py --checks commit    # Fast commit validation
    python scripts/quality_gate.py --checks pr        # Full PR validation
    python scripts/quality_gate.py --verbose --checks python-lint-format
    python scripts/quality_gate.py --help             # Show slop-mop help

Note: For local development, prefer using ``sm`` directly:
    pipx install slopmop   # one-time setup
    sm validate commit
"""

import shutil
import subprocess
import sys
from pathlib import Path

# Map old gate names to new namespaced format
GATE_MAP: dict[str, str] = {
    "python-lint-format": "python:lint-format",
    "python-tests": "python:tests",
    "python-coverage": "python:coverage",
    "python-static-analysis": "python:static-analysis",
    "python-complexity": "quality:complexity",
    "python-security": "security:full",
    "python-security-local": "security:local",
    "python-diff-coverage": "python:diff-coverage",
    "python-new-code-coverage": "python:new-code-coverage",
    "js-lint-format": "javascript:lint-format",
    "js-tests": "javascript:tests",
    "js-coverage": "javascript:coverage",
    "frontend-check": "javascript:frontend",
    "frontend": "javascript:frontend",
    "duplication": "quality:duplication",
    "template-validation": "general:templates",
    "smoke-tests": "integration:smoke-tests",
    "integration-tests": "integration:integration-tests",
    "e2e-tests": "integration:e2e-tests",
}

PROFILES = {
    "commit",
    "pr",
    "quick",
    "python",
    "javascript",
    "e2e",
    "security",
    "security-local",
    "quality",
}


def translate_args(args: list[str]) -> list[str]:
    """Translate old --checks syntax to new verb-based syntax.

    Old format: --checks commit
    New format: validate commit

    Old format: --checks python-lint-format python-tests
    New format: validate --quality-gates python:lint-format,python:tests

    Old format: --verbose --checks commit
    New format: validate commit --verbose
    """
    extra_args: list[str] = []
    checks: list[str] = []
    verbose = False
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == "--verbose":
            verbose = True
            i += 1
        elif arg == "--checks":
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                checks.append(GATE_MAP.get(args[i], args[i]))
                i += 1
        elif arg.startswith("--checks="):
            for check in arg[9:].split(","):
                checks.append(GATE_MAP.get(check, check))
            i += 1
        elif arg in ("--help", "-h", "--list-checks"):
            return ["help"]
        else:
            extra_args.append(arg)
            i += 1

    result = ["validate"]

    if len(checks) == 1 and checks[0] in PROFILES:
        result.append(checks[0])
    elif checks:
        result.extend(["--quality-gates", ",".join(checks)])

    if verbose:
        result.append("--verbose")

    result.extend(extra_args)
    return result


def _find_sm() -> str:
    """Locate the ``sm`` executable."""
    sm = shutil.which("sm")
    if sm:
        return sm
    # Fall back to python -m slopmop.sm (works if slopmop is pip-installed
    # in the current venv but the entry-point script isn't on PATH).
    return ""


def main() -> int:
    """Run slop-mop quality gate."""
    project_root = Path(__file__).resolve().parent.parent

    sm_path = _find_sm()

    # Translate legacy --checks syntax → sm validate …
    sm_args = translate_args(sys.argv[1:])

    # Inject --project-root for validate commands
    verb = sm_args[0] if sm_args else "validate"
    if verb == "validate":
        has_project_root = any(
            a == "--project-root" or a.startswith("--project-root=") for a in sm_args
        )
        if not has_project_root:
            sm_args.extend(["--project-root", str(project_root)])

    if sm_path:
        cmd = [sm_path] + sm_args
    else:
        # Try as a Python module
        cmd = [sys.executable, "-m", "slopmop.sm"] + sm_args

    try:
        result = subprocess.run(cmd, cwd=str(project_root))
        return result.returncode
    except FileNotFoundError:
        print(
            "Error: slop-mop (sm) is not installed.\n"
            "Install via:  pipx install slopmop\n"
            "  or:         pip install slopmop",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
