"""
Login Service Module

Handles user authentication functionality including:
- Login verification and session creation
- Account lockout protection
- Login attempt tracking
- Logout and session cleanup
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import src.database.database_service as db
from data.session import SessionService
from src.utils.time_utils import get_current_time

from .password_service import AccountLockedError, PasswordService

logger = logging.getLogger(__name__)

# Constants
INVALID_CREDENTIALS_MSG = "Invalid email or password"


class LoginError(Exception):
    """Raised when login operations fail"""


class LoginService:
    """Service for managing user authentication"""

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    @staticmethod
    def _validate_account_status(user: Dict[str, Any]) -> None:
        """
        Validate user account status and raise appropriate error if not active.

        Args:
            user: User dictionary containing account_status field

        Raises:
            LoginError: If account is not active with appropriate message
        """
        account_status = user.get("account_status")
        if account_status == "active":
            return  # Account is valid

        # Map status to error message
        status_messages = {
            "pending": "Account is pending activation. Please check your email for verification instructions.",
            "suspended": "Account has been suspended. Please contact support.",
            "deactivated": "Account has been deactivated. Please contact support.",
        }

        error_msg = status_messages.get(
            account_status, "Account is not available for login"
        )
        raise LoginError(error_msg)

    @staticmethod
    def authenticate_user(
        email: str, password: str, remember_me: bool = False
    ) -> Dict[str, Any]:
        """
        Authenticate a user and create session

        Args:
            email: User email address
            password: User password
            remember_me: Whether to create extended session

        Returns:
            Dictionary containing user details and session info

        Raises:
            LoginError: If authentication fails
            AccountLockedError: If account is locked
        """
        try:
            # Normalize email
            email = email.lower().strip()

            # Check for account lockout first
            PasswordService.check_account_lockout(email)

            # Get user by email
            user = db.get_user_by_email(email)
            if not user:
                # Track failed attempt even for non-existent users
                PasswordService.track_failed_login(email)
                raise LoginError(INVALID_CREDENTIALS_MSG)

            # Check account status
            LoginService._validate_account_status(user)

            # Check email verification
            if not user.get("email_verified", False):
                raise LoginError(
                    "Please verify your email address before logging in. "
                    "Check your inbox for the verification link."
                )

            # Verify password
            password_hash = user.get("password_hash")
            if not password_hash:
                raise LoginError("Account is not configured for password login")

            if not PasswordService.verify_password(password, password_hash):
                # Track failed login attempt
                PasswordService.track_failed_login(email)
                raise LoginError(INVALID_CREDENTIALS_MSG)

            # Clear failed attempts on successful login
            PasswordService.clear_failed_attempts(email)

            # Update last login timestamp
            db.update_user(
                user["user_id"],
                {
                    "last_login_at": get_current_time(),
                    "login_count": user.get("login_count", 0) + 1,
                },
            )

            # Fetch institution name if user has an institution
            institution_name = None
            institution_short_name = None
            if user.get("institution_id"):
                institution = db.get_institution_by_id(user["institution_id"])
                if institution:
                    institution_name = institution.get("name")
                    institution_short_name = institution.get("short_name")

            # Create user session with natural keys for stability across reseeds
            SessionService.create_user_session(
                {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "role": user["role"],
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "institution_id": user.get("institution_id"),
                    "institution_short_name": institution_short_name,  # Natural key
                    "institution_name": institution_name,
                    "program_ids": user.get("program_ids", []),
                    "display_name": user.get(
                        "display_name", user["email"].split("@")[0]
                    ),
                    "system_date_override": user.get("system_date_override"),
                },
                remember_me,
            )

            logger.info("[Login Service] Successful login for user: %s", email)

            return {
                "user_id": user["user_id"],
                "email": user["email"],
                "role": user["role"],
                "institution_id": user.get("institution_id"),
                "display_name": user.get("display_name"),
                "login_success": True,
                "message": "Login successful",
            }

        except AccountLockedError:
            # Re-raise account locked errors
            raise
        except Exception as e:
            logger.error("[Login Service] Login failed for %s: %s", email, str(e))
            if INVALID_CREDENTIALS_MSG in str(e) or "Account" in str(e):
                raise LoginError(str(e)) from e
            else:
                raise LoginError("Login failed. Please try again.") from e

    @staticmethod
    def logout_user() -> Dict[str, Any]:
        """
        Logout current user and cleanup session

        Returns:
            Dictionary containing logout status
        """
        try:
            # Get current session info for logging
            session_info = SessionService.get_session_info()
            user_email = session_info.get("email", "unknown")

            # Destroy session
            SessionService.destroy_session()

            logger.info("[Login Service] User logged out: %s", user_email)

            return {"logout_success": True, "message": "Logout successful"}

        except Exception as e:
            logger.error("[Login Service] Logout error: %s", str(e))
            # Even if there's an error, try to destroy the session
            try:
                SessionService.destroy_session()
            except Exception as logout_err:  # nosec B110
                logger.debug(
                    "[Login Service] Secondary session destroy also failed: %s",
                    logout_err,
                )

            return {"logout_success": True, "message": "Logout completed"}

    @staticmethod
    def get_login_status() -> Dict[str, Any]:
        """
        Get current login status

        Returns:
            Dictionary containing login status and user info
        """
        try:
            # Check if user is logged in
            if not SessionService.is_user_logged_in():
                return {"logged_in": False, "message": "Not logged in"}

            # Validate session
            if not SessionService.validate_session():
                return {"logged_in": False, "message": "Session expired or invalid"}

            # Get session info
            session_info = SessionService.get_session_info()

            return {
                "logged_in": True,
                "user_id": session_info.get("user_id"),
                "email": session_info.get("email"),
                "role": session_info.get("role"),
                "institution_id": session_info.get("institution_id"),
                "display_name": session_info.get("display_name"),
                "last_activity": session_info.get("last_activity"),
                "message": "User is logged in",
            }

        except Exception as e:
            logger.error("[Login Service] Error getting login status: %s", str(e))
            return {"logged_in": False, "message": "Unable to determine login status"}

    @staticmethod
    def refresh_session() -> Dict[str, Any]:
        """
        Refresh current user session

        Returns:
            Dictionary containing refresh status
        """
        try:
            if not SessionService.is_user_logged_in():
                raise LoginError("No active session to refresh")

            # Refresh session activity timestamp
            SessionService.refresh_session()

            return {
                "refresh_success": True,
                "message": "Session refreshed successfully",
            }

        except Exception as e:
            logger.error("[Login Service] Session refresh failed: %s", str(e))
            raise LoginError(f"Failed to refresh session: {str(e)}") from e

    @staticmethod
    def check_account_lockout_status(email: str) -> Dict[str, Any]:
        """
        Check account lockout status for an email

        Args:
            email: Email address to check

        Returns:
            Dictionary containing lockout status
        """
        try:
            email = email.lower().strip()

            is_locked, unlock_time = PasswordService.is_account_locked(email)

            if is_locked:
                return {
                    "is_locked": True,
                    "unlock_time": unlock_time.isoformat() if unlock_time else None,
                    "message": f'Account is locked until {unlock_time.strftime("%Y-%m-%d %H:%M:%S UTC") if unlock_time else "unknown"}',
                }
            else:
                return {"is_locked": False, "message": "Account is not locked"}

        except Exception as e:
            logger.error(
                "[Login Service] Error checking lockout status for %s: %s",
                email,
                str(e),
            )
            return {"is_locked": False, "message": "Unable to determine lockout status"}

    @staticmethod
    def send_account_locked_notification(email: str) -> bool:
        """
        Send notification email when account is locked

        Args:
            email: Email address to notify

        Returns:
            True if notification sent successfully
        """
        try:
            # Get user details
            user = db.get_user_by_email(email)
            if not user:
                return False

            # Get institution details (for future use)
            if user.get("institution_id"):
                db.get_institution_by_id(user["institution_id"])

            # Send notification email (if email service supports it)
            # For now, just log the event
            logger.warning(
                "[Login Service] Account locked notification should be sent to: %s",
                email,
            )

            return True

        except Exception as e:
            logger.error(
                "[Login Service] Failed to send account locked notification to %s: %s",
                email,
                str(e),
            )
            return False

    @staticmethod
    def unlock_account(email: str, admin_user_id: str) -> Dict[str, Any]:
        """
        Manually unlock a locked account (admin function)

        Args:
            email: Email address to unlock
            admin_user_id: ID of admin performing the unlock

        Returns:
            Dictionary containing unlock status
        """
        try:
            email = email.lower().strip()

            # Clear failed attempts (this effectively unlocks the account)
            PasswordService.clear_failed_attempts(email)

            logger.info(
                "[Login Service] Account unlocked for %s by admin %s",
                email,
                admin_user_id,
            )

            return {
                "unlock_success": True,
                "message": f"Account {email} has been unlocked",
            }

        except Exception as e:
            logger.error(
                "[Login Service] Failed to unlock account %s: %s", email, str(e)
            )
            raise LoginError(f"Failed to unlock account: {str(e)}") from e


# Convenience functions for use in other modules
def login_user(email: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
    """Convenience function for user login"""
    return LoginService.authenticate_user(email, password, remember_me)


def logout_user() -> Dict[str, Any]:
    """Convenience function for user logout"""
    return LoginService.logout_user()


def is_user_logged_in() -> bool:
    """Convenience function to check if user is logged in"""
    status = LoginService.get_login_status()
    return status.get("logged_in", False)


def get_current_user_info() -> Optional[Dict[str, Any]]:
    """Convenience function to get current user info"""
    status = LoginService.get_login_status()
    if status.get("logged_in"):
        return {
            "user_id": status.get("user_id"),
            "email": status.get("email"),
            "role": status.get("role"),
            "institution_id": status.get("institution_id"),
            "display_name": status.get("display_name"),
        }
    return None
