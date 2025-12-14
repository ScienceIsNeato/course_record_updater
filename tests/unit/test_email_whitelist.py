"""
Unit tests for EmailWhitelist functionality.

Tests whitelist enforcement in local/test environments
and bypass in dev/staging/production.
"""

import os
from unittest.mock import patch

import pytest

from email_providers.whitelist import (
    EmailWhitelist,
    get_email_whitelist,
    reset_whitelist,
)


class TestEmailWhitelist:
    """Tests for EmailWhitelist class."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_whitelist()

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_whitelist()

    # =========================
    # Environment Behavior Tests
    # =========================

    def test_whitelist_enforced_in_local_env(self):
        """Whitelist should be enforced in local environment."""
        whitelist = EmailWhitelist(env="local", whitelist_emails=["allowed@test.com"])

        assert whitelist.whitelist_enforced is True
        assert whitelist.is_allowed("allowed@test.com") is True
        assert whitelist.is_allowed("blocked@random.com") is False

    def test_whitelist_enforced_in_test_env(self):
        """Whitelist should be enforced in test environment."""
        whitelist = EmailWhitelist(env="test", whitelist_emails=["*@test.local"])

        assert whitelist.whitelist_enforced is True
        assert whitelist.is_allowed("anyone@test.local") is True
        assert whitelist.is_allowed("anyone@other.com") is False

    def test_whitelist_enforced_in_e2e_env(self):
        """Whitelist should be enforced in e2e environment."""
        whitelist = EmailWhitelist(env="e2e", whitelist_emails=["*@ethereal.email"])

        assert whitelist.whitelist_enforced is True
        assert whitelist.is_allowed("test@ethereal.email") is True
        assert whitelist.is_allowed("real@gmail.com") is False

    def test_whitelist_disabled_in_dev_env(self):
        """Whitelist should NOT be enforced in dev environment."""
        whitelist = EmailWhitelist(env="dev", whitelist_emails=["limited@test.com"])

        assert whitelist.whitelist_enforced is False
        assert whitelist.is_allowed("anyone@anywhere.com") is True
        assert whitelist.is_allowed("any@random-domain.org") is True

    def test_whitelist_disabled_in_staging_env(self):
        """Whitelist should NOT be enforced in staging environment."""
        whitelist = EmailWhitelist(env="staging", whitelist_emails=[])

        assert whitelist.whitelist_enforced is False
        assert whitelist.is_allowed("user@example.com") is True

    def test_whitelist_disabled_in_production_env(self):
        """Whitelist should NOT be enforced in production environment."""
        whitelist = EmailWhitelist(env="production", whitelist_emails=[])

        assert whitelist.whitelist_enforced is False
        assert whitelist.is_allowed("customer@company.com") is True
        assert whitelist.is_allowed("user@anydomain.net") is True

    # =========================
    # Pattern Matching Tests
    # =========================

    def test_exact_email_match(self):
        """Exact email addresses should match."""
        whitelist = EmailWhitelist(
            env="test", whitelist_emails=["user1@test.com", "user2@test.com"]
        )

        assert whitelist.is_allowed("user1@test.com") is True
        assert whitelist.is_allowed("user2@test.com") is True
        assert whitelist.is_allowed("user3@test.com") is False

    def test_domain_wildcard_match(self):
        """Domain wildcards (*@domain.com) should match."""
        whitelist = EmailWhitelist(
            env="test", whitelist_emails=["*@ethereal.email", "*@test.local"]
        )

        assert whitelist.is_allowed("anyone@ethereal.email") is True
        assert whitelist.is_allowed("user123@test.local") is True
        assert whitelist.is_allowed("user@gmail.com") is False

    def test_case_insensitive_matching(self):
        """Email matching should be case-insensitive."""
        whitelist = EmailWhitelist(
            env="test", whitelist_emails=["User@Test.Com", "*@ETHEREAL.EMAIL"]
        )

        assert whitelist.is_allowed("USER@TEST.COM") is True
        assert whitelist.is_allowed("user@test.com") is True
        assert whitelist.is_allowed("Anyone@Ethereal.Email") is True

    def test_whitespace_handling(self):
        """Whitelist should handle whitespace in emails."""
        whitelist = EmailWhitelist(
            env="test", whitelist_emails=["  user@test.com  ", "  *@ethereal.email  "]
        )

        assert whitelist.is_allowed("user@test.com") is True
        assert whitelist.is_allowed("  user@test.com  ") is True

    # =========================
    # Empty Whitelist Tests
    # =========================

    def test_empty_whitelist_blocks_all_in_test(self):
        """Empty whitelist in test env should block all emails."""
        whitelist = EmailWhitelist(env="test", whitelist_emails=[])

        assert whitelist.is_allowed("any@email.com") is False

    def test_empty_whitelist_allows_all_in_production(self):
        """Empty whitelist in production should allow all emails."""
        whitelist = EmailWhitelist(env="production", whitelist_emails=[])

        assert whitelist.is_allowed("any@email.com") is True

    # =========================
    # Blocked Reason Tests
    # =========================

    def test_get_blocked_reason_returns_none_when_allowed(self):
        """Should return None for allowed emails."""
        whitelist = EmailWhitelist(env="test", whitelist_emails=["*@test.local"])

        assert whitelist.get_blocked_reason("user@test.local") is None

    def test_get_blocked_reason_returns_message_when_blocked(self):
        """Should return descriptive message for blocked emails."""
        whitelist = EmailWhitelist(env="test", whitelist_emails=["*@test.local"])

        reason = whitelist.get_blocked_reason("user@blocked.com")

        assert reason is not None
        assert "user@blocked.com" in reason
        assert "test" in reason  # environment name
        assert "*@test.local" in reason  # configured pattern

    # =========================
    # Singleton Tests
    # =========================

    @patch.dict(os.environ, {"ENV": "test", "EMAIL_WHITELIST": "*@test.com"})
    def test_singleton_uses_environment_variables(self):
        """Singleton should read from environment variables."""
        reset_whitelist()
        whitelist = get_email_whitelist()

        assert whitelist.env == "test"
        assert whitelist.is_allowed("user@test.com") is True
        assert whitelist.is_allowed("user@other.com") is False

    def test_singleton_returns_same_instance(self):
        """get_email_whitelist should return same instance."""
        reset_whitelist()

        with patch.dict(os.environ, {"ENV": "local", "EMAIL_WHITELIST": ""}):
            whitelist1 = get_email_whitelist()
            whitelist2 = get_email_whitelist()

            assert whitelist1 is whitelist2
