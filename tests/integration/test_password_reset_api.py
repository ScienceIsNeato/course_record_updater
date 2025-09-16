"""
Integration tests for password reset API endpoints

Tests the complete password reset flow through the API endpoints.
"""

import json
from unittest.mock import patch

import pytest

from app import app


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"

    with app.test_client() as client:
        with app.app_context():
            yield client


class TestPasswordResetAPI:
    """Test password reset API endpoints"""

    @patch("password_reset_service.PasswordResetService")
    def test_forgot_password_success(self, mock_service, client):
        """Test successful password reset request"""
        # Setup
        mock_service.request_password_reset.return_value = {
            "request_success": True,
            "message": "Reset email sent",
        }

        # Execute
        response = client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": "test@example.com"}),
            content_type="application/json",
        )

        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["request_success"] is True
        mock_service.request_password_reset.assert_called_once_with("test@example.com")

    def test_forgot_password_missing_email(self, client):
        """Test password reset request with missing email"""
        # Execute - send JSON with other field but no email
        response = client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"other_field": "value"}),
            content_type="application/json",
        )

        # Verify
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Missing required field: email" in data["error"]

    def test_forgot_password_no_json(self, client):
        """Test password reset request with no JSON data"""
        # Execute
        response = client.post("/api/auth/forgot-password")

        # Verify - Flask returns 500 for unsupported media type, not 400
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Password reset request failed" in data["error"]

    @patch("password_reset_service.PasswordResetService")
    def test_forgot_password_rate_limit(self, mock_service, client):
        """Test password reset request with rate limit exceeded"""
        # Setup
        mock_service.request_password_reset.side_effect = Exception("Too many requests")

        # Execute
        response = client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": "test@example.com"}),
            content_type="application/json",
        )

        # Verify
        assert response.status_code == 429
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Too many" in data["error"]

    @patch("password_reset_service.PasswordResetService")
    def test_forgot_password_development_restriction(self, mock_service, client):
        """Test password reset request with development email restriction"""
        # Setup
        mock_service.request_password_reset.side_effect = Exception(
            "restricted in development"
        )

        # Execute
        response = client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": "test@cei.edu"}),
            content_type="application/json",
        )

        # Verify
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "restricted in development" in data["error"]


class TestResetPasswordAPI:
    """Test password reset completion API"""

    @patch("password_reset_service.PasswordResetService")
    def test_reset_password_success(self, mock_service, client):
        """Test successful password reset"""
        # Setup
        mock_service.reset_password.return_value = {
            "reset_success": True,
            "email": "test@example.com",
            "message": "Password reset successfully",
        }

        # Execute
        response = client.post(
            "/api/auth/reset-password",
            data=json.dumps(
                {"reset_token": "valid-token", "new_password": "NewSecurePassword123!"}
            ),
            content_type="application/json",
        )

        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["reset_success"] is True
        assert data["email"] == "test@example.com"
        mock_service.reset_password.assert_called_once_with(
            reset_token="valid-token", new_password="NewSecurePassword123!"
        )

    def test_reset_password_missing_fields(self, client):
        """Test password reset with missing required fields"""
        # Execute - missing new_password
        response = client.post(
            "/api/auth/reset-password",
            data=json.dumps({"reset_token": "token"}),
            content_type="application/json",
        )

        # Verify
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Missing required field: new_password" in data["error"]

    @patch("password_reset_service.PasswordResetService")
    def test_reset_password_invalid_token(self, mock_service, client):
        """Test password reset with invalid token"""
        # Setup
        mock_service.reset_password.side_effect = Exception("Invalid token")

        # Execute
        response = client.post(
            "/api/auth/reset-password",
            data=json.dumps(
                {"reset_token": "invalid-token", "new_password": "NewPassword123!"}
            ),
            content_type="application/json",
        )

        # Verify
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Invalid token" in data["error"]

    @patch("password_reset_service.PasswordResetService")
    def test_reset_password_validation_failed(self, mock_service, client):
        """Test password reset with validation failure"""
        # Setup
        mock_service.reset_password.side_effect = Exception("validation failed")

        # Execute
        response = client.post(
            "/api/auth/reset-password",
            data=json.dumps({"reset_token": "valid-token", "new_password": "weak"}),
            content_type="application/json",
        )

        # Verify
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "validation failed" in data["error"]


class TestValidateResetTokenAPI:
    """Test reset token validation API"""

    @patch("password_reset_service.PasswordResetService")
    def test_validate_token_valid(self, mock_service, client):
        """Test validation of valid token"""
        # Setup
        mock_service.validate_reset_token.return_value = {
            "valid": True,
            "email": "test@example.com",
            "message": "Token is valid",
        }

        # Execute
        response = client.get("/api/auth/validate-reset-token/valid-token")

        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["valid"] is True
        assert data["email"] == "test@example.com"
        mock_service.validate_reset_token.assert_called_once_with("valid-token")

    @patch("password_reset_service.PasswordResetService")
    def test_validate_token_invalid(self, mock_service, client):
        """Test validation of invalid token"""
        # Setup
        mock_service.validate_reset_token.return_value = {
            "valid": False,
            "message": "Token is invalid",
        }

        # Execute
        response = client.get("/api/auth/validate-reset-token/invalid-token")

        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["valid"] is False
        assert "invalid" in data["message"]

    @patch("password_reset_service.PasswordResetService")
    def test_validate_token_error(self, mock_service, client):
        """Test token validation with service error"""
        # Setup
        mock_service.validate_reset_token.side_effect = Exception("Service error")

        # Execute
        response = client.get("/api/auth/validate-reset-token/error-token")

        # Verify
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Failed to validate reset token" in data["error"]


