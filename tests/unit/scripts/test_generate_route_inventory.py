"""Unit tests for scripts/generate_route_inventory.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_route_inventory_module() -> Any:
    root = Path(__file__).resolve().parents[3]
    script_path = root / "scripts" / "generate_route_inventory.py"
    spec = importlib.util.spec_from_file_location(
        "generate_route_inventory", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_load_module = _load_route_inventory_module


def test_extract_routes_from_file_and_regex(tmp_path: Path) -> None:
    module = _load_route_inventory_module()

    api_routes_dir = tmp_path / "api" / "routes"
    api_routes_dir.mkdir(parents=True)
    py_file = api_routes_dir / "sample_routes.py"
    py_file.write_text(
        "\n".join(
            [
                "from flask import Blueprint",
                "bp = Blueprint('x', url_prefix='/api/sample')",
                "@bp.route('/ping', methods=['GET', 'POST'])",
                "def ping():",
                "    return 'ok'",
                "",
                "# @bp.route('/commented')",
                "@bp.route('/hello')",
                "def hello():",
                "    return 'hi'",
            ]
        ),
        encoding="utf-8",
    )

    ast_routes = module.extract_routes_from_file(py_file)
    regex_routes = module.extract_routes_regex(py_file)

    assert len(ast_routes) == 2
    assert any(r["path"] == "/ping" for r in ast_routes)
    assert len(regex_routes) == 2
    assert any(r["path"] == "/hello" for r in regex_routes)
    assert module.get_blueprint_prefix(py_file) == "/api/sample"


def test_extract_routes_from_file_error(tmp_path: Path, capsys: Any) -> None:
    module = _load_route_inventory_module()

    bad_file = tmp_path / "broken.py"
    bad_file.write_text("def x(:\n", encoding="utf-8")

    routes = module.extract_routes_from_file(bad_file)
    out = capsys.readouterr().out

    assert routes == []
    assert "Error parsing" in out


def test_extract_auth_and_access_helpers(tmp_path: Path) -> None:
    module = _load_module()

    auth_file = tmp_path / "auth_routes.py"
    auth_file.write_text(
        "\n".join(
            [
                "@login_required",
                "@permission_required('manage_users')",
                "def secure_fn():",
                "    if has_permission('x'):",
                "        return True",
            ]
        ),
        encoding="utf-8",
    )

    auth = module.extract_auth_requirements(auth_file, "secure_fn")
    assert auth["login_required"] is True
    assert auth["permission_required"] == "manage_users"
    assert auth["has_permission_check"] is True

    assert module.map_route_to_template("/", "x.py") == "splash.html"
    assert (
        module.map_route_to_template("/reset-password/token", "x.py")
        == "auth/reset_password.html"
    )
    assert module.map_route_to_template("/unknown", "x.py") == ""

    assert module._determine_api_role_access("/api/health", auth) == ["public"]
    assert module._determine_api_role_access("/api/data", auth) == ["site_admin"]
    assert module._determine_page_role_access("/dashboard", auth) == [
        "site_admin",
        "institution_admin",
        "program_admin",
        "instructor",
    ]


def test_enrich_and_report_generation(tmp_path: Path) -> None:
    module = _load_module()

    raw_routes = [
        {
            "path": "/dashboard",
            "methods": ["GET"],
            "type": "page",
            "source_file": "src/app.py",
            "function_name": "dashboard",
            "login_required": True,
            "permission_required": None,
            "has_permission_check": False,
        },
        {
            "path": "/dashboard",
            "methods": ["GET"],
            "type": "page",
            "source_file": "src/app.py",
            "function_name": "dashboard_dup",
            "login_required": True,
            "permission_required": None,
            "has_permission_check": False,
        },
        {
            "path": "/api/auth/login",
            "methods": ["POST"],
            "type": "api",
            "source_file": "src/api/routes/auth.py",
            "function_name": "login",
            "login_required": False,
            "permission_required": None,
            "has_permission_check": False,
        },
    ]

    unique = module._deduplicate_routes(raw_routes)
    enriched = module._enrich_routes(unique)

    assert len(unique) == 2
    assert len(enriched) == 2
    assert any(r["template"] == "dashboard/{role}.html" for r in enriched)

    out_file = tmp_path / "route_inventory.md"
    module._write_markdown_report(out_file, enriched)

    report = out_file.read_text(encoding="utf-8")
    assert "# Route Inventory" in report
    assert "API Routes" in report
    assert "Routes by Role" in report


def test_main_end_to_end(tmp_path: Path, monkeypatch: Any) -> None:
    module = _load_module()

    project = tmp_path / "project"
    scripts_dir = project / "scripts"
    scripts_dir.mkdir(parents=True)

    app_py = project / "app.py"
    app_py.write_text(
        "\n".join(
            [
                "@app.route('/')",
                "def home():",
                "    return 'ok'",
            ]
        ),
        encoding="utf-8",
    )

    api_routes_py = project / "api_routes.py"
    api_routes_py.write_text(
        "\n".join(
            [
                "@api.route('/health')",
                "def health():",
                "    return 'ok'",
            ]
        ),
        encoding="utf-8",
    )

    mod_routes = project / "api" / "routes"
    mod_routes.mkdir(parents=True)
    users_py = mod_routes / "users.py"
    users_py.write_text(
        "\n".join(
            [
                "from flask import Blueprint",
                "bp = Blueprint('users', __name__, url_prefix='/api/users')",
                "@bp.route('/list', methods=['GET'])",
                "def list_users():",
                "    return []",
            ]
        ),
        encoding="utf-8",
    )

    fake_script = scripts_dir / "generate_route_inventory.py"
    fake_script.write_text("# placeholder", encoding="utf-8")
    monkeypatch.setattr(module, "__file__", str(fake_script))

    module.main()

    output = project / "logs" / "exploration" / "route_inventory.md"
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "/" in text
    assert "/api/health" in text
    assert "/api/list" in text
