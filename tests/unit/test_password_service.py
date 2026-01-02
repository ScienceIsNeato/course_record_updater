"""
Unit tests for Password Management Service

Tests password hashing, validation, reset tokens, and security policies.
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.services.password_service import (
    AccountLockedError,
    PasswordService,
    PasswordValidationError,
    RateLimitError,
    generate_reset_token,
    hash_password,
    validate_password_strength,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing and verification functionality"""

    def test_hash_password_success(self):
        """Test successful password hashing"""
        password = "TestPass123!"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plain text
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_hash_password_with_weak_password_fails(self):
        """Test that weak passwords are rejected during hashing"""
        with pytest.raises(PasswordValidationError):
            hash_password("weak")

    @patch("src.services.password_service.bcrypt.hashpw")
    def test_hash_password_bcrypt_exception(self, mock_hashpw):
        """Test hash_password exception handling when bcrypt fails"""
        # Setup mock to raise exception
        mock_hashpw.side_effect = Exception("bcrypt failed")

        # Execute & Verify
        with pytest.raises(Exception, match="bcrypt failed"):
            hash_password("ValidPassword123!")

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPass123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPass123!"
        wrong_password = "WrongPass123!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_with_invalid_hash(self):
        """Test password verification with invalid hash"""
        password = "TestPass123!"
        invalid_hash = "invalid_hash"

        assert verify_password(password, invalid_hash) is False

    def test_hash_consistency(self):
        """Test that same password produces different hashes (due to salt)"""
        password = "TestPass123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts should produce different hashes
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestPasswordValidation:
    """Test password strength validation"""

    def test_valid_password(self):
        """Test that valid password passes validation"""
        # Should not raise exception
        validate_password_strength("TestPass123!")

    def test_empty_password(self):
        """Test that empty password fails validation"""
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            validate_password_strength("")

    def test_too_short_password(self):
        """Test that short password fails validation"""
        with pytest.raises(PasswordValidationError, match="at least 8 characters"):
            validate_password_strength("Test1!")

    def test_too_long_password(self):
        """Test that very long password fails validation"""
        long_password = "A" * 129 + "1!"
        with pytest.raises(
            PasswordValidationError, match="no more than 128 characters"
        ):
            validate_password_strength(long_password)

    def test_no_lowercase(self):
        """Test that password without lowercase fails validation"""
        with pytest.raises(PasswordValidationError, match="lowercase letter"):
            validate_password_strength("TESTPASS123!")

    def test_no_uppercase(self):
        """Test that password without uppercase fails validation"""
        with pytest.raises(PasswordValidationError, match="uppercase letter"):
            validate_password_strength("testpass123!")

    def test_no_digit(self):
        """Test that password without digit fails validation"""
        with pytest.raises(PasswordValidationError, match="digit"):
            validate_password_strength("TestPassword!")

    def test_no_special_character(self):
        """Test that password without special character fails validation"""
        with pytest.raises(PasswordValidationError, match="special character"):
            validate_password_strength("TestPassword123")

    def test_various_special_characters(self):
        """Test that various special characters are accepted"""
        special_chars = '!@#$%^&*(),.?":{}|<>'
        for char in special_chars:
            password = f"TestPass123{char}"
            # Should not raise exception
            validate_password_strength(password)


class TestResetTokens:
    """Test password reset token functionality"""

    def test_generate_reset_token(self):
        """Test reset token generation"""
        token = generate_reset_token()

        assert isinstance(token, str)
        assert len(token) > 0

        # Generate another token to ensure they're different
        token2 = generate_reset_token()
        assert token != token2

    def test_create_reset_token_data(self):
        """Test reset token data creation"""
        user_id = "user123"
        email = "test@example.com"

        token_data = PasswordService.create_reset_token_data(user_id, email)

        assert token_data["user_id"] == user_id
        assert token_data["email"] == email
        assert token_data["used"] is False
        assert "token" in token_data
        assert "expires_at" in token_data
        assert "created_at" in token_data

        # Check expiry is in the future
        assert token_data["expires_at"] > datetime.now(timezone.utc)

    def test_reset_token_validation_valid(self):
        """Test validation of valid reset token"""
        token_data = {
            "token": "valid_token",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False,
        }

        assert PasswordService.is_reset_token_valid(token_data) is True

    def test_reset_token_validation_expired(self):
        """Test validation of expired reset token"""
        token_data = {
            "token": "expired_token",
            "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
            "used": False,
        }

        assert PasswordService.is_reset_token_valid(token_data) is False

    def test_reset_token_validation_used(self):
        """Test validation of already used reset token"""
        token_data = {
            "token": "used_token",
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": True,
        }

        assert PasswordService.is_reset_token_valid(token_data) is False

    def test_reset_token_validation_no_data(self):
        """Test validation with no token data"""
        assert PasswordService.is_reset_token_valid(None) is False
        assert PasswordService.is_reset_token_valid({}) is False

    def test_reset_token_validation_iso_string_expiry(self):
        """Test validation with ISO string expiry date"""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "token": "iso_token",
            "expires_at": future_time.isoformat(),
            "used": False,
        }

        assert PasswordService.is_reset_token_valid(token_data) is True

    def test_reset_token_validation_invalid_iso_string(self):
        """Test validation with invalid ISO string expiry date format"""
        token_data = {
            "token": "invalid_token",
            "expires_at": "invalid-date-format",  # Invalid ISO format
            "used": False,
        }

        assert PasswordService.is_reset_token_valid(token_data) is False


