"""
Registration Service

Handles user registration flows including:
- Institution admin self-registration with email verification
- User invitation acceptance with pre-populated data
- Account activation and welcome processes

Features:
- Secure token-based email verification
- Automatic institution and default program creation
- Integration with password and session services
- Comprehensive validation and error handling
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

# Import other services
import src.database.database_service as db
from .email_service import send_verification_email, send_welcome_email
from src.utils.logging_config import get_logger
from src.models.models import Institution, Program, User, UserInvitation
from .password_service import PasswordService, PasswordValidationError

# Get standardized logger
logger = get_logger(__name__)

# Registration configuration
VERIFICATION_TOKEN_EXPIRY_HOURS = 24
INVITATION_TOKEN_EXPIRY_DAYS = 7
DEFAULT_PROGRAM_NAME = "Unclassified"


class RegistrationError(Exception):
    """Raised when registration process encounters an error"""

    pass


class RegistrationService:
    """
    Comprehensive registration service for admin self-registration and invitations

    Handles the complete registration flow from form submission to account activation
    """

    @staticmethod
    def register_institution_admin(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        institution_name: str,
        website_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a new institution administrator with email verification

        Args:
            email: Admin's email address (becomes username)
            password: Plain text password (will be hashed)
            first_name: Admin's first name
            last_name: Admin's last name
            institution_name: Name of the institution
            website_url: Optional institution website

        Returns:
            Dictionary with registration result and verification info

        Raises:
            RegistrationError: If registration fails
            PasswordValidationError: If password doesn't meet requirements
        """
        logger.info(
            f"[Registration] Starting institution admin registration for {logger.sanitize(email)}"
        )

        try:
            # Validate password strength
            PasswordService.validate_password_strength(password)

            # Check if user already exists
            existing_user = db.get_user_by_email(email)
            if existing_user:
                raise RegistrationError(f"An account with email {email} already exists")

            # Generate verification token
            verification_token = secrets.token_urlsafe(32)
            verification_expires_at = datetime.now(timezone.utc) + timedelta(
                hours=VERIFICATION_TOKEN_EXPIRY_HOURS
            )

            # Hash password
            password_hash = PasswordService.hash_password(password)

            # Create institution
            institution_id = Institution.generate_id()
            institution_data = Institution.create_schema(
                name=institution_name,
                short_name=institution_name[:20],  # Use first 20 chars as short name
                created_by="system",  # Will be updated after user creation
                admin_email=email,
                website_url=website_url,
                allow_self_registration=True,
                require_email_verification=True,
            )
            institution_data["id"] = institution_id

            # Create default "Unclassified" program
            program_id = Program.generate_id()
            program_data = Program.create_schema(
                name=DEFAULT_PROGRAM_NAME,
                short_name="UNCLASS",
                institution_id=institution_id,
                created_by="system",  # Will be updated after user creation
                description="Default program for courses not assigned to specific programs",
                is_default=True,
                program_admins=[],  # Will add admin after user creation
            )
            program_data["id"] = program_id

            # Create user (pending verification)
            user_id = User.generate_id()
            user_data = User.create_schema(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role="institution_admin",
                institution_id=institution_id,
                password_hash=password_hash,
                account_status="pending",
                program_ids=[program_id],
            )
            user_data["id"] = user_id

            # Add email verification fields
            user_data["email_verification_token"] = verification_token
            user_data["email_verification_expires_at"] = verification_expires_at
            user_data["email_verified"] = False

            # Update institution with admin user ID
            institution_data["created_by_user_id"] = user_id
            institution_data["admin_user_ids"] = [user_id]

            # Update program with admin user ID
            program_data["program_admins"] = [user_id]

            # Save to database in transaction-like manner
            db.create_institution(institution_data)
            db.create_program(program_data)
            db.create_user(user_data)

            logger.info(
                f"[Registration] Created user {user_id}, institution {institution_id}, program {program_id}"
            )

            # Send verification email
            display_name = f"{first_name} {last_name}".strip()
            email_sent = send_verification_email(
                email=email,
                verification_token=verification_token,
                user_name=display_name,
            )

            if not email_sent:
                logger.warning(
                    f"[Registration] Failed to send verification email to {logger.sanitize(email)}"
                )

            return {
                "success": True,
                "user_id": user_id,
                "institution_id": institution_id,
                "program_id": program_id,
                "verification_token": verification_token,
                "verification_expires_at": verification_expires_at,
                "email_sent": email_sent,
                "message": "Registration successful! Please check your email to verify your account.",
            }

        except PasswordValidationError:
            # Re-raise password validation errors
            raise
        except Exception as e:
            logger.error(f"[Registration] Failed to register institution admin: {e}")
            raise RegistrationError(f"Registration failed: {str(e)}")

    @staticmethod
    def verify_email(verification_token: str) -> Dict[str, Any]:
        """
        Verify user's email address and activate account

        Args:
            verification_token: Email verification token

        Returns:
            Dictionary with verification result

        Raises:
            RegistrationError: If verification fails
        """
        logger.info(
            f"[Registration] Processing email verification for token: {logger.sanitize(verification_token[:8])}..."
        )

        try:
            # Find user by verification token
            user = db.get_user_by_verification_token(verification_token)
            if not user:
                raise RegistrationError("Invalid verification token")

            # Check if token is expired
            expires_at = user.get("email_verification_expires_at")
            if not expires_at:
                raise RegistrationError("Verification token has no expiry date")

            # Handle both datetime objects and ISO strings
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    raise RegistrationError("Invalid verification token expiry format")

            if expires_at < datetime.now(timezone.utc):
                raise RegistrationError("Verification token has expired")

            # Check if already verified
            if user.get("account_status") == "active":
                return {
                    "success": True,
                    "already_verified": True,
                    "user_id": user["id"],
                    "message": "Account is already verified and active",
                }

            # Activate account
            user_updates = {
                "account_status": "active",
                "email_verified": True,
                "email_verified_at": datetime.now(timezone.utc),
                "email_verification_token": None,
                "email_verification_expires_at": None,
                "updated_at": datetime.now(timezone.utc),
            }

            db.update_user(user["id"], user_updates)

            logger.info(
                f"[Registration] Email verified and account activated for user {user['id']}"
            )

            # Get institution for welcome email
            institution = db.get_institution_by_id(user["institution_id"])
            institution_name = (
                institution["name"] if institution else "Course Record Updater"
            )

            # Send welcome email
            display_name = (
                f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            )
            welcome_sent = send_welcome_email(
                email=user["email"],
                user_name=display_name,
                institution_name=institution_name,
            )

            return {
                "success": True,
                "already_verified": False,
                "user_id": user["id"],
                "email": user["email"],
                "display_name": display_name,
                "institution_name": institution_name,
                "welcome_email_sent": welcome_sent,
                "message": "Email verified successfully! Your account is now active.",
            }

        except RegistrationError:
            # Re-raise registration errors
            raise
        except Exception as e:
            logger.error(f"[Registration] Failed to verify email: {e}")
            raise RegistrationError(f"Email verification failed: {str(e)}")

    @staticmethod
    def resend_verification_email(email: str) -> Dict[str, Any]:
        """
        Resend verification email for pending user

        Args:
            email: User's email address

        Returns:
            Dictionary with resend result

        Raises:
            RegistrationError: If resend fails
        """
        logger.info(
            f"[Registration] Resending verification email to {logger.sanitize(email)}"
        )

        try:
            # Find user by email
            user = db.get_user_by_email(email)
            if not user:
                raise RegistrationError("No account found with that email address")

            # Check if already verified
            if user.get("account_status") == "active":
                raise RegistrationError("Account is already verified and active")

            # Generate new verification token
            verification_token = secrets.token_urlsafe(32)
            verification_expires_at = datetime.now(timezone.utc) + timedelta(
                hours=VERIFICATION_TOKEN_EXPIRY_HOURS
            )

            # Update user with new token
            user_updates = {
                "email_verification_token": verification_token,
                "email_verification_expires_at": verification_expires_at,
                "updated_at": datetime.now(timezone.utc),
            }

            db.update_user(user["id"], user_updates)

            # Send verification email
            display_name = (
                f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            )
            email_sent = send_verification_email(
                email=email,
                verification_token=verification_token,
                user_name=display_name,
            )

            if not email_sent:
                logger.warning(
                    f"[Registration] Failed to resend verification email to {logger.sanitize(email)}"
                )

            return {
                "success": True,
                "email_sent": email_sent,
                "verification_expires_at": verification_expires_at,
                "message": "Verification email sent! Please check your email.",
            }

        except RegistrationError:
            # Re-raise registration errors
            raise
        except Exception as e:
            logger.error(f"[Registration] Failed to resend verification email: {e}")
            raise RegistrationError(f"Failed to resend verification email: {str(e)}")

    @staticmethod
    def get_registration_status(email: str) -> Dict[str, Any]:
        """
        Get registration status for an email address

        Args:
            email: Email address to check

        Returns:
            Dictionary with registration status
        """
        try:
            user = db.get_user_by_email(email)

            if not user:
                return RegistrationService._build_not_registered_status()

            # Determine status based on account state
            return RegistrationService._build_user_status(user)

        except Exception as e:
            logger.error(f"[Registration] Failed to get registration status: {e}")
            return RegistrationService._build_error_status(str(e))

    @staticmethod
    def _build_not_registered_status() -> Dict[str, Any]:
        """Build status response for non-existent user."""
        return {
            "exists": False,
            "status": "not_registered",
            "message": "No account found with this email address",
        }

    @staticmethod
    def _build_user_status(user: Dict[str, Any]) -> Dict[str, Any]:
        """Build status response for existing user based on account state."""
        account_status = user.get("account_status", "unknown")
        email_verified = user.get("email_verified", False)

        if account_status == "active" and email_verified:
            return RegistrationService._build_active_status(user)
        elif account_status == "pending":
            return RegistrationService._build_pending_status(user, email_verified)
        else:
            return RegistrationService._build_other_status(user, account_status)

    @staticmethod
    def _build_active_status(user: Dict[str, Any]) -> Dict[str, Any]:
        """Build status response for active, verified user."""
        return {
            "exists": True,
            "status": "active",
            "user_id": user["id"],
            "role": user.get("role"),
            "institution_id": user.get("institution_id"),
            "message": "Account is active and verified",
        }

    @staticmethod
    def _build_pending_status(
        user: Dict[str, Any], email_verified: bool
    ) -> Dict[str, Any]:
        """Build status response for pending verification user."""
        is_expired = RegistrationService._check_verification_expired(user)

        return {
            "exists": True,
            "status": "pending_verification",
            "user_id": user["id"],
            "email_verified": email_verified,
            "verification_expired": is_expired,
            "message": "Account exists but email verification is pending",
        }

    @staticmethod
    def _check_verification_expired(user: Dict[str, Any]) -> bool:
        """Check if email verification has expired."""
        verification_expires_at = user.get("email_verification_expires_at")

        if not verification_expires_at:
            return False

        # Parse string datetime if needed
        if isinstance(verification_expires_at, str):
            try:
                verification_expires_at = datetime.fromisoformat(
                    verification_expires_at.replace("Z", "+00:00")
                )
            except ValueError:
                return False

        return verification_expires_at < datetime.now(timezone.utc)

    @staticmethod
    def _build_other_status(
        user: Dict[str, Any], account_status: str
    ) -> Dict[str, Any]:
        """Build status response for other account states."""
        return {
            "exists": True,
            "status": account_status,
            "user_id": user["id"],
            "message": f"Account status: {account_status}",
        }

    @staticmethod
    def _build_error_status(error_message: str) -> Dict[str, Any]:
        """Build status response for error cases."""
        return {
            "exists": False,
            "status": "error",
            "message": f"Failed to check registration status: {error_message}",
        }


# Convenience functions for easy import
def register_institution_admin(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    institution_name: str,
    website_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function for institution admin registration"""
    return RegistrationService.register_institution_admin(
        email, password, first_name, last_name, institution_name, website_url
    )


def verify_email(verification_token: str) -> Dict[str, Any]:
    """Convenience function for email verification"""
    return RegistrationService.verify_email(verification_token)


def resend_verification_email(email: str) -> Dict[str, Any]:
    """Convenience function for resending verification email"""
    return RegistrationService.resend_verification_email(email)


def get_registration_status(email: str) -> Dict[str, Any]:
    """Convenience function for getting registration status"""
    return RegistrationService.get_registration_status(email)