class TestResetStatusAPI:
    """Test reset status API"""

    @patch("password_reset_service.PasswordResetService")
    def test_reset_status_pending(self, mock_service, client):
        """Test getting reset status when reset is pending"""
        # Setup
        mock_service.get_reset_status.return_value = {
            "has_pending_reset": True,
            "expires_at": "2024-12-31T23:59:59",
            "message": "Reset is pending",
        }

        # Execute
        response = client.get("/api/auth/reset-status/test@example.com")

        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["has_pending_reset"] is True
        assert data["expires_at"] == "2024-12-31T23:59:59"
        mock_service.get_reset_status.assert_called_once_with("test@example.com")

    @patch("password_reset_service.PasswordResetService")
    def test_reset_status_no_pending(self, mock_service, client):
        """Test getting reset status when no reset is pending"""
        # Setup
        mock_service.get_reset_status.return_value = {
            "has_pending_reset": False,
            "message": "No pending reset",
        }

        # Execute
        response = client.get("/api/auth/reset-status/test@example.com")

        # Verify
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["has_pending_reset"] is False
        assert "No pending" in data["message"]

    @patch("password_reset_service.PasswordResetService")
    def test_reset_status_error(self, mock_service, client):
        """Test reset status with service error"""
        # Setup
        mock_service.get_reset_status.side_effect = Exception("Service error")

        # Execute
        response = client.get("/api/auth/reset-status/test@example.com")

        # Verify
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Failed to get reset status" in data["error"]


class TestPasswordResetFlowIntegration:
    """Integration tests for complete password reset flow"""

    @patch("password_reset_service.PasswordResetService")
    def test_complete_password_reset_flow(self, mock_service, client):
        """Test complete password reset flow: request -> validate -> reset"""

        # Step 1: Request password reset
        mock_service.request_password_reset.return_value = {
            "request_success": True,
            "message": "Reset email sent",
        }

        request_response = client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": "test@example.com"}),
            content_type="application/json",
        )

        assert request_response.status_code == 200
        request_data = json.loads(request_response.data)
        assert request_data["request_success"] is True

        # Step 2: Validate reset token
        mock_service.validate_reset_token.return_value = {
            "valid": True,
            "email": "test@example.com",
            "message": "Token is valid",
        }

        validate_response = client.get("/api/auth/validate-reset-token/valid-token")
        assert validate_response.status_code == 200
        validate_data = json.loads(validate_response.data)
        assert validate_data["valid"] is True

        # Step 3: Complete password reset
        mock_service.reset_password.return_value = {
            "reset_success": True,
            "email": "test@example.com",
            "message": "Password reset successfully",
        }

        reset_response = client.post(
            "/api/auth/reset-password",
            data=json.dumps(
                {"reset_token": "valid-token", "new_password": "NewSecurePassword123!"}
            ),
            content_type="application/json",
        )

        assert reset_response.status_code == 200
        reset_data = json.loads(reset_response.data)
        assert reset_data["reset_success"] is True

        # Verify all service methods were called
        mock_service.request_password_reset.assert_called_once()
        mock_service.validate_reset_token.assert_called_once()
        mock_service.reset_password.assert_called_once()

    @patch("password_reset_service.PasswordResetService")
    def test_password_reset_with_status_check(self, mock_service, client):
        """Test password reset flow with status checking"""

        # Step 1: Check initial status (no pending reset)
        mock_service.get_reset_status.return_value = {
            "has_pending_reset": False,
            "message": "No pending reset",
        }

        status_response1 = client.get("/api/auth/reset-status/test@example.com")
        assert status_response1.status_code == 200
        status_data1 = json.loads(status_response1.data)
        assert status_data1["has_pending_reset"] is False

        # Step 2: Request password reset
        mock_service.request_password_reset.return_value = {
            "request_success": True,
            "message": "Reset email sent",
        }

        request_response = client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": "test@example.com"}),
            content_type="application/json",
        )

        assert request_response.status_code == 200

        # Step 3: Check status again (now pending)
        mock_service.get_reset_status.return_value = {
            "has_pending_reset": True,
            "expires_at": "2024-12-31T23:59:59",
            "message": "Reset is pending",
        }

        status_response2 = client.get("/api/auth/reset-status/test@example.com")
        assert status_response2.status_code == 200
        status_data2 = json.loads(status_response2.data)
        assert status_data2["has_pending_reset"] is True

        # Verify service calls
        assert mock_service.get_reset_status.call_count == 2
        mock_service.request_password_reset.assert_called_once()
