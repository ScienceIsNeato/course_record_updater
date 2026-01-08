"""Unit tests for system date override API endpoints.

TDD: Tests for GET/POST/DELETE /api/profile/system-date.
"""

from datetime import datetime, timezone

import pytest


class TestSystemDateEndpoints:
    """Tests for system date override API endpoints."""

    # =========================================================================
    # GET /api/profile/system-date
    # =========================================================================

    def test_get_system_date_returns_override_when_set(self, client, mocker):
        """GET returns override date when user has one set."""
        override_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_user = {
            "user_id": "test-user-id",
            "email": "admin@test.com",
            "role": "institution_admin",
            "institution_id": "test-inst-id",
            "system_date_override": override_date,
        }

        mocker.patch("src.api_routes.get_current_user", return_value=mock_user)

        response = client.get("/api/profile/system-date")
        assert response.status_code == 200
        data = response.get_json()
        assert data["is_overridden"] is True
        assert data["override_date"] == override_date.isoformat()

    def test_get_system_date_returns_not_overridden_when_none(self, client, mocker):
        """GET returns not overridden when user has no override."""
        mock_user = {
            "user_id": "test-user-id",
            "email": "admin@test.com",
            "role": "institution_admin",
            "institution_id": "test-inst-id",
            "system_date_override": None,
        }

        mocker.patch("src.api_routes.get_current_user", return_value=mock_user)

        response = client.get("/api/profile/system-date")
        assert response.status_code == 200
        data = response.get_json()
        assert data["is_overridden"] is False
        assert data["override_date"] is None

    def test_get_system_date_requires_admin_role(self, client, mocker):
        """GET returns 403 for non-admin (faculty) users."""
        mock_user = {
            "user_id": "test-user-id",
            "email": "faculty@test.com",
            "role": "instructor",
            "institution_id": "test-inst-id",
            "system_date_override": None,
        }

        mocker.patch("src.api_routes.get_current_user", return_value=mock_user)

        response = client.get("/api/profile/system-date")
        assert response.status_code == 403

    def test_get_system_date_requires_authentication(self, client, mocker):
        """GET returns 401 when not authenticated."""
        mocker.patch("src.api_routes.get_current_user", return_value=None)

        response = client.get("/api/profile/system-date")
        assert response.status_code == 401

    # =========================================================================
    # POST /api/profile/system-date
    # =========================================================================

    def test_post_system_date_sets_override(self, client, mocker):
        """POST sets the override date."""
        mock_user = {
            "user_id": "test-user-id",
            "email": "admin@test.com",
            "role": "institution_admin",
            "institution_id": "test-inst-id",
            "system_date_override": None,
        }

        mocker.patch("src.api_routes.get_current_user", return_value=mock_user)
        mock_update = mocker.patch("src.api_routes.update_user", return_value=True)

        response = client.post(
            "/api/profile/system-date",
            json={"date": "2024-01-15T12:00:00Z"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["force_refresh"] is True
        mock_update.assert_called_once()

    def test_post_system_date_requires_admin_role(self, client, mocker):
        """POST returns 403 for non-admin users."""
        mock_user = {
            "user_id": "test-user-id",
            "email": "faculty@test.com",
            "role": "instructor",
            "institution_id": "test-inst-id",
            "system_date_override": None,
        }

        mocker.patch("src.api_routes.get_current_user", return_value=mock_user)

        response = client.post(
            "/api/profile/system-date",
            json={"date": "2024-01-15T12:00:00Z"},
        )
        assert response.status_code == 403

    def test_post_system_date_validates_date_format(self, client, mocker):
        """POST returns 400 for invalid date format."""
        mock_user = {
            "user_id": "test-user-id",
            "email": "admin@test.com",
            "role": "institution_admin",
            "institution_id": "test-inst-id",
            "system_date_override": None,
        }

        mocker.patch("src.api_routes.get_current_user", return_value=mock_user)

        response = client.post(
            "/api/profile/system-date",
            json={"date": "not-a-date"},
        )
        assert response.status_code == 400

    # =========================================================================
    # DELETE /api/profile/system-date
    # =========================================================================

    def test_delete_system_date_clears_override(self, client, mocker):
        """DELETE clears the override."""
        override_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_user = {
            "user_id": "test-user-id",
            "email": "admin@test.com",
            "role": "institution_admin",
            "institution_id": "test-inst-id",
            "system_date_override": override_date,
        }

        mocker.patch("src.api_routes.get_current_user", return_value=mock_user)
        mock_update = mocker.patch("src.api_routes.update_user", return_value=True)

        response = client.delete("/api/profile/system-date")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["force_refresh"] is True
        mock_update.assert_called_once()

    def test_delete_system_date_requires_admin_role(self, client, mocker):
        """DELETE returns 403 for non-admin users."""
        mock_user = {
            "user_id": "test-user-id",
            "email": "faculty@test.com",
            "role": "instructor",
            "institution_id": "test-inst-id",
            "system_date_override": None,
        }

        mocker.patch("src.api_routes.get_current_user", return_value=mock_user)

        response = client.delete("/api/profile/system-date")
        assert response.status_code == 403
