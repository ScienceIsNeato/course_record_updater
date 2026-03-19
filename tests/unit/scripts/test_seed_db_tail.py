"""Focused tests for seed_db.py helper/entrypoint paths."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest


def _load_seed_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    script_path = root / "scripts" / "seed_db.py"
    spec = importlib.util.spec_from_file_location("seed_db", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_database_url_paths(monkeypatch: Any) -> None:
    module = _load_seed_module()

    args = argparse.Namespace(env="dev", clear=False, demo=False, manifest=None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://manual")
    assert module._resolve_database_url(args) == "postgresql://manual"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("NEON_DB_URL_DEV", "postgresql://dev")
    assert module._resolve_database_url(args) == "postgresql://dev"

    monkeypatch.delenv("NEON_DB_URL_DEV", raising=False)
    with pytest.raises(SystemExit) as ex:
        module._resolve_database_url(args)
    assert ex.value.code == 1

    args_local = argparse.Namespace(env="local", clear=False, demo=False, manifest=None)
    assert module._resolve_database_url(args_local) == "sqlite:///course_records_dev.db"


def test_confirm_deployed_environment_paths(monkeypatch: Any) -> None:
    module = _load_seed_module()

    local_args = argparse.Namespace(env="local", clear=False)
    module._confirm_deployed_environment(local_args, "sqlite:///local.db")

    remote_args = argparse.Namespace(env="dev", clear=True)
    with patch("builtins.input", return_value="yes"):
        module._confirm_deployed_environment(remote_args, "postgresql://x")

    with patch("builtins.input", return_value="no"):
        with pytest.raises(SystemExit) as ex:
            module._confirm_deployed_environment(remote_args, "postgresql://x")
        assert ex.value.code == 0

    with patch("builtins.input", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as ex2:
            module._confirm_deployed_environment(remote_args, "postgresql://x")
        assert ex2.value.code == 0


def test_clear_flask_sessions_and_rotate_token(
    tmp_path: Path, capsys: Any, monkeypatch: Any
) -> None:
    module = _load_seed_module()

    project_root = tmp_path / "proj"
    (project_root / "flask_session").mkdir(parents=True)
    (project_root / "data" / "flask_session").mkdir(parents=True)
    (project_root / "flask_session" / "a.sess").write_text("x", encoding="utf-8")
    (project_root / "data" / "flask_session" / "b.sess").write_text(
        "x", encoding="utf-8"
    )

    monkeypatch.setattr(module, "project_root", project_root)
    module._clear_flask_sessions()

    assert list((project_root / "flask_session").glob("*")) == []
    assert list((project_root / "data" / "flask_session").glob("*")) == []

    with patch(
        "src.services.auth_service.write_db_generation", return_value="abcd1234ef"
    ):
        module._rotate_db_generation()

    out = capsys.readouterr().out
    assert "Cleared 2 session file" in out
    assert "Rotated database generation token" in out


def test_execute_seeding_demo_and_baseline(tmp_path: Path, monkeypatch: Any) -> None:
    module = _load_seed_module()

    demo_args = argparse.Namespace(demo=True, clear=True, manifest=None, env="local")
    demo_instance = Mock()
    demo_instance.seed_demo.return_value = True
    demo_instance.log = Mock()

    with (
        patch.object(module, "DemoSeeder", return_value=demo_instance),
        patch("src.database.database_service.reset_database"),
        patch.object(module, "_clear_flask_sessions"),
        patch.object(module, "_rotate_db_generation"),
    ):
        assert module._execute_seeding(demo_args) is True

    baseline_args = argparse.Namespace(
        demo=False,
        clear=False,
        manifest=str(tmp_path / "manifest.json"),
        env="local",
    )
    (tmp_path / "manifest.json").write_text('{"k": "v"}', encoding="utf-8")

    baseline_instance = Mock()
    baseline_instance.seed_baseline.return_value = True
    baseline_instance.log = Mock()

    with patch.object(module, "BaselineTestSeeder", return_value=baseline_instance):
        assert module._execute_seeding(baseline_args) is True
        baseline_instance.seed_baseline.assert_called_once_with({"k": "v"})


def test_execute_seeding_manifest_load_failure(tmp_path: Path) -> None:
    module = _load_seed_module()

    args = argparse.Namespace(
        demo=False,
        clear=False,
        manifest=str(tmp_path / "missing.json"),
        env="local",
    )

    with pytest.raises(SystemExit) as ex:
        module._execute_seeding(args)
    assert ex.value.code == 1


def test_main_success_and_arg_error(monkeypatch: Any) -> None:
    module = _load_seed_module()

    # Success path
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["seed_db.py", "--env", "local"],
    )
    with (
        patch.object(module, "_resolve_database_url", return_value="sqlite:///x.db"),
        patch.object(module, "_confirm_deployed_environment"),
        patch("src.database.database_service.refresh_connection"),
        patch.object(module, "_execute_seeding", return_value=True),
    ):
        with pytest.raises(SystemExit) as ex:
            module.main()
        assert ex.value.code == 0

    # Invalid args path
    monkeypatch.setattr(module.sys, "argv", ["seed_db.py", "--bad-flag"])
    with pytest.raises(SystemExit):
        module.main()