class TestAccountLockout:
    """Test account lockout functionality"""

    def setup_method(self):
        """Clear failed attempts before each test"""
        PasswordService._failed_attempts.clear()

    def test_track_failed_login(self):
        """Test tracking failed login attempts"""
        email = "test@example.com"

        PasswordService.track_failed_login(email)

        assert email in PasswordService._failed_attempts
        assert PasswordService._failed_attempts[email]["count"] == 1

    def test_multiple_failed_logins(self):
        """Test multiple failed login attempts"""
        email = "test@example.com"

        for i in range(3):
            PasswordService.track_failed_login(email)

        assert PasswordService._failed_attempts[email]["count"] == 3

    def test_account_lockout_after_max_attempts(self):
        """Test account gets locked after max failed attempts"""
        email = "test@example.com"

        # Track max failed attempts
        for i in range(5):
            PasswordService.track_failed_login(email)

        is_locked, locked_until = PasswordService.is_account_locked(email)
        assert is_locked is True
        assert locked_until is not None
        assert locked_until > datetime.now(timezone.utc)

    def test_account_not_locked_before_max_attempts(self):
        """Test account is not locked before max attempts"""
        email = "test@example.com"

        # Track some failed attempts but not max
        for i in range(3):
            PasswordService.track_failed_login(email)

        is_locked, locked_until = PasswordService.is_account_locked(email)
        assert is_locked is False
        assert locked_until is None

    def test_clear_failed_attempts(self):
        """Test clearing failed login attempts"""
        email = "test@example.com"

        PasswordService.track_failed_login(email)
        assert email in PasswordService._failed_attempts

        PasswordService.clear_failed_attempts(email)
        assert email not in PasswordService._failed_attempts

    def test_check_account_lockout_raises_exception(self):
        """Test that locked account raises exception"""
        email = "test@example.com"

        # Lock the account
        for i in range(5):
            PasswordService.track_failed_login(email)

        with pytest.raises(AccountLockedError, match="Account is locked"):
            PasswordService.check_account_lockout(email)

    def test_check_account_lockout_no_exception_when_not_locked(self):
        """Test that unlocked account doesn't raise exception"""
        email = "test@example.com"

        # Should not raise exception
        PasswordService.check_account_lockout(email)

    def test_lockout_expiry(self):
        """Test that lockout expires after timeout"""
        email = "test@example.com"

        # Mock time to simulate lockout expiry
        with patch("src.services.password_service.datetime") as mock_datetime:
            # Set initial time
            initial_time = datetime.now(timezone.utc)
            mock_datetime.now.return_value = initial_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Lock the account
            for i in range(5):
                PasswordService.track_failed_login(email)

            # Verify account is locked
            is_locked, _ = PasswordService.is_account_locked(email)
            assert is_locked is True

            # Fast forward time past lockout duration
            future_time = initial_time + timedelta(minutes=35)
            mock_datetime.now.return_value = future_time

            # Check lockout status again
            is_locked, _ = PasswordService.is_account_locked(email)
            assert is_locked is False


class TestRateLimiting:
    """Test password reset rate limiting"""

    def setup_method(self):
        """Clear rate limit data before each test"""
        PasswordService._reset_requests.clear()

    def test_rate_limit_within_limit(self):
        """Test that requests within limit are allowed"""
        email = "test@example.com"

        # Should not raise exception
        PasswordService.check_rate_limit(email)
        PasswordService.check_rate_limit(email)

    def test_rate_limit_exceeded(self):
        """Test that rate limit is enforced"""
        email = "test@example.com"

        # Make maximum allowed requests
        for i in range(3):
            PasswordService.check_rate_limit(email)

        # Next request should be rate limited
        with pytest.raises(RateLimitError, match="Too many password reset requests"):
            PasswordService.check_rate_limit(email)

    def test_rate_limit_window_cleanup(self):
        """Test that old requests are cleaned up"""
        email = "test@example.com"

        # Mock time to simulate window expiry
        with patch("src.services.password_service.time") as mock_time:
            # Set initial time
            initial_time = 1000.0
            mock_time.time.return_value = initial_time

            # Make maximum requests
            for i in range(3):
                PasswordService.check_rate_limit(email)

            # Fast forward past rate limit window
            future_time = initial_time + (61 * 60)  # 61 minutes
            mock_time.time.return_value = future_time

            # Should be able to make requests again
            PasswordService.check_rate_limit(email)


class TestPasswordServiceIntegration:
    """Integration tests for password service"""

    def test_complete_password_lifecycle(self):
        """Test complete password creation and verification cycle"""
        password = "SecurePass123!"

        # Hash password
        hashed = hash_password(password)

        # Verify correct password
        assert verify_password(password, hashed) is True

        # Verify incorrect password
        assert verify_password("WrongPass123!", hashed) is False

    def test_reset_token_lifecycle(self):
        """Test complete reset token creation and validation cycle"""
        user_id = "user123"
        email = "test@example.com"

        # Create token data
        token_data = PasswordService.create_reset_token_data(user_id, email)

        # Validate token
        assert PasswordService.is_reset_token_valid(token_data) is True

        # Mark as used
        token_data["used"] = True

        # Should no longer be valid
        assert PasswordService.is_reset_token_valid(token_data) is False

    def test_failed_login_and_lockout_cycle(self):
        """Test complete failed login tracking and lockout cycle"""
        email = "test@example.com"

        # Clear any existing data
        PasswordService._failed_attempts.clear()

        # Track failed attempts
        for i in range(4):
            PasswordService.track_failed_login(email)
            # Should not be locked yet
            is_locked, _ = PasswordService.is_account_locked(email)
            assert is_locked is False

        # Fifth attempt should trigger lockout
        PasswordService.track_failed_login(email)
        is_locked, locked_until = PasswordService.is_account_locked(email)
        assert is_locked is True
        assert locked_until is not None

        # Clear attempts (simulating successful login after lockout expires)
        PasswordService.clear_failed_attempts(email)
        is_locked, _ = PasswordService.is_account_locked(email)
        assert is_locked is False
