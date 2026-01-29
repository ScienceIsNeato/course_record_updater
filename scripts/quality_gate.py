#!/usr/bin/env python3
"""Quality gate wrapper that delegates to slop-mop.

This thin wrapper provides a simple interface to the slop-mop quality gate
framework installed as a git submodule.

Usage:
    python scripts/quality_gate.py --checks commit    # Fast commit validation
    python scripts/quality_gate.py --checks pr        # Full PR validation
    python scripts/quality_gate.py --verbose --checks python-lint-format
    python scripts/quality_gate.py --help             # Show slop-mop help

Note: This wrapper exists for CI compatibility. For local development,
prefer using the `sm` command directly after installing slop-mop:
    cd tools/slopmop && pip install -e .
    sm validate commit
"""

import sys
from pathlib import Path


def translate_args(args: list[str]) -> list[str]:
    """Translate old --checks syntax to new verb-based syntax.

    Old format: --checks commit
    New format: validate commit

    Old format: --checks python-lint-format python-tests
    New format: validate --quality-gates python:lint-format,python:tests

    Old format: --verbose --checks commit
    New format: validate commit --verbose
    """
    # Map old gate names to new namespaced format
    gate_map = {
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

    new_args = []
    checks = []
    verbose = False
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == "--verbose":
            verbose = True
            i += 1
        elif arg == "--checks":
            # Collect all arguments after --checks until next flag or end
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                check = args[i]
                # Translate old gate names to new format
                checks.append(gate_map.get(check, check))
                i += 1
        elif arg.startswith("--checks="):
            # Handle --checks=value format
            for check in arg[9:].split(","):
                checks.append(gate_map.get(check, check))
            i += 1
        elif arg == "--help" or arg == "-h":
            return ["help"]
        elif arg == "--list-checks":
            return ["help"]
        else:
            new_args.append(arg)
            i += 1

    # Build the new command
    result = ["validate"]

    # Check if any check is a profile (commit, pr, quick, python, javascript, e2e)
    profiles = {
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

    if len(checks) == 1 and checks[0] in profiles:
        # Single profile - use as positional argument
        result.append(checks[0])
    elif checks:
        # Multiple gates or non-profile - use --quality-gates
        result.extend(["--quality-gates", ",".join(checks)])

    if verbose:
        result.append("--verbose")

    result.extend(new_args)

    return result


def main() -> int:
    """Run slop-mop quality gate."""
    # Find project root and slopmop location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    slopmop_dir = project_root / "tools" / "slopmop"

    # Check if slopmop submodule is available
    if not slopmop_dir.exists():
        print("Error: slop-mop submodule not found at tools/slopmop", file=sys.stderr)
        print("Run: git submodule update --init --recursive", file=sys.stderr)
        return 1

    cli_module = slopmop_dir / "slopmop" / "sm.py"
    if not cli_module.exists():
        print(f"Error: slop-mop CLI not found at {cli_module}", file=sys.stderr)
        return 1

    # Add slopmop to Python path
    sys.path.insert(0, str(slopmop_dir))

    # Import slop-mop CLI - narrow try/except for import only
    try:
        from slopmop.sm import main as slopmop_main
    except ImportError as e:
        print(f"Error importing slop-mop: {e}", file=sys.stderr)
        print("Try: pip install -e tools/slopmop", file=sys.stderr)
        return 1

    # Translate old --checks syntax to new verb-based syntax
    args = translate_args(sys.argv[1:])

    # Determine the verb (first argument)
    verb = args[0] if args else "validate"

    # Only add project root for validate command (help/config don't need it)
    if verb == "validate":
        has_project_root = any(
            arg == "--project-root" or arg.startswith("--project-root=") for arg in args
        )
        if not has_project_root:
            args.extend(["--project-root", str(project_root)])

    return slopmop_main(args)


if __name__ == "__main__":
    sys.exit(main())
