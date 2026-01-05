"""Unit tests for time_utils module.

TDD: These tests define the expected behavior for get_current_time().
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def flask_app():
    """Create Flask app context for testing."""
    from src.app import app

    app.config["TESTING"] = True
    return app


class TestGetCurrentTime:
    """Tests for get_current_time() function."""

    def test_returns_datetime_with_timezone(self, flask_app):
        """get_current_time() returns timezone-aware datetime."""
        from src.utils.time_utils import get_current_time

        with flask_app.app_context():
            result = get_current_time()
            assert isinstance(result, datetime)
            assert result.tzinfo == timezone.utc

    def test_returns_real_time_when_no_user(self, flask_app):
        """Without a logged-in user, returns real datetime.now()."""
        from flask import g

        from src.utils.time_utils import get_current_time

        with flask_app.app_context():
            # Ensure no current_user is set
            if hasattr(g, "current_user"):
                delattr(g, "current_user")

            before = datetime.now(timezone.utc)
            result = get_current_time()
            after = datetime.now(timezone.utc)

            # Result should be between before and after (real time)
            assert before <= result <= after

    def test_returns_real_time_when_user_has_no_override(self, flask_app):
        """User without override gets real datetime.now()."""
        from flask import g

        from src.utils.time_utils import get_current_time

        with flask_app.app_context():
            mock_user = MagicMock()
            mock_user.system_date_override = None
            g.current_user = mock_user

            before = datetime.now(timezone.utc)
            result = get_current_time()
            after = datetime.now(timezone.utc)

            assert before <= result <= after

    def test_returns_override_when_user_has_override_set(self, flask_app):
        """User with override gets override datetime."""
        from flask import g

        from src.utils.time_utils import get_current_time

        with flask_app.app_context():
            override_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
            mock_user = MagicMock()
            mock_user.system_date_override = override_date
            g.current_user = mock_user

            result = get_current_time()

            assert result == override_date

    def test_handles_missing_current_user_attribute_on_g(self, flask_app):
        """Handles case where g doesn't have current_user attr."""
        from flask import g

        from src.utils.time_utils import get_current_time

        with flask_app.app_context():
            # Ensure no current_user attribute exists
            if hasattr(g, "current_user"):
                delattr(g, "current_user")

            before = datetime.now(timezone.utc)
            result = get_current_time()
            after = datetime.now(timezone.utc)

            assert before <= result <= after

    def test_returns_real_time_outside_request_context(self):
        """Outside of any Flask context, returns real datetime.now()."""
        from src.utils.time_utils import get_current_time

        before = datetime.now(timezone.utc)
        result = get_current_time()
        after = datetime.now(timezone.utc)

        assert before <= result <= after
