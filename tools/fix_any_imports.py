from pathlib import Path


ROOT = Path("tests")


def find_insert_at(lines: list[str]) -> int:
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1

    if index < len(lines):
        line = lines[index]
        if line.startswith(('"""', "'''")):
            quote = line[:3]
            if line.count(quote) >= 2 and len(line) > 5:
                index += 1
            else:
                index += 1
                while index < len(lines):
                    if quote in lines[index]:
                        index += 1
                        break
                    index += 1

    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.startswith("#"):
            index += 1
            continue
        if line.startswith(("from __future__ import ", "import ", "from ")):
            paren_depth = line.count("(") - line.count(")")
            index += 1
            while paren_depth > 0 and index < len(lines):
                paren_depth += lines[index].count("(") - lines[index].count(")")
                index += 1
            continue
        break

    return index


def needs_any(lines: list[str]) -> bool:
    return any(": Any" in line or "-> Any" in line for line in lines)


def has_top_any(lines: list[str]) -> bool:
    cutoff = find_insert_at(lines)
    for line in lines[: cutoff + 1]:
        if line.startswith("from typing import ") and "Any" in line:
            return True
    return False


def rewrite_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original_lines = text.splitlines()
    lines: list[str] = []
    in_broken_import_block = False

    for line in original_lines:
        stripped = line.strip()

        if stripped == "from typing import Any":
            continue

        if line.startswith("from ") and line.rstrip().endswith("import ("):
            in_broken_import_block = True
            lines.append(line)
            continue

        if in_broken_import_block and stripped in {"Any,", "from,", "import,", "typing,"}:
            continue

        lines.append(line)

        if in_broken_import_block and ")" in line:
            in_broken_import_block = False

    if needs_any(lines) and not has_top_any(lines):
        lines.insert(find_insert_at(lines), "from typing import Any")

    new_text = "\n".join(lines)
    if text.endswith("\n"):
        new_text += "\n"

    if new_text == text:
        return False

    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    changed = []
    for path in ROOT.rglob("*.py"):
        if rewrite_file(path):
            changed.append(str(path))

    print(f"fixed {len(changed)} files")
    for name in changed[:50]:
        print(name)


if __name__ == "__main__":
    main()