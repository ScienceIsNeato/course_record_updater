"""Focused unit tests for src/import_cli.py."""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, mock_open, patch

import pytest

import src.import_cli as import_cli


def _build_args(**overrides: Any) -> import_cli.CLIArgs:
    defaults = {
        "file": "sample.xlsx",
        "institution_id": "inst-1",
        "use_mine": False,
        "use_theirs": True,
        "merge": False,
        "manual_review": False,
        "dry_run": False,
        "adapter": "cei_excel_format_v1",
        "verbose": False,
        "report_file": None,
        "validate_only": False,
        "delete_existing_db": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)  # type: ignore[return-value]


def _build_result(**overrides: Any) -> Any:
    defaults = {
        "success": True,
        "dry_run": False,
        "execution_time": 1.25,
        "records_processed": 10,
        "records_created": 5,
        "records_updated": 3,
        "records_skipped": 2,
        "conflicts_detected": 0,
        "conflicts_resolved": 0,
        "conflicts": [],
        "errors": [],
        "warnings": [],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_determine_conflict_strategy_variants() -> None:
    assert (
        import_cli.determine_conflict_strategy(
            _build_args(use_mine=True, use_theirs=False)
        )
        == "use_mine"
    )
    assert (
        import_cli.determine_conflict_strategy(_build_args(use_theirs=True))
        == "use_theirs"
    )
    assert (
        import_cli.determine_conflict_strategy(
            _build_args(use_theirs=False, merge=True)
        )
        == "merge"
    )
    assert (
        import_cli.determine_conflict_strategy(
            _build_args(use_theirs=False, manual_review=True)
        )
        == "manual_review"
    )
    assert (
        import_cli.determine_conflict_strategy(_build_args(use_theirs=False))
        == "use_theirs"
    )


def test_validate_file_paths(monkeypatch: Any, capsys: Any) -> None:
    missing = str(Path("missing.xlsx"))
    monkeypatch.setattr(import_cli.os.path, "exists", lambda _: False)
    assert import_cli.validate_file(missing) is False
    assert "Error:" in capsys.readouterr().out

    monkeypatch.setattr(import_cli.os.path, "exists", lambda _: True)
    monkeypatch.setattr(import_cli.os, "access", lambda *_: False)
    assert import_cli.validate_file("locked.xlsx") is False

    monkeypatch.setattr(import_cli.os, "access", lambda *_: True)
    with patch("builtins.input", return_value="n"):
        assert import_cli.validate_file("bad.txt") is False

    with patch("builtins.input", return_value="y"):
        assert import_cli.validate_file("bad.txt") is True
    assert import_cli.validate_file("good.xlsx") is True


def test_print_summary_verbose_conflicts_and_lists(capsys: Any) -> None:
    conflict = SimpleNamespace(
        entity_type="course",
        entity_key="MATH-101",
        field_name="course_name",
        existing_value="Old",
        import_value="New",
        resolution="use_theirs",
    )
    result = _build_result(
        conflicts_detected=12,
        conflicts_resolved=10,
        conflicts=[conflict] * 12,
        errors=["e1", "e2"],
        warnings=["w1"],
    )

    import_cli.print_summary(result, verbose=True)
    out = capsys.readouterr().out
    assert "IMPORT SUMMARY" in out
    assert "Conflict Details" in out
    assert "and 2 more conflicts" in out
    assert "ERRORS (2)" in out
    assert "WARNINGS (1)" in out


def test_save_report_success_and_failure(capsys: Any) -> None:
    result = _build_result()

    with (
        patch.object(import_cli, "create_import_report", return_value="report body"),
        patch("builtins.open", mock_open()) as mocked_open,
    ):
        import_cli.save_report(result, "report.txt")

    mocked_open.assert_called_once_with("report.txt", "w", encoding="utf-8")
    assert "Detailed report saved" in capsys.readouterr().out

    with patch.object(
        import_cli, "create_import_report", side_effect=RuntimeError("boom")
    ):
        import_cli.save_report(result, "report.txt")
    assert "Error saving report" in capsys.readouterr().out


def test_confirm_execution_paths() -> None:
    with patch("builtins.input", return_value="y"):
        import_cli.confirm_execution()

    with patch("builtins.input", return_value="n"):
        with pytest.raises(SystemExit) as ex:
            import_cli.confirm_execution()
        assert ex.value.code == 0


def test_handle_validate_only_mode_success_and_failure(capsys: Any) -> None:
    args = _build_args(validate_only=True, verbose=True)
    service = Mock()
    service.validate_file.side_effect = [
        _build_result(success=True),
        _build_result(success=False, errors=["bad sheet", "bad rows"]),
    ]

    with patch.object(import_cli, "ImportService", return_value=service):
        with pytest.raises(SystemExit) as ex1:
            import_cli.handle_validate_only_mode(args)
        assert ex1.value.code == 0

        with pytest.raises(SystemExit) as ex2:
            import_cli.handle_validate_only_mode(args)
        assert ex2.value.code == 1

    out = capsys.readouterr().out
    assert "Valid format" in out
    assert "bad sheet" in out


def test_execute_import_success_failure_and_exceptions(capsys: Any) -> None:
    args = _build_args(report_file="report.txt", verbose=True)
    success_result = _build_result(success=True)
    failure_result = _build_result(success=False)

    with (
        patch.object(
            import_cli, "import_excel", side_effect=[success_result, failure_result]
        ),
        patch.object(import_cli, "print_summary") as print_summary,
        patch.object(import_cli, "save_report") as save_report,
    ):
        with pytest.raises(SystemExit) as ex1:
            import_cli.execute_import(args, "use_theirs")
        assert ex1.value.code == 0

        with pytest.raises(SystemExit) as ex2:
            import_cli.execute_import(args, "use_theirs")
        assert ex2.value.code == 1

    assert print_summary.call_count == 2
    assert save_report.call_count == 2

    with patch.object(import_cli, "import_excel", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as ex3:
            import_cli.execute_import(args, "use_theirs")
        assert ex3.value.code == 130

    with patch.object(import_cli, "import_excel", side_effect=RuntimeError("boom")):
        with pytest.raises(SystemExit) as ex4:
            import_cli.execute_import(args, "use_theirs")
        assert ex4.value.code == 1

    out = capsys.readouterr().out
    assert "Import completed successfully!" in out
    assert "Import completed with errors" in out
    assert "Import cancelled by user" in out
    assert "Unexpected error during import" in out


def test_main_success_validate_only_and_invalid_file() -> None:
    args = _build_args(dry_run=False, validate_only=False)

    with (
        patch.object(import_cli, "parse_arguments", return_value=args),
        patch.object(import_cli, "validate_file", return_value=True),
        patch.object(import_cli, "print_configuration"),
        patch.object(import_cli, "confirm_execution") as confirm_execution,
        patch.object(import_cli, "handle_validate_only_mode") as validate_only,
        patch.object(import_cli, "execute_import") as execute_import,
    ):
        import_cli.main()

    confirm_execution.assert_called_once_with()
    validate_only.assert_not_called()
    execute_import.assert_called_once_with(args, "use_theirs")

    validate_args = _build_args(validate_only=True)
    with (
        patch.object(import_cli, "parse_arguments", return_value=validate_args),
        patch.object(import_cli, "validate_file", return_value=True),
        patch.object(import_cli, "print_configuration"),
        patch.object(import_cli, "confirm_execution") as confirm_execution_2,
        patch.object(import_cli, "handle_validate_only_mode") as validate_only_2,
        patch.object(import_cli, "execute_import") as execute_import_2,
    ):
        import_cli.main()

    confirm_execution_2.assert_not_called()
    validate_only_2.assert_called_once_with(validate_args)
    execute_import_2.assert_called_once_with(validate_args, "use_theirs")

    with (
        patch.object(import_cli, "parse_arguments", return_value=args),
        patch.object(import_cli, "validate_file", return_value=False),
    ):
        with pytest.raises(SystemExit) as ex:
            import_cli.main()
        assert ex.value.code == 1
