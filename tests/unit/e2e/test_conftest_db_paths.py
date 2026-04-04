"""Focused coverage for renamed E2E database paths."""

from __future__ import annotations

import importlib.util
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, call


def _load_e2e_conftest_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    module_path = root / "tests" / "e2e" / "conftest.py"
    spec = importlib.util.spec_from_file_location(
        "loopcloser_e2e_conftest", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyApp:
    def __init__(self) -> None:
        self.config: dict[str, str] = {}

    def app_context(self) -> Any:
        return nullcontext()


class _DummyPage:
    def __init__(self) -> None:
        self.context = SimpleNamespace(clear_cookies=Mock())
        self.goto_calls: list[str] = []
        self.load_states: list[str] = []
        self.fill_calls: list[tuple[str, str]] = []
        self.click_calls: list[str] = []
        self.expect_response_calls: list[str] = []
        self.wait_for_url_calls: list[tuple[str, dict[str, Any]]] = []
        self.wait_for_function_calls: list[tuple[str, dict[str, Any]]] = []

    def goto(self, url: str) -> None:
        self.goto_calls.append(url)

    def wait_for_load_state(self, state: str) -> None:
        self.load_states.append(state)

    def fill(self, selector: str, value: str) -> None:
        self.fill_calls.append((selector, value))

    def click(self, selector: str) -> None:
        self.click_calls.append(selector)

    def expect_response(self, predicate: Any) -> Any:
        self.expect_response_calls.append("called")
        return nullcontext()

    def wait_for_url(self, url: str, **kwargs: Any) -> None:
        self.wait_for_url_calls.append((url, kwargs))

    def wait_for_function(self, script: str, **kwargs: Any) -> None:
        self.wait_for_function_calls.append((script, kwargs))


def test_setup_serial_environment_uses_loopcloser_db(monkeypatch: Any) -> None:
    module = _load_e2e_conftest_module()
    server_process = object()
    clean_stale_db = Mock()
    seed_database = Mock()
    start_server = Mock(return_value=server_process)

    monkeypatch.setattr(module, "_clean_stale_db", clean_stale_db)
    monkeypatch.setattr(module, "_seed_database", seed_database)
    monkeypatch.setattr(module, "_start_e2e_server", start_server)

    proc, worker_db = module._setup_serial_environment(3002)

    assert proc is server_process
    assert worker_db == "loopcloser_e2e.db"
    assert clean_stale_db.call_args_list == [
        call("loopcloser_e2e.db"),
        call("loopcloser_e2e.db"),
    ]
    seed_database.assert_called_once_with("loopcloser_e2e.db")
    start_server.assert_called_once_with(
        3002,
        "loopcloser_e2e.db",
        {"ENV": "e2e", "FLASK_ENV": "e2e", "WTF_CSRF_ENABLED": "false"},
        log_file="server.log",
    )


def test_setup_parallel_environment_uses_loopcloser_worker_db(
    tmp_path: Path, monkeypatch: Any
) -> None:
    module = _load_e2e_conftest_module()
    server_process = object()
    copy_database = Mock()
    start_server = Mock(return_value=server_process)

    monkeypatch.chdir(tmp_path)
    (tmp_path / "loopcloser_e2e.db").write_text("seed", encoding="utf-8")
    monkeypatch.setattr(module.shutil, "copy2", copy_database)
    monkeypatch.setattr(module, "_start_e2e_server", start_server)

    proc, worker_db = module._setup_parallel_environment(4, 3006)

    assert proc is server_process
    assert worker_db == "loopcloser_e2e_worker4.db"
    copy_database.assert_called_once_with(
        "loopcloser_e2e.db", "loopcloser_e2e_worker4.db"
    )
    start_server.assert_called_once_with(
        3006,
        "loopcloser_e2e_worker4.db",
        {"ENV": "e2e", "FLASK_ENV": "e2e", "WTF_CSRF_ENABLED": "false"},
        log_file="logs/e2e_worker4.log",
    )


def test_authenticated_login_fixtures_use_robust_dashboard_waits() -> None:
    module = _load_e2e_conftest_module()
    cases = [
        (
            module.authenticated_page.__wrapped__,
            module.INSTITUTION_ADMIN_EMAIL,
            module.INSTITUTION_ADMIN_PASSWORD,
            30000,
            True,
        ),
        (
            module.authenticated_site_admin_page.__wrapped__,
            module.SITE_ADMIN_EMAIL,
            module.SITE_ADMIN_PASSWORD,
            10000,
            False,
        ),
        (
            module.authenticated_institution_admin_page.__wrapped__,
            module.INSTITUTION_ADMIN_EMAIL,
            module.INSTITUTION_ADMIN_PASSWORD,
            30000,
            True,
        ),
        (
            module.authenticated_program_admin_page.__wrapped__,
            module.PROGRAM_ADMIN_EMAIL,
            module.PROGRAM_ADMIN_PASSWORD,
            15000,
            True,
        ),
        (
            module.program_admin_authenticated_page.__wrapped__,
            module.PROGRAM_ADMIN_EMAIL,
            module.PROGRAM_ADMIN_PASSWORD,
            15000,
            False,
        ),
    ]

    for (
        fixture_func,
        expected_email,
        expected_password,
        timeout,
        expects_context,
    ) in cases:
        page = _DummyPage()

        returned_page = fixture_func(page)

        assert returned_page is page
        page.context.clear_cookies.assert_called_once_with()
        assert page.goto_calls == [f"{module.BASE_URL}/login"]
        assert page.load_states[0] == "networkidle"
        assert page.fill_calls == [
            ('input[name="email"]', expected_email),
            ('input[name="password"]', expected_password),
        ]
        assert page.click_calls == ['button[type="submit"]']
        if fixture_func in {
            module.authenticated_page.__wrapped__,
            module.authenticated_institution_admin_page.__wrapped__,
        }:
            assert page.expect_response_calls == ["called"]
        else:
            assert page.expect_response_calls == []
        assert page.wait_for_url_calls == [
            (
                (
                    f"{module.BASE_URL}/dashboard*"
                    if fixture_func
                    in {
                        module.authenticated_page.__wrapped__,
                        module.authenticated_institution_admin_page.__wrapped__,
                    }
                    else f"{module.BASE_URL}/dashboard"
                ),
                {"timeout": timeout, "wait_until": "domcontentloaded"},
            )
        ]
        if expects_context:
            assert page.load_states[-1] == "networkidle"
            assert len(page.wait_for_function_calls) == 1
            expected_context_timeout = (
                30000
                if fixture_func
                in {
                    module.authenticated_page.__wrapped__,
                    module.authenticated_institution_admin_page.__wrapped__,
                }
                else 15000
            )
            assert page.wait_for_function_calls[0][1] == {
                "timeout": expected_context_timeout
            }
        else:
            assert page.wait_for_function_calls == []


def test_reset_account_locks_uses_loopcloser_worker_db(monkeypatch: Any) -> None:
    module = _load_e2e_conftest_module()
    dummy_app = _DummyApp()
    clear_failed_attempts = Mock()

    monkeypatch.setitem(sys.modules, "src.app", SimpleNamespace(app=dummy_app))
    monkeypatch.setattr(module, "get_worker_id", lambda: 6)
    monkeypatch.setattr(
        module.PasswordService, "clear_failed_attempts", clear_failed_attempts
    )

    reset_account_locks = module.reset_account_locks.__wrapped__
    fixture_gen = reset_account_locks()
    next(fixture_gen)

    expected_db = os.path.abspath("loopcloser_e2e_worker6.db")
    assert dummy_app.config["SQLALCHEMY_DATABASE_URI"] == f"sqlite:///{expected_db}"

    try:
        next(fixture_gen)
    except StopIteration:
        pass


def test_reset_account_locks_uses_loopcloser_serial_db(monkeypatch: Any) -> None:
    module = _load_e2e_conftest_module()
    dummy_app = _DummyApp()
    clear_failed_attempts = Mock()

    monkeypatch.setitem(sys.modules, "src.app", SimpleNamespace(app=dummy_app))
    monkeypatch.setattr(module, "get_worker_id", lambda: None)
    monkeypatch.setattr(
        module.PasswordService, "clear_failed_attempts", clear_failed_attempts
    )

    reset_account_locks = module.reset_account_locks.__wrapped__
    fixture_gen = reset_account_locks()
    next(fixture_gen)

    expected_db = os.path.abspath("loopcloser_e2e.db")
    assert dummy_app.config["SQLALCHEMY_DATABASE_URI"] == f"sqlite:///{expected_db}"

    try:
        next(fixture_gen)
    except StopIteration:
        pass
