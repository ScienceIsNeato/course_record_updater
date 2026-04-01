"""Unit tests for scripts/test_mailtrap_smtp.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import pytest


def _load_mailtrap_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    script_path = root / "scripts" / "test_mailtrap_smtp.py"
    spec = importlib.util.spec_from_file_location("test_mailtrap_smtp", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_get_mailtrap_api_token(monkeypatch: Any, capsys: Any) -> None:
    module = _load_mailtrap_module()

    monkeypatch.setenv("MAILTRAP_API_TOKEN", "abc123")
    assert module._get_mailtrap_api_token() == "abc123"

    monkeypatch.delenv("MAILTRAP_API_TOKEN", raising=False)
    assert module._get_mailtrap_api_token() is None
    out = capsys.readouterr().out
    assert "Missing MAILTRAP_API_TOKEN" in out
    assert "Add this to your .env file" in out


def test_build_test_recipients() -> None:
    module = _load_mailtrap_module()

    recipients = module._build_test_recipients()
    assert len(recipients) == 3
    assert recipients[0]["email"].endswith("@loopclosertests.mailtrap.io")


@pytest.mark.parametrize(
    ("status_code", "payload", "expected"),
    [
        (200, {"success": True}, True),
        (200, {"success": False}, False),
        (429, {}, False),
        (500, {}, False),
    ],
)
def test_send_via_mailtrap_api_status_handling(
    status_code: int, payload: dict[str, Any], expected: bool, capsys: Any
) -> None:
    module = _load_mailtrap_module()
    response = Mock(status_code=status_code)
    response.json.return_value = payload

    with patch.object(module.requests, "post", return_value=response) as post:
        assert (
            module._send_via_mailtrap_api(
                "token", "to@example.com", "subject", "<p>hi</p>", "hi"
            )
            is expected
        )

    post.assert_called_once()
    assert "Bearer token" == post.call_args.kwargs["headers"]["Authorization"]
    assert "to@example.com" == post.call_args.kwargs["json"]["to"][0]["email"]
    assert post.call_args.kwargs["timeout"] == 30
    assert "to@example.com" in capsys.readouterr().out


def test_send_via_mailtrap_api_exception(capsys: Any) -> None:
    module = _load_mailtrap_module()

    with patch.object(module.requests, "post", side_effect=RuntimeError("boom")):
        assert (
            module._send_via_mailtrap_api(
                "token", "to@example.com", "subject", "<p>hi</p>", "hi"
            )
            is False
        )

    assert "Error sending to to@example.com" in capsys.readouterr().out


def test_report_mailtrap_results_success_and_failure(capsys: Any) -> None:
    module = _load_mailtrap_module()
    email_manager = Mock()
    email_manager.get_failed_jobs.return_value = [
        SimpleNamespace(
            to_email="bad@example.com",
            last_error="rate limited",
            attempts=3,
        )
    ]

    success_stats = {"sent": 3, "failed": 0, "pending": 0}
    failure_stats = {"sent": 1, "failed": 1, "pending": 1}

    assert module._report_mailtrap_results(success_stats, email_manager) is True
    assert module._report_mailtrap_results(failure_stats, email_manager) is False

    out = capsys.readouterr().out
    assert "SUCCESS! All test emails sent" in out
    assert "PARTIAL SUCCESS" in out
    assert "bad@example.com" in out


def test_test_mailtrap_api_missing_token_and_success(monkeypatch: Any) -> None:
    module = _load_mailtrap_module()

    with patch.object(module, "_get_mailtrap_api_token", return_value=None):
        assert module.test_mailtrap_api() is False

    email_manager = Mock()
    email_manager.send_all.return_value = {"sent": 3, "failed": 0, "pending": 0}

    with (
        patch.object(module, "_get_mailtrap_api_token", return_value="secret"),
        patch.object(module, "EmailManager", return_value=email_manager) as manager_cls,
        patch.object(module, "_report_mailtrap_results", return_value=True) as report,
    ):
        assert module.test_mailtrap_api() is True

    manager_cls.assert_called_once_with(
        rate=0.1,
        max_retries=3,
        base_delay=5.0,
        max_delay=60.0,
    )
    assert email_manager.add_email.call_count == 3
    send_callable = email_manager.send_all.call_args.args[0]
    assert callable(send_callable)
    assert email_manager.send_all.call_args.kwargs["timeout"] == 60
    report.assert_called_once_with(
        {"sent": 3, "failed": 0, "pending": 0}, email_manager
    )
