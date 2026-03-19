#!/usr/bin/env python3
"""Ensure slopmop agent template directories exist in CI environments.

Some slopmop wheel installs can miss agent template directories used when
building the CLI parser. This helper creates any missing directories so `sm`
commands can run reliably in CI.
"""

from pathlib import Path


def main() -> int:
    import slopmop
    from slopmop.agent_install.registry import TARGETS

    templates_root = (
        Path(slopmop.__file__).resolve().parent / "agent_install" / "templates"
    )
    templates_root.mkdir(parents=True, exist_ok=True)

    ensured = set()
    for target in TARGETS.values():
        template_dir = templates_root / target.template_dir
        template_dir.mkdir(parents=True, exist_ok=True)
        ensured.add(target.template_dir)

    print("Ensured slopmop template dirs:", ", ".join(sorted(ensured)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
