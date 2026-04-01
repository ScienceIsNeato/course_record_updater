"""Unit tests for scripts/test_export.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch


def _load_test_export_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    script_path = root / "scripts" / "test_export.py"
    spec = importlib.util.spec_from_file_location("test_export_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ensure_mocku_institution_uses_existing(capsys: Any) -> None:
    module = _load_test_export_module()

    with (
        patch(
            "src.database.database_service.get_institution_by_short_name",
            return_value={"institution_id": "inst-123"},
        ),
        patch(
            "src.database.database_service.create_default_mocku_institution"
        ) as create,
    ):
        institution_id = module.ensure_mocku_institution()

    assert institution_id == "inst-123"
    create.assert_not_called()
    assert "Using existing MockU institution" in capsys.readouterr().out


def test_ensure_mocku_institution_creates_when_missing(capsys: Any) -> None:
    module = _load_test_export_module()

    with (
        patch(
            "src.database.database_service.get_institution_by_short_name",
            return_value=None,
        ),
        patch(
            "src.database.database_service.create_default_mocku_institution",
            return_value="inst-new",
        ) as create,
    ):
        institution_id = module.ensure_mocku_institution()

    assert institution_id == "inst-new"
    create.assert_called_once_with()
    assert "Created MockU institution" in capsys.readouterr().out


def test_create_export_test_data_builds_expected_records() -> None:
    module = _load_test_export_module()

    with (
        patch.object(
            module, "create_user", side_effect=["user-1", "user-2"]
        ) as create_user,
        patch.object(
            module, "create_course", side_effect=["course-1", "course-2"]
        ) as create_course,
        patch.object(module, "create_term", return_value="term-1") as create_term,
    ):
        module.create_export_test_data("inst-55")

    assert create_user.call_count == 2
    assert create_course.call_count == 2
    create_term.assert_called_once()
    assert create_user.call_args_list[0].args[0]["institution_id"] == "inst-55"
    assert create_course.call_args_list[1].args[0]["course_number"] == "SCI-201"
    assert create_term.call_args.args[0]["term_name"] == "Fall 2024"


def test_run_export_handles_success_and_failure(capsys: Any) -> None:
    module = _load_test_export_module()
    success_result = SimpleNamespace(
        success=True,
        file_path="build-output/test_export.xlsx",
        records_exported=7,
        warnings=["warn"],
        errors=[],
    )
    failure_result = SimpleNamespace(
        success=False,
        file_path=None,
        records_exported=0,
        warnings=[],
        errors=["boom"],
    )

    export_service = Mock()
    export_service.export_data.side_effect = [success_result, failure_result]

    with patch.object(module, "ExportService", return_value=export_service):
        assert module.run_export("inst-ok") is True
        assert module.run_export("inst-bad") is False

    first_config = export_service.export_data.call_args_list[0].args[0]
    first_output = export_service.export_data.call_args_list[0].args[1]
    assert first_config.institution_id == "inst-ok"
    assert first_output == Path("build-output/test_export.xlsx")
    out = capsys.readouterr().out
    assert "Export successful" in out
    assert "Export failed" in out


def test_run_export_test_success_and_exception_paths() -> None:
    module = _load_test_export_module()

    with (
        patch.object(module, "ensure_mocku_institution", return_value="inst-1"),
        patch.object(module, "create_export_test_data") as create_data,
        patch.object(module, "run_export", return_value=True) as run_export,
    ):
        assert module.run_export_test() is True

    create_data.assert_called_once_with("inst-1")
    run_export.assert_called_once_with("inst-1")

    with patch.object(
        module, "ensure_mocku_institution", side_effect=RuntimeError("explode")
    ):
        assert module.run_export_test() is False
