"""Coverage for migrate_v1.py entrypoint defaults."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path
from typing import Any


def test_main_defaults_to_loopcloser_db(
    tmp_path: Path, capsys: Any, monkeypatch: Any
) -> None:
    root = Path(__file__).resolve().parents[3]
    script_path = root / "scripts" / "migrate_v1.py"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["migrate_v1.py"])

    runpy.run_path(str(script_path), run_name="__main__")

    out = capsys.readouterr().out
    assert "Migrating loopcloser.db..." in out
    assert "Database loopcloser.db not found." in out
