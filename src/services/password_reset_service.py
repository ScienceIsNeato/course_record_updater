"""
Password Reset Service Module

Handles password reset functionality including:
- Password reset request processing
- Secure token generation and validation
- Password reset completion
- Email notifications for reset events
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import src.database.database_service as db

from .email_service import EmailService, EmailServiceError
from .password_service import PasswordService, PasswordValidationError

logger = logging.getLogger(__name__)


class PasswordResetError(Exception):
    """Raised when password reset operations fail"""


class PasswordResetService:
    """Service for managing password reset functionality"""

    RESET_TOKEN_EXPIRY_HOURS = 2  # Password reset tokens expire in 2 hours
    MAX_RESET_REQUESTS_PER_HOUR = 3  # Maximum reset requests per email per hour

    @staticmethod
    def _validate_account_status(user: Dict[str, Any]) -> None:
        """Validate user account status for password reset"""
        if user.get("account_status") != "active":
            if user.get("account_status") == "pending":
                raise PasswordResetError(
                    "Account is pending activation. Please verify your email first."
                )
            elif user.get("account_status") == "suspended":
                raise PasswordResetError(
                    "Account is suspended. Please contact support."
                )
            elif user.get("account_status") == "deactivated":
                raise PasswordResetError(
                    "Account is deactivated. Please contact support."
                )
            else:
                raise PasswordResetError("Account is not available for password reset.")

    @staticmethod
    def request_password_reset(email: str) -> Dict[str, Any]:
        """
        Process password reset request and send reset email

        Args:
            email: User email address

        Returns:
            Dictionary containing request status

        Raises:
            PasswordResetError: If reset request fails
        """
        try:
            # Normalize email
            email = email.lower().strip()

            # Check rate limiting
            PasswordResetService._check_reset_rate_limit(email)

            # Get user by email
            user = db.get_user_by_email(email)
            if not user:
                # For security, don't reveal if email exists or not
                # Still log the attempt but return success
                logger.warning(  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
                    "Password reset requested for non-existent email: %s", email
                )
                return {
                    "request_success": True,
                    "message": "If an account with this email exists, you will receive a password reset link.",
                }

            # Check if account is active
            PasswordResetService._validate_account_status(user)

            # Generate reset token
            reset_token = PasswordService.generate_reset_token()
            token_data = PasswordService.create_reset_token_data(
                user["user_id"], user["email"]
            )

            # Update user with reset token
            reset_data = {
                "password_reset_token": reset_token,
                "password_reset_token_data": token_data,
                "password_reset_requested_at": datetime.now(timezone.utc),
            }

            success = db.update_user(user["user_id"], reset_data)
            if not success:
                raise PasswordResetError(
                    "Failed to generate reset token. Please try again."
                )

            # Send reset email
            email_sent = EmailService.send_password_reset_email(
                email=user["email"],
                reset_token=reset_token,
                user_name=user.get("display_name", user["email"].split("@")[0]),
            )

            if not email_sent:
                # nosemgrep
                logger.error("Failed to send password reset email to: %s", email)
                # Don't fail the request - user might still use the token if they have it

            logger.info("Password reset requested for user: %s", email)  # nosemgrep

            return {
                "request_success": True,
                "message": "If an account with this email exists, you will receive a password reset link.",
            }

        except EmailServiceError as e:
            # Handle email service errors specifically
            logger.error(  # nosemgrep
                "Email service error during password reset for %s: %s", email, str(e)
            )
            if "protected domain" in str(e).lower():
                # In non-production, inform user about email protection
                raise PasswordResetError(
                    "Email sending is restricted in development environment."
                )
            else:
                raise PasswordResetError(
                    "Failed to send reset email. Please try again."
                )
        except Exception as e:
            # nosemgrep
            logger.error("Password reset request failed for %s: %s", email, str(e))
            if isinstance(e, PasswordResetError):
                raise
            else:
                raise PasswordResetError(
                    "Password reset request failed. Please try again."
                ) from e

    @staticmethod
    def reset_password(reset_token: str, new_password: str) -> Dict[str, Any]:
        """
        Complete password reset with new password

        Args:
            reset_token: Password reset token
            new_password: New password

        Returns:
            Dictionary containing reset status

        Raises:
            PasswordResetError: If password reset fails
        """
        try:
            # Validate new password strength
            PasswordService.validate_password_strength(new_password)

            # Find user by reset token
            user = PasswordResetService._get_user_by_reset_token(reset_token)
            if not user:
                raise PasswordResetError("Invalid or expired reset token.")

            # Validate token data
            token_data = user.get("password_reset_token_data")
            if not token_data or not PasswordService.is_reset_token_valid(token_data):
                raise PasswordResetError(
                    "Reset token has expired or been used. Please request a new one."
                )

            # Hash new password
            password_hash = PasswordService.hash_password(new_password)

            # Update user with new password and clear reset token
            update_data = {
                "password_hash": password_hash,
                "password_reset_token": None,
                "password_reset_token_data": None,
                "password_reset_completed_at": datetime.now(timezone.utc),
                "password_changed_at": datetime.now(timezone.utc),
            }

            success = db.update_user(user["user_id"], update_data)
            if not success:
                raise PasswordResetError("Failed to update password. Please try again.")

            # Clear any failed login attempts
            PasswordService.clear_failed_attempts(user["email"])

            # Send confirmation email
            try:
                EmailService.send_password_reset_confirmation_email(
                    email=user["email"],
                    user_name=user.get("display_name", user["email"].split("@")[0]),
                )
            except Exception as e:
                # Don't fail password reset if confirmation email fails
                logger.warning(  # nosemgrep
                    "Failed to send password reset confirmation email to %s: %s",
                    user["email"],
                    str(e),
                )

            # nosemgrep
            logger.info("Password reset completed for user: %s", user["email"])

            return {
                "reset_success": True,
                "user_id": user["user_id"],
                "email": user["email"],
                "message": "Password has been reset successfully. You can now log in with your new password.",
            }

        except PasswordValidationError as e:
            raise PasswordResetError(f"Password validation failed: {str(e)}") from e
        except Exception as e:
            logger.error(  # nosemgrep
                "Password reset failed for token %s: %s",
                reset_token[:8] + "...",
                str(e),
            )
            if isinstance(e, PasswordResetError):
                raise
            else:
                raise PasswordResetError(
                    "Password reset failed. Please try again."
                ) from e

    @staticmethod
    def validate_reset_token(reset_token: str) -> Dict[str, Any]:
        """
        Validate a password reset token without using it

        Args:
            reset_token: Password reset token to validate

        Returns:
            Dictionary containing validation status and user info
        """
        try:
            # Find user by reset token
            user = PasswordResetService._get_user_by_reset_token(reset_token)
            if not user:
                return {"valid": False, "message": "Invalid or expired reset token."}

            # Validate token data
            token_data = user.get("password_reset_token_data")
            if not token_data or not PasswordService.is_reset_token_valid(token_data):
                return {
                    "valid": False,
                    "message": "Reset token has expired or been used.",
                }

            return {
                "valid": True,
                "user_id": user["user_id"],
                "email": user["email"],
                "display_name": user.get("display_name"),
                "message": "Reset token is valid.",
            }

        except Exception as e:
            logger.error("Error validating reset token: %s", str(e))  # nosemgrep
            return {"valid": False, "message": "Unable to validate reset token."}

    @staticmethod
    def get_reset_status(email: str) -> Dict[str, Any]:
        """
        Get password reset status for an email

        Args:
            email: Email address to check

        Returns:
            Dictionary containing reset status
        """
        try:
            email = email.lower().strip()

            user = db.get_user_by_email(email)
            if not user:
                return {
                    "has_pending_reset": False,
                    "message": "No user found with this email.",
                }

            # Check if there's a pending reset token
            reset_token = user.get("password_reset_token")
            token_data = user.get("password_reset_token_data")

            if not reset_token or not token_data:
                return {
                    "has_pending_reset": False,
                    "message": "No pending password reset.",
                }

            # Check if token is still valid
            if not PasswordService.is_reset_token_valid(token_data):
                return {
                    "has_pending_reset": False,
                    "message": "Previous reset token has expired.",
                }

            # Calculate expiry time
            expires_at = token_data.get("expires_at")

            return {
                "has_pending_reset": True,
                "expires_at": expires_at,
                "message": "Password reset is pending. Check your email for the reset link.",
            }

        except Exception as e:
            logger.error("Error checking reset status for %s: %s", email, str(e))
            return {
                "has_pending_reset": False,
                "message": "Unable to check reset status.",
            }

    @staticmethod
    def _get_user_by_reset_token(reset_token: str) -> Optional[Dict[str, Any]]:
        """
        Find user by password reset token

        Args:
            reset_token: Reset token to search for

        Returns:
            User data if found, None otherwise
        """
        try:
            # This is a simplified implementation
            # In production, you might want a more efficient query
            # For now, we'll need to add a method to database_service
            return db.get_user_by_reset_token(reset_token)
        except Exception as e:
            logger.error("Error finding user by reset token: %s", str(e))  # nosemgrep
            return None

    @staticmethod
    def _check_reset_rate_limit(email: str) -> None:
        """
        Check if user has exceeded password reset rate limit

        Args:
            email: Email address to check

        Raises:
            PasswordResetError: If rate limit exceeded
        """
        try:
            # Use the existing rate limiting from PasswordService
            # This checks for password reset requests
            PasswordService.check_rate_limit(email)
        except Exception as e:
            if "rate limit" in str(e).lower():
                raise PasswordResetError(
                    "Too many password reset requests. Please wait before trying again."
                ) from e
            else:
                # Don't fail on other errors, just log them
                logger.warning("Error checking rate limit for %s: %s", email, str(e))


# Convenience functions for use in other modules
def request_password_reset(email: str) -> Dict[str, Any]:
    """Convenience function for password reset request"""
    return PasswordResetService.request_password_reset(email)


def reset_password(reset_token: str, new_password: str) -> Dict[str, Any]:
    """Convenience function for password reset completion"""
    return PasswordResetService.reset_password(reset_token, new_password)


def validate_reset_token(reset_token: str) -> Dict[str, Any]:
    """Convenience function for reset token validation"""
    return PasswordResetService.validate_reset_token(reset_token)


def get_reset_status(email: str) -> Dict[str, Any]:
    """Convenience function for reset status check"""
    return PasswordResetService.get_reset_status(email)
