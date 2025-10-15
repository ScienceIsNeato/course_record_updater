"""
Unit tests for EmailWhitelist
"""

from email_providers.whitelist import EmailWhitelist, get_email_whitelist


class TestEmailWhitelist:
    """Test EmailWhitelist functionality"""

    def test_initialization_with_defaults(self):
        """Test whitelist initialization with defaults"""
        whitelist = EmailWhitelist()
        assert whitelist.env in ("local", "development", "test")

    def test_initialization_with_explicit_values(self):
        """Test whitelist initialization with explicit values"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=["test1@example.com", "test2@example.com"],
        )
        assert whitelist.env == "test"
        assert whitelist.is_allowed("test1@example.com")
        assert whitelist.is_allowed("test2@example.com")

    def test_exact_match(self):
        """Test exact email matching"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=["allowed@example.com"],
        )
        assert whitelist.is_allowed("allowed@example.com")
        assert not whitelist.is_allowed("notallowed@example.com")

    def test_wildcard_domain(self):
        """Test wildcard domain matching"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=["*@example.com"],
        )
        assert whitelist.is_allowed("anyone@example.com")
        assert whitelist.is_allowed("test@example.com")
        assert not whitelist.is_allowed("test@other.com")

    def test_case_insensitive(self):
        """Test case-insensitive matching"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=["test@example.com"],  # Store lowercase
        )
        assert whitelist.is_allowed("test@example.com")
        assert whitelist.is_allowed("TEST@EXAMPLE.COM")

    def test_filter_recipients(self):
        """Test filtering recipient lists"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=["allowed@example.com", "*@test.com"],
        )

        recipients = [
            "allowed@example.com",
            "blocked@example.com",
            "test@test.com",
            "another@test.com",
        ]

        allowed, blocked = whitelist.filter_recipients(recipients)

        assert len(allowed) == 3
        assert "allowed@example.com" in allowed
        assert "test@test.com" in allowed
        assert "another@test.com" in allowed

        assert len(blocked) == 1
        assert "blocked@example.com" in blocked

    def test_get_safe_recipient_allowed(self):
        """Test get_safe_recipient with allowed email"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=["allowed@example.com"],
        )
        assert (
            whitelist.get_safe_recipient("allowed@example.com") == "allowed@example.com"
        )

    def test_get_safe_recipient_with_fallback(self):
        """Test get_safe_recipient with fallback"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=["allowed@example.com"],
        )
        result = whitelist.get_safe_recipient(
            "blocked@example.com", fallback="allowed@example.com"
        )
        assert result == "allowed@example.com"

    def test_get_safe_recipient_uses_first_whitelisted(self):
        """Test get_safe_recipient uses first whitelisted email"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=["first@example.com", "second@example.com"],
        )
        result = whitelist.get_safe_recipient("blocked@example.com")
        assert result in ["first@example.com", "second@example.com"]

    def test_get_safe_recipient_no_whitelist(self):
        """Test get_safe_recipient with no whitelist returns original"""
        whitelist = EmailWhitelist(
            env="test",
            whitelist_emails=[],
        )
        result = whitelist.get_safe_recipient("blocked@example.com")
        assert result == "blocked@example.com"


class TestEmailWhitelistSingleton:
    """Test EmailWhitelist singleton"""

    def test_get_email_whitelist_returns_instance(self):
        """Test that get_email_whitelist returns EmailWhitelist instance"""
        whitelist = get_email_whitelist()
        assert isinstance(whitelist, EmailWhitelist)

    def test_get_email_whitelist_returns_same_instance(self):
        """Test that get_email_whitelist returns same instance"""
        whitelist1 = get_email_whitelist()
        whitelist2 = get_email_whitelist()
        assert whitelist1 is whitelist2
