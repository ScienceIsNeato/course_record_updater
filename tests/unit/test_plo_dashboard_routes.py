"""Unit tests for src.api.routes.plo_dashboard (PLO dashboard API)."""

import sys
from unittest.mock import patch

import pytest
from flask import Flask

# ---------------------------------------------------------------------------
# Module-swap trick: import the blueprint with decorators bypassed so we can
# test the view functions directly with a minimal Flask test app.
# ---------------------------------------------------------------------------

_original_module = sys.modules.get("src.api.routes.plo_dashboard")

with (
    patch("src.services.auth_service.login_required", lambda f: f),
    patch(
        "src.services.auth_service.permission_required", lambda *a, **kw: lambda f: f
    ),
):
    if "src.api.routes.plo_dashboard" in sys.modules:
        del sys.modules["src.api.routes.plo_dashboard"]
    from src.api.routes.plo_dashboard import plo_dashboard_bp

    _test_module = sys.modules["src.api.routes.plo_dashboard"]

# Restore original module
if _original_module is not None:
    sys.modules["src.api.routes.plo_dashboard"] = _original_module
else:
    sys.modules.pop("src.api.routes.plo_dashboard", None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _swap_module():
    """Ensure patches target the test-imported module."""
    saved = sys.modules.get("src.api.routes.plo_dashboard")
    sys.modules["src.api.routes.plo_dashboard"] = _test_module
    yield
    if saved is not None:
        sys.modules["src.api.routes.plo_dashboard"] = saved
    else:
        sys.modules.pop("src.api.routes.plo_dashboard", None)


@pytest.fixture
def app():
    test_app = Flask(__name__)
    test_app.config["TESTING"] = True
    test_app.register_blueprint(plo_dashboard_bp)
    return test_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Sample tree response for mocking
# ---------------------------------------------------------------------------

_TREE_DATA = {
    "programs": [
        {
            "id": "prog-1",
            "name": "Biology",
            "short_name": "BIOL",
            "plo_count": 2,
            "mapped_clo_count": 3,
            "mapping_version": 1,
            "mapping_status": "published",
            "assessment_display_mode": "percentage",
            "plos": [],
        }
    ],
    "term": {"id": "term-1", "name": "Fall 2025"},
    "summary": {
        "total_programs": 1,
        "total_plos": 2,
        "total_mapped_clos": 3,
        "clos_with_data": 2,
        "clos_missing_data": 1,
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetTree:
    @patch("src.api.routes.plo_dashboard.get_plo_dashboard_tree")
    @patch("src.api.routes.plo_dashboard.get_current_institution_id_safe")
    def test_success(self, mock_inst, mock_tree, client):
        mock_inst.return_value = "inst-1"
        mock_tree.return_value = _TREE_DATA

        resp = client.get("/api/plo-dashboard/tree")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["summary"]["total_programs"] == 1
        mock_tree.assert_called_once_with(
            institution_id="inst-1", term_id=None, program_id=None
        )

    @patch("src.api.routes.plo_dashboard.get_plo_dashboard_tree")
    @patch("src.api.routes.plo_dashboard.get_current_institution_id_safe")
    def test_with_filters(self, mock_inst, mock_tree, client):
        mock_inst.return_value = "inst-1"
        mock_tree.return_value = _TREE_DATA

        resp = client.get("/api/plo-dashboard/tree?term_id=term-1&program_id=prog-1")

        assert resp.status_code == 200
        mock_tree.assert_called_once_with(
            institution_id="inst-1", term_id="term-1", program_id="prog-1"
        )

    @patch("src.api.routes.plo_dashboard.get_current_institution_id_safe")
    def test_no_institution_returns_403(self, mock_inst, client):
        mock_inst.return_value = ""

        resp = client.get("/api/plo-dashboard/tree")

        assert resp.status_code == 403
        data = resp.get_json()
        assert data["success"] is False
        assert "institution" in data["error"].lower()

    @patch("src.api.routes.plo_dashboard.get_plo_dashboard_tree")
    @patch("src.api.routes.plo_dashboard.get_current_institution_id_safe")
    def test_service_error_returns_500(self, mock_inst, mock_tree, client):
        mock_inst.return_value = "inst-1"
        mock_tree.side_effect = RuntimeError("DB connection failed")

        resp = client.get("/api/plo-dashboard/tree")

        assert resp.status_code == 500
        data = resp.get_json()
        assert data["success"] is False

    @patch("src.api.routes.plo_dashboard.get_plo_dashboard_tree")
    @patch("src.api.routes.plo_dashboard.get_current_institution_id_safe")
    def test_empty_tree(self, mock_inst, mock_tree, client):
        mock_inst.return_value = "inst-1"
        mock_tree.return_value = {
            "programs": [],
            "term": None,
            "summary": {
                "total_programs": 0,
                "total_plos": 0,
                "total_mapped_clos": 0,
                "clos_with_data": 0,
                "clos_missing_data": 0,
            },
        }

        resp = client.get("/api/plo-dashboard/tree")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["programs"] == []
